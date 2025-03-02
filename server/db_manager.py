import sqlite3
import os

class server_db:
    def __init__(self):
        self.db_directory = "server/db"
        self.db_route = ""


    def set_db(self, username):     
        os.makedirs(self.db_directory, exist_ok=True)
        self.db_route = os.path.join(self.db_directory, f"{username}.db")

        conn = sqlite3.connect(self.db_route, check_same_thread=False)
        cursor = conn.cursor()

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                ip TEXT NOT NULL,
                port INTEGER NOT NULL
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS replic_users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                ip TEXT NOT NULL,
                port INTEGER NOT NULL,
                owner TEXT NOT NULL
            )
        ''')

        conn.commit()
        conn.close()


    def register_user(self, username, ip, port):
        with sqlite3.connect(self.db_route, check_same_thread=False) as conn:
            cursor = conn.cursor()
            
            # Verificar si el usuario ya existe
            cursor.execute('''
                SELECT id FROM users WHERE username = ?
            ''', (username,))
            
            existing_user = cursor.fetchone()
            
            if existing_user:
                # Actualizar información existente
                cursor.execute('''
                    UPDATE users 
                    SET ip = ?, port = ?
                    WHERE username = ?
                ''', (ip, port, username))
            else:
                # Insertar nuevo usuario
                cursor.execute('''
                    INSERT INTO users (username, ip, port)
                    VALUES (?, ?, ?)
                ''', (username, ip, port))

            conn.commit()
        
    def register_replic_user(self, username, ip, port, owner):
        with sqlite3.connect(self.db_route, check_same_thread=False) as conn:
            cursor = conn.cursor()
            
            # Verificar si el usuario ya existe
            cursor.execute('''
                SELECT id FROM replic_users WHERE username = ?
            ''', (username,))
            
            existing_user = cursor.fetchone()
            
            if existing_user:
                # Actualizar información existente
                cursor.execute('''
                    UPDATE replic_users 
                    SET ip = ?, port = ?, owner = ?
                    WHERE username = ?
                ''', (ip, port, owner, username))
            else:
                # Insertar nuevo usuario
                cursor.execute('''
                    INSERT INTO replic_users (username, ip, port, owner)
                    VALUES (?, ?, ?, ?)
                ''', (username, ip, port, owner))

            conn.commit()
        
    def resolve_user(self, username):
        with sqlite3.connect(self.db_route, check_same_thread=False) as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT ip, port FROM users WHERE username = ?
            ''', (username,))
            
            address = cursor.fetchone()
            # print(address)
            return address
        

    def get_bd_copy(self):
        with sqlite3.connect(self.db_route, check_same_thread=False) as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT username, ip, port FROM users
            ''')

            data = cursor.fetchall()
            return data


    def get_alien_users(self, lower_bound, upper_bound, hash_function):
        with sqlite3.connect(self.db_route, check_same_thread=False) as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT username, ip, port FROM users
            ''')

            data = cursor.fetchall()
            alien_users = []
            for user in data:
                user_hash = hash_function(user[0])
                if user_hash < lower_bound or user_hash > upper_bound:
                    alien_users.append(user)

            return alien_users
        
    def delete_user(self, username):
        with sqlite3.connect(self.db_route, check_same_thread=False) as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                DELETE FROM users WHERE username = ?
            ''', (username,))
            
            conn.commit()

    def drop_replics(self, owner):
        with sqlite3.connect(self.db_route, check_same_thread=False) as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                DELETE FROM replic_users WHERE owner = ?
            ''', (owner,))

            conn.commit()

    def get_replics(self, owner):
        with sqlite3.connect(self.db_route, check_same_thread=False) as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT username, ip, port FROM replic_users WHERE owner = ?
            ''', (owner,))

            data = cursor.fetchall()

            return data