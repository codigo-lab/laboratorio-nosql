from fastapi import FastAPI, Request, HTTPException
from pydantic import BaseModel
from pymongo import MongoClient
from bson import ObjectId
import os
import requests

app = FastAPI(title="API NoSQL (vulnerable)")

# Conexion con MongoDB
mongo = MongoClient(os.getenv("MONGO_HOST", "mongo"), 27017)
db = mongo[os.getenv("MONGO_DATABASE", "tienda")]

# Modelo de pedidos
class Pedido(BaseModel):
    producto: str
    cantidad: int


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


# LOGIN VULNERABLE A NoSQL INJECTION
@app.post("/login_mongo")
async def login(req: Request):
    data = await req.json()

    user = db.usuarios.find_one(
        {
            "username": data.get("username"),
            "password": data.get("password")
        },
        {"_id": 0}
    )

    if user:
        return {"msg": "ok"}

    raise HTTPException(status_code=401, detail="Bad creds")


# BUSQUEDA EN ELASTICSEARCH
@app.get("/articulos")
def art_search(q: str = "*"):
    host = os.getenv("ELASTIC_HOST", "elasticsearch")

    return requests.get(
        f"http://{host}:9200/articulos/_search",
        params={"q": q},
        timeout=10
    ).json()