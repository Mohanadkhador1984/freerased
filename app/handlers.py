from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from .database import add_order, update_order, get_order
from .utils import generate_activation_code, final_report
from .config import MERCHANT_ID

def team_keyboard(order_id: int):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔑 إرسال كود التفعيل", callback_data=f"activate:{order_id}")],
        [InlineKeyboardButton("❌ إلغاء الطلب", callback_data=f"cancel:{order_id}")]
    ])

def new_order_keyboard():
    return InlineKeyboardMarkup([[InlineKeyboardButton("🔄 طلب جديد", callback_data="new_order")]])

def send_team_keyboard(order_id: int):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📤 إرسال لفريق العمل", callback_data=f"send_team:{order_id}")]
    ])

# بدء البوت
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_photo(
        photo=open("qr.png", "rb"),
        caption=(
            "💳 تعليمات الدفع:\n"
            "1️⃣ امسح الباركود أعلاه أو أرسل المبلغ إلى الباركود: ce95cda303cc0c382736307089e2ddeb\n"
            "2️⃣ بعد الدفع، أرسل اسم التطبيق الذي تريد شراءه:\n"
            "   - MQBank\n"
            "   - Bacly"
        )
    )

# استقبال النصوص
async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    text = update.message.text.strip()

    # الخطوة 1: اسم التطبيق
    if "app_name" not in context.user_data:
        context.user_data["app_name"] = text
        await update.message.reply_text("📱 أرسل الآن الرقم الخاص بجهازك (32 خانة).")
        return

    # الخطوة 2: Device ID
    if "device_id" not in context.user_data:
        context.user_data["device_id"] = text
        await update.message.reply_text("📸 أرسل الآن صورة أو نص إشعار الدفع.")
        return

    # الخطوة 3: إشعار الدفع كنص
    if "notify_msg" not in context.user_data:
        context.user_data["notify_msg"] = text
        order_id = add_order(user.id, context.user_data["app_name"], text, context.user_data["device_id"])
        context.user_data["order_id"] = order_id

        await update.message.reply_text(
            "✅ تم استلام إشعار الدفع.\n"
            "اضغط الزر لإرسال الطلب لفريق العمل.",
            reply_markup=send_team_keyboard(order_id)
        )
        return

# استقبال صورة إشعار الدفع
async def proof_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    order_id = context.user_data.get("order_id")

    file_id = update.message.photo[-1].file_id if update.message.photo else update.message.document.file_id

    if not order_id:
        order_id = add_order(user.id, context.user_data.get("app_name","-"), "صورة إشعار", context.user_data.get("device_id","-"))
        context.user_data["order_id"] = order_id

    update_order(order_id, proof_file_id=file_id)

    await update.message.reply_text(
        "✅ تم استلام صورة إشعار الدفع.\n"
        "اضغط الزر لإرسال الطلب لفريق العمل.",
        reply_markup=send_team_keyboard(order_id)
    )

# أزرار فريق العمل
async def team_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    parts = query.data.split(":")
    action = parts[0]
    order_id = int(parts[1]) if len(parts) > 1 else None

    if action == "new_order":
        context.user_data.clear()
        await query.message.reply_text(
            "📱 أرسل اسم التطبيق الذي تريد شراءه:\n- MQBank\n- Bacly"
        )
        return

    order = get_order(order_id) if order_id else None
    if not order:
        await query.message.reply_text("❌ الطلب غير موجود.")
        return

    # إرسال الطلب لفريق العمل
    if action == "send_team":
        msg = await context.bot.send_message(
            chat_id=MERCHANT_ID,
            text=(
                f"🟦 طلب جديد #{order_id}\n"
                f"📱 التطبيق: {order['app_name']}\n"
                f"🔢 رقم الجهاز: {order['device_id']}\n"
                f"🧾 إشعار: {order['notify_msg'] or '-'}"
            ),
            reply_markup=team_keyboard(order_id)
        )
        if order.get("proof_file_id"):
            await context.bot.send_photo(
                chat_id=MERCHANT_ID,
                photo=order["proof_file_id"],
                caption=f"🖼️ صورة إشعار الدفع لطلب #{order_id}"
            )

        update_order(order_id, team_msg_id=msg.message_id)

        await query.message.reply_text("📤 تم إرسال طلبك لفريق العمل ✅", reply_markup=new_order_keyboard())
        context.user_data.clear()
        return

    # فريق العمل: إرسال كود التفعيل
    if action == "activate":
        code = generate_activation_code(order["device_id"])
        update_order(order_id, activation_code=code, status="done")

        # إرسال الكود للزبون
        await context.bot.send_message(
            chat_id=order["user_id"],
            text=f"🔑 كود التفعيل الخاص بجهازك: {code}"
        )

        # تقرير نهائي للطرفين
        report = final_report(order_id, get_order(order_id))
        await context.bot.send_message(chat_id=MERCHANT_ID, text=report)
        await context.bot.send_message(chat_id=order["user_id"], text=report, reply_markup=new_order_keyboard())

        # حذف رسائل الطلب المؤقتة
        if order.get("team_msg_id"):
            try:
                await context.bot.delete_message(chat_id=MERCHANT_ID, message_id=order["team_msg_id"])
            except:
                pass
        try:
            await query.message.delete()
        except:
            pass
        return

    # فريق العمل: إلغاء الطلب
    if action == "cancel":
        update_order(order_id, status="canceled")
        await context.bot.send_message(chat_id=order["user_id"], text="❌ تم إلغاء طلبك.", reply_markup=new_order_keyboard())
        return
