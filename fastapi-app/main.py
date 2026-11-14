from fastapi import FastAPI, Request, HTTPException, Query
from pydantic import BaseModel, StrictStr
from pymongo import MongoClient
from bson import ObjectId
import os
import requests
import logging
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

app = FastAPI(title="API NoSQL (vulnerable)")
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
logger_seguridad = logging.getLogger("uvicorn.error")

def alerta_limite(request: Request, exc: RateLimitExceeded):
    logger_seguridad.warning(
        "ALERTA_RATE_LIMIT ip=%s ruta=%s",
        request.client.host if request.client else "desconocida",
        request.url.path
    )
    return _rate_limit_exceeded_handler(request, exc)

app.add_exception_handler(RateLimitExceeded, alerta_limite)

# Conexion con MongoDB
mongo = MongoClient(
    host=os.getenv("MONGO_HOST", "mongo"),
    port=27017,
    username=os.environ["MONGO_USER"],
    password=os.environ["MONGO_PASSWORD"],
    authSource="tienda"
)
db = mongo[os.getenv("MONGO_DATABASE", "tienda")]

# Modelo de pedidos
class Pedido(BaseModel):
    producto: str
    cantidad: int

class Login(BaseModel):
    username: StrictStr
    password: StrictStr


# CONSULTAR PEDIDOS
@app.get("/pedidos")
def listar_pedidos():
    pedidos = list(db.pedidos.find())
    for pedido in pedidos:
        pedido["_id"] = str(pedido["_id"])
    return pedidos


# CREAR PEDIDO
@app.post("/pedidos")
def crear_pedido(pedido: Pedido):
    resultado = db.pedidos.insert_one(pedido.model_dump())
    return {"id": str(resultado.inserted_id)}


# ACTUALIZAR PEDIDO
@app.put("/pedidos/{pedido_id}")
def actualizar_pedido(pedido_id: str, pedido: Pedido):
    if not ObjectId.is_valid(pedido_id):
        raise HTTPException(status_code=400, detail="ID invalido")

    resultado = db.pedidos.update_one(
        {"_id": ObjectId(pedido_id)},
        {"$set": pedido.model_dump()}
    )

    if resultado.matched_count == 0:
        raise HTTPException(status_code=404, detail="Pedido no encontrado")

    return {"msg": "Pedido actualizado"}


# ELIMINAR PEDIDO
@app.delete("/pedidos/{pedido_id}")
def eliminar_pedido(pedido_id: str):
    if not ObjectId.is_valid(pedido_id):
        raise HTTPException(status_code=400, detail="ID invalido")

    resultado = db.pedidos.delete_one({"_id": ObjectId(pedido_id)})

    if resultado.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Pedido no encontrado")

    return {"msg": "Pedido eliminado"}


# LOGIN CON VALIDACION PYDANTIC
@app.post("/login_mongo")
@limiter.limit("5/minute")
async def login(request: Request, data: Login):
    user = db.usuarios.find_one(
        {
            "username": data.username,
            "password": data.password
        },
        {"_id": 0}
    )

    if user:
        return {"msg": "ok"}

    logger_seguridad.warning("ALERTA_LOGIN_FALLIDO usuario=%r", data.username)
    raise HTTPException(status_code=401, detail="Bad creds")


# BUSQUEDA CONTROLADA EN ELASTICSEARCH
@app.get("/articulos")
@limiter.limit("10/minute")
def art_search(
    request: Request,
    q: str = Query(default="", max_length=80),
    pagina: int = Query(default=1, ge=1, le=20),
    tamano: int = Query(default=10, ge=1, le=20)
):
    host = os.getenv("ELASTIC_HOST", "elasticsearch")

    termino = q.strip()

    consulta = (
        {"match": {"titulo": termino}}
        if termino else {"match_all": {}}
    )

    cuerpo = {
        "from": (pagina - 1) * tamano,
        "size": tamano,
        "query": consulta
    }

    respuesta = requests.post(
        f"http://{host}:9200/articulos/_search",
        json=cuerpo,
        timeout=10
    )

    respuesta.raise_for_status()
    return respuesta.json()