import os
import itertools
import logging
from typing import Dict, Any, List, Tuple

logger = logging.getLogger(__name__)

MERCHANT_ID_STR = os.getenv("MERCHANT_ID")
try:
    MERCHANT_ID = int(MERCHANT_ID_STR) if MERCHANT_ID_STR else None
except ValueError:
    MERCHANT_ID = None

MERCHANT_PHONE = os.getenv("MERCHANT_PHONE", "غير محدد")
MERCHANT_QR = os.getenv("MERCHANT_QR", None)

# مولد أرقام الطلبات
_order_id_counter = itertools.count(1001)

# قاعدة بيانات مؤقتة بالذاكرة
ORDERS: Dict[int, Dict[str, Any]] = {}
merchant_final_msg_id: Dict[int, int] = {}
customer_conversations: Dict[tuple, List[int]] = {}
merchant_temp_msgs: Dict[int, List[int]] = {}

def is_merchant(uid: int) -> bool:
    return MERCHANT_ID is not None and uid == MERCHANT_ID

def fmt_paid(paid: bool) -> str:
    return "✅ مدفوع" if paid else "⏳ غير مدفوع"

def calc_extra_and_net(amount_str: str) -> Tuple[int, int, int]:
    try:
        amount = int(str(amount_str).strip())
    except Exception:
        amount = 0
    extra = (amount // 1000) * 200
    net_amount = amount + extra
    return amount, extra, net_amount

def badge_status(order: Dict[str, Any]) -> str:
    if order.get("status") == "new":
        return "🟦 جديد"
    if order.get("status") == "done":
        return "🟢 منفّذ" if order.get("paid") else "🔴 منفّذ (بدون دفع)"
    if order.get("status") == "canceled":
        return "⚫️ مُلغى"
    return "⚪️ غير معروف"

def order_header(order_id: int, order: Dict[str, Any]) -> str:
    return f"رقم الطلب: #{order_id}"

def order_summary(order_id: int, order: Dict[str, Any]) -> str:
    paid_status = fmt_paid(order.get("paid", False))
    amount_str = str(order.get("amount", 0))
    status = badge_status(order)
    lines = [
        "📩 ملخص الطلب",
        order_header(order_id, order),
        status,
        "",
        f"👤 الاسم: {order.get('name', '-')}",
        f"📱 الرقم: {order.get('phone', '-')}",
        f"🟡 الشبكة: {order.get('network', '-')}",
        f"💰 المبلغ: {amount_str}",
        f"💳 حالة الدفع: {paid_status}",
    ]
    if order.get("notify_msg"):
        lines.append(f"📥 إشعار الدفع: موجود")
    if order.get("transaction_id"):
        lines.append(f"🔢 رقم العملية: {order.get('transaction_id')}")
    return "\n".join(lines)

def final_report_text(order_id: int, order: Dict[str, Any]) -> str:
    paid = order.get("paid", False)
    amount, extra, net_amount = calc_extra_and_net(str(order.get("amount", 0)))
    paid_status = fmt_paid(paid)
    status = badge_status(order)
    notify_line = "🚫 لا يوجد"
    if order.get("notify_msg"):
        notify_line = "✅ أُرسل"

    lines = [
        "📊 التقرير النهائي",
        order_header(order_id, order),
        status,
        "",
        f"👤 الاسم: {order.get('name', '-')}",
        f"📱 الرقم: {order.get('phone', '-')}",
        f"🟡 الشبكة: {order.get('network', '-')}",
        f"💰 المبلغ المطلوب: {amount}",
        f"➕ الزيادة: {extra}",
        f"💵 الصافي المطلوب: {net_amount}",
        f"💳 حالة الدفع: {paid_status}",
        f"📥 إشعار الدفع: {notify_line}",
    ]
    if order.get("transaction_id"):
        lines.append(f"🔢 رقم العملية: {order['transaction_id']}")
    if order.get("notify_msg"):
        lines.append("\n🧾 نص الإشعار:")
        lines.append(order["notify_msg"])
    return "\n".join(lines)

def next_order_id() -> int:
    return next(_order_id_counter)