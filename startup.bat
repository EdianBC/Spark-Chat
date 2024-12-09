@echo off
echo Iniciando el proceso de construcción y despliegue...

REM Detener y eliminar contenedores existentes
echo Deteniendo y eliminando contenedores existentes...
docker-compose down -v --remove-orphans
if %ERRORLEVEL% neq 0 (
    echo Error al detener los contenedores.
    pause
    exit /b 1
)

REM Construir las imágenes desde los Dockerfiles
echo Construyendo las imágenes...
docker build -t router-image -f Dockerfile.router .
if %ERRORLEVEL% neq 0 (
    echo Error al construir la imagen del router.
    pause
    exit /b 1
)

docker build -t server-image -f Dockerfile.server .
if %ERRORLEVEL% neq 0 (
    echo Error al construir la imagen del servidor.
    pause
    exit /b 1
)

docker build -t client-image -f Dockerfile.client .
if %ERRORLEVEL% neq 0 (
    echo Error al construir la imagen del cliente.
    pause
    exit /b 1
)

REM Levantar los servicios con Docker Compose
echo Levantando los servicios definidos en docker-compose.yml...
docker-compose up -d --build
if %ERRORLEVEL% neq 0 (
    echo Error al levantar los servicios con Docker Compose.
    pause
    exit /b 1
)

echo Proceso completado exitosamente. Los servicios están corriendo.
pause
