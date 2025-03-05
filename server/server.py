import socket
import threading
import sys
import json
import db_manager
import time
import random
# from termcolor import colored as col
import struct


HASH_MOD = 10**18+3
FAIL_TOLERANCE = 3


class ChatServer:
    def __init__(self, name):
        self.name = name

        self.command_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.command_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        self.ping_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.ping_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        self.db_manager = db_manager.server_db()
        self.db_lock = threading.Lock()

        self.lower_bound = 0
        self.upper_bound = HASH_MOD - 1

        self.predecessor = None
        self.successor = None
        self.successors = []

        self.replics = []
        self.replicants = []

        self.running = True
        self.crisis = False


    
    #region Start Sequence 
    
    def start(self):
        with self.db_lock:
            self.db_manager.set_db(self.name)

        servers = self.discover_servers()

        if not servers:
            print("No other servers running")
        else:
            for server in servers:
                print(f"Server found: {server[0]} at {server[1]}")
            self.join_to_servers(servers)

        # if self.successor:
            # self.successors = self.get_successors()

        self.command_socket.bind(("", 12345))
        self.ping_socket.bind(("", 12346))

        self.print_info()

        integrity_check = threading.Thread(target=self.tape_integrity_check, daemon=True)
        integrity_check.start()
        successors_provider = threading.Thread(target=self.successors_provider, daemon=True)
        successors_provider.start()
        ping_listener = threading.Thread(target=self.listen_for_ping, daemon=True)
        ping_listener.start()
        # correct_bd = threading.Thread(target=self.correct_bd, daemon=True)
        # correct_bd.start()
        replics_manager = threading.Thread(target=self.replics_manager, daemon=True)
        replics_manager.start()
        # replicants_manager = threading.Thread(target=self.replicants_manager, daemon=True)
        # replicants_manager.start()
        info_updater = threading.Thread(target=self.info_updater, daemon=True)
        info_updater.start()

        threading.Thread(target=self.multicast_listener, daemon=True).start()

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

    def get_successors(self):
        successors = []
        if self.successor:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                try:
                    sock.settimeout(0.5)
                    sock.sendto(f"SUCC {FAIL_TOLERANCE+1}".encode(), (self.successor, 12345))
                    data, _ = sock.recvfrom(1024)
                    response = data.decode()
                    if response.startswith("OK"):
                        print(f"Respnse from backup is :{response}")
                        _, successors = response.split(" ", 1)
                        successors = successors.split(" ")
                        print(f"Now backup successors are: {successors}")
                    else:
                        print(f"Getting backup successors failed: {response}")
                        successors = self.successors
                except Exception as e:
                    print(f"Getting backup successors failed with exception: {e}")
                    successors = self.successors
            return successors
    


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
                    self.successors = successors_list[: FAIL_TOLERANCE + 1]
                    if self.predecessor:
                        self.command_socket.sendto(f"SUCC {self.get_ip()} {successors}".encode(), (self.predecessor, 12345))

                elif message.startswith("FIX"):
                    self.crisis = True
                    # fix_task = threading.Thread(target=self.fix_tape, daemon=True)
                    # fix_task.start()
                    self.fix_tape()
                    self.replicants_manager()
                    self.correct_bd()
                    self.crisis = False


                elif message.startswith("REPLIC"):
                    _, username, ip, port = message.split(" ")
                    if address[0] not in self.replicants:
                        self.replicants.append(address[0])
                    with self.db_lock:
                        self.db_manager.register_replic_user(username, ip, port, address[0])
                
                elif message.startswith("DROP_REPLICS"):
                    _, owner = message.split(" ")
                    with self.db_lock:
                        self.db_manager.drop_replics(owner)
                    try:
                        self.replicants.remove(owner)
                    except Exception:
                        pass

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
        # print('a')

        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            if username_hash < self.lower_bound:
                # print('a')
                sock.sendto(f"REGISTER {answer_to_ip} {answer_to_port} {username} {ip} {port}".encode(), (self.predecessor, 12345))
                print(f"Sent to predecessor {self.predecessor}")
                # print('b')
        
            elif username_hash > self.upper_bound:
                # print('c')
                sock.sendto(f"REGISTER {answer_to_ip} {answer_to_port} {username} {ip} {port}".encode(), (self.successor, 12345))
                print(f"Sent to successor {self.successor}")
                # print('d')
            else:
                # print('e')
                with self.db_lock:
                    self.db_manager.register_user(username, ip, port)
                response = f"OK User '{username}' in ({ip}:{port}) successfully registered"
                if answer_to_ip != '.':
                    sock.sendto(response.encode(), (answer_to_ip, answer_to_port))
                # print('f')
                for replic in self.replics:
                    sock.sendto(f"REPLIC {username} {ip} {port}".encode(), (replic, 12345))
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
                with self.db_lock:
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




    #region Services

    def successors_provider(self):
        while self.running:
            if self.successor is None and self.predecessor:
                with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                    sock.sendto(f"SUCC {self.get_ip()}".encode(), (self.predecessor, 12345))
            time.sleep(5)


    def tape_integrity_check(self):
        while self.running:
            # self.successors = self.get_successors()
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
        self.crisis = True
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
        self.crisis = False

                
    def fix_tape_forward(self):
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.settimeout(0.1)
            for successor in self.successors:
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
            self.successors = []

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


    def correct_bd(self):
        # while self.running:
        #     if self.crisis:
        #         time.sleep(1)
        #         continue
        with self.db_lock:
            alien_users = self.db_manager.get_alien_users(self.lower_bound, self.upper_bound, self.rolling_hash)
        for user in alien_users:
            with self.db_lock:
                self.register_user('.', '.', user[0], user[1], user[2])
                self.db_manager.delete_user(user[0])
            # time.sleep(1)


    def replics_manager(self):
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            while self.running:
                if self.crisis:
                    time.sleep(1)
                    continue
                new_replics_needed = FAIL_TOLERANCE + 1 - len(self.replics)
                # print(f"Replics needed: {new_replics_needed}")
                replics = self.replics.copy()
                for replic in replics:
                    if not self.ping(replic): 
                        new_replics_needed += 1
                        replics.remove(replic)
                        sock.sendto(b"DROP_REPLIC", (replic, 12345))
                if new_replics_needed > 0:            
                    new_replics = self.find_new_replics(new_replics_needed, replics)
                    if new_replics:
                        print(f"New replics: {new_replics}")
                    replics.extend(new_replics)
                    self.replics = replics

                    with self.db_lock:
                        user_info = self.db_manager.get_bd_copy()
                    for user in user_info:
                        for replic in new_replics:
                            sock.sendto(f"REPLIC {user[0]} {user[1]} {user[2]}".encode(), (replic, 12345))
                time.sleep(1)


    def find_new_replics(self, needed, actual_replics):
        servers = self.ping_all_servers()
        if not servers:
            return []
        
        try:
            servers.remove(self.get_ip())
        except Exception:
            pass

        for replic in actual_replics:
            try:
                servers.remove(replic)
            except Exception:
                pass

        needed = min(needed, len(servers))

        return random.sample(servers, needed)        


    def replicants_manager(self):
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            # while self.running:
            #     if self.crisis:
            #         time.sleep(1)
            #         continue
            for replicant in self.replicants:
                if not self.ping(replicant):
                    with self.db_lock:
                        user_info = self.db_manager.get_replics(replicant)
                    for user in user_info:
                        self.register_user('.', '.', user[0], user[1], user[2])
                    self.replicants.remove(replicant)
                    with self.db_lock:
                        self.db_manager.drop_replics(replicant)
                    print(f"Asimilated data from {replicant}")
            # time.sleep(1)


    def info_updater(self):
        while self.running:
            self.print_info()
            time.sleep(10)


    #region Utils

    def get_ip(self):
        return socket.gethostbyname(socket.gethostname())
    

    def ping(self, ip, timeout=0.1):
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.settimeout(timeout)
            try:
                sock.sendto(b"PING", (ip, 12346))
                _, _ = sock.recvfrom(1024)
                return True
            except Exception as e:
                return False
            
    def ping_all_servers(self, timeout=0.1):
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.settimeout(timeout)
            servers = []
            broadcast_address = ("<broadcast>", 12346)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            try:
                sock.sendto("PING".encode(), broadcast_address)
                while True:
                    _, address = sock.recvfrom(1024)
                    servers.append(address[0])
            except socket.timeout:
                pass

            return servers


    def print_info(self):
        print(f"Server '{self.name}' on ({self.get_ip()}:12345). Storing in range ({self.lower_bound}, {self.upper_bound}). Predecessor is {self.predecessor}, successor is {self.successor}")
        print(f"Successors: {self.successors}")
        print(f"Replics: {self.replics}")
        print(f"Replicants: {self.replicants}")

    def rolling_hash(self, s: str, base=911382629, mod=HASH_MOD) -> int:   
        hash_value = 0
        for c in s:
            hash_value = (hash_value * base + ord(c)) % mod
        return hash_value
    


    # region Multicast Stuff
    def multicast_listener(self) -> None:
        """
        Function that listens for multicast requests.
        When it receives the DISCOVER_SERVER message, it responds with its IP address.
        """
        MCAST_GRP = "224.0.0.1"
        MCAST_PORT = 10003
        DISCOVER_MSG = "DISCOVER_SERVER"
        BUFFER_SIZE = 1024
        # Crear socket UDP
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        # Permitir que varias instancias puedan reutilizar el puerto
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        # Vincular el socket a todas las interfaces en el puerto MCAST_PORT
        sock.bind(("", MCAST_PORT))

        # Unirse al grupo multicast
        mreq = struct.pack("=4sl", socket.inet_aton(MCAST_GRP), socket.INADDR_ANY)
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)

        
        print(f"[Muticast] Escuchando mensajes en {MCAST_GRP}:{MCAST_PORT}")
        

        while True:
            try:
                data, addr = sock.recvfrom(BUFFER_SIZE)
                message = data.decode().strip()
                print(f"Recibido mensaje: '{message}' desde {addr}")
                if message.startswith(DISCOVER_MSG + ":"):
                    local_ip = self.get_ip()
                    _, rec_ip, rec_port = message.split(":")
                    print(f"{rec_ip} {rec_port}")
                    sock.sendto(local_ip.encode(), (rec_ip, int(rec_port)))
                else:
                    local_ip = self.get_ip()
                    sock.sendto(local_ip.encode(), addr)
            except Exception as e:
                print(f"Error en el listener: {e}")
                time.sleep(1)


    # def discover_servers(self, timeout: str = 1) -> list:
    #     """
    #     Sends a multicast request to discover servers and waits for responses.

    #     :param timeout: Maximum time (in seconds) to wait for responses.
    #     :return: List of IPs of the discovered servers.
    #     """
    #     MCAST_GRP = "224.0.0.1"
    #     MCAST_PORT = 10003
    #     MESSAGE = "DISCOVER_SERVER"
    #     BUFFER_SIZE = 1024

    #     # Crear socket UDP para enviar y recibir
    #     sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    #     sock.settimeout(timeout)

    #     # Configurar TTL del paquete multicast
    #     ttl = struct.pack("b", 1)
    #     sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, ttl)

    #     # Enviar la petición multicast
    #     try:
    #         sock.sendto(MESSAGE.encode(), (MCAST_GRP, MCAST_PORT))
    #     except Exception as e:
    #         print(f"Error enviando el mensaje multicast: {e}")
    #         return []

    #     servers = []
    #     start_time = time.time()
    #     while True:
    #         try:
    #             data, addr = sock.recvfrom(BUFFER_SIZE)
    #             server_ip = data.decode().strip()
    #             servers.append(server_ip)
    #             print(f"Servidor descubierto: {server_ip}")
    #         except socket.timeout:
    #             break
    #         except Exception as e:
    #             print(f"Error recibiendo datos: {e}")
    #             break
    #         if time.time() - start_time > timeout:
    #             break

    #     sock.close()

    #     print(f"Servers descubiertos con multicast: {servers}")

    #     return [("main", server) for server in servers]




if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Use: python server.py <name>")
        sys.exit(1)
    name = sys.argv[1]
    server = ChatServer(name)
    server.start()



'''
 To do:
 -Add locks to database operations
 -Add replication (to predecessor and successor and some random)
    -Add a process that manages replication

 -Update client commands to work with ring
'''