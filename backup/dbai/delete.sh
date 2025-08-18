#!/bin/bash
chmod 600 /app/backend/oracle-db.key
REMOTE_USER=opc
REMOTE_HOST=10.0.0.6
SSH_KEY=/app/backend/oracle-db.key
REMOTE_DIR=/home/opc/moca/dbai

# Leer COSTUMER local desde contenedor
MARKETPLACE_DIR="/app/marketplace"
FILE=$(ls $MARKETPLACE_DIR | head -n 1)
COSTUMER=$(grep COSTUMER "$MARKETPLACE_DIR/$FILE" | cut -d'=' -f2)

echo "🚀 Conectando por SSH para ejecutar delete.sh en remoto con COSTUMER=$COSTUMER..."

ssh -i "$SSH_KEY" -o StrictHostKeyChecking=no "$REMOTE_USER@$REMOTE_HOST" bash -c "'
  set -e
  export COSTUMER=${COSTUMER}
  cd $REMOTE_DIR

  echo \"📦 Cargando variables de entorno...\"
  ENV_FILE=.env_\$COSTUMER
  if [[ ! -f \$ENV_FILE ]]; then
    echo \"❌ ERROR: No se encontró \$ENV_FILE\"
    exit 1
  fi

  set -a
  source \$ENV_FILE
  set +a

  echo \"🛑 Deteniendo y eliminando contenedor \$CONTAINER_NAME...\"
  docker compose down || true

  echo \"🗑️ Borrando directorio \$DIR_DEL y archivo \$ENV_FILE...\"
  sudo rm -rf \$DIR_DEL
  sudo rm -f \$ENV_FILE

  echo \"✅ Limpieza completa.\"
'"

