import socket
import threading
import sys

class ChatClient:
    def __init__(self):
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.server_address = None
        self.username = None
        self.running = True

    def discover_servers(self):
        self.client_socket.settimeout(3)
        servers = []
        broadcast_address = ("<broadcast>", 12345)
        self.client_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        try:
            self.client_socket.sendto("DISCOVER".encode(), broadcast_address)
            while True:
                data, address = self.client_socket.recvfrom(1024)
                server_name = data.decode()
                servers.append((server_name, address[0]))
        except socket.timeout:
            pass
        return servers

    def connect_to_server(self, server_ip):
        self.server_address = (server_ip, 12345)

    def register_or_login(self):
        while True:
            username = input("Introduce tu nombre de usuario único: ").strip()
            if " " in username:
                print("El nombre de usuario no puede contener espacios.")
                continue
            self.client_socket.sendto(f"REGISTER {username}".encode(), self.server_address)
            response, _ = self.client_socket.recvfrom(1024)
            if response.decode().startswith("OK"):
                print(response.decode())
                self.username = username
                break
            else:
                print(response.decode())

    def send_message(self):
        while self.running:
            message = input()
            if message.startswith("@"):
                try:
                    recipient, content = message[1:].split(" ", 1)
                    self.client_socket.sendto(f"RESOLVE {recipient}".encode(), self.server_address)
                    response, _ = self.client_socket.recvfrom(1024)
                    if response.decode().startswith("OK"):
                        _, ip, port = response.decode().split()
                        recipient_address = (ip, int(port))
                        self.client_socket.sendto(f"{self.username}: {content}".encode(), recipient_address)
                    else:
                        print(response.decode())
                except ValueError:
                    print("Formato incorrecto. Usa: @destinatario mensaje")
            elif message.lower() == "salir":
                self.running = False
                print("Saliendo del chat...")
                break
            else:
                print("Mensaje no válido. Usa: @destinatario mensaje")

    def listen_for_messages(self):
        while self.running:
            try:
                data, address = self.client_socket.recvfrom(1024)
                print(data.decode())
            except:
                break

    def start(self):
        print("Buscando servidores disponibles...")
        servers = self.discover_servers()
        if not servers:
            print("No se encontraron servidores.")
            return
        print("Servidores encontrados:")
        for i, (name, ip) in enumerate(servers):
            print(f"{i + 1}. {name} ({ip})")
        choice = int(input("Selecciona un servidor por número: ")) - 1
        self.connect_to_server(servers[choice][1])
        self.register_or_login()

        threading.Thread(target=self.listen_for_messages, daemon=True).start()
        self.send_message()


if __name__ == "__main__":
    client = ChatClient()
    client.start()
