import socket
import threading
import sys
import json
import db_manager
import time


HASH_MOD = 10**18+3
FAIL_TOLERANCE = 3


class ChatServer:
    def __init__(self, name):
        self.name = name

        self.command_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.command_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        self.ping_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.command_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        self.db_manager = db_manager.server_db()

        self.lower_bound = 0
        self.upper_bound = HASH_MOD - 1

        self.predecessor = None
        self.successor = None
        self.backup_successors = []

        self.running = True



    
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

        # if self.successor:
            # self.backup_successors = self.get_backup_successors()

        self.command_socket.bind(("", 12345))
        self.ping_socket.bind(("", 12346))

        print(f"Server '{self.name}' started on ({self.get_ip()}:12345). Storing in range ({self.lower_bound}, {self.upper_bound}). Predecessor is {self.predecessor}, successor is {self.successor}")
        
        integrity_check = threading.Thread(target=self.tape_integrity_check, daemon=True)
        integrity_check.start()
        integrity_check = threading.Thread(target=self.backup_successors_provider, daemon=True)
        integrity_check.start()
        ping_listener = threading.Thread(target=self.listen_for_ping, daemon=True)
        ping_listener.start()

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
                        _, lower_bound, upper_bound = response.split(" ")
                        range = int(upper_bound) - int(lower_bound)
                        if range > longest_range:
                            longest_range_server = server
                            longest_range = range
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

    def get_backup_successors(self):
        backup_successors = []
        if self.successor:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                try:
                    sock.settimeout(0.5)
                    sock.sendto(f"SUCC {FAIL_TOLERANCE+1}".encode(), (self.successor, 12345))
                    data, _ = sock.recvfrom(1024)
                    response = data.decode()
                    if response.startswith("OK"):
                        print(f"Respnse from backup is :{response}")
                        _, backup_successors = response.split(" ", 1)
                        backup_successors = backup_successors.split(" ")
                        print(f"Now backup successors are: {backup_successors}")
                    else:
                        print(f"Getting backup successors failed: {response}")
                        backup_successors = self.backup_successors
                except Exception as e:
                    print(f"Getting backup successors failed with exception: {e}")
                    backup_successors = self.backup_successors
            return backup_successors
    


    #region Commands

    def listen_for_messages(self):

        while self.running:
            try:
                data, address = self.command_socket.recvfrom(1024)
                message = data.decode()
                
                if message != "PING":
                    print(f"Message from {address}: {message}")

                
                if message.startswith("DISCOVER"):
                    self.command_socket.sendto(f"{self.name}".encode(), address)

                elif message.startswith("PING"):
                    self.command_socket.sendto("PONG".encode(), address)
                
                elif message.startswith("RANGE"):
                    self.command_socket.sendto(f"OK {self.lower_bound} {self.upper_bound}".encode(), address)
                
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
                    self.resolve_user(answer_to_ip, int(answer_to_port), username)

                elif message.startswith("SUCC"):
                    _, successors = message.split(" ", 1)
                    successors_list = successors.split(" ")
                    self.backup_successors = successors_list[: FAIL_TOLERANCE + 1]
                    if self.predecessor:
                        self.command_socket.sendto(f"SUCC {self.get_ip()} {successors}".encode(), (self.predecessor, 12345))
                    # try:
                    #     _, answer_to_ip, answer_to_port, hops, successors_list = message.split(" ", 4)  
                    # except Exception as e:
                    #     _, hops = message.split(" ")
                    #     successors_list = ""
                    #     answer_to_ip = address[0]
                    #     answer_to_port = address[1]
                    # self.process_successors_request(answer_to_ip, int(answer_to_port), hops, successors_list)
                elif message.startswith("FIX"):
                    fix_task = threading.Thread(target=self.fix_tape, daemon=True)
                    fix_task.start()

                elif message.startswith("KILL"):
                    self.running = False
                    time.sleep(3)
                    return

            except Exception as e:
                print(f"Server error: {e}")


    def listen_for_ping(self):
        while self.running:
            try:
                data, address = self.ping_socket.recvfrom(1024)
                message = data.decode()
                if message == "PING":
                    self.ping_socket.sendto("PONG".encode(), address)
            except:
                pass


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
                address = self.db_manager.resolve_user(username)
                if address:
                    ip, port = address
                    response = f"OK {ip} {port}"
                    sock.sendto(response.encode(), (answer_to_ip, answer_to_port))
                    print(f"Resolved address of user '{username}', ({ip}:{port})")
                else:
                    response = f"ERROR 404 User not found"
                    sock.sendto(response.encode(), (answer_to_ip, answer_to_port))
                    print(f"ERROR 404 User not found")


    def process_join_request(self, joinee):
        joinee_lower_bound = int((self.lower_bound + self.upper_bound) / 2)
        joinee_upper_bound = self.upper_bound
        joinee_successor = "_" if self.successor is None else self.successor
        joinee_predecessor = self.get_ip()

        self.request_predecessor_change(self.successor, joinee[0])
        
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.sendto(f"OK {joinee_lower_bound} {joinee_upper_bound} {joinee_predecessor} {joinee_successor}".encode(), joinee)
   
        self.upper_bound = joinee_lower_bound - 1
        self.successor = joinee[0]

    def request_predecessor_change(self, target, new_predecessor):
        if target is not None:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                sock.settimeout(1)
                sock.sendto(f"PRED_CHANGE {new_predecessor}".encode(), (target, 12345))

    # def process_successors_request(self, answer_to_ip, answer_to_port, hops, successors_list):
    #     hops = int(hops)-1
    #     successors_list = f"{successors_list} {self.get_ip()}" if successors_list else self.get_ip()

    #     with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
    #         sock.settimeout(0.1)
    #         if hops == "0" or self.successor is None:
    #             response = f"OK {successors_list}"
    #             sock.sendto(response.encode(), (answer_to_ip, answer_to_port))
    #         else:
    #             try:
    #                 sock.sendto(f"SUCC {answer_to_ip} {answer_to_port} {hops} {successors_list}".encode(), (self.successor, 12345))
    #             except Exception as e:
    #                 print(f"Error in successors list: {e}")
    #                 response = f"ERROR"
    #                 sock.sendto(response.encode(), (answer_to_ip, answer_to_port))


    def backup_successors_provider(self):
        while self.running:
            if self.successor is None and self.predecessor:
                with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                    sock.sendto(f"SUCC {self.get_ip()}".encode(), (self.predecessor, 12345))
            time.sleep(5)


    def tape_integrity_check(self):
        while self.running:
            # self.backup_successors = self.get_backup_successors()
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                broadcast_address = ("<broadcast>", 12345)
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
                sock.settimeout(0.1)
                try:
                    if self.successor:
                        sock.sendto("PING".encode(), (self.successor, 12346))
                        _, _ = sock.recvfrom(1024)
                
                    if self.predecessor:
                        sock.sendto("PING".encode(), (self.predecessor, 12346))
                        _, _ = sock.recvfrom(1024)
                    
                except Exception as e:
                    print("Tape integrity compromised")
                    sock.sendto("FIX".encode(), broadcast_address)

            time.sleep(1)

        print("Shutting tape integrity check off")

    def fix_tape(self):
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.settimeout(0.1)
            if self.successor:
                try:
                    sock.sendto(f"PING", (self.successor, 12346))
                    _, _ = sock.recvfrom(1024)
                except Exception as e:
                    self.fix_tape_forward()
            time.sleep(0.1 * 3 * FAIL_TOLERANCE)
            if self.predecessor:
                try:
                    sock.sendto(f"PING", (self.predecessor, 12346))
                    _, _ = sock.recvfrom(1024)
                except Exception as e:
                    self.fix_tape_backward()
        self.print_info()

                
    def fix_tape_forward(self):
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.settimeout(0.1)
            for successor in self.backup_successors:
                try:
                    sock.sendto(f"PING".encode(), (successor, 12346))
                    _, _ = sock.recvfrom(1024)
                    sock.settimeout(5)
                    sock.sendto(f"RANGE".encode(), (successor, 12345))
                    data, _ = sock.recvfrom(1024)
                    data.decode()
                    _, lower_bound, _ = data.split()
                    self.upper_bound = int(lower_bound) - 1
                    self.request_predecessor_change(successor, self.get_ip())
                    self.successor = successor
                    return
                except Exception as e:
                    print(f"Server {successor} unavailable: {e}")
            self.upper_bound = HASH_MOD - 1
            self.successor = None
            self.backup_successors = []

    def fix_tape_backward(self):
        if self.predecessor:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                sock.settimeout(0.5)
                try:
                    sock.sendto(f"PING".encode(), (self.predecessor, 12346))
                    _, _ = sock.recvfrom(1024)
                except Exception as e:
                    sock.sendto(f"KILL".encode(), (self.predecessor, 12345))
                    self.lower_bound = 0
                    self.predecessor = None



    #region Utils

    def get_ip(self):
        return socket.gethostbyname(socket.gethostname())

    def print_info(self):
        print(f"Server '{self.name}' on ({self.get_ip()}:12345). Storing in range ({self.lower_bound}, {self.upper_bound}). Predecessor is {self.predecessor}, successor is {self.successor}")
        print(f"Backup successors: {self.backup_successors}")

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
 -Add locks to database operationss
 -Add replication (to predecessor and successor and some random)
    -Add a process that manages replication

 -Update client commands to work with ring
'''