import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
BOT_USERNAME = os.getenv("BOT_USERNAME", "").strip()

# تنظيف MERCHANT_ID وضمان أنه int صحيح
_raw_mid = os.getenv("MERCHANT_ID", "").strip()
try:
    MERCHANT_ID = int(_raw_mid) if _raw_mid else 0
except ValueError:
    raise ValueError(f"MERCHANT_ID غير صالح: القيمة كانت {_raw_mid!r}. يجب أن يكون رقمًا صحيحًا.")

MERCHANT_PHONE = os.getenv("MERCHANT_PHONE", "غير محدد").strip()
MERCHANT_QR = os.getenv("MERCHANT_QR", "").strip()

USE_POLLING = os.getenv("USE_POLLING", "0").strip() == "1"
PUBLIC_URL = os.getenv("PUBLIC_URL", "").strip()
