#!/bin/bash

read -p "Container name (e.g. dbai0): " CONTAINER_NAME
read -p "External port (e.g. 1522): " PORT
read -s -p "Password: " ORACLE_PWD
echo

# Path to volume with the most free space
VOLUME_PATH="/home/opc/moca1/opt/vector-ai/${CONTAINER_NAME}/volume"
mkdir -p "$VOLUME_PATH"
sudo cp -r /home/opc/moca1/opt/vector-ai/source "$VOLUME_PATH"
sudo chmod 777 "$VOLUME_PATH/source"
DIR_DEL="/home/opc/moca1/opt/vector-ai/${CONTAINER_NAME}"

# Create .env file
cat <<EOF > .env
CONTAINER_NAME=${CONTAINER_NAME}
PORT=${PORT}
VOLUME_PATH=${VOLUME_PATH}/source
ORACLE_PWD=${ORACLE_PWD}
DIR_DEL=${DIR_DEL}
EOF

# Launch container
docker compose up -d

echo "⏳ Waiting for the database to be ready..."

# Wait until the log says "DATABASE IS READY TO USE!"
until docker logs "$CONTAINER_NAME" 2>&1 | grep -q "DATABASE IS READY TO USE"; do
  sleep 5
done

echo "✅ Database is ready. Running embed.py..."
python3 /home/opc/moca/dbai/embed.py

