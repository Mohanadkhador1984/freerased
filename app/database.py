import sqlite3
from pathlib import Path

DB_PATH = Path("bot.db")

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            app_name TEXT,
            device_id TEXT,
            notify_msg TEXT,
            proof_file_id TEXT,
            activation_code TEXT,
            status TEXT DEFAULT 'pending',
            team_msg_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

def add_order(user_id: int, app_name: str, notify_msg: str = None, device_id: str = None) -> int:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO orders (user_id, app_name, device_id, notify_msg, status) VALUES (?, ?, ?, ?, 'pending')",
        (user_id, app_name, device_id, notify_msg)
    )
    conn.commit()
    oid = cur.lastrowid
    conn.close()
    return oid

def update_order(order_id: int, **kwargs):
    """تحديث أي حقل في الطلب"""
    if not kwargs:
        return
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    fields = ", ".join([f"{k}=?" for k in kwargs.keys()])
    values = list(kwargs.values())
    values.append(order_id)
    cur.execute(f"UPDATE orders SET {fields} WHERE id=?", values)
    conn.commit()
    conn.close()

def get_order(order_id: int):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        SELECT id,user_id,app_name,device_id,notify_msg,proof_file_id,activation_code,status,team_msg_id,created_at
        FROM orders WHERE id=?
    """, (order_id,))
    row = cur.fetchone()
    conn.close()
    if not row:
        return None
    keys = ["id","user_id","app_name","device_id","notify_msg","proof_file_id","activation_code","status","team_msg_id","created_at"]
    return dict(zip(keys, row))
