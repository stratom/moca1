#!/bin/bash

read -p "🗑️ Nombre del cliente a eliminar (COSTUMER): " COSTUMER
ENV_FILE=".env_${COSTUMER}"

if [ -f "$ENV_FILE" ]; then
  echo "🛑 Deteniendo y eliminando contenedor..."
  env $(cat "$ENV_FILE" | xargs) docker compose -f ../docker-compose.yml down

  rm "$ENV_FILE"
  echo "✅ Archivo $ENV_FILE eliminado."
else
  echo "⚠️ Archivo $ENV_FILE no encontrado."
fi

if grep -q "COSTUMER=${COSTUMER}" ${COSTUMER} 2>/dev/null; then
  rm ${COSTUMER}
  echo "🧹 Archivo costumer_oracle eliminado."
fi
