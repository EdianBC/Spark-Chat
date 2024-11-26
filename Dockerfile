FROM python:3.9-slim

WORKDIR /app

COPY ./src/server/server.py ./server.py
COPY ./src/client/client.py ./client.py

CMD ["python", "server.py"]
