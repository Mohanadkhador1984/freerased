import os
import logging
from dotenv import load_dotenv
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters
from app.handlers import start, text_handler, merchant_action

# تحميل ملف .env
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
dotenv_path = os.path.join(BASE_DIR, ".env")
load_dotenv(dotenv_path=dotenv_path)

print("DEBUG BOT_TOKEN =", os.getenv("BOT_TOKEN"))
print("DEBUG MERCHANT_ID =", os.getenv("MERCHANT_ID"))
print("DEBUG MERCHANT_PHONE =", os.getenv("MERCHANT_PHONE"))

def build_app():
    logging.basicConfig(
        format="%(asctime)s - %(levelname)s - %(message)s",
        level=logging.INFO
    )

    token = os.getenv("BOT_TOKEN")
    if not token:
        raise RuntimeError("❌ BOT_TOKEN غير موجود في ملف .env")

    app = Application.builder().token(token).build()

    # إضافة المعالجات
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))
    app.add_handler(CallbackQueryHandler(merchant_action))   # ← مهم للتعامل مع أزرار التاجر

    return app
