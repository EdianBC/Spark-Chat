import socket
import threading

HOST = '0.0.0.0'  # Escucha en todas las interfaces
PORT = 5000
clients = []

def handle_client(conn, addr):
    print(f"Conexión desde {addr}")
    while True:
        try:
            msg = conn.recv(1024).decode('utf-8')
            if not msg:
                break
            print(f"{addr}: {msg}")
            # Reenvía el mensaje a todos los demás clientes
            for client in clients:
                if client != conn:
                    client.send(f"{addr}: {msg}".encode('utf-8'))
        except:
            break
    conn.close()
    clients.remove(conn)

server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.bind((HOST, PORT))
server.listen()
print(f"Servidor escuchando en {HOST}:{PORT}")

while True:
    conn, addr = server.accept()
    clients.append(conn)
    threading.Thread(target=handle_client, args=(conn, addr)).start()
