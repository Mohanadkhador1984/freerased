import sqlite3
from pathlib import Path

DB_PATH = Path("bot.db")

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    # جدول الطلبات
    cur.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            device_id TEXT,
            notify_msg TEXT,
            proof_file_id TEXT,
            activation_code TEXT,
            status TEXT DEFAULT 'pending',
            team_msg_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    # جدول الزوار
    cur.execute("""
        CREATE TABLE IF NOT EXISTS visitors (
            user_id INTEGER PRIMARY KEY,
            first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    # جدول المشتركين في الإشعارات
    cur.execute("""
        CREATE TABLE IF NOT EXISTS subscribers (
            user_id INTEGER PRIMARY KEY,
            first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_broadcast TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

def add_visitor(user_id: int):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("INSERT OR IGNORE INTO visitors (user_id) VALUES (?)", (user_id,))
    conn.commit()
    conn.close()

def count_visitors() -> int:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM visitors")
    count = cur.fetchone()[0]
    conn.close()
    return count

def add_order(user_id: int, device_id: str, notify_msg: str = None) -> int:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO orders (user_id, device_id, notify_msg, status) VALUES (?, ?, ?, 'pending')",
        (user_id, device_id, notify_msg)
    )
    conn.commit()
    oid = cur.lastrowid
    conn.close()
    return oid

def update_order(order_id: int, **kwargs):
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
        SELECT id,user_id,device_id,notify_msg,proof_file_id,activation_code,status,team_msg_id,created_at
        FROM orders WHERE id=?
    """, (order_id,))
    row = cur.fetchone()
    conn.close()
    if not row:
        return None
    keys = ["id","user_id","device_id","notify_msg","proof_file_id","activation_code","status","team_msg_id","created_at"]
    return dict(zip(keys, row))

# إدارة المشتركين (للإرسال الجماعي)
def add_subscriber(user_id: int):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("INSERT OR IGNORE INTO subscribers (user_id) VALUES (?)", (user_id,))
    conn.commit()
    conn.close()

def get_subscribers(limit: int = None, offset: int = 0):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    q = "SELECT user_id FROM subscribers ORDER BY first_seen ASC"
    if limit is not None:
        q += " LIMIT ? OFFSET ?"
        cur.execute(q, (limit, offset))
    else:
        cur.execute(q)
    rows = cur.fetchall()
    conn.close()
    return [r[0] for r in rows]

def count_subscribers() -> int:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM subscribers")
    count = cur.fetchone()[0]
    conn.close()
    return count

def mark_broadcast_sent(user_id: int):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("UPDATE subscribers SET last_broadcast=CURRENT_TIMESTAMP WHERE user_id=?", (user_id,))
    conn.commit()
    conn.close()

def remove_subscriber(user_id: int):
    # يمكن استخدامها لاحقًا إذا رغبت بإلغاء الاشتراك
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("DELETE FROM subscribers WHERE user_id=?", (user_id,))
    conn.commit()
    conn.close()