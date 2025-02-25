import sqlite3
import os

class server_db:
    def __init__(self):
        self.db_directory = "db"
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