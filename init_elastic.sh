#!/bin/sh
set -eu

ES_URL="${ES_URL:-http://localhost:9200}"

# Crear el indice de articulos si no existe
if [ "$(curl -s -o /dev/null -w '%{http_code}' "$ES_URL/articulos")" = "404" ]; then
    curl -fsS -X PUT "$ES_URL/articulos" \
        -H "Content-Type: application/json" \
        -d '{
          "mappings": {
            "properties": {
              "titulo": {"type": "text"},
              "categoria": {"type": "keyword"},
              "precio": {"type": "float"}
            }
          }
        }'
fi

# Insertar articulos ficticios
curl -fsS -X PUT "$ES_URL/articulos/_doc/1?refresh=wait_for" \
    -H "Content-Type: application/json" \
    -d '{"titulo":"Portatil","categoria":"informatica","precio":850}'

curl -fsS -X PUT "$ES_URL/articulos/_doc/2?refresh=wait_for" \
    -H "Content-Type: application/json" \
    -d '{"titulo":"Teclado","categoria":"perifericos","precio":35}'

curl -fsS -X PUT "$ES_URL/articulos/_doc/3?refresh=wait_for" \
    -H "Content-Type: application/json" \
    -d '{"titulo":"Raton","categoria":"perifericos","precio":20}'