import socket
import threading
import os
import json

class ChatClient:
    def __init__(self):
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.message_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.message_socket.settimeout(3)
        self.message_socket.bind(("", 0))

        self.server_address = None
        self.server_name = None
        self.username = None
        self.running = True
        self.actual_chat = None
        self.interlocutor = None

    def read_response(self, socket):
        response = ''
        while True:
            part, _ = socket.recvfrom(1024)
            response += part.decode()
            if response.endswith('\r\n') or len(part) < 1024:
                break
        return response

    def send_command(self, command) -> str:
        self.client_socket.sendto(f"{command}".encode(), self.server_address)
        return self.read_response(self.client_socket)
        

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

    def connect_to_server(self, server):
        self.server_address = (server[1], 12345)
        self.server_name = server[0]

    def register_or_login(self):
        while True:
            username = input("Please write your username: ").strip()
            if " " in username:
                print("Username cannot contain spaces.")
                continue
            message_ip, message_port = self.message_socket.getsockname()
            # self.client_socket.sendto(f"REGISTER {username} {message_ip} {message_port}".encode(), self.server_address)
            # response, _ = self.client_socket.recvfrom(1024)
            response = self.send_command(f"REGISTER {username} {message_port}")
            if response.startswith("OK"):
                # print(response.decode())
                self.username = username
                break
            else:
                print(response)

    def run(self):

        os.system('cls' if os.name == 'nt' else 'clear')
        print(f"Welcome to ✨Spark Chat✨{self.username}! Use '@recipient' to send private messages (nudes not allowed yet!).")

        while self.running:
            message = input()
         
            if message.startswith("@") and not " " in message:
                self.interlocutor = message[1:]
                self.actual_chat = self.load_chat(self.interlocutor)
                self.private_chat()

            elif message.lower() == "/quit":
                self.running = False
                print("Goodbye...")
                break

            else:
                print("Invalid command. Use '@recipient' to send private messages or '/quit' to exit.")

    def private_chat(self):
        # self.client_socket.sendto(f"RESOLVE {recipient}".encode(), self.server_address)
        # response, _ = self.client_socket.recvfrom(1024)
        response = self.send_command(f"RESOLVE {self.interlocutor}")
        if response.startswith("OK"):
            _, ip, port = response.split()
            recipient_address = (ip, int(port))
        else:
            print(response)
            return
        
        os.system('cls' if os.name == 'nt' else 'clear')
        print(f"Starting private chat with {self.interlocutor}...")
        self.print_previous_chat()

        while True:
            message = input()
            if message.lower() == "/back":

                with open(f"chats/{self.server_name}-{self.username}-{self.interlocutor}.json", "w") as file:
                    file.write(json.dumps(self.actual_chat))
                
                self.actual_chat = None
                self.interlocutor = None

                os.system('cls' if os.name == 'nt' else 'clear')
                print(f"Welcome to ✨Spark Chat✨ {self.username}! Use '@recipient' to send private messages (nudes not allowed yet!).")
                break

            try:
                self.actual_chat.append(message)
                self.message_socket.sendto(f"{self.username}: {message}".encode(), recipient_address)
            except Exception as e:
                print(f"Error sending message: {e}")

    def print_previous_chat(self):
        
        for message in self.actual_chat:
            print(message)

    def load_chat(self, interlocutor): 
        os.makedirs("chats", exist_ok=True)
        try:
            with open(f"chats/{self.server_name}-{self.username}-{interlocutor}.json", "r") as file:
                chat = json.loads(file.read())
        except:
            chat = []
        return chat

    def listen_for_messages(self):
        while self.running:
            try:
                # data, address = self.message_socket.recvfrom(1024)
                # print(data.decode())
                message = self.read_response(self.message_socket)
                if message:
                    sender = message.split(":")[0]

                    if sender == self.interlocutor:
                        self.actual_chat.append(message)
                        print(message)
                    else:
                        chat = self.load_chat(sender)
                        chat.append(message)
                        with open(f"chats/{self.server_name}-{self.username}-{sender}.json", "w") as file:
                            file.write(json.dumps(chat))
                        
            except:
                # break
                pass


    def start(self):
        print("Searching for available servers...")
        servers = self.discover_servers()
        if not servers:
            print("No servers were found :(")
            return
        print("Servers found:")
        for i, (name, ip) in enumerate(servers):
            print(f"{i + 1}. {name} ({ip})")
        choice = int(input("Select a server by number: ")) - 1
        self.connect_to_server(servers[choice])
        
        self.register_or_login()

        threading.Thread(target=self.listen_for_messages, daemon=True).start()
        self.run()


if __name__ == "__main__":
    client = ChatClient()
    client.start()
