import socket
import threading
import os
import json
import time

class ChatClient:
    def __init__(self):
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.client_socket.settimeout(3)
        self.message_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.message_socket.settimeout(3)
        self.message_socket.bind(("", 0))

        self.server_address = None
        self.server_name = None
        self.username = None
        self.running = True
        self.interlocutor = None
        self.update_chat_flag = False
        self.file_lock = threading.Lock()
        self.pending_list = []


    def read_response(self, socket):
        response = ''
        address = None

        while True:
            part, address = socket.recvfrom(1024)
            response += part.decode()
            if response.endswith('\r\n') or len(part) < 1024:
                break
        return response, address

    def send_command(self, command) -> str:
        self.client_socket.sendto(f"{command}".encode(), self.server_address)
        response, _ = self.read_response(self.client_socket)
        return response
        
    def send_message(self, message, address):
        self.message_socket.sendto(message.encode(), address)

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


    def print_chat(self, chat):
        for message in chat:
            if message["sender"] == self.username:
                print(message["text"])
            else:
                print(f"{message['sender']}: {message['text']}")
            message["readed"] = True
        self.save_chat(chat, self.interlocutor)

    def update_chat(self, interlocutor):
        while self.update_chat_flag:
            changed_something = False
            chat = self.load_chat(interlocutor)
            for message in chat:
                if not message["readed"]:
                    changed_something = True
                    if message["sender"] == self.username:
                        print(message["text"])
                    else:
                        print(f"{message['sender']}: {message['text']}")
                    message["readed"] = True
            if changed_something:
                self.save_chat(chat, interlocutor)

    def load_chat(self, interlocutor): 
        os.makedirs("chats", exist_ok=True)
        chat = []
        try:
            with self.file_lock:
                with open(f"chats/{self.server_name}-{self.username}-{interlocutor}.json", "r") as file:
                    chat = json.loads(file.read())
        except Exception as e:
            # print(f'Problem loading chat: {e}')
            pass
        # print(len(chat))
        return chat
    
    def save_chat(self, chat, interlocutor): 
        os.makedirs("chats", exist_ok=True) 
        try:
            with self.file_lock:
                with open(f"chats/{self.server_name}-{self.username}-{interlocutor}.json", "w") as file:
                    file.write(json.dumps(chat))
        except Exception as e:
            print(f"EROOOOOOOOOOOR: {e}")

    def listen_for_messages(self):
        while self.running:
            try:
                # data, address = self.message_socket.recvfrom(1024)
                # print(data.decode())
                message, address = self.read_response(self.message_socket)
                if message.startswith("MESSAGE"):
                    _, sender, text = message.split(" ", 2)
                    chat = self.load_chat(sender)
                    chat.append({"sender":sender, "text":text, "readed":False})
                    # with self.file_lock:
                    #     with open(f"chats/{self.server_name}-{self.username}-{sender}.json", "w") as file:
                    #         file.write(json.dumps(chat))
                    self.save_chat(chat, sender)
                elif message.startswith("PING"):
                    self.message_socket.sendto("PONG".encode(), address)
            except Exception as e:
                # print(f"Error in the listening: {e}")
                pass

    def is_user_online(self, address):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                sock.settimeout(0.5)
                sock_port = sock.getsockname()[1]
                sock.sendto(f"PING".encode(), address)
                response, _ = sock.recvfrom(1024)
                return response.decode() == "PONG"
        except socket.timeout:
            # print(f"Timeout while checking if user is online at {address}")
            pass
        except Exception as e:
            # print(f"Error checking if user is online at {address}: {e}")
            pass
        return False

    def send_pending_messages(self):
        while self.running:
            try:
                if self.pending_list:
                    for user, message in self.pending_list:
                        response = self.send_command(f"RESOLVE {user}")
                        address = None
                        if response.startswith("OK"):
                            _, ip, port = response.split()
                            address = (ip, int(port))
                        else:
                            continue
                        if self.is_user_online(address):
                            self.send_message(message, address)
                            self.pending_list.remove((user, message))
                time.sleep(1)
            except Exception as e:
                print(f"Error sending pending messages: {e}")
                pass

#region UI

    def run_ui(self):
        status = self.search_servers_ui()
        if status != "OK":
            return
        time.sleep(1)

        status = self.register_or_login_ui()
        if status != "OK":
            return
        time.sleep(1)

        threading.Thread(target=self.listen_for_messages, daemon=True).start()
        threading.Thread(target=self.send_pending_messages, daemon=True).start()
        
        status = "MAIN"

        while True:
            if status == "MAIN":
                status = self.main_menu_ui()

            elif status == "PV":
                status = self.private_chat_ui()

            elif status == "QUIT":
                print("Farewell my beloved...")
                break


    def search_servers_ui(self):
        try:
            os.system('cls' if os.name == 'nt' else 'clear')
            while True:
                print("Searching for available servers...")
                servers = self.discover_servers()
                if not servers:
                    print("No servers were found :(")
                    choice = input("Do you want to search again? (y/n): ")
                    if choice.lower() != "y":
                        return "NOT OK"
                else:
                    print("Servers found:")
                    for i, (name, ip) in enumerate(servers):
                        print(f"{i + 1}. {name} ({ip})")
                    choice = int(input("Select a server by number: ")) - 1
                    self.connect_to_server(servers[choice])
                    print(f"Connected to {servers[choice][0]}")
                    return "OK"
        except Exception as e:
            print(f"An error ocurred while seacrching servers: {e}")
            return "NOT OK"


    def register_or_login_ui(self):
        try:
            os.system('cls' if os.name == 'nt' else 'clear')
            while True:
                username = input("Please write your username: ").strip()
                if " " in username or not username or '-' in username:
                    print("Username cannot contain spaces, hyphens or be empty.")
                    continue
                message_ip, message_port = self.message_socket.getsockname()
                response = self.send_command(f"REGISTER {username} {message_port}")
                if response.startswith("OK"):
                    self.username = username
                    return "OK"
                else:
                    print(response)
                    return "NOT OK"
        except Exception as e:
            print(f"An error ocurred while registering: {e}")
            return "NOT OK"

    
    def main_menu_ui(self):
        os.system('cls' if os.name == 'nt' else 'clear')
        print(f"Welcome, {self.username}, to ✨Spark Chat✨! Available commands:\n*Use '@recipient' to enter a private chat (nudes not allowed yet!).\n*Use '/quit' to exit.")

        # print_chats()

        while True:
            command = input()
         
            if command.startswith("@") and not " " in command:
                self.interlocutor = command[1:]
                return "PV"

            elif command == "/quit":
                return "QUIT"

            else:
                print("Invalid command. Use '@recipient' to send private messages or '/quit' to exit.")

    def private_chat_ui(self): 
        try:   
            os.system('cls' if os.name == 'nt' else 'clear')
            print(f"Starting private chat with {self.interlocutor}. Type '/back' to return to the main menu.")

            response = self.send_command(f"RESOLVE {self.interlocutor}")
            if response.startswith("OK"):
                _, ip, port = response.split()
                recipient_address = (ip, int(port))
            else:
                print(response)
                return "MAIN"
            
            self.print_chat(self.load_chat(self.interlocutor))
    
            self.update_chat_flag = True
            threading.Thread(target=self.update_chat, args=(self.interlocutor,), daemon=True).start()

            while True:
                message = input()

                if message.lower() == "/back":
                    self.interlocutor = None
                    self.update_chat_flag = False
                    return "MAIN"
                
                elif message:
                    chat = self.load_chat(self.interlocutor)
                    chat.append({"sender":self.username, "text":message, "readed":True})
                    self.save_chat(chat, self.interlocutor)

                    if self.is_user_online(recipient_address):
                        self.message_socket.sendto(f"MESSAGE {self.username} {message}".encode(), recipient_address)
                    else:
                        response = self.send_command(f"RESOLVE {self.interlocutor}")
                        if response.startswith("OK"):
                            _, ip, port = response.split()
                            recipient_address = (ip, int(port))
                            if self.is_user_online(recipient_address):
                                self.message_socket.sendto(f"MESSAGE {self.username} {message}".encode(), recipient_address)
                            else:
                                self.pending_list.append((self.interlocutor, f"MESSAGE {self.username} {message}"))
                        # print(f"User {self.interlocutor} is offline. Message will be sent when user is online.")
                
        except Exception as e:
            print(f"Error in chat: {e}")
            self.update_chat_flag = False
            time.sleep(3)
            raise e
            return "MAIN"

#endregion


if __name__ == "__main__":
    client = ChatClient()
    client.run_ui()


"""
TODO:
- [x] Separate ui from backend
- [x] Change to TCP at least for sending messages
- [x] Implement service to send messages that failed to be sent
- [x] Dockerize
- [x] Implement what happens if the server is down (user search for new server)
- [x] Update to sqlite
"""