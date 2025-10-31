from telegram import InlineKeyboardButton, InlineKeyboardMarkup

def customer_menu():
    keyboard = [
        [InlineKeyboardButton("➕ طلب تحويل", callback_data="new_order")]
    ]
    return InlineKeyboardMarkup(keyboard)

def merchant_menu():
    keyboard = [
        [InlineKeyboardButton("📋 الطلبات الجديدة", callback_data="pending")],
        [InlineKeyboardButton("✅ تم التنفيذ", callback_data="done")],
        [InlineKeyboardButton("❌ إلغاء", callback_data="cancel")]
    ]
    return InlineKeyboardMarkup(keyboard)

def validate_customer_input(text: str):
    """
    يتوقع إدخال z: '09XXXXXXXX 5000'
    يرجع (phone, amount_str) أو (None, None) إذا الصيغة خاطئة
    """
    parts = text.strip().split()
    if len(parts) != 2:
        return None, None
    phone, amount = parts
    # تحقق مبسط للرقم السوري
    if not (phone.isdigit() and phone.startswith("09") and len(phone) == 10):
        return None, None
    # تحقق المبلغ رقم
    if not amount.replace(".", "", 1).isdigit():
        return None, None
    return phone, amount
