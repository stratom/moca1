## Script de embeddings: ejecuta el flujo de embedding para el COSTUMER seleccionado
#!/bin/bash
chmod 600 /app/backend/oracle-db.key
REMOTE_USER=opc
REMOTE_HOST=10.0.0.3
SSH_KEY=/app/backend/oracle-db.key
REMOTE_DIR=/home/opc/moca1/dbai
# Leer COSTUMER local desde contenedor
MARKETPLACE_DIR="/app/marketplace/"
if [ -d "$MARKETPLACE_DIR" ]; then
  FIRST_FILE=$(ls "$MARKETPLACE_DIR" | head -n 1)
  COSTUMER_FILE="$MARKETPLACE_DIR$FIRST_FILE"
else
  COSTUMER_FILE="/app/marketplace/oracle"
fi
if [ -f "$COSTUMER_FILE" ]; then
  COSTUMER=$(grep COSTUMER "$COSTUMER_FILE" | cut -d'=' -f2)
else
  COSTUMER="default"
fi
CONTAINER_NAME_DOCKER="frontendai-${COSTUMER}"
echo "COSTUMER: $COSTUMER"
echo "CONTAINER_NAME: $CONTAINER_NAME_DOCKER"

echo "🚀 Conectando por SSH para copiar PDFs desde contenedor al host y ejecutar embed.py para COSTUMER=$COSTUMER..."


ssh -i "$SSH_KEY" -o StrictHostKeyChecking=no "$REMOTE_USER@$REMOTE_HOST" bash -c "'
  set -e
  export COSTUMER=${COSTUMER}
  cd "$REMOTE_DIR"

  echo \"📦 Cargando variables de entorno...\"
  ENV_FILE=.env_\$COSTUMER
  echo \$ENV_FILE 
  if [[ ! -f \$ENV_FILE ]]; then
    echo \"❌ ERROR: No se encontró \$ENV_FILE\"
    exit 1
  fi

  set -a
  source \$ENV_FILE
  set +a
  echo "\$VOLUME_PATH"
  echo "\$CONTAINER_NAME"
  echo "\$CONTAINER_NAME_DOCKER"

  echo "Copiando PDFs desde contenedor $CONTAINER_NAME_DOCKER a \$VOLUME_PATH"
  mkdir -p \$VOLUME_PATH

    if ! sudo docker ps > /dev/null 2>&1; then
      echo "⚠️ No se puede conectar al daemon Docker. Intentando reparar..."
      sudo systemctl start docker
      sudo usermod -aG docker $REMOTE_USER
      echo "🔄 Docker iniciado y usuario agregado al grupo docker. Cierra sesión y vuelve a entrar si es necesario."
      if ! sudo docker ps > /dev/null 2>&1; then
        echo "❌ No se pudo reparar el acceso a Docker. Abortando embedding."
        exit 1
      fi
    fi

  echo "docker cp $CONTAINER_NAME_DOCKER:/home/opc/moca1/opt/vector-ai/$CONTAINER_NAME/volume/. $VOLUME_PATH/"
  docker cp $CONTAINER_NAME_DOCKER:/home/opc/moca1/opt/vector-ai/\$CONTAINER_NAME/volume/. \$VOLUME_PATH/
  #                     docker cp $CONTAINER_NAME:/opt/vector-ai/\$CONTAINER_NAME/volume/source/. \$VOLUME_PATH/

  echo \"📁 Archivos copiados. Ejecutando embed.py...\"
  python3.9 embed.py "$COSTUMER"
'"

