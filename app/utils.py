import base64

def generate_activation_code(device_id: str) -> str:
    # توليد كود التفعيل من رقم الجهاز (Base64 وأخذ أول 10 محارف)
    return base64.b64encode(device_id.encode()).decode()[:10]

def final_report(order_id: int, order: dict) -> str:
    return (
        f"📊 التقرير النهائي\n"
        f"رقم الطلب: #{order_id}\n"
        f"🔢 رمز نسختك الكاملة : {order.get('device_id','-')}\n"
        f"🧾 إشعار الدفع: {order.get('notify_msg','-')}\n"
        f"🖼️ صورة إشعار: {'✅ موجود' if order.get('proof_file_id') else '🚫 لا يوجد'}\n"
        f"🔑 كود التفعيل: {order.get('activation_code','-')}\n"
        f"📌 الحالة: {order.get('status','pending')}"
    )
