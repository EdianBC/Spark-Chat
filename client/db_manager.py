import sqlite3
import os

class user_db:
    def __init__(self):
        self.db_directory = "chats"
        self.db_route = ""
        # conn = sqlite3.connect("users.db")

    def set_db(self, username):     
        
        os.makedirs(self.db_directory, exist_ok=True)
        self.db_route = os.path.join(self.db_directory, f"{username}.db")

        conn = sqlite3.connect(self.db_route, check_same_thread=False)
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
        conn = sqlite3.connect(self.db_route, check_same_thread=False)
        cursor = conn.cursor()
                
        cursor.execute("INSERT INTO messages (author, receiver, text, seen) VALUES (?, ?, ?, ?)", (author, receiver, text, seen))
        conn.commit()

        conn.close()

    def get_chat(self, user1, user2):
        
        conn = sqlite3.connect(self.db_route, check_same_thread=False)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT *
            FROM messages
            WHERE (author = ? AND receiver = ?)
            OR (author = ? AND receiver = ?)
            ORDER BY date_time ASC
        ''', (user1, user2, user2, user1))

        chat = cursor.fetchall()
        
        conn.commit()
        conn.close()
        return chat
    
    def get_unseen_messages(self, user1, user2):
        conn = sqlite3.connect(self.db_route, check_same_thread=False)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT *
            FROM messages
            WHERE author = ? AND receiver = ? AND seen = 0
        ''', (user2, user1))

        unseen_messages = cursor.fetchall()

        conn.commit()
        conn.close()

        # print(f"Unseen {user1} - {user2}")

        return unseen_messages
    
    def set_messages_as_seen(self, user1, user2):
        conn = sqlite3.connect(self.db_route, check_same_thread=False)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE messages
            SET seen = 1
            WHERE author = ? AND receiver = ?
        ''', (user2, user1))

        conn.commit()
        conn.close()

        # print(f"Visto {user1} - {user2}")
        
    def get_unseen_resume(self, user):
        conn = sqlite3.connect(self.db_route, check_same_thread=False)
        cursor = conn.cursor()

        cursor.execute('''
            SELECT author, COUNT(*) 
            FROM messages 
            WHERE receiver = ? AND seen = 0
            GROUP BY author
        ''', (user,))
        unseen_resume = cursor.fetchall()

        conn.close()
        return unseen_resume