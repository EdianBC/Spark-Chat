import socket
import threading
import sys
import json
import db_manager
import time


class ChatServer:
    def __init__(self, server_name):
        self.server_name = server_name
        self.users = {}
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_address = ("", 12345)

        self.db_manager = db_manager.server_db()

        self.lower_bound = 0
        self.upper_bound = 100

        self.predecessor = None
        self.successor = None

    def start(self):
        # try:
        #     with open("users.json", "r") as file:
        #         self.users = json.loads(file.read())
        # except:
        #     pass
        self.db_manager.set_db(self.server_name)


        servers = self.discover_servers()

        if not servers:
            print("No other servers running")
        else:
            for server in servers:
                print(f"Server found: {server[0]} at {server[1]}")

            self.join_to_servers(servers)
        

        # listening = threading.Thread(target=self.listen_for_messages, daemon=True)
        # listening.start()

        print(f"Server '{self.server_name}' started on ({self.get_ip()}:12345). Storing in range ({self.lower_bound}, {self.upper_bound}). Predecessor is {self.predecessor}, successor is {self.successor}")

        # time.sleep(3)

        self.server_socket.bind(self.server_address)
        # threading.Thread.join(listening)
        self.listen_for_messages()


    def discover_servers(self):
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock: 
            sock.settimeout(1)
            servers = []
            broadcast_address = ("<broadcast>", 12345)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            try:
                sock.sendto("DISCOVER".encode(), broadcast_address)
                while True:
                    data, address = sock.recvfrom(1024)
                    server_name = data.decode()
                    servers.append((server_name, address[0]))
            except socket.timeout:
                pass

            return servers

    def join_to_servers(self, servers):
        longest_server = self.get_longest_range(servers)
        self.request_join(longest_server)

    def get_longest_range(self, servers):
        longest_range = -1
        longest_server = None
        for server in servers:
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                    sock.settimeout(3)
                    sock.sendto(f"RANGE".encode(), (server[1], 12345))
                    data, _ = sock.recvfrom(1024)
                    response = data.decode()
                    if response.startswith("OK"):
                        _, range = response.split(" ")
                        if int(range) > longest_range:
                            longest_server = server
                            longest_range = int(range)
            except Exception as e:
                print(f"Error getting range from server '{server[0]}': {e}")

        return longest_server
    

    def request_join(self, server):
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.settimeout(1)
            sock.sendto(f"JOIN".encode(), (server[1], 12345))
            data, _ = sock.recvfrom(1024)
            response = data.decode()
            if response.startswith("OK"):
                _, lower_bound, upper_bound, predecessor, successor = response.split()
                self.lower_bound = int(lower_bound)
                self.upper_bound = int(upper_bound)
                self.predecessor = predecessor
                if successor != "_":
                    self.successor = successor
                else:
                    self.successor = None
            else:
                print(f"Joining request failed: {response}") 


    def listen_for_messages(self):
        # print('hello')
        while True:
            try:
                # print('awaw')
                data, address = self.server_socket.recvfrom(1024)
                # if address[0] == self.get_ip():
                #     print('wtf amigo no te envies mensajes a ti mismo')
                #     continue
                # print('awawaaa')
                message = data.decode()
                print(f"Message from {address}: {message}")
                if message.startswith("REGISTER "):
                    self.register_user(message, address)
                elif message.startswith("RESOLVE "):
                    self.resolve_user(message, address)
                elif message.startswith("DISCOVER"):
                    self.server_socket.sendto(f"{self.server_name}".encode(), address)
                elif message.startswith("RANGE"):
                    self.server_socket.sendto(f"OK {self.upper_bound - self.lower_bound}".encode(), address)
                elif message.startswith("JOIN"):
                    self.process_join_request(address)
                    self.print_info()
                elif message.startswith("PRED_CHANGE"):
                    self.change_predecessor(message)
                    self.print_info()

                    
            except Exception as e:
                print(f"Server error: {e}")

    def change_predecessor(self, message):
        _, predecessor = message.split(" ")
        self.predecessor = predecessor

    def register_user(self, message, client_address):
        try:
            _, username, port = message.split(" ")

            new_user = username not in self.users.keys()
            self.users[username] = (client_address[0], int(port))
            
            if new_user:
                response = f"OK User {username} listening on {client_address[0]}:{port}. Successfully registered."
                
                with open("users.json", "w") as file:
                    file.write(json.dumps(self.users))
            else:
                response = f"OK User {username} listening on {client_address[0]}:{port}. Successfully updated."
        except Exception as e:
            response = f"ERROR registering user '{username}': {e}"

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

    def process_join_request(self, joinee):
        # print(f"joineee is '{joinee}'")
        joinee_lower_bound = int((self.lower_bound + self.upper_bound) / 2)
        joinee_upper_bound = self.upper_bound
        #asignar el sucesor del nuevo
        joinee_successor = "_" if self.successor is None else self.successor
        joinee_predecessor = self.get_ip()
        #Avisarle al succesor que tiene un nuevo predecessor
        self.request_predecessor_change(self.successor, joinee[0])
        
        #(lower, upper, predecessor, successor)
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.settimeout(1)
            sock.sendto(f"OK {joinee_lower_bound} {joinee_upper_bound} {joinee_predecessor} {joinee_successor}".encode(), joinee)
        #empezar a pasarle los datos que le tocan
        #recortarme mi rango
        self.upper_bound = joinee_lower_bound
        #cambiar mi sucesor
        self.successor = joinee[0]

    def request_predecessor_change(self, successor, new_predecessor):
        if successor is not None:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                sock.settimeout(1)
                sock.sendto(f"PRED_CHANGE {new_predecessor}".encode(), (successor, 12345))

    def get_ip(self):
        return socket.gethostbyname(socket.gethostname())

    def print_info(self):
        print(f"Server '{self.server_name}' on ({self.get_ip()}:12345). Storing in range ({self.lower_bound}, {self.upper_bound}). Predecessor is {self.predecessor}, successor is {self.successor}")



if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Use: python server.py <SERVER_NAME>")
        sys.exit(1)
    server_name = sys.argv[1]
    server = ChatServer(server_name)
    server.start()



'''
 
'''