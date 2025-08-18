#!/bin/bash
chmod 600 /app/backend/oracle-db.key
REMOTE_USER=opc
REMOTE_HOST=10.0.0.6
SSH_KEY=/app/backend/oracle-db.key
REMOTE_DIR=/home/opc/moca/dbai

# Leer COSTUMER local desde contenedor
COSTUMER=$(grep COSTUMER /app/marketplace/oracle | cut -d'=' -f2)
CONTAINER_NAME="frontendai-${COSTUMER}"

echo "🚀 Conectando por SSH para copiar PDFs desde contenedor al host y ejecutar embed.py para COSTUMER=$COSTUMER..."

ssh -i "$SSH_KEY" "$REMOTE_USER@$REMOTE_HOST" bash -c "'\
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

  echo \"🐳 Copiando PDFs desde contenedor $CONTAINER_NAME a \$VOLUME_PATH...\"
  mkdir -p \$VOLUME_PATH

  sudo docker cp $CONTAINER_NAME:/home/opc/moca1/opt/vector-ai/\$CONTAINER_NAME/volume/source/. \$VOLUME_PATH/

  echo \"📁 Archivos copiados. Ejecutando embed.py...\"
  python3 embed.py "$COSTUMER"
'"

