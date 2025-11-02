import re

def is_valid_phone(phone: str) -> bool:
    return bool(re.fullmatch(r"^09\d{8}$", phone.strip()))

def calc_extra_and_net(amount: int):
    extra = (amount // 1000) * 200
    return amount, extra, amount + extra

def order_summary(order_id: int, order: dict) -> str:
    amount, extra, net = calc_extra_and_net(order.get("amount", 0) or 0)
    paid = "✅ مدفوع" if order.get("paid") else "⏳ غير مدفوع"
    return (
        f"📩 ملخص الطلب\n"
        f"رقم الطلب: #{order_id}\n"
        f"👤 الاسم: {order.get('name','-')}\n"
        f"📱 الرقم: {order.get('phone','-')}\n"
        f"💰 المبلغ: {amount}\n"
        f"➕ الزيادة: {extra}\n"
        f"💵 الصافي: {net}\n"
        f"💳 حالة الدفع: {paid}"
    )

def final_report(order_id: int, order: dict) -> str:
    amount, extra, net = calc_extra_and_net(order.get("amount", 0) or 0)
    return (
        f"📊 التقرير النهائي\n"
        f"رقم الطلب: #{order_id}\n"
        f"👤 الاسم: {order.get('name','-')}\n"
        f"📱 الرقم: {order.get('phone','-')}\n"
        f"💰 المبلغ: {amount}\n"
        f"➕ الزيادة: {extra}\n"
        f"💵 الصافي: {net}\n"
        f"🔢 رقم العملية: {order.get('transaction_id','-')}\n"
        f"🧾 آخر نص لإشعار الدفع: {order.get('notify_msg','-')}\n"
        f"🖼️ آخر صورة/ملف إشعار: {'✅ موجود' if order.get('proof_file_id') else '🚫 لا يوجد'}\n"
        f"💳 حالة الدفع: {'✅ مدفوع' if order.get('paid') else '⏳ غير مدفوع'}\n"
        f"📌 الحالة: {order.get('status','pending')}"
    )

def extract_transaction_id(text: str) -> str | None:
    if not text:
        return None
    m = re.search(r"\b(\d{6,})\b", text)
    return m.group(1) if m else None
