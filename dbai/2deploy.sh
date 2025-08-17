#!/bin/bash

#read -p "Container name (e.g. dbai0): " CONTAINER_NAME
#read -p "External port (e.g. 1522): " PORT
#read -s -p "Password: " ORACLE_PWD
#echo

# Path to volume with the most free space
#IP=10.0.0.6
#VOLUME_PATH="/opt/vector-ai/${CONTAINER_NAME}/volume"
#mkdir -p "$VOLUME_PATH"
#sudo cp -r /opt/vector-ai/source "$VOLUME_PATH"
#sudo chmod 777 "$VOLUME_PATH/source"
#DIR_DEL="/opt/vector-ai/${CONTAINER_NAME}"
#sudo chmod 777 "$DIR_DEL"


# Create .env file
#cat <<EOF > .env
#CONTAINER_NAME=${CONTAINER_NAME}
#PORT=${PORT}
#VOLUME_PATH=${VOLUME_PATH}
#ORACLE_PWD=${ORACLE_PWD}
#DIR_DEL=${DIR_DEL}
#IP=${IP}
#EOF

sudo chown -R 54321:54321 /opt/vector-ai/dbai3/volume/oradata
sudo chmod -R 775 /opt/vector-ai/dbai3/volume/oradata

# Launch container
docker compose up -d

echo "⏳ Waiting for the database to be ready..."

# Wait until the log says "DATABASE IS READY TO USE!"
until docker logs "$CONTAINER_NAME" 2>&1 | grep -q "DATABASE IS READY TO USE"; do
  sleep 5
done

echo "✅ Database is ready. execute embeddings"
#python3 /home/opc/moca/dbai/embed.py

