import os
import logging
from dotenv import load_dotenv
from flask import Flask
from app.bot import build_app
from app.database import init_db

# إعداد اللوج
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# تحميل المتغيرات من .env (للتشغيل المحلي فقط)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
dotenv_path = os.path.join(BASE_DIR, ".env")
load_dotenv(dotenv_path=dotenv_path)

# تهيئة قاعدة البيانات
init_db()

# بناء تطبيق تيليغرام
app = build_app()

# قراءة إعدادات التشغيل
USE_POLLING = os.getenv("USE_POLLING", "0") == "1"
PORT = int(os.environ.get("PORT", 10000))  # Render يمرر هذا تلقائيًا
BOT_TOKEN = os.getenv("BOT_TOKEN")
PUBLIC_URL = os.getenv("PUBLIC_URL", "")  # لويبهوك فقط

# Flask للصحة (نستخدمه فقط في وضع Polling)
flask_app = Flask(__name__)

@flask_app.route("/")
def home():
    return "Service OK"

@flask_app.route("/ping")
def ping():
    return "I am alive!"

if __name__ == "__main__":
    if USE_POLLING:
        # نمط Polling: نكشف Flask على PORT و نشغّل البوت Polling
        # ملاحظة: لا يوجد أي خادم آخر على PORT
        # نستخدم werkzeug لتقديم /ping و البوت يعمل Polling بشكل منفصل داخل العملية
        import threading
        def run_flask():
            flask_app.run(host="0.0.0.0", port=PORT)
        threading.Thread(target=run_flask, daemon=True).start()

        print("🚀 تشغيل البوت عبر Polling...")
        app.run_polling(allowed_updates=["message", "callback_query"])
    else:
        # نمط Webhook: لا نشغّل Flask إطلاقًا لتجنب تعارض المنفذ
        if not PUBLIC_URL:
            raise RuntimeError("PUBLIC_URL غير مضبوط في وضع Webhook")

        webhook_url = f"{PUBLIC_URL}/{BOT_TOKEN}"
        print(f"🚀 تشغيل البوت عبر Webhook… {webhook_url}")

        # خادم Tornado الخاص بـ PTB سيستمع على PORT (Render)
        app.run_webhook(
            listen="0.0.0.0",
            port=PORT,
            url_path=BOT_TOKEN,
            webhook_url=webhook_url,
            allowed_updates=["message", "callback_query"],
        )

# (venv) G:\All_my_project\rasidk-fawri>python main.py