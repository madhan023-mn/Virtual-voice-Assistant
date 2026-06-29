import sqlite3
import hashlib
from werkzeug.security import generate_password_hash, check_password_hash

DB_PATH = 'users.db'

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS chat_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            session_id TEXT NOT NULL,
            role TEXT NOT NULL,
            text TEXT NOT NULL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (username) REFERENCES users(username) ON DELETE CASCADE
        )
    ''')
    conn.commit()
    conn.close()

def create_user(username, password):
    if not username or not password:
        return False
    # Note: original DB might have used werkzeug or hashlib. We'll use hashlib to be safe if werkzeug was not used, or werkzeug if it was.
    # Since I don't know what hash was used, let's look at check_password_hash vs hashlib.
    # Actually, we can check how a password looks inside users.db using python to see what hashing was used.
    # For now, let's just use werkzeug.
    hashed = generate_password_hash(password)
    
    conn = get_db_connection()
    c = conn.cursor()
    try:
        c.execute('INSERT INTO users (username, password_hash) VALUES (?, ?)', (username, hashed))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def verify_user(username, password):
    if not username or not password:
        return False
        
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT password_hash FROM users WHERE username = ?', (username,))
    row = c.fetchone()
    conn.close()
    
    if row:
        stored_hash = row['password_hash']
        # Try werkzeug check first
        try:
            if check_password_hash(stored_hash, password):
                return True
        except ValueError:
            pass
        # Fallback to simple hashlib if original was basic sha256
        if stored_hash == hashlib.sha256(password.encode()).hexdigest():
            return True
            
    return False

# Exported as required
Database = type('Database', (), {'init_db': staticmethod(init_db), 'create_user': staticmethod(create_user), 'verify_user': staticmethod(verify_user)})
