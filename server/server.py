import socket
import threading
import sys
import json

class ChatServer:
    def __init__(self, server_name):
        self.server_name = server_name
        self.users = {}
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.server_address = ("", 12345)

    def start(self):
        try:
            with open("users.json", "r") as file:
                self.users = json.loads(file.read())
        except:
            pass

        self.server_socket.bind(self.server_address)
        print(f"Server '{self.server_name}' started on {self.get_ip()}:12345")
        self.listen_for_messages()

    def listen_for_messages(self):
        while True:
            try:
                data, client_address = self.server_socket.recvfrom(1024)
                message = data.decode()
                print(f"Message from {client_address}: {message}")
                if message.startswith("REGISTER "):
                    self.register_user(message, client_address)
                elif message.startswith("RESOLVE "):
                    self.resolve_user(message, client_address)
                elif message.startswith("DISCOVER"):
                    response = f"{self.server_name}"
                    self.server_socket.sendto(response.encode(), client_address)
            except Exception as e:
                print(f"Server error: {e}")

    def register_user(self, message, client_address):
        _, username, port = message.split(" ")

        new_user = username not in self.users.keys()
        self.users[username] = (client_address[0], int(port))
        
        if new_user:
            response = f"OK User {username} listening on {client_address[0]}:{port}. Successfully registered."
            
            with open("users.json", "w") as file:
                file.write(json.dumps(self.users))
        else:
            response = f"OK User {username} listening on {client_address[0]}:{port}. Successfully updated."

        print(response)
        self.server_socket.sendto(response.encode(), client_address)

    def resolve_user(self, message, address):
        _, username = message.split(" ")
        if username in self.users:
            user_address = self.users[username]
            response = f"OK {user_address[0]} {user_address[1]}"
        else:
            response = f"ERROR User '{username}' does not exist."

        print(response)
        self.server_socket.sendto(response.encode(), address)

    def get_ip(self):
        return socket.gethostbyname(socket.gethostname())


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Use: python server.py <SERVER_NAME>")
        sys.exit(1)
    server_name = sys.argv[1]
    server = ChatServer(server_name)
    server.start()
