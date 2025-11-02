import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
BOT_USERNAME = os.getenv("BOT_USERNAME", "")

MERCHANT_ID = int(os.getenv("MERCHANT_ID", "0"))
MERCHANT_PHONE = os.getenv("MERCHANT_PHONE", "غير محدد")
MERCHANT_QR = os.getenv("MERCHANT_QR", "")

USE_POLLING = os.getenv("USE_POLLING", "0") == "1"
PUBLIC_URL = os.getenv("PUBLIC_URL", "")
