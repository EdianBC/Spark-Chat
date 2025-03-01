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
            CREATE TABLE IF NOT EXISTS groups (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                group_name TEXT NOT NULL
            )
        ''')

        conn.commit()
        conn.close()

        def register_user(self, username, ip, port):
            try:
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
                        message = f"User {username} updated successfully"
                    else:
                        # Insertar nuevo usuario
                        cursor.execute('''
                            INSERT INTO users (username, ip, port)
                            VALUES (?, ?, ?)
                        ''', (username, ip, port))
                        message = f"User {username} registered successfully"
                    
                    conn.commit()
                    return message
                    
            except sqlite3.Error as e:
                return f"Database error: {str(e)}"
            except Exception as e:
                return f"General error: {str(e)}"