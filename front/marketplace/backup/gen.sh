#!/bin/bash

read -p "🔤 Nombre del cliente (COSTUMER): " COSTUMER
read -p "🌐 Puerto frontend (PORT_FRONTEND): " PORT_FRONTEND

ENV_FILE=".env_${COSTUMER}"
echo "✅ Generando archivo $ENV_FILE..."

echo "COSTUMER=${COSTUMER}" > "$ENV_FILE"
echo "PORT_FRONTEND=${PORT_FRONTEND}" >> "$ENV_FILE"

echo "✅ Listo. Variables guardadas en:"
echo " - $ENV_FILE"
echo " - ${COSTUMER}"

echo "COSTUMER=${COSTUMER}" > ${COSTUMER}
echo "PORT_FRONTEND=${PORT_FRONTEND}" >> ${COSTUMER}

echo "🚀 Levantando contenedor con Docker Compose..."
env $(cat "$ENV_FILE" | xargs) docker compose -f ../docker-compose.yml up -d


