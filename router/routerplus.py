import socket
import threading

# Configuración de puerto y direcciones
PORT = 12345

# Datos para la red de clientes (client_network)
CLIENT_IP = "192.168.2.254"
CLIENT_BROADCAST = "192.168.2.255"

# Datos para la red de servidores (server_network)
SERVER_IP = "192.168.3.254"
SERVER_BROADCAST = "192.168.3.255"

def relay_from_client():
    """
    Escucha en la red de clientes y reenvía a la red de servidores.
    """

    while True:
        try:
            # Socket para recibir en client_network
            recv_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            recv_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            recv_sock.bind((CLIENT_IP, PORT))

            # Socket para enviar en server_network (habilitar broadcast)
            send_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            send_sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

            print(f"[CLIENT->SERVER] Escuchando en {CLIENT_IP}:{PORT} y reenviando a {SERVER_BROADCAST}:{PORT}")
            while True:
                data, addr = recv_sock.recvfrom(4096)
                if not addr[0].startswith('172'):
                    print(f"[CLIENT->SERVER] Recibido de {addr}: {data}")
                    send_sock.sendto(data, (SERVER_BROADCAST, PORT))
        except ValueError as e:
            break
        except Exception as e:
            pass

def relay_from_server():
    """
    Escucha en la red de servidores y reenvía a la red de clientes.
    """

    while True:
        try:
            # Socket para recibir en server_network
            recv_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            recv_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            recv_sock.bind((SERVER_IP, PORT))

            # Socket para enviar en client_network (habilitar broadcast)
            send_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            send_sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)


            print(f"[SERVER->CLIENT] Escuchando en {SERVER_IP}:{PORT} y reenviando a {CLIENT_BROADCAST}:{PORT}")
            while True:
                data, addr = recv_sock.recvfrom(4096)
                if not addr[0].startswith('172'):
                    print(f"[SERVER->CLIENT] Recibido de {addr}: {data}")
                    send_sock.sendto(data, (CLIENT_BROADCAST, PORT))
        except ValueError as e:
            break
        except Exception as e:
            pass

if __name__ == "__main__":
    # Crear hilos para ambas direcciones de reenvío
    thread_client = threading.Thread(target=relay_from_client, daemon=True)
    thread_server = threading.Thread(target=relay_from_server, daemon=True)

    thread_client.start()
    thread_server.start()

    thread_client.join()
    thread_server.join()
