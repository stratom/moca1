#!/bin/bash

read -p "🔤 Nombre del cliente (COSTUMER): " COSTUMER
read -p "🌐 Puerto frontend (PORT_FRONTEND): " PORT_FRONTEND

BASE_DIR="$(pwd)"  # /home/opc/moca1/front/marketplace
ENV_FILE=".env_${COSTUMER}"
CLIENT_FILE="${COSTUMER}"
CLIENT_DIR="${BASE_DIR}/client_${COSTUMER}"  # ⬅️ cambio aquí

echo "✅ Generando archivo $ENV_FILE..."

# Guardar variables en archivos dentro del mismo directorio
echo "COSTUMER=${COSTUMER}" > "$ENV_FILE"
echo "PORT_FRONTEND=${PORT_FRONTEND}" >> "$ENV_FILE"

echo "COSTUMER=${COSTUMER}" > "$CLIENT_FILE"
echo "PORT_FRONTEND=${PORT_FRONTEND}" >> "$CLIENT_FILE"

# Verifica que no haya conflicto
if [ -f "$CLIENT_DIR" ]; then
  echo "❌ Error: ya existe un archivo con nombre '${CLIENT_DIR}', no se puede crear el directorio."
  exit 1
fi

# Crear carpeta del cliente
mkdir -p "$CLIENT_DIR"

# Copiar docker-compose.yml y .env dentro de la carpeta
cp ../docker-compose.yml "$CLIENT_DIR/docker-compose.yml"
cp "$ENV_FILE" "$CLIENT_DIR/.env"

echo "✅ Archivos copiados en $CLIENT_DIR"

# Entrar a la carpeta del cliente
cd "$CLIENT_DIR" || exit 1

# 🚀 Levantar el contenedor
echo "🚀 Levantando contenedor con Docker Compose..."
docker compose up -d

