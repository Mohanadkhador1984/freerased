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
        name TEXT,
        phone TEXT,
        amount INTEGER,
        paid INTEGER DEFAULT 0,
        status TEXT DEFAULT 'pending',  -- pending | done | canceled
        transaction_id TEXT,
        notify_msg TEXT,                -- آخر نص لإشعار الدفع (من الزبون أو التاجر)
        proof_file_id TEXT,             -- آخر صورة/ملف لإشعار الدفع
        merchant_msg_id INTEGER,        -- الرسالة الرئيسية لدى التاجر (ذات الأزرار)
        final_msg_id INTEGER,           -- التقرير النهائي لدى التاجر
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    conn.commit()
    conn.close()

def add_order(user_id: int, name: str, phone: str, amount: int) -> int:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO orders (user_id, name, phone, amount, status) VALUES (?, ?, ?, ?, 'pending')",
        (user_id, name, phone, amount)
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
        SELECT id,user_id,name,phone,amount,paid,status,transaction_id,notify_msg,proof_file_id,
               merchant_msg_id,final_msg_id,created_at
        FROM orders WHERE id=?
    """, (order_id,))
    row = cur.fetchone()
    conn.close()
    if not row:
        return None
    keys = ["id","user_id","name","phone","amount","paid","status","transaction_id","notify_msg",
            "proof_file_id","merchant_msg_id","final_msg_id","created_at"]
    return dict(zip(keys, row))
