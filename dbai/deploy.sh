#!/bin/bash

# Verificar que COSTUMER esté definida
if [[ -z "$COSTUMER" ]]; then
  echo "❌ ERROR: COSTUMER no está definido"
  exit 1
fi

ENV_FILE=".env_${COSTUMER}"

# Validar existencia del archivo .env específico
if [[ ! -f "$ENV_FILE" ]]; then
  echo "❌ ERROR: No se encontró $ENV_FILE"
  exit 1
fi

# Cargar variables de entorno desde archivo específico
set -a
source "$ENV_FILE"
set +a

# Validar que todas las variables estén presentes
if [[ -z "$CONTAINER_NAME" || -z "$PORT" || -z "$VOLUME_PATH" || -z "$ORACLE_PWD" ]]; then
  echo "❌ ERROR: Faltan variables en el archivo $ENV_FILE"
  exit 1
fi

# Crear directorio para oradata si no existe
echo "📁 Creando $VOLUME_PATH si no existe..."
sudo mkdir -p "$VOLUME_PATH"
sudo chown -R 54321:54321 "$VOLUME_PATH"
sudo chmod -R 775 "$VOLUME_PATH"

# Lanzar contenedor
echo "🐳 Levantando contenedor Docker..."
docker compose up -d

echo "⏳ Esperando a que la base de datos esté lista..."

# Esperar a que esté lista
until docker logs "$CONTAINER_NAME" 2>&1 | grep -q "DATABASE IS READY TO USE"; do
  sleep 5
done

echo "✅ La base de datos está lista. Ejecutando embeddings..."
#python3 /home/opc/moca/dbai/embed.py

