#!/bin/bash

echo "Iniciando el proceso de construcción y despliegue..."

# Detener y eliminar contenedores existentes
echo "Deteniendo y eliminando contenedores existentes..."
docker-compose down -v --remove-orphans
if [ $? -ne 0 ]; then
    echo "Error al detener los contenedores."
    read -p "Presiona Enter para continuar..."
    exit 1
fi

# Construir las imágenes desde los Dockerfiles
echo "Construyendo las imágenes..."
docker build -t router-image -f Dockerfile.router .
if [ $? -ne 0 ]; then
    echo "Error al construir la imagen del router."
    read -p "Presiona Enter para continuar..."
    exit 1
fi

docker build -t server-image -f Dockerfile.server .
if [ $? -ne 0 ]; then
    echo "Error al construir la imagen del servidor."
    read -p "Presiona Enter para continuar..."
    exit 1
fi

docker build -t client-image -f Dockerfile.client .
if [ $? -ne 0 ]; then
    echo "Error al construir la imagen del cliente."
    read -p "Presiona Enter para continuar..."
    exit 1
fi

# Levantar los servicios con Docker Compose
echo "Levantando los servicios definidos en docker-compose.yml..."
docker-compose up -d --build
if [ $? -ne 0 ]; then
    echo "Error al levantar los servicios con Docker Compose."
    read -p "Presiona Enter para continuar..."
    exit 1
fi

echo "Proceso completado exitosamente. Los servicios están corriendo."
read -p "Presiona Enter para continuar..."