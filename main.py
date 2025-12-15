import os
import logging

from app.bot import build_app
from app.database import init_db

# إعداد اللوج
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

if __name__ == "__main__":
    init_db()
    app = build_app()

    token = os.getenv("BOT_TOKEN")
    public_url = os.getenv("PUBLIC_URL")
    port = int(os.environ.get("PORT", 10000))

    if not token or not public_url:
        raise RuntimeError("BOT_TOKEN أو PUBLIC_URL غير مضبوطين")

    webhook_url = f"{public_url}/{token}"
    print(f"🚀 تشغيل البوت عبر Webhook… {webhook_url}")

    app.run_webhook(
        listen="0.0.0.0",
        port=port,
        url_path=token,
        webhook_url=webhook_url,
        allowed_updates=["message", "callback_query"],
    )
