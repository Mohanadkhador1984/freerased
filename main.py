import os
from dotenv import load_dotenv

# حمّل ملف .env قبل أي استيراد آخر
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
dotenv_path = os.path.join(BASE_DIR, ".env")
load_dotenv(dotenv_path=dotenv_path)

from app.bot import build_app

if __name__ == "__main__":
    app = build_app()
    print("🚀 البوت شغال وينتظر أوامر تيليغرام...")
    app.run_polling()
