import socket
import threading
import sys

class ChatServer:
    def __init__(self, server_name):
        self.server_name = server_name
        self.users = {}  # Diccionario para almacenar usuarios: {username: (ip, port)}
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.server_address = ("", 12345)

    def start(self):
        self.server_socket.bind(self.server_address)
        print(f"Servidor '{self.server_name}' iniciado en {self.get_ip()}:12345")
        self.listen_for_messages()

    def listen_for_messages(self):
        while True:
            try:
                data, address = self.server_socket.recvfrom(1024)
                message = data.decode()
                print(f"Mensaje recibido de {address}: {message}")
                if message.startswith("REGISTER"):
                    self.register_user(message, address)
                elif message.startswith("RESOLVE"):
                    self.resolve_user(message, address)
                elif message.startswith("DISCOVER"):
                    response = f"{self.server_name}"
                    self.server_socket.sendto(response.encode(), address)
            except Exception as e:
                print(f"Error en el servidor: {e}")

    def register_user(self, message, address):
        _, username = message.split(" ")
        if username in self.users:
            response = f"ERROR El usuario '{username}' ya está registrado."
        else:
            self.users[username] = address
            response = f"OK Usuario '{username}' registrado con éxito."
        self.server_socket.sendto(response.encode(), address)

    def resolve_user(self, message, address):
        _, username = message.split(" ")
        if username in self.users:
            user_address = self.users[username]
            response = f"OK {user_address[0]} {user_address[1]}"
        else:
            response = f"ERROR El usuario '{username}' no existe."
        self.server_socket.sendto(response.encode(), address)

    def get_ip(self):
        return socket.gethostbyname(socket.gethostname())


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Uso: python server.py <NOMBRE_DEL_SERVIDOR>")
        sys.exit(1)
    server_name = sys.argv[1]
    server = ChatServer(server_name)
    server.start()
