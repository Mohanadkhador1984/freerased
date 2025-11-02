from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from .database import add_order, update_order, get_order
from .utils import is_valid_phone, order_summary, final_report, extract_transaction_id
from .config import MERCHANT_ID, MERCHANT_PHONE, MERCHANT_QR

# تتبع رسائل التاجر المؤقتة لكل طلب لحذفها لاحقًا
MERCHANT_TEMP_MSGS: dict[int, list[int]] = {}  # {order_id: [msg_ids]}
# انتظار مدخلات التاجر (رقم العملية/إشعار الدفع) لكل تاجر
MERCHANT_WAIT: dict[int, dict] = {}  # {merchant_id: {"order_id": int, "mode": "tx"|"notify"}}

def merchant_keyboard(order_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ تأكيد الدفع", callback_data=f"confirm:{order_id}")],
        [InlineKeyboardButton("❌ إلغاء الطلب", callback_data=f"cancel:{order_id}")],
        [InlineKeyboardButton("🔢 إدخال رقم العملية", callback_data=f"ask_tx:{order_id}")],
        [InlineKeyboardButton("🧾 إدخال إشعار الدفع", callback_data=f"ask_notify:{order_id}")]
    ])

# بدء البوت: عرض باركود شام كاش ورقم التاجر بحقل مستقل
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text(
        f"🔑 كود شام كاش للتاجر:\n{MERCHANT_QR}\n📱 رقم التاجر: {MERCHANT_PHONE}\n\n"
        "أرسل رقم الموبايل الذي تريد شحنه بصيغة 09xxxxxxxx."
    )

# تدفق الزبون: رقم الهاتف → المبلغ → إشعار الدفع → زر إرسال للتاجر
async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    text = update.message.text.strip()

    # إذا كان المرسل هو التاجر وفي وضع انتظار إدخال (رقم العملية/الإشعار)
    if user.id == MERCHANT_ID and user.id in MERCHANT_WAIT:
        wait = MERCHANT_WAIT[user.id]
        order_id = wait.get("order_id")
        mode = wait.get("mode")
        order = get_order(order_id)
        if not order:
            await update.message.reply_text("❌ الطلب غير موجود.")
            MERCHANT_WAIT.pop(user.id, None)
            return

        if mode == "tx":
            # إدخال رقم العملية بحرية
            update_order(order_id, transaction_id=text)
            # نسخة للزبون فورًا
            try:
                await context.bot.send_message(
                    chat_id=order["user_id"],
                    text=f"🔢 رقم العملية من التاجر لطلب #{order_id}: {text}"
                )
            except Exception:
                pass
            # حذف رسالة التاجر حتى لا تبقى دردشة فردية
            try:
                await update.message.delete()
            except Exception:
                pass

        elif mode == "notify":
            # إشعار دفع نصي من التاجر
            update_order(order_id, notify_msg=text)
            # نسخة للزبون فورًا
            try:
                await context.bot.send_message(
                    chat_id=order["user_id"],
                    text=f"🧾 إشعار الدفع من التاجر لطلب #{order_id}:\n{text}"
                )
            except Exception:
                pass
            try:
                await update.message.delete()
            except Exception:
                pass

        MERCHANT_WAIT.pop(user.id, None)
        return

    # الزبون: رقم الهاتف
    if "phone" not in context.user_data:
        if not is_valid_phone(text):
            await update.message.reply_text("⚠️ أدخل رقم صحيح بصيغة 09xxxxxxxx.")
            return
        context.user_data["phone"] = text
        await update.message.reply_text("💰 أرسل المبلغ المطلوب (أرقام فقط).")
        return

    # الزبون: المبلغ
    if "amount" not in context.user_data:
        if not text.isdigit():
            await update.message.reply_text("⚠️ أرسل رقمًا صحيحًا للمبلغ.")
            return
        amount = int(text)
        if amount <= 0:
            await update.message.reply_text("⚠️ المبلغ يجب أن يكون أكبر من صفر.")
            return
        context.user_data["amount"] = amount

        # إنشاء الطلب
        order_id = add_order(user.id, user.first_name or "-", context.user_data["phone"], amount)
        context.user_data["order_id"] = order_id
        order = get_order(order_id)

        summary = order_summary(order_id, order)
        await update.message.reply_text(
            f"{summary}\n\n"
            f"📌 ادفع عبر شام كاش:\n🔑 الكود: {MERCHANT_QR}\n📱 التاجر: {MERCHANT_PHONE}\n\n"
            f"ثم أرسل إشعار الدفع كنص أو صورة، ويمكنك أيضًا إدخال رقم العملية (اختياري)."
        )
        return

    # الزبون: إشعار الدفع (كنص) + استخراج رقم العملية اختياري + إرسال نسخة للتاجر فورًا
    order_id = context.user_data.get("order_id")
    if not order_id:
        await update.message.reply_text("⚠️ ابدأ بإرسال رقم الهاتف والمبلغ أولًا.")
        return

    tx = extract_transaction_id(text)
    update_order(order_id, notify_msg=text)
    if tx:
        update_order(order_id, transaction_id=tx)

    # نسخة للتاجر فورًا
    m = await context.bot.send_message(
        chat_id=MERCHANT_ID,
        text=f"🧾 إشعار دفع من الزبون - طلب #{order_id}:\n{text}"
    )
    MERCHANT_TEMP_MSGS.setdefault(order_id, []).append(m.message_id)

    # زر "إرسال للتاجر"
    send_btn = InlineKeyboardMarkup([
        [InlineKeyboardButton("📤 إرسال للتاجر", callback_data=f"send_merchant:{order_id}")]
    ])
    await update.message.reply_text(
        "✅ تم استلام إشعار الدفع.\nاضغط الزر لإرسال الطلب للتاجر.",
        reply_markup=send_btn
    )

# الزبون: استقبال صور/وثائق إشعار الدفع + إرسال نسخة للتاجر فورًا
async def proof_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    order_id = context.user_data.get("order_id")
    if not order_id:
        await update.message.reply_text("⚠️ ابدأ بإرسال رقم الهاتف والمبلغ أولًا.")
        return

    file_id = None
    if update.message.photo:
        file_id = update.message.photo[-1].file_id
    elif update.message.document:
        file_id = update.message.document.file_id
    else:
        await update.message.reply_text("⚠️ أرسل صورة أو ملف إشعار الدفع.")
        return

    update_order(order_id, proof_file_id=file_id)

    # نسخة للتاجر فورًا
    p = await context.bot.send_photo(
        chat_id=MERCHANT_ID,
        photo=file_id,
        caption=f"🧾 صورة إشعار دفع من الزبون - طلب #{order_id}"
    )
    MERCHANT_TEMP_MSGS.setdefault(order_id, []).append(p.message_id)

    # زر "إرسال للتاجر"
    send_btn = InlineKeyboardMarkup([
        [InlineKeyboardButton("📤 إرسال للتاجر", callback_data=f"send_merchant:{order_id}")]
    ])
    await update.message.reply_text(
        "✅ تم استلام صورة/ملف إشعار الدفع.\nاضغط الزر لإرسال الطلب للتاجر.",
        reply_markup=send_btn
    )

# إجراءات الأزرار (الزبون والتاجر)
async def merchant_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    parts = query.data.split(":")
    action = parts[0]
    order_id = int(parts[1])
    order = get_order(order_id)

    if action == "send_merchant":
        if not order:
            await query.message.reply_text("❌ الطلب غير موجود.")
            return

        summary = order_summary(order_id, order)
        # رسالة رئيسية للتاجر (تبقى مع أزرار دائمة حتى التنفيذ أو الإلغاء)
        msg = await context.bot.send_message(
            chat_id=MERCHANT_ID,
            text=f"🟦 طلب جديد\n{summary}\n\n🔑 كود شام كاش: {MERCHANT_QR}\n📱 {MERCHANT_PHONE}",
            reply_markup=merchant_keyboard(order_id)
        )
        update_order(order_id, merchant_msg_id=msg.message_id)

        await query.message.reply_text("📤 تم إرسال الطلب للتاجر.")
        return

    if not order:
        await query.message.reply_text("❌ الطلب غير موجود.")
        return

    # التاجر: إدخال رقم العملية أو إشعار الدفع
    if action == "ask_tx":
        MERCHANT_WAIT[MERCHANT_ID] = {"order_id": order_id, "mode": "tx"}
        # رسالة إرشادية تُضاف للمؤقتات (تحذف لاحقًا)
        msg = await query.message.reply_text(f"🔢 أرسل رقم العملية لطلب #{order_id} كرسالة نصية هنا.")
        MERCHANT_TEMP_MSGS.setdefault(order_id, []).append(msg.message_id)
        return

    if action == "ask_notify":
        MERCHANT_WAIT[MERCHANT_ID] = {"order_id": order_id, "mode": "notify"}
        msg = await query.message.reply_text(f"🧾 أرسل إشعار الدفع (نص أو صورة/ملف) لطلب #{order_id} هنا.")
        MERCHANT_TEMP_MSGS.setdefault(order_id, []).append(msg.message_id)
        return

    # تأكيد التنفيذ
    if action == "confirm":
        update_order(order_id, paid=1, status="done")
        order = get_order(order_id)
        report = final_report(order_id, order)

        # إرسال تقرير نهائي ثابت للتاجر
        final_msg = await context.bot.send_message(chat_id=MERCHANT_ID, text=report)
        update_order(order_id, final_msg_id=final_msg.message_id)

        # حذف الرسالة الرئيسية لدى التاجر
        if order.get("merchant_msg_id"):
            try:
                await context.bot.delete_message(chat_id=MERCHANT_ID, message_id=order["merchant_msg_id"])
            except Exception:
                pass

        # حذف كل الرسائل المؤقتة المرتبطة بهذا الطلب (إرشادات، نسخ إشعارات/صور)
        for mid in MERCHANT_TEMP_MSGS.get(order_id, []):
            try:
                await context.bot.delete_message(chat_id=MERCHANT_ID, message_id=mid)
            except Exception:
                pass
        MERCHANT_TEMP_MSGS.pop(order_id, None)
        MERCHANT_WAIT.pop(MERCHANT_ID, None)

        # إشعار الزبون + التقرير النهائي المتضمّن كل ما أرسله الطرفان
        await context.bot.send_message(chat_id=order["user_id"], text="✅ تم التسليم، شكرًا لك!")
        await context.bot.send_message(chat_id=order["user_id"], text=report)
        return

    # إلغاء الطلب
    if action == "cancel":
        update_order(order_id, status="canceled")

        # حذف الرسالة الرئيسية والرسائل المؤقتة لدى التاجر
        if order.get("merchant_msg_id"):
            try:
                await context.bot.delete_message(chat_id=MERCHANT_ID, message_id=order["merchant_msg_id"])
            except Exception:
                pass
        for mid in MERCHANT_TEMP_MSGS.get(order_id, []):
            try:
                await context.bot.delete_message(chat_id=MERCHANT_ID, message_id=mid)
            except Exception:
                pass
        MERCHANT_TEMP_MSGS.pop(order_id, None)
        MERCHANT_WAIT.pop(MERCHANT_ID, None)

        # إشعار الزبون بالإلغاء
        await context.bot.send_message(chat_id=order["user_id"], text="❌ تم إلغاء طلبك.")
        await query.message.reply_text(f"❌ تم إلغاء الطلب #{order_id}")
        return
