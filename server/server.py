import socket
import threading
import sys
import json
import db_manager
import time


HASH_MOD = 10**18+3


class ChatServer:
    def __init__(self, name):
        self.name = name

        self.command_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.command_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        self.db_manager = db_manager.server_db()

        self.lower_bound = 0
        self.upper_bound = HASH_MOD - 1

        self.predecessor = None
        self.successor = None



    
    #region Start Sequence 
    
    def start(self):

        self.db_manager.set_db(self.name)

        servers = self.discover_servers()

        if not servers:
            print("No other servers running")
        else:
            for server in servers:
                print(f"Server found: {server[0]} at {server[1]}")
            self.join_to_servers(servers)

        # listening = threading.Thread(target=self.listen_for_messages, daemon=True)
        # listening.start()

        print(f"Server '{self.name}' started on ({self.get_ip()}:12345). Storing in range ({self.lower_bound}, {self.upper_bound}). Predecessor is {self.predecessor}, successor is {self.successor}")

        self.command_socket.bind(("", 12345))
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
        longest_range_server = self.get_longest_range_server(servers)
        self.request_join(longest_range_server)

    def get_longest_range_server(self, servers):
        longest_range = -1
        longest_range_server = None
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
                            longest_range_server = server
                            longest_range = int(range)
            except Exception as e:
                print(f"Error getting range from server '{server[0]}': {e}")

        return longest_range_server
    

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
                raise ValueError


    

    #region Commands

    def listen_for_messages(self):

        while True:
            try:
                data, address = self.command_socket.recvfrom(1024)
                message = data.decode()
                print(f"Message from {address}: {message}")

                
                if message.startswith("DISCOVER"):
                    self.command_socket.sendto(f"{self.name}".encode(), address)
                
                elif message.startswith("RANGE"):
                    self.command_socket.sendto(f"OK {self.upper_bound - self.lower_bound}".encode(), address)
                
                elif message.startswith("JOIN"):
                    self.process_join_request(address)
                    self.print_info()
                
                elif message.startswith("PRED_CHANGE"):
                    _, predecessor = message.split(" ")
                    self.change_predecessor(predecessor)
                    self.print_info()

                elif message.startswith("REGISTER"):
                    try:
                        _, answer_to_ip, answer_to_port, username, ip, port = message.split(" ")  
                    except Exception as e:
                        _, username, ip, port = message.split(" ")
                        answer_to_ip = address[0]
                        answer_to_port = address[1]
                    ########################## Use regex to identify if it is one option or another 
                    self.register_user(answer_to_ip, int(answer_to_port), username, ip, int(port))

                elif message.startswith("RESOLVE"):
                    try:
                        _, answer_to_ip, answer_to_port, username = message.split(" ")  
                    except Exception as e:
                        _, username = message.split(" ")
                        answer_to_ip = address[0]
                        answer_to_port = address[1]
                    ########################## Use regex to identify if it is one option or another 
                
                    self.resolve_user(answer_to_ip, answer_to_port, username)

                    
            except Exception as e:
                print(f"Server error: {e}")


    def change_predecessor(self, predecessor):
        self.predecessor = predecessor


    def register_user(self, answer_to_ip, answer_to_port, username, ip, port):
        
        username_hash = self.rolling_hash(username)

        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            if username_hash < self.lower_bound:
                sock.sendto(f"REGISTER {answer_to_ip} {answer_to_port} {username} {ip} {port}".encode(), (self.predecessor, 12345))
                print(f"Sent to predecessor {self.predecessor}")
        
            elif username_hash > self.upper_bound:
                sock.sendto(f"REGISTER {answer_to_ip} {answer_to_port} {username} {ip} {port}".encode(), (self.successor, 12345))
                print(f"Sent to successor {self.successor}")
            else:
                self.db_manager.register_user(username, ip, port)
                response = f"OK User '{username}' in ({ip}:{port}) successfully registered"
                with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                    sock.sendto(response.encode(), (answer_to_ip, answer_to_port))
                print(response)


    def resolve_user(self, answer_to_ip, answer_to_port, username):

        username_hash = self.rolling_hash(username)
        
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            if username_hash < self.lower_bound:
                sock.sendto(f"RESOLVE {answer_to_ip} {answer_to_port} {username}".encode(), (self.predecessor, 12345))
                print(f"Sent to predecessor {self.predecessor}")
        
            elif username_hash > self.upper_bound:
                sock.sendto(f"RESOLVE {answer_to_ip} {answer_to_port} {username}".encode(), (self.successor, 12345))
                print(f"Sent to successor {self.successor}")
            else:
                ip, port = self.db_manager.resolve_user(username)
                response = f"OK {ip} {port}"
                with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                    sock.sendto(response.encode(), (answer_to_ip, answer_to_port))
                print(f"Resolved address of user '{username}', ({ip}:{port})")

    def process_join_request(self, joinee):
        joinee_lower_bound = int((self.lower_bound + self.upper_bound) / 2)
        joinee_upper_bound = self.upper_bound
        joinee_successor = "_" if self.successor is None else self.successor
        joinee_predecessor = self.get_ip()

        self.request_predecessor_change(self.successor, joinee[0])
        
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.settimeout(1)
            sock.sendto(f"OK {joinee_lower_bound} {joinee_upper_bound} {joinee_predecessor} {joinee_successor}".encode(), joinee)
   
        self.upper_bound = joinee_lower_bound - 1
        self.successor = joinee[0]

    def request_predecessor_change(self, successor, new_predecessor):
        if successor is not None:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                sock.settimeout(1)
                sock.sendto(f"PRED_CHANGE {new_predecessor}".encode(), (successor, 12345))




    #region Utils

    def get_ip(self):
        return socket.gethostbyname(socket.gethostname())

    def print_info(self):
        print(f"Server '{self.name}' on ({self.get_ip()}:12345). Storing in range ({self.lower_bound}, {self.upper_bound}). Predecessor is {self.predecessor}, successor is {self.successor}")

    def rolling_hash(self, s: str, base=911382629, mod=HASH_MOD) -> int:   
        hash_value = 0
        for c in s:
            hash_value = (hash_value * base + ord(c)) % mod
        return hash_value

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Use: python server.py <name>")
        sys.exit(1)
    name = sys.argv[1]
    server = ChatServer(name)
    server.start()



'''
 To do:
 -Update bd system in client commands
 -Add replication (to predecessor and successor and some random)
    -Add a process that manages replication

 -Update client commands to work with ring
'''