import socket
import threading
import os
import json
import time
import db_manager


class chat_client:
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
        self.file_lock = threading.Lock()
        self.pending_list = {}
        self.pending_lock = threading.Lock()

        self.contact_list = {}

        self.db = db_manager.user_db()


    def set_user(self, username):
        self.username = username
        self.db.set_db(username)
        self.run_background()


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
        try:
            self.client_socket.sendto(
                f"{command}".encode(), self.server_address)
            response, _ = self.read_response(self.client_socket)
            return response
        except Exception as e:
            return f"ERROR in communication with server: {e}"

    def send_message(self, recipient, message):

        _, sender, text = message.split(" ", 2) # Ok this is a parche, but it works

        if recipient == self.username:
            self.db.insert_new_message(self.username, recipient, text, True)
            return True

        try:
            address = self.contact_list.get(recipient)
            # print(f"Sending message to {recipient}")
            if not address:
                address = self.resolve_user(recipient)

            if self.is_user_online(address):
                # print("User is online")
                self.db.insert_new_message(self.username, recipient, text, True)
                self.message_socket.sendto(message.encode(), address)
                return True
            else:
                # print("User is offline")
                address = self.resolve_user(recipient)
                if address:
                    if self.is_user_online(address):
                        # print("User is online2")
                        self.db.insert_new_message(self.username, recipient, text, True)
                        self.message_socket.sendto(message.encode(), address)
                        return True
                    else:
                        # print("User is still offline")
                        return False
                else:
                    # print("Error resolving user")
                    return False
        except Exception as e:
            print(f"ERROR sending message: {e}")

    def add_to_pending_list(self, recipient, message):
        with self.pending_lock:
            if recipient in self.pending_list.keys():
                self.pending_list[recipient].append(message)
            else:
                self.pending_list[recipient] = [message]

    def resolve_user(self, username):
        response = self.send_command(f"RESOLVE {username}")
        if response.startswith("OK"):
            _, ip, port = response.split()
            self.contact_list[username] = (ip, int(port))
            return (ip, int(port))
        else:
            return None

    def discover_servers(self):
        self.client_socket.settimeout(3)
        servers = []
        broadcast_address = ("<broadcast>", 12345)
        self.client_socket.setsockopt(
            socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        try:
            self.client_socket.sendto("DISCOVER".encode(), broadcast_address)
            while True:
                data, address = self.client_socket.recvfrom(1024)
                server_name = data.decode()
                servers.append((server_name, address[0]))
        except socket.timeout:
            pass

        if len(servers) == 0: #Parchecito uwu
            try:
                self.client_socket.sendto("DISCOVER".encode(), ("192.168.3.2", 12345))
                while True:
                    data, address = self.client_socket.recvfrom(1024)
                    server_name = data.decode()
                    servers.append((server_name, address[0]))
            except socket.timeout:
                pass
        return servers

    def connect_to_server(self, server):
        try:
            self.server_address = (server[1], 12345)
            self.server_name = server[0]
        except Exception as e:
            return f"ERROR connecting with server: {e}"


    def load_chat(self, interlocutor):
        # os.makedirs("chats", exist_ok=True)
        # chat = []
        # try:
        #     with self.file_lock:
        #         with open(f"chats/{self.server_name}-{self.username}-{interlocutor}.json", "r") as file:
        #             chat = json.loads(file.read())
        # except Exception as e:
        #     # print(f'Problem loading chat: {e}')
        #     pass
        # # print(len(chat))

        chat = self.db.get_chat(self.username, interlocutor)

        return chat

    # def save_chat(self, chat, interlocutor):
    #     os.makedirs("chats", exist_ok=True)
    #     try:
    #         with self.file_lock:
    #             with open(f"chats/{self.server_name}-{self.username}-{interlocutor}.json", "w") as file:
    #                 file.write(json.dumps(chat))
    #     except Exception as e:
    #         print(f"ERROR saving chat: {e}")

    def listen_for_messages(self):
        # print("Listening for messages")
        # time.sleep(1)
        while self.running:
            try:
                message, address = self.read_response(self.message_socket)
                # print(f"Message from {address}: {message}")
                if message.startswith("MESSAGE"):
                    _, sender, text = message.split(" ", 2)
                    # chat = self.load_chat(sender) ############################Delete this line
                    # chat.append({"sender": sender, "text": text, "readed":False}) ############################Delete this line

                    self.db.insert_new_message(sender, self.username, text, False)

                    self.contact_list[sender] = address
                
                    # self.save_chat(chat, sender) ############################Delete this line
                elif message.startswith("PING"):
                    self.message_socket.sendto("PONG".encode(), address)
            except Exception as e:
                # print(f"Error in the listening: {e}")
                pass

    def is_user_online(self, address):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                sock.settimeout(0.5)
                sock.bind(('', 0))
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
            # print(f"Pending messages: {self.pending_list}")
            try:
                with self.pending_lock:
                    pending_users = list(self.pending_list.keys())
                for username in pending_users:
                    with self.pending_lock:
                        while self.send_message(username, self.pending_list[username][0]):
                            self.pending_list[username].pop(0)
                            if len(self.pending_list[username]) == 0:
                                del self.pending_list[username]
                                break
                        else:
                            pass
                time.sleep(1)
            except Exception as e:
                print(f"Error sending pending messages: {e}")
                pass

    def run_background(self):
        # print("Starting background threads")
        threading.Thread(target=self.listen_for_messages, daemon=True).start()
        threading.Thread(target=self.send_pending_messages,
                         daemon=True).start()
        # print("Background threads started")
        time.sleep(1)

if __name__ == "__main__":
    # client = chat_client()
    # client.run_ui()
    pass


"""
TODO:
- [x] Change to TCP at least for sending messages (one socket UDP for pinging and one thread with TCP for every conversation)
- [x] Implement what happens if the server is down (auto search of new server)
"""


"""
#Server
import socket

def start_server():
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind(('0.0.0.0', 12345))
    server_socket.listen(5)
    print("Server started and listening on port 12345")

    while True:
        client_socket, client_address = server_socket.accept()
        print(f"Connection from {client_address}")
        handle_client(client_socket)

def handle_client(client_socket):
    while True:
        try:
            message = client_socket.recv(1024).decode('utf-8')
            if not message:
                break
            print(f"Received: {message}")
            response = f"Echo: {message}"
            client_socket.send(response.encode('utf-8'))
        except ConnectionResetError:
            break
    client_socket.close()

if __name__ == "__main__":
    start_server()
"""

"""
#Client
import socket

def start_client():
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_socket.connect(('127.0.0.1', 12345))
    print("Connected to server")

    while True:
        message = input("Enter message to send: ")
        if message.lower() == 'exit':
            break
        client_socket.send(message.encode('utf-8'))
        response = client_socket.recv(1024).decode('utf-8')
        print(f"Received from server: {response}")

    client_socket.close()

if __name__ == "__main__":
    start_client()
"""
