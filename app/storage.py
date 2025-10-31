from typing import Optional, List, Dict
from app.db import get_conn

def ensure_user(user_id: int, username: Optional[str], chat_id: Optional[int]) -> None:
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT id FROM users WHERE id = ?", (user_id,))
    if not c.fetchone():
        c.execute("INSERT INTO users (id, username, chat_id) VALUES (?, ?, ?)", (user_id, username, chat_id))
    else:
        c.execute("UPDATE users SET username = ?, chat_id = ? WHERE id = ?", (username, chat_id, user_id))
    conn.commit()
    conn.close()

def set_user_role(user_id: int, role: str) -> None:
    conn = get_conn()
    c = conn.cursor()
    c.execute("UPDATE users SET role = ? WHERE id = ?", (role, user_id))
    conn.commit()
    conn.close()

def link_phone(user_id: int, phone: str) -> None:
    conn = get_conn()
    c = conn.cursor()
    c.execute("UPDATE users SET phone = ?, is_verified = 1 WHERE id = ?", (phone, user_id))
    conn.commit()
    conn.close()

def create_order(user_id: int, to_phone: str, amount: float, fee: float = 0) -> int:
    conn = get_conn()
    c = conn.cursor()
    c.execute("""
        INSERT INTO orders (user_id, to_phone, amount, fee, status)
        VALUES (?, ?, ?, ?, 'PENDING')
    """, (user_id, to_phone, amount, fee))
    order_id = c.lastrowid
    conn.commit()
    conn.close()
    return order_id

def list_orders(status: Optional[str] = None, limit: int = 20) -> List[Dict]:
    conn = get_conn()
    c = conn.cursor()
    if status:
        c.execute("""
            SELECT id, user_id, to_phone, amount, fee, status, created_at
            FROM orders WHERE status = ? ORDER BY id DESC LIMIT ?
        """, (status, limit))
    else:
        c.execute("""
            SELECT id, user_id, to_phone, amount, fee, status, created_at
            FROM orders ORDER BY id DESC LIMIT ?
        """, (limit,))
    rows = c.fetchall()
    conn.close()
    return [
        {
            "id": r[0], "user_id": r[1], "to_phone": r[2], "amount": r[3],
            "fee": r[4], "status": r[5], "created_at": r[6]
        } for r in rows
    ]

def list_user_orders(user_id: int, limit: int = 20) -> List[Dict]:
    conn = get_conn()
    c = conn.cursor()
    c.execute("""
        SELECT id, user_id, to_phone, amount, fee, status, created_at
        FROM orders WHERE user_id = ? ORDER BY id DESC LIMIT ?
    """, (user_id, limit))
    rows = c.fetchall()
    conn.close()
    return [
        {
            "id": r[0], "user_id": r[1], "to_phone": r[2], "amount": r[3],
            "fee": r[4], "status": r[5], "created_at": r[6]
        } for r in rows
    ]

def update_order_status(order_id: int, status: str, note: Optional[str] = None) -> bool:
    conn = get_conn()
    c = conn.cursor()
    c.execute("""
        UPDATE orders SET status = ?, note = ?, updated_at = datetime('now') WHERE id = ?
    """, (status, note, order_id))
    conn.commit()
    ok = c.rowcount > 0
    conn.close()
    return ok
