import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters
from .config import BOT_TOKEN, MERCHANT_ID
from .utils import generate_activation_code

logger = logging.getLogger(__name__)

def build_app():
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN مفقود. ضع التوكن في ملف .env")

    app = Application.builder().token(BOT_TOKEN).build()

    # أمر /start للتاجر
    async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        if not user or user.id != MERCHANT_ID:
            await update.message.reply_text("❌ هذا البوت مخصص للتاجر فقط.")
            return
        await update.message.reply_text("✅ أهلاً بك، أرسل الرقم التسلسلي للحصول على كود التفعيل.")

    app.add_handler(CommandHandler("start", start))

    # استقبال أي نص من التاجر → توليد كود التفعيل
    async def serial_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        if not user or user.id != MERCHANT_ID:
            await update.message.reply_text("❌ هذا البوت مخصص للتاجر فقط.")
            return

        device_id = (update.message.text or "").strip()
        if not device_id:
            await update.message.reply_text("⚠️ الرجاء إرسال رقم تسلسلي صالح.")
            return

        code = generate_activation_code(device_id)
        await update.message.reply_text(f"🔑 كود التفعيل: {code}")

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, serial_handler))

    # Error handler
    async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
        logger.error("Exception while handling update", exc_info=context.error)
    app.add_error_handler(error_handler)

    return app
