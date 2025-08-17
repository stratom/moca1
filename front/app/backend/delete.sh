#!/bin/bash

# Load DIR_DEL from .env
DIR_DEL=$(grep DIR_DEL .env | awk -F '=' '{print $2}')

# Stop and remove container
docker compose down

# Delete full directory and .env
sudo rm -rf "$DIR_DEL"
sudo rm -f .env

