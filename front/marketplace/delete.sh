#!/bin/bash

read -p "🗑️ Nombre del cliente a eliminar (COSTUMER): " COSTUMER

ENV_FILE=".env_${COSTUMER}"
CLIENT_FILE="${COSTUMER}.txt"
OLD_CLIENT_FILE="${COSTUMER}"        # Archivo sin extensión
CLIENT_DIR="client_${COSTUMER}"

if [ -d "$CLIENT_DIR" ]; then
  echo "🛑 Deteniendo y eliminando contenedor de $COSTUMER..."
  cd "$CLIENT_DIR" || exit 1
  docker compose down
  cd ..
  rm -rf "$CLIENT_DIR"
  echo "✅ Carpeta $CLIENT_DIR eliminada."
else
  echo "⚠️ No se encontró la carpeta $CLIENT_DIR"
fi

if [ -f "$ENV_FILE" ]; then
  rm "$ENV_FILE"
  echo "🧹 Archivo $ENV_FILE eliminado."
fi

if [ -f "$CLIENT_FILE" ]; then
  rm "$CLIENT_FILE"
  echo "🧹 Archivo $CLIENT_FILE eliminado."
fi

if [ -f "$OLD_CLIENT_FILE" ]; then
  rm "$OLD_CLIENT_FILE"
  echo "🧹 Archivo $OLD_CLIENT_FILE eliminado."
fi

