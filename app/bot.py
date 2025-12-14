import logging
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    ConversationHandler, ContextTypes, filters
)
from .handlers import start, text_handler, proof_handler, stats, team_action
from .database import init_db, get_subscribers, count_subscribers, mark_broadcast_sent
from .config import BOT_TOKEN, MERCHANT_ID

logger = logging.getLogger(__name__)

ASK_TEXT, CONFIRM = range(2)

# ✅ لوحة تحكم التاجر
def admin_panel_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📢 إرسال إشعار جماعي", callback_data="admin:broadcast")],
        [InlineKeyboardButton("👥 عدد المشتركين", callback_data="admin:subs_count")]
    ])


def build_app():
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN مفقود. ضع التوكن في ملف .env")

    init_db()
    app = Application.builder().token(BOT_TOKEN).build()

    # أوامر عامة
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("stats", stats))

    # ✅ أمر wake للتأكد من عمل البوت
    async def wake(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        if user and user.id == MERCHANT_ID:
            await update.message.reply_text("✅ البوت مستيقظ ويعمل بشكل صحيح.")
        else:
            await update.message.reply_text("ℹ️ هذا الأمر مخصص للتاجر فقط.")
    app.add_handler(CommandHandler("wake", wake))

    # ✅ لوحة تحكم التاجر
    async def panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        if not user or user.id != MERCHANT_ID:
            return
        await update.message.reply_text("⚙️ لوحة التحكّم:", reply_markup=admin_panel_kb())
    app.add_handler(CommandHandler("panel", panel))

    # ✅ أزرار لوحة التاجر
    async def admin_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        if query.from_user.id != MERCHANT_ID:
            return ConversationHandler.END

        if query.data == "admin:broadcast":
            context.user_data["broadcast"] = {}
            await query.message.reply_text("✍️ اكتب نص الإشعار لإرساله لجميع المشتركين.")
            return ASK_TEXT

        if query.data == "admin:subs_count":
            total = count_subscribers()
            await query.message.reply_text(f"👥 عدد المشتركين الحاليين: {total}")
            return ConversationHandler.END

        return ConversationHandler.END

    # ✅ إدخال نص الإشعار
    async def ask_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
        txt = (update.message.text or "").strip()
        if not txt:
            await update.message.reply_text("⚠️ الرجاء إرسال نص صالح.")
            return ASK_TEXT

        context.user_data["broadcast"]["text"] = txt
        await update.message.reply_text(
            f"📢 سيتم إرسال الرسالة التالية للجميع:\n\n{txt}\n\nأكتب: نعم للتأكيد أو لا للإلغاء."
        )
        return CONFIRM

    # ✅ تأكيد الإرسال
    async def confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
        ans = (update.message.text or "").strip().lower()
        if ans not in ["نعم", "yes", "y", "ا", "اي", "ايوه", "ايوا"]:
            await update.message.reply_text("❌ تم إلغاء العملية.")
            context.user_data.pop("broadcast", None)
            return ConversationHandler.END

        text = context.user_data["broadcast"]["text"]
        await update.message.reply_text("🚀 جاري إرسال الإشعار...")

        subs = get_subscribers() or []
        if not subs:
            await update.message.reply_text("⚠️ لا يوجد مشتركين حالياً.")
            context.user_data.pop("broadcast", None)
            return ConversationHandler.END

        # تنظيف الـ IDs
        cleaned_subs = []
        for uid in subs:
            try:
                cleaned_subs.append(int(str(uid).strip()))
            except Exception:
                logger.warning(f"Subscriber ID غير صالح: {uid}")

        sent, failed = 0, 0
        BATCH = 25

        for i in range(0, len(cleaned_subs), BATCH):
            batch = cleaned_subs[i:i+BATCH]
            tasks = [send_one(context, uid, text) for uid in batch]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for r in results:
                if r is True:
                    sent += 1
                else:
                    failed += 1
            await asyncio.sleep(1.2)

        await update.message.reply_text(
            f"📢 تم الإرسال.\n✅ ناجحة: {sent}\n⚠️ فاشلة: {failed}\n👥 المجموع: {len(cleaned_subs)}"
        )
        context.user_data.pop("broadcast", None)
        return ConversationHandler.END

    # ✅ إرسال رسالة واحدة
    async def send_one(context: ContextTypes.DEFAULT_TYPE, user_id: int, text: str):
        try:
            await context.bot.send_message(chat_id=int(user_id), text=text)
            mark_broadcast_sent(user_id)
            return True
        except Exception as e:
            logger.warning(f"فشل إرسال الإشعار إلى {user_id}: {e}")
            return False

    # ✅ إلغاء المحادثة
    async def cancel_conv(update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text("❌ تم إلغاء العملية.")
        return ConversationHandler.END

    # ✅ ConversationHandler للبث الجماعي
    conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(admin_buttons, pattern=r"^admin:")],
        states={
            ASK_TEXT: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_text)],
            CONFIRM: [MessageHandler(filters.TEXT & ~filters.COMMAND, confirm)],
        },
        fallbacks=[CommandHandler("cancel", cancel_conv)],
        per_user=True,
        per_chat=True,
        allow_reentry=True
    )
    app.add_handler(conv)

    # ✅ باقي الهاندلرز (طلبات/فريق)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))
    app.add_handler(MessageHandler(filters.PHOTO | filters.Document.ALL, proof_handler))
    app.add_handler(CallbackQueryHandler(team_action))

    # ✅ Error handler
    async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
        logger.error("Exception while handling update", exc_info=context.error)
    app.add_error_handler(error_handler)

    return app
