import sqlite3
import csv
import io
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent / "chatbot_logs.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS logs (
            id TEXT PRIMARY KEY,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            chat_id TEXT,
            user_query TEXT,
            bot_response TEXT,
            feedback INTEGER
        )
    ''')
    conn.commit()
    conn.close()

def log_interaction(message_id: str, chat_id: str, user_query: str, bot_response: str):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        INSERT OR IGNORE INTO logs (id, chat_id, user_query, bot_response)
        VALUES (?, ?, ?, ?)
    ''', (message_id, chat_id, user_query, bot_response))
    conn.commit()
    conn.close()

def update_feedback(message_id: str, feedback: int):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        UPDATE logs SET feedback = ? WHERE id = ?
    ''', (feedback, message_id))
    conn.commit()
    conn.close()

def get_all_logs():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM logs ORDER BY timestamp DESC")
    rows = c.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_logs_csv_string() -> str:
    logs = get_all_logs()
    if not logs:
        return ""
    
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=logs[0].keys())
    writer.writeheader()
    writer.writerows(logs)
    return output.getvalue()
