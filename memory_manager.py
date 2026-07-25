import sqlite3
import os
import datetime

DB_PATH = 'memory.db'

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # User Profile table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_profile (
            user_email TEXT,
            key TEXT,
            value TEXT,
            PRIMARY KEY (user_email, key)
        )
    ''')
    
    # Conversations table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT,
            timestamp TEXT,
            speaker TEXT,
            text TEXT
        )
    ''')
    
    conn.commit()
    conn.close()

def get_profile_context(user_email: str = None) -> str:
    """Returns a summarized string of the user profile to be injected into the system prompt."""
    init_db()
    if not user_email:
        user_email = 'default_user'
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT key, value FROM user_profile WHERE user_email = ?', (user_email,))
    rows = cursor.fetchall()
    conn.close()
    
    if not rows:
        return "No past memory found. Treat this as a new user."
        
    profile_details = []
    for key, val in rows:
        profile_details.append(f"- {key}: {val}")
        
    return f"PAST USER PROFILE & MEMORIES FOR {user_email}:\n" + "\n".join(profile_details)

def update_profile(key: str, value: str, user_email: str = None):
    init_db()
    if not user_email:
        user_email = 'default_user'
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('INSERT OR REPLACE INTO user_profile (user_email, key, value) VALUES (?, ?, ?)', (user_email, key, value))
    conn.commit()
    conn.close()

def log_conversation(session_id: str, speaker: str, text: str):
    init_db()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    timestamp = datetime.datetime.now().isoformat()
    cursor.execute('INSERT INTO conversations (session_id, timestamp, speaker, text) VALUES (?, ?, ?, ?)',
                   (session_id, timestamp, speaker, text))
    conn.commit()
    conn.close()

def get_session_history(session_id: str):
    init_db()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT speaker, text FROM conversations WHERE session_id = ? ORDER BY timestamp ASC', (session_id,))
    rows = cursor.fetchall()
    conn.close()
    return rows
