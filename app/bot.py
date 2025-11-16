import logging
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters
from .handlers import start, text_handler, team_action, proof_handler, stats
from .database import init_db
from .config import BOT_TOKEN, MERCHANT_ID

logger = logging.getLogger(__name__)

def build_app() -> Application:
    # يمكن إبقاء init_db() في main فقط؛ لا ضرر في وجوده هنا أيضًا
    init_db()

    app = Application.builder().token(BOT_TOKEN).build()

    # الأوامر
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("stats", stats))

    # أمر استيقاظ يدوي للتاجر
    async def wake(update, context):
        user = update.effective_user
        if user and user.id == MERCHANT_ID:
            await update.message.reply_text("✅ البوت مستيقظ ويعمل.")
        else:
            await update.message.reply_text("ℹ️ هذا الأمر للتاجر فقط.")
    app.add_handler(CommandHandler("wake", wake))

    # استقبال النصوص
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))

    # استقبال الصور/الملفات
    app.add_handler(MessageHandler(filters.PHOTO | filters.Document.ALL, proof_handler))

    # أزرار فريق العمل
    app.add_handler(CallbackQueryHandler(team_action))

    # معالج أخطاء عام
    async def error_handler(update, context):
        logger.error("Exception while handling update", exc_info=context.error)
    app.add_error_handler(error_handler)

    return app
