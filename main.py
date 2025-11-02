import os
from dotenv import load_dotenv
from app.bot import build_app

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
dotenv_path = os.path.join(BASE_DIR, ".env")
load_dotenv(dotenv_path=dotenv_path)

if __name__ == "__main__":
    app = build_app()

    if os.getenv("USE_POLLING", "0") == "1":
        print("🚀 تشغيل البوت محليًا عبر polling...")
        app.run_polling(allowed_updates=["message", "callback_query"])
    else:
        token = os.getenv("BOT_TOKEN")
        port = int(os.environ.get("PORT", 5000))
        base_url = os.environ.get("PUBLIC_URL")
        url = f"{base_url}/{token}"

        print(f"🚀 البوت شغال عبر Webhook... {url}")
        app.run_webhook(
            listen="0.0.0.0",
            port=port,
            url_path=token,
            webhook_url=url,
            allowed_updates=["message", "callback_query"],
        )
