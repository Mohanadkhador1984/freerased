import os
from dotenv import load_dotenv
from app.bot import build_app

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
dotenv_path = os.path.join(BASE_DIR, ".env")
load_dotenv(dotenv_path=dotenv_path)

if __name__ == "__main__":
    app = build_app()

    token = os.getenv("BOT_TOKEN")
    port = int(os.environ.get("PORT", 5000))
    url = f"https://telegram-bot-abho.onrender.com/{token}"

    print("🚀 البوت شغال عبر Webhook...")
    app.run_webhook(
        listen="0.0.0.0",
        port=port,
        url_path=token,
        webhook_url=url,
    )
