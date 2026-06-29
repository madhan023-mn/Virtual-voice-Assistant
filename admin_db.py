import sqlite3
import os
from datetime import datetime

DB_PATH = 'developer_data.db'

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    c = conn.cursor()
    # Create user_status table for blocking
    c.execute('''
        CREATE TABLE IF NOT EXISTS user_status (
            username TEXT PRIMARY KEY,
            is_blocked BOOLEAN NOT NULL DEFAULT 0
        )
    ''')
    # Create login_logs table
    c.execute('''
        CREATE TABLE IF NOT EXISTS login_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            ip_address TEXT
        )
    ''')
    conn.commit()
    conn.close()

def is_user_blocked(username):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT is_blocked FROM user_status WHERE username = ?', (username,))
    row = c.fetchone()
    conn.close()
    if row:
        return bool(row['is_blocked'])
    return False

def set_user_blocked(username, blocked_status=True):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('''
        INSERT INTO user_status (username, is_blocked)
        VALUES (?, ?)
        ON CONFLICT(username) DO UPDATE SET is_blocked=excluded.is_blocked
    ''', (username, 1 if blocked_status else 0))
    conn.commit()
    conn.close()

def log_user_login(username, ip_address):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('''
        INSERT INTO login_logs (username, ip_address)
        VALUES (?, ?)
    ''', (username, ip_address))
    conn.commit()
    conn.close()

def get_all_user_statuses():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT username, is_blocked FROM user_status')
    rows = c.fetchall()
    conn.close()
    return [{'username': row['username'], 'is_blocked': bool(row['is_blocked'])} for row in rows]

def get_login_logs(username):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT timestamp, ip_address FROM login_logs WHERE username = ? ORDER BY timestamp DESC LIMIT 50', (username,))
    rows = c.fetchall()
    conn.close()
    return [{'timestamp': row['timestamp'], 'ip_address': row['ip_address']} for row in rows]

# Initialize db when module is imported
init_db()
