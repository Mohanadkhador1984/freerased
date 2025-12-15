import os
import logging
import threading
from dotenv import load_dotenv
from flask import Flask
from app.bot import build_app
from app.database import init_db

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
dotenv_path = os.path.join(BASE_DIR, ".env")
load_dotenv(dotenv_path=dotenv_path)

init_db()
app = build_app()

flask_app = Flask(__name__)

@flask_app.route("/")
def home():
    return "Service OK"

@flask_app.route("/ping")
def ping():
    return "I am alive!"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    flask_app.run(host="0.0.0.0", port=port)

def setup_keep_alive(app):
    async def keep_alive(context):
        logger.info("Keep-Alive tick (every 60s)")
    app.job_queue.run_repeating(keep_alive, interval=60, first=5)

if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    setup_keep_alive(app)
    print("🚀 تشغيل البوت عبر Polling على Render...")
    app.run_polling(allowed_updates=["message", "callback_query"])

# (venv) G:\All_my_project\rasidk-fawri>python main.py