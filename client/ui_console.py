import client
import time
import os
import threading

class console_app:
    def __init__(self):
        
        self.running = True
        self.interlocutor = None
        self.update_chat_flag = False

        self.chat_client = client.chat_client()

    def print_message(self, message):
        if(message[1] == self.chat_client.username):
            print(f"{message[3]} [ID: {message[0]}, Date: {message[4]}]")
        else:
            print(f"{message[1]}: {message[3]} [ID: {message[0]}, Date: {message[4]}]")

    def print_chat(self, interlocutor):
        chat = self.chat_client.load_chat(interlocutor)
        for message in chat:
            self.print_message(message)

    def print_unseen_resume(self):
        resume = self.chat_client.db.get_unseen_resume(self.chat_client.username)

        if not resume:
            print("No new messages.")
            return

        print("New messages:")
        for user, count in resume:
            if count == 1:
                print(f"{user}: 1 unseen message.")
            else:
                print(f"{user}: {count} unseen messages.")


    def update_chat(self, interlocutor):
        while self.update_chat_flag:
            unseen = self.chat_client.db.get_unseen_messages(self.chat_client.username, interlocutor)
            # print(unseen)
            # time.sleep(1)
            
            for message in unseen:
                self.print_message(message)

            # print(f"Chat u[pdated {self.chat_client.username} - {interlocutor}")
            self.chat_client.db.set_messages_as_seen(self.chat_client.username, interlocutor)
            time.sleep(0.1)


    def run_ui(self):
        status = self.search_servers_ui()
        if status != "OK":
            return
        time.sleep(1)

        status = self.register_or_login_ui()
        if status != "OK":
            return
        time.sleep(1)
        
        status = "MAIN"

        while True:
            if status == "MAIN":
                status = self.main_menu_ui()

            elif status == "PV":
                status = self.private_chat_ui()

            elif status == "QUIT":
                print("Farewell my beloved...")
                break

            else:
                print("An error ocurred. Please wait...")
                time.sleep(3)
                status = "MAIN"
        print("WIIIIII TEST")

    def search_servers_ui(self):
        try:
            os.system('cls' if os.name == 'nt' else 'clear')
            while True:
                print("Searching for available servers...")
                # servers = self.chat_client.discover_servers()
                servers = self.chat_client.discover_servers_multicast()
                if not servers:
                    print("No servers were found :(")
                    choice = input("Do you want to search again? (y/n): ")
                    if choice.lower() == "n":
                        return "NOT OK"
                else:
                    print("Servers found:")
                    print(servers)
                    for i, (name, ip) in enumerate(servers):
                        print(f"{i + 1}. {name} ({ip})")
                    choice = int(input("Select a server by number: ")) - 1
                    self.chat_client.connect_to_server(servers[choice])
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
                message_ip, message_port = self.chat_client.message_socket.getsockname()
                response = self.chat_client.register_user(username)
                if response:
                    return "OK"
                else:
                    return "NOT OK"
        except Exception as e:
            print(f"An error ocurred while registering: {e}")
            return "NOT OK"

    
    def main_menu_ui(self):
        os.system('cls' if os.name == 'nt' else 'clear')
        print(f"Welcome, {self.chat_client.username}, to ✨Spark Chat✨!  Type /help if you need it.")

        self.print_unseen_resume()

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
            
            self.print_chat(self.interlocutor)
    
            self.update_chat_flag = True
            threading.Thread(target=self.update_chat, args=(self.interlocutor,), daemon=True).start()

            while True:
                command = input()

                if command.lower() == "/back":
                    self.interlocutor = None
                    self.update_chat_flag = False
                    return "MAIN"
                
                elif command:
                    # chat = self.chat_client.load_chat(self.interlocutor)  ############### Delete this line
                    # chat.append({"sender":self.chat_client.username, "text":command, "readed":True}) ############### Delete this line
                    # self.chat_client.save_chat(chat, self.interlocutor) ############### Delete this line

                    message = f"MESSAGE {self.chat_client.username} {command}"
                    if not self.chat_client.send_message(self.interlocutor, message):
                        self.chat_client.add_to_pending_list(self.interlocutor, message)

                    # if self.chat_client.is_user_online(recipient_address):
                    #     self.message_socket.sendto(f"MESSAGE {self.chat_client.username} {message}".encode(), recipient_address)
                    # else:
                    #     response = self.chat_client.send_command(f"RESOLVE {self.interlocutor}")
                    #     if response.startswith("OK"):
                    #         _, ip, port = response.split()
                    #         recipient_address = (ip, int(port))
                    #         if self.is_user_online(recipient_address):
                    #             self.message_socket.sendto(f"MESSAGE {self.chat_client.username} {message}".encode(), recipient_address)
                    #         else:
                    #             self.pending_list.append((self.interlocutor, f"MESSAGE {self.chat_client.username} {message}"))
                        # print(f"User {self.interlocutor} is offline. Message will be sent when user is online.")
                
        except Exception as e:
            print(f"Error in chat: {e}")
            self.interlocutor = None
            self.update_chat_flag = False
            time.sleep(3)
            return "MAIN"

# #endregion


if __name__ == "__main__":
    app = console_app()
    app.run_ui()



