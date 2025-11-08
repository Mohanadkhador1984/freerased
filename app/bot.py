import logging
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters
from .handlers import start, text_handler, team_action, proof_handler, stats   # أضفنا stats هنا
from .database import init_db
from .config import BOT_TOKEN

# تفعيل نظام اللوج
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def build_app() -> Application:
    # تهيئة قاعدة البيانات
    init_db()

    # إنشاء التطبيق
    app = Application.builder().token(BOT_TOKEN).build()

    # الأوامر
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("stats", stats))   # أمر الإحصائيات الجديد

    # استقبال النصوص (Device ID, إشعار الدفع, رقم العملية)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))

    # استقبال الصور/الملفات (إشعار الدفع)
    app.add_handler(MessageHandler(filters.PHOTO | filters.Document.ALL, proof_handler))

    # أزرار فريق العمل
    app.add_handler(CallbackQueryHandler(team_action))

    return app
