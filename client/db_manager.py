import sqlite3
import os

class user_db:
    def __init__(self):
        self.db_directory = "chats"
        self.db_route = ""

    def set_db(self, username):     
        
        os.makedirs(self.db_directory, exist_ok=True)
        self.db_route = os.path.join(self.db_directory, f"{username}.db")

        conn = sqlite3.connect(self.db_route)
        cursor = conn.cursor()

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS chats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                author TEXT NOT NULL,
                receiver TEXT NOT NULL,
                text TEXT NOT NULL,
                date_time DATETIME DEFAULT CURRENT_TIMESTAMP,
                seen BOOLEAN DEFAULT 0
            )
        ''')

        conn.commit()
        conn.close()

        print(f"Base de datos creada para el usuario: {username}")

    
    def insert_new_message(self, author, receiver, text, seen):
        conn = sqlite3.connect(self.db_route)
        cursor = conn.cursor()
                
        cursor.execute("INSERT INTO messages (author, receiver, text, seen) VALUES (?, ?, ?, ?)", (author, receiver, text, seen))
        conn.commit()

        conn.close()

    def get_chat(self, user1, user2):
        
        conn = sqlite3.connect(self.db_route)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT *
            FROM messages
            WHERE (author = ? AND receiver = ?)
            OR (author = ? AND receiver = ?)
            ORDER BY date_time ASC
        ''', (user1, user2, user2, user1))

        chat = cursor.fetchall()
        
        conn.close()
        return chat
        
