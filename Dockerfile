FROM python:3.9-slim

WORKDIR /app

# Copiar todo el contenido de la carpeta 'src' dentro de la imagen
COPY src/ /app/

# CMD para ejecutar el servidor por defecto
CMD ["python", "server/server.py"]
