import socket
import threading

SERVER_IP = 'server'  # Nombre del contenedor Docker para el servidor
SERVER_PORT = 5000

def receive_messages(sock):
    while True:
        try:
            msg = sock.recv(1024).decode('utf-8')
            if msg:
                print(msg)
        except:
            print("Conexión cerrada")
            break

client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client.connect((SERVER_IP, SERVER_PORT))

threading.Thread(target=receive_messages, args=(client,)).start()

print("Conectado al servidor.")
print("Escribe mensajes para enviarlos:")

while True:
    msg = input()
    if msg.lower() == 'exit':
        break
    client.send(msg.encode('utf-8'))

client.close()
