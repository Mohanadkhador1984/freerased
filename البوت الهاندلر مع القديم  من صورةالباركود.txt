import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from .database import (
    add_order, update_order, get_order,
    add_visitor, count_visitors, add_subscriber
)
from .utils import generate_activation_code, final_report
from .config import MERCHANT_ID

logger = logging.getLogger(__name__)

# أزرار
def team_keyboard(order_id: int):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔑 إرسال كود التفعيل", callback_data=f"activate:{order_id}")],
        [InlineKeyboardButton("❌ إلغاء الطلب", callback_data=f"cancel:{order_id}")]
    ])

def new_order_keyboard():
    return InlineKeyboardMarkup([[InlineKeyboardButton("🔄 طلب جديد", callback_data="new_order")]])

def send_team_keyboard(order_id: int):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📤 إرسال", callback_data=f"send_team:{order_id}")]
    ])

# بدء البوت
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    context.user_data.clear()

    if user:
        try:
            add_visitor(user.id)
            add_subscriber(user.id)
        except Exception as e:
            logger.warning(f"Visitor/subscriber insert failed: {e}")

    total = count_visitors()

    await update.message.reply_text("⏳ جارٍ تجهيز الخدمة... يرجى الانتظار لحظات.")

    # إشعار التاجر بفتح البوت
    try:
        await context.bot.send_message(
            chat_id=MERCHANT_ID,
            text=(
                f"📢 إشعار جديد:\n"
                f"👤 زائر جديد: {user.full_name if user else '-'} (ID: {user.id if user else '-'})\n"
                f"📊 إجمالي الزوار الآن: {total}"
            )
        )
    except Exception as e:
        logger.warning(f"Failed to notify merchant: {e}")

    # إرسال تعليمات + صورة
    try:
        await update.message.reply_photo(
            photo=open("qr.png", "rb"),
            caption=(
                "⚠️ تنويه هام\n"
                "قد يتأخر رد البوت أحيانًا لمدّة لا تتجاوز دقيقة واحدة نتيجة الضغط.\n\n"
                "في حال تأخر أكثر من ذلك، أرسل رمز النسخة الكاملة عبر واتساب من داخل التطبيق.\n\n"
                "طرق الدفع:\n"
                "1) الشام كاش:\n"
                "- امسح باركود الحساب في الأعلى أو استخدم العنوان:\n"
                "`ce95cda303cc0c382736307089e2ddeb`\n\n"
                "2) سيريتل كاش:\n"
                "- تحويل كاش يدوي إلى الرقم: `0997625546` (ليس تعبئة وحدات).\n\n"
                "الخطوة التالية:\n"
                "- انسخ رمز النسخة الكاملة من التطبيق، ثم الصقه هنا وأرسله.\n"
            )
        )
    except FileNotFoundError:
        await update.message.reply_text(
            "⚠️ لم يتم العثور على صورة QR (qr.png). اكمل الخطوات دون الصورة.\n"
            "أرسل رمز النسخة الكاملة هنا للمتابعة."
        )

# إحصائيات الزوار (للتاجر فقط)
async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not user or user.id != MERCHANT_ID:
        return
    total = count_visitors()
    await update.message.reply_text(f"📊 عدد الزوار الذين ضغطوا Start: {total}")

# استقبال النصوص
async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    text = (update.message.text or "").strip()

    if user:
        add_subscriber(user.id)

    # الخطوة 1: Device ID
    if "device_id" not in context.user_data:
        context.user_data["device_id"] = text
        await update.message.reply_text("📸 أرسل الآن صورة إشعار الدفع (لقطة شاشة) أو نص إشعار الدفع أو رقم العملية.")
        return

    # الخطوة 2: إشعار الدفع كنص
    if "notify_msg" not in context.user_data:
        context.user_data["notify_msg"] = text
        order_id = add_order(user.id, context.user_data["device_id"], text)
        context.user_data["order_id"] = order_id

        await update.message.reply_text(
            "✅ ممتاز.\n"
            "اضغط إرسال لاستلام بيانات الدفع الخاصة بك.",
            reply_markup=send_team_keyboard(order_id)
        )
        return

# استقبال صورة إشعار الدفع
async def proof_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user:
        add_subscriber(user.id)

    order_id = context.user_data.get("order_id")

    file_id = None
    if update.message.photo:
        file_id = update.message.photo[-1].file_id
    elif update.message.document:
        file_id = update.message.document.file_id

    if not order_id:
        order_id = add_order(user.id, context.user_data.get("device_id", "-"), "صورة إشعار")
        context.user_data["order_id"] = order_id

    if file_id:
        update_order(order_id, proof_file_id=file_id)

    await update.message.reply_text(
        "✅ ممتاز.\n"
        "اضغط إرسال لاستلام بيانات الدفع الخاصة بك.",
        reply_markup=send_team_keyboard(order_id)
    )

# أزرار فريق العمل
async def team_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    parts = query.data.split(":")
    action = parts[0]
    order_id = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else None

    if action == "new_order":
        context.user_data.clear()
        await query.message.reply_text("📱 أدخل رمز النسخة الكاملة الخاصة بجهازك (انسخه من التطبيق ثم الصقه هنا).")
        return

    order = get_order(order_id) if order_id else None
    if not order:
        await query.message.reply_text("❌ الطلب غير موجود.")
        return

    # إرسال الطلب للتاجر
    if action == "send_team":
        msg = await context.bot.send_message(
            chat_id=MERCHANT_ID,
            text=(
                f"🟦 طلب جديد #{order_id}\n"
                f"🔢 رقم الجهاز: {order['device_id']}\n"
                f"🧾 إشعار: {order['notify_msg'] or '-'}\n"
                f"📌 الحالة: {order.get('status','pending')}"
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

        await context.bot.send_message(
            chat_id=order["user_id"],
            text=f"🔑 كود التفعيل الخاص بجهازك: {code}"
        )

        report = final_report(order_id, get_order(order_id))
        await context.bot.send_message(chat_id=MERCHANT_ID, text=f"📊 تقرير نهائي:\n{report}")
        await context.bot.send_message(chat_id=order["user_id"], text=f"📊 تقرير طلبك:\n{report}", reply_markup=new_order_keyboard())

        if order.get("team_msg_id"):
            try:
                await context.bot.delete_message(chat_id=MERCHANT_ID, message_id=order["team_msg_id"])
            except Exception as e:
                logger.warning(f"Delete team message failed: {e}")
        try:
            await query.message.delete()
        except Exception as e:
            logger.warning(f"Delete query message failed: {e}")
        return

    # فريق العمل: إلغاء الطلب
    if action == "cancel":
        update_order(order_id, status="canceled")
        await context.bot.send_message(
            chat_id=order["user_id"],
            text="❌ تم إلغاء طلبك.",
            reply_markup=new_order_keyboard()
        )
        await context.bot.send_message(
            chat_id=MERCHANT_ID,
            text=f"❌ تم إلغاء الطلب #{order_id} من قبل فريق العمل."
        )
        return
