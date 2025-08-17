#!/bin/bash
chmod 600 /app/backend/oracle-db.key
REMOTE_USER=opc
REMOTE_HOST=10.0.0.6
SSH_KEY=/app/backend/oracle-db.key
REMOTE_DIR=/home/opc/moca/dbai

# Leer COSTUMER desde archivo local
COSTUMER=$(grep COSTUMER /app/marketplace/oracle | cut -d'=' -f2)

echo "🚀 Conectando y ejecutando deploy.sh remotamente..."

ssh -i "$SSH_KEY" -o StrictHostKeyChecking=no "$REMOTE_USER@$REMOTE_HOST" bash -c "'
  set -e
  export COSTUMER=${COSTUMER}
  cd $REMOTE_DIR
  bash deploy.sh
'"

