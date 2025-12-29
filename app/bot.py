import re
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters
from .config import BOT_TOKEN, MERCHANT_ID
from .utils import generate_activation_code

UUID_REGEX = re.compile(r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}")

def build_app():
    app = Application.builder().token(BOT_TOKEN).build()

    async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        if not user or user.id != MERCHANT_ID:
            await update.message.reply_text("❌ هذا البوت مخصص للتاجر فقط.")
            return
        await update.message.reply_text("✅ أرسل النص الذي يحتوي الرمز التسلسلي (UUID).")

    app.add_handler(CommandHandler("start", start))

    async def serial_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        if not user or user.id != MERCHANT_ID:
            await update.message.reply_text("❌ هذا البوت مخصص للتاجر فقط.")
            return

        text = (update.message.text or "").strip()
        match = UUID_REGEX.search(text)
        if not match:
            await update.message.reply_text("⚠️ لم يتم العثور على رمز تسلسلي صالح في النص.")
            return

        device_id = match.group(0)
        code = generate_activation_code(device_id)

        # إرسال الكود فقط بدون أي نص إضافي
        await update.message.reply_text(code)

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, serial_handler))

    return app
