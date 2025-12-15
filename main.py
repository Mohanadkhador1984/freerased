import os
import logging
import threading
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

# خادم Flask لمسارات الصحة
flask_app = Flask(__name__)

@flask_app.route("/")
def home():
    return "Service OK"

@flask_app.route("/ping")
def ping():
    return "I am alive!"

def run_flask():
    """
    يختار المنفذ تلقائيًا حسب بيئة الاستضافة:
    - Render يمرر المنفذ عبر env باسم PORT (عادة 10000)
    - Fly.io يمكن ضبط PING_PORT أو استخدام PORT عند الـ webhook
    """
    port = int(os.environ.get("PORT", os.environ.get("PING_PORT", 8080)))
    flask_app.run(host="0.0.0.0", port=port)

def setup_keep_alive(app):
    # مهمة دورية داخلية كل دقيقة
    async def keep_alive(context):
        logger.info("Keep-Alive tick (every 60s)")
    app.job_queue.run_repeating(keep_alive, interval=60, first=5)

if __name__ == "__main__":
    # تهيئة قاعدة البيانات
    init_db()

    # بناء تطبيق تيليغرام
    app = build_app()

    # تشغيل Flask في Thread منفصل
    threading.Thread(target=run_flask, daemon=True).start()

    # إضافة مهمة Keep-Alive
    setup_keep_alive(app)

    # اختيار نمط التشغيل (Polling أو Webhook)
    use_polling = os.getenv("USE_POLLING", "0") == "1"
    if use_polling:
        print("🚀 تشغيل البوت عبر Polling...")
        app.run_polling(allowed_updates=["message", "callback_query"])
    else:
        token = os.getenv("BOT_TOKEN")
        port = int(os.environ.get("PORT", 5000))  # Render/Fly.io يوفر PORT
        base_url = os.environ.get("PUBLIC_URL")
        if not base_url:
            raise RuntimeError("PUBLIC_URL غير مضبوط")
        webhook_url = f"{base_url}/{token}"
        print(f"🚀 تشغيل البوت عبر Webhook… {webhook_url}")
        app.run_webhook(
            listen="0.0.0.0",
            port=port,
            url_path=token,
            webhook_url=webhook_url,
            allowed_updates=["message", "callback_query"],
        )

# (venv) G:\All_my_project\rasidk-fawri>python main.py