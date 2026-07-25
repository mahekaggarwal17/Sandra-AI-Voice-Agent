# database.py
import sqlite3
import os
import hashlib
import secrets
import json
import datetime

DB_PATH = 'memory.db'

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 1. Users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            phone_number TEXT
        )
    ''')
    
    # 2. OAuth tokens table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS oauth_tokens (
            user_id INTEGER PRIMARY KEY,
            token_json TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    ''')
    
    # 3. Conversations table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT UNIQUE NOT NULL,
            user_id INTEGER,
            timestamp TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    ''')
    
    # 4. Messages table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conversation_id TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            speaker TEXT NOT NULL,
            text TEXT NOT NULL,
            FOREIGN KEY (conversation_id) REFERENCES conversations(session_id) ON DELETE CASCADE
        )
    ''')
    
    # 5. User memory/profile (key-value scoped per user)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_profile (
            user_id INTEGER,
            key TEXT,
            value TEXT,
            PRIMARY KEY (user_id, key),
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    ''')
    
    conn.commit()
    conn.close()

# Password Helpers using PBKDF2
def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    pw_hash = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt.encode('utf-8'), 100000)
    return f"{salt}${pw_hash.hex()}"

def verify_password(stored_password_hash: str, provided_password: str) -> bool:
    try:
        salt, pw_hash = stored_password_hash.split('$')
        computed_hash = hashlib.pbkdf2_hmac('sha256', provided_password.encode('utf-8'), salt.encode('utf-8'), 100000)
        return computed_hash.hex() == pw_hash
    except Exception:
        return False

# User CRUD
def create_user(email: str, password: str, phone_number: str = None) -> int:
    init_db()
    pw_hash = hash_password(password)
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            'INSERT INTO users (email, password_hash, phone_number) VALUES (?, ?, ?)',
            (email, pw_hash, phone_number)
        )
        conn.commit()
        user_id = cursor.lastrowid
        return user_id
    except sqlite3.IntegrityError:
        raise Exception("User with this email already exists.")
    finally:
        conn.close()

def authenticate_user(email: str, password: str):
    init_db()
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT id, email, password_hash, phone_number FROM users WHERE email = ?', (email,))
    row = cursor.fetchone()
    conn.close()
    if row and verify_password(row['password_hash'], password):
        return {
            "id": row['id'],
            "email": row['email'],
            "phone_number": row['phone_number']
        }
    return None

def get_user_by_id(user_id: int):
    init_db()
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT id, email, phone_number FROM users WHERE id = ?', (user_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return dict(row)
    return None

def get_user_by_email(email: str):
    init_db()
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT id, email, phone_number FROM users WHERE email = ?', (email,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return dict(row)
    return None

# OAuth Token CRUD
def save_oauth_token(user_id: int, token_data: dict):
    init_db()
    conn = get_db_connection()
    cursor = conn.cursor()
    token_json = json.dumps(token_data)
    cursor.execute(
        'INSERT OR REPLACE INTO oauth_tokens (user_id, token_json) VALUES (?, ?)',
        (user_id, token_json)
    )
    conn.commit()
    conn.close()

def get_oauth_token(user_id: int) -> dict:
    init_db()
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT token_json FROM oauth_tokens WHERE user_id = ?', (user_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return json.loads(row['token_json'])
    return None

# Conversation Logs CRUD
def start_conversation(session_id: str, user_id: int = None):
    init_db()
    conn = get_db_connection()
    cursor = conn.cursor()
    timestamp = datetime.datetime.now().isoformat()
    cursor.execute(
        'INSERT OR IGNORE INTO conversations (session_id, user_id, timestamp) VALUES (?, ?, ?)',
        (session_id, user_id, timestamp)
    )
    conn.commit()
    conn.close()

def log_message(session_id: str, speaker: str, text: str, user_id: int = None):
    init_db()
    start_conversation(session_id, user_id)
    
    conn = get_db_connection()
    cursor = conn.cursor()
    timestamp = datetime.datetime.now().isoformat()
    cursor.execute(
        'INSERT INTO messages (conversation_id, timestamp, speaker, text) VALUES (?, ?, ?, ?)',
        (session_id, timestamp, speaker, text)
    )
    conn.commit()
    conn.close()

def get_conversation_history(session_id: str):
    init_db()
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        'SELECT speaker, text FROM messages WHERE conversation_id = ? ORDER BY timestamp ASC',
        (session_id,)
    )
    rows = cursor.fetchall()
    conn.close()
    return [(row['speaker'], row['text']) for row in rows]

def get_user_conversations(user_id: int):
    init_db()
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        'SELECT session_id, timestamp FROM conversations WHERE user_id = ? ORDER BY timestamp DESC',
        (user_id,)
    )
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

# User Profile / Memory CRUD
def update_profile(user_id: int, key: str, value: str):
    init_db()
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        'INSERT OR REPLACE INTO user_profile (user_id, key, value) VALUES (?, ?, ?)',
        (user_id, key, value)
    )
    conn.commit()
    conn.close()

def get_profile_context(user_id: int) -> str:
    init_db()
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT key, value FROM user_profile WHERE user_id = ?', (user_id,))
    rows = cursor.fetchall()
    conn.close()
    
    if not rows:
        return "No past memory found. Treat this as a new user."
        
    profile_details = []
    for row in rows:
        profile_details.append(f"- {row['key']}: {row['value']}")
        
    return "PAST USER PROFILE & MEMORIES:\n" + "\n".join(profile_details)
