#!/bin/bash
chmod 600 /app/backend/oracle-db.key
REMOTE_USER=opc
REMOTE_HOST=10.0.0.3
SSH_KEY=/app/backend/oracle-db.key
REMOTE_DIR=/home/opc/moca1/dbai

# Leer COSTUMER local desde contenedor


# Obtener el nombre del cliente leyendo el archivo marketplace/<cliente>

MARKETPLACE_DIR="/app/marketplace"
echo "[DIAG] Buscando archivos de cliente en $MARKETPLACE_DIR..."
client=""
for f in "$MARKETPLACE_DIR"/*; do
  if [[ -f "$f" ]]; then
    val=$(grep COSTUMER "$f" | cut -d'=' -f2)
    if [[ -n "$val" ]]; then
      client="$val"
      echo "[DIAG] Archivo de cliente detectado: $f"
      echo "[DIAG] Cliente detectado: $client"
      break
    fi
  fi
done

if [[ -z "$client" ]]; then
  echo "❌ [ERROR] No se encontró variable COSTUMER en ningún archivo de $MARKETPLACE_DIR"
  exit 2
fi

echo "🚀 Conectando por SSH para ejecutar delete.sh en remoto con client=$client..."

if [[ -z "$client" ]]; then
  echo "❌ [ERROR] Variable client está vacía. Abortando ejecución SSH."
  exit 10
fi

echo "🚀 Conectando por SSH para ejecutar delete.sh en remoto con client=$client..."

ssh -i "$SSH_KEY" -o StrictHostKeyChecking=no "$REMOTE_USER@$REMOTE_HOST" bash <<EOF
set -e
CLIENT_DIR=client_$client
echo '[DIAG REMOTO] Cliente recibido: $client'
cd $REMOTE_DIR
if [[ -z "$client" ]]; then
  echo '❌ [ERROR REMOTO] Variable client está vacía en remoto. Abortando.'
  exit 11
fi

echo '[DIAG REMOTO] Buscando directorio ' "\$CLIENT_DIR"
if [[ -d "\$CLIENT_DIR" ]]; then
  cd "\$CLIENT_DIR"
  echo '[DIAG REMOTO] Entrando a ' "\$CLIENT_DIR"
else
  echo '❌ [ERROR REMOTO] No existe el directorio ' "\$CLIENT_DIR"
  exit 4
fi
ENV_FILE=.env_$client
echo '[DIAG REMOTO] Buscando archivo de entorno ' "\$ENV_FILE"
if [[ ! -f "\$ENV_FILE" ]]; then
  echo '❌ [ERROR REMOTO] No se encontró ' "\$ENV_FILE"
  exit 5
fi
set -a
source "\$ENV_FILE"
set +a
echo '[DIAG REMOTO] Variables de entorno cargadas.'
echo '🛑 Deteniendo y eliminando contenedor ' "\$CONTAINER_NAME"
docker compose down || true
cd ..
echo '🗑️ Borrando directorio ' "\$CLIENT_DIR" ' y archivo ' "\$ENV_FILE"
sudo rm -rf "\$CLIENT_DIR"
sudo rm -f "\$ENV_FILE"
echo '✅ Limpieza completa.'
EOF