import os
import itertools
import logging
from typing import Dict, Any, List, Tuple

logger = logging.getLogger(__name__)

# بيئة
MERCHANT_ID_STR = os.getenv("MERCHANT_ID")
try:
    MERCHANT_ID = int(MERCHANT_ID_STR) if MERCHANT_ID_STR else None
except ValueError:
    MERCHANT_ID = None

MERCHANT_PHONE = os.getenv("MERCHANT_PHONE", "غير محدد")
MERCHANT_QR = os.getenv("MERCHANT_QR", None)

# مولد أرقام الطلبات
_order_id_counter = itertools.count(1001)

# قاعدة بيانات بسيطة داخل الذاكرة
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
    notice = ""
    if order.get("notify_msg"):
        notice = "\n\n📥 إشعار الدفع موجود."
    return (
        f"📩 ملخص الطلب\n"
        f"{order_header(order_id, order)}\n"
        f"{status}\n\n"
        f"👤 الاسم: {order.get('name', '-')}\n"
        f"📱 الرقم: {order.get('phone', '-')}\n"
        f"💰 المبلغ: {amount_str}\n"
        f"💳 حالة الدفع: {paid_status}"
        f"{notice}"
    )

def final_report_text(order_id: int, order: Dict[str, Any]) -> str:
    paid = order.get("paid", False)
    amount, extra, net_amount = calc_extra_and_net(str(order.get("amount", 0)))
    paid_status = fmt_paid(paid)
    status = badge_status(order)
    notify_line = "🚫 لا يوجد"
    if order.get("notify_msg"):
        notify_line = "✅ أُرسل"
    return (
        f"📊 التقرير النهائي\n"
        f"{order_header(order_id, order)}\n"
        f"{status}\n\n"
        f"👤 الاسم: {order.get('name', '-')}\n"
        f"📱 الرقم: {order.get('phone', '-')}\n"
        f"💰 المبلغ المطلوب: {amount}\n"
        f"➕ الزيادة: {extra}\n"
        f"💵 الصافي المطلوب: {net_amount}\n"
        f"💳 حالة الدفع: {paid_status}\n"
        f"📥 إشعار الدفع: {notify_line}"
        + (f"\n\n🧾 نص الإشعار:\n{order['notify_msg']}" if order.get("notify_msg") else "")
    )

def next_order_id() -> int:
    return next(_order_id_counter)