# Auditoría de seguridad en MongoDB y Elasticsearch con FastAPI


## 1. Descripción del proyecto

Este repositorio contiene un laboratorio de seguridad orientado al análisis de vulnerabilidades en bases de datos NoSQL y servicios de búsqueda.

El entorno integra MongoDB 7, Elasticsearch 7.17.10 y una API desarrollada con FastAPI sobre Python 3.11. La infraestructura se despliega mediante Docker Compose para facilitar su reproducción y la comparación entre diferentes configuraciones de seguridad.

El trabajo contempla dos escenarios: una configuración inicial deliberadamente vulnerable y una configuración reforzada mediante controles de autenticación, autorización, validación de entradas y reducción de la superficie de exposición.


## 2. Alcance del laboratorio

Las pruebas se realizarán exclusivamente sobre un entorno local y con datos ficticios.

La configuración inicial deshabilita los mecanismos de autenticación de MongoDB y Elasticsearch con fines de evaluación. Los puertos publicados se restringen a la interfaz local `127.0.0.1`.

Este entorno no está diseñado para su despliegue en producción.


## 3. Requisitos del entorno

- Windows 11 con WSL 2.
- Docker Desktop.
- Docker Compose.
- curl para las pruebas HTTP.


## 4. Estructura del repositorio

El laboratorio se organiza a partir de un archivo Docker Compose que define los servicios y sus conexiones. La aplicación FastAPI se mantiene en un directorio independiente, mientras que los scripts de inicialización permiten preparar los datos de prueba.

laboratorio-nosql/
├── docker-compose.yml
├── init_mongo.js
├── init_elastic.sh
├── README.md
└── fastapi-app/
    ├── Dockerfile
    ├── requirements.txt
    └── main.py

**Descripción de los archivos:**

- docker-compose.yml: configura MongoDB, Elasticsearch, FastAPI y Caddy, incluyendo redes, puertos, variables de entorno y dependencias.
- init_mongo.js: inicializa la base de datos `tienda` con usuarios y pedidos ficticios.
- init_elastic.sh: crea el índice `articulos` e incorpora los documentos de prueba.
- fastapi-app/Dockerfile: construye la imagen de FastAPI sobre Python 3.11.
- fastapi-app/requirements.txt: contiene las dependencias Python, incluida SlowAPI.
- fastapi-app/main.py: implementa los endpoints, la validación de entradas, la limitación de peticiones y el registro de alertas.
- Caddyfile: configura el proxy inverso y el acceso HTTPS mediante TLS local.
- .env: almacena las credenciales de conexión a MongoDB.
- .gitignore: evita incorporar al repositorio credenciales, respaldos y archivos temporales.
- baseline/: conserva las versiones iniciales vulnerables utilizadas para comparar ataques y defensas.


## 5. Despliegue e inicialización

### 5.1. Configuración inicial de MongoDB y credenciales

Antes de iniciar el laboratorio, se debe crear un archivo `.env` en la raíz del proyecto con las credenciales que utilizará FastAPI para conectarse a MongoDB:

MONGO_USER=app_tienda
MONGO_PASSWORD=CAMBIAR_POR_UNA_CONTRASENA_SEGURA


La contraseña debe sustituirse por una propia y coincidir con la asignada al usuario de MongoDB. El archivo `.env` está excluido del repositorio mediante `.gitignore`.

El usuario `app_tienda` debe disponer únicamente del rol `readWrite` sobre la base de datos `tienda`.

**Inicialización de MongoDB**

En una instalación nueva, se inicia primero el contenedor de MongoDB:

docker compose up -d mongo

Esto permite preparar las cuentas de acceso antes de arrancar FastAPI.

Para crear el usuario administrador inicial, se accede a MongoDB desde el propio contenedor:

docker compose exec mongo mongosh admin

**Creación del usuario administrador**

En la consola de mongosh, ejecutar:
db.createUser({
    user: "lab_admin",
    pwd: passwordPrompt(),
    roles: [{ role: "userAdminAnyDatabase", db: "admin" }]


**Creación del usuario de la aplicación**

Una vez creado el administrador, salir de `mongosh`:

exit

Conectarse de nuevo a MongoDB utilizando la cuenta administradora:

docker compose exec mongo mongosh tienda --username lab_admin --authenticationDatabase admin --password


Introducir la contraseña de `lab_admin` y crear el usuario de la aplicación:

db.createUser({
    user: "app_tienda",
    pwd: passwordPrompt(),
    roles: [{ role: "readWrite", db: "tienda" }]
})

La contraseña introducida debe coincidir con `MONGO_PASSWORD` del archivo `.env`. El rol `readWrite` limita sus permisos de lectura y escritura a la base de datos `tienda`.

**Verificación de permisos**

Salir de `mongosh` y comprobar el acceso con la cuenta de la aplicación:

docker compose exec mongo mongosh tienda --username app_tienda --authenticationDatabase tienda --password --quiet --eval "printjson(db.pedidos.findOne())"


El resultado esperado es un documento de la colección `pedidos`.

Esta configuración se realiza únicamente en instalaciones nuevas, sin usuarios MongoDB previamente creados. Tras completarla, continuar con el apartado 5.2

### 5.2. Arranque de los servicios

Desde PowerShell, situarse en el directorio raíz del proyecto y ejecutar:

docker compose up -d --build

El comando descarga las imágenes necesarias, construye la aplicación FastAPI e inicia los tres servicios definidos en `docker-compose.yml`.

Para comprobar el estado de los contenedores:

docker compose ps


Los servicios `mongo`, `elasticsearch` y `fastapi-app` deben aparecer con estado `Up`.

**Puertos locales:**

- MongoDB: `127.0.0.1:27017`
- Elasticsearch: `127.0.0.1:9200`
- FastAPI: `127.0.0.1:8000`

### 5.3. Inicialización de los datos

**MongoDB**

En el primer arranque, MongoDB ejecuta automáticamente `init_mongo.js`, siempre que el directorio de datos esté vacío.

El script crea los siguientes datos de prueba en la base de datos `tienda`:

- Colección `usuarios`: dos usuarios ficticios.
- Colección `pedidos`: tres registros.

**Elasticsearch**

La carga de artículos se realiza manualmente desde PowerShell, en el directorio raíz del proyecto:

(Get-Content .\init_elastic.sh -Raw) -replace "r", "" | docker compose exec -T elasticsearch sh


El script crea el índice `articulos` e incorpora tres documentos de prueba.

La inicialización se considera correcta cuando Elasticsearch confirma la creación del índice y de los documentos sin errores.


### 5.4. Comprobaciones iniciales (smoke tests)

Con los tres servicios en ejecución y los datos cargados, verificar los endpoints desde PowerShell.

**Consulta de pedidos (MongoDB):**

curl.exe http://localhost:8000/pedidos


**Autenticación con credenciales de prueba:**

Invoke-RestMethod -Method Post -Uri "http://localhost:8000/login_mongo" -ContentType "application/json" -Body '{"username":"alice","password":"clave123"}'


**Búsqueda de artículos (Elasticsearch):**

curl.exe "http://localhost:8000/articulos"



## 6. Pruebas de seguridad (baseline inseguro)

Comandos ejecutados desde PowerShell para reproducir las vulnerabilidades de la configuración inicial. Todas las pruebas se realizan exclusivamente en el laboratorio local.

### 6.1. MongoDB

**NoSQL Injection en el login:**

Invoke-RestMethod -Method Post -Uri "http://localhost:8000/login_mongo" -ContentType "application/json" -Body '{"username":"alice","password":{"$ne":"x"}}'


**Lectura sin autenticación:**

docker compose exec mongo mongosh tienda --quiet --eval "printjson(db.pedidos.findOne())"


**Escritura sin autenticación:**

docker compose exec mongo mongosh tienda --quiet --eval "printjson(db.pruebas_seguridad.insertOne({tipo:'escritura_anonima',origen:'laboratorio'}))"



### 6.2. Elasticsearch

**Enumeración de índices:**

curl.exe "http://localhost:9200/_cat/indices?v"


**Consulta anónima de documentos:**

curl.exe "http://localhost:9200/articulos/_search?q=*"

**Eliminación del índice de prueba:**

curl.exe -X DELETE "http://localhost:9200/articulos"




## 7. Configuración de seguridad

Se han aplicado las siguientes modificaciones:

- **MongoDB:** autorización habilitada mediante `--auth` y usuario `app_tienda` con rol `readWrite` sobre `tienda`.
- **FastAPI:** validación estricta de credenciales mediante Pydantic.
- **Elasticsearch:** búsquedas mediante `match`, longitud máxima de 80 caracteres y paginación limitada.
- **Red:** puertos 27017 y 9200 sin publicar en el host. FastAPI permanece accesible en `127.0.0.1:8000`.
- **Credenciales:** archivo `.env` local, excluido del repositorio mediante `.gitignore`.


### 7.1. Aplicar y comprobar la configuración

docker compose up -d --build
docker compose ps


**Comprobaciones de seguridad:**

# MongoDB a través de FastAPI
curl.exe -k -i https://localhost:8443/pedidos

# Límite de paginación
curl.exe -k -i "https://localhost:8443/articulos?tamano=100"

# Puerto Elasticsearch no publicado
curl.exe -i http://localhost:9200/


### 7.2. Verificación CRUD de pedidos

Las cuatro operaciones se comprueban mediante HTTPS, utilizando un pedido ficticio que se elimina al finalizar.

Ejecutar en PowerShell, por orden:

# CREATE: crear un pedido y guardar su identificador
$id = (curl.exe -k -s -X POST "https://localhost:8443/pedidos" -H "Content-Type: application/json" -d '{\"producto\":\"PruebaCRUD\",\"cantidad\":1}' | ConvertFrom-Json).id
"Pedido creado: $id"

# READ: consultar los pedidos
curl.exe -k -i "https://localhost:8443/pedidos"

# UPDATE: modificar el pedido de prueba
curl.exe -k -i -X PUT "https://localhost:8443/pedidos/$id" -H "Content-Type: application/json" -d '{\"producto\":\"PruebaCRUD\",\"cantidad\":2}'

# DELETE: eliminar el pedido de prueba
curl.exe -k -i -X DELETE "https://localhost:8443/pedidos/$id"

# Comprobar que permanecen los pedidos originales
curl.exe -k -i "https://localhost:8443/pedidos"


El identificador `$id` se obtiene automáticamente para evitar introducir uno fijo.


## 8. Endurecimiento adicional

### 8.1. Limitación de peticiones

Se utiliza `slowapi` para limitar las solicitudes por dirección IP:

- `/login_mongo`: 5 peticiones por minuto.
- `/articulos`: 10 peticiones por minuto.

**Prueba del límite de autenticación (PowerShell):**

1..7 | ForEach-Object {
    curl.exe -k -s -o NUL -w "%{http_code}" -X POST "https://localhost:8443/login_mongo" -H "Content-Type: application/json" -d '{\"username\":\"alice\",\"password\":\"incorrecta\"}'
}


Las respuestas esperadas son `401` y, al superar el límite, `429`.

### 8.2. Cifrado HTTPS

Caddy actúa como proxy inverso mediante el archivo `Caddyfile`, con TLS local (`tls internal`). Solo se publica `127.0.0.1:8443`; los puertos de FastAPI, MongoDB y Elasticsearch permanecen internos.

curl.exe -k -i https://localhost:8443/pedidos


El primer comando debe devolver `200 OK` y el segundo debe fallar al intentar conectar.

La opción `-k` omite la comprobación de confianza del certificado local; debe utilizarse únicamente para estas pruebas.

### 8.3. Copia de seguridad de MongoDB

Generar una copia comprimida, introduciendo la contraseña de `app_tienda` cuando se solicite:

docker compose exec mongo mongodump --db tienda --username app_tienda --authenticationDatabase tienda --archive=/tmp/tienda-backup.archive.gz --gzip


Copiar el respaldo al equipo anfitrión:

docker compose cp mongo:/tmp/tienda-backup.archive.gz .\tienda-backup.archive.gz


Comprobar el archivo sin restaurar los datos:

docker compose exec mongo mongorestore --archive=/tmp/tienda-backup.archive.gz --gzip --dryRun --verbose --username app_tienda --authenticationDatabase tienda


El respaldo se excluye del repositorio mediante `.gitignore`.

### 8.4. Monitorización y alertas

FastAPI registra advertencias por autenticaciones fallidas (`ALERTA_LOGIN_FALLIDO`) y límites superados (`ALERTA_RATE_LIMIT`).

Consultar las alertas:

docker compose logs --no-log-prefix fastapi-app 2>&1 | Select-String "ALERTA_"


Los registros permiten identificar eventos asociados a `/login_mongo` y `/articulos`. Las alertas se conservan en los logs del contenedor.  



