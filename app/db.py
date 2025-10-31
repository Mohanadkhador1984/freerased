import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "bot.db"

def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db():
    conn = get_conn()
    c = conn.cursor()
    c.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY,              -- Telegram user_id
        username TEXT,
        phone TEXT,
        role TEXT DEFAULT 'customer',        -- customer | merchant | admin
        is_verified INTEGER DEFAULT 0,
        chat_id INTEGER,
        created_at TEXT DEFAULT (datetime('now'))
    )
    """)
    c.execute("""
    CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        to_phone TEXT NOT NULL,              -- رقم المستلم
        amount REAL NOT NULL,                -- المبلغ
        fee REAL DEFAULT 0,                  -- العمولة
        status TEXT DEFAULT 'PENDING',       -- PENDING | DONE | CANCELED
        note TEXT,
        created_at TEXT DEFAULT (datetime('now')),
        updated_at TEXT DEFAULT (datetime('now')),
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
    )
    """)
    conn.commit()
    conn.close()
