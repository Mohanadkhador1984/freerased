import os
import logging
import itertools
from typing import Dict, Any, List, Tuple

from telegram import (
    Update,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ReplyKeyboardMarkup,
)
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)

# قراءة بيانات التاجر من .env
merchant_id_str = os.getenv("MERCHANT_ID")
try:
    MERCHANT_ID = int(merchant_id_str) if merchant_id_str else None
except ValueError:
    MERCHANT_ID = None

MERCHANT_PHONE = os.getenv("MERCHANT_PHONE", "غير محدد")
MERCHANT_QR = os.getenv("MERCHANT_QR", None)

# لوحات الأزرار
customer_keyboard = ReplyKeyboardMarkup(
    [["➕ طلب تحويل", "📷 باركود شام كاش"]],
    resize_keyboard=True
)
merchant_keyboard = ReplyKeyboardMarkup([["📋 الطلبات الجديدة"]], resize_keyboard=True)

# مولّد أرقام طلبات
_order_id_counter = itertools.count(1001)

# قاعدة بيانات الطلبات
ORDERS: Dict[int, Dict[str, Any]] = {}
merchant_final_msg_id: Dict[int, int] = {}
customer_conversations: Dict[tuple, List[int]] = {}
merchant_temp_msgs: Dict[int, List[int]] = {}

# ----------------- أدوات مساعدة -----------------
def is_merchant(uid: int) -> bool:
    return MERCHANT_ID is not None and uid == MERCHANT_ID

def fmt_paid(paid: bool) -> str:
    return "✅ مدفوع" if paid else "⏳ غير مدفوع"

def calc_extra_and_net(amount_str: str) -> Tuple[int, int, int]:
    try:
        amount = int(str(amount_str).strip())
    except Exception:
        amount = 0
    extra = (amount // 1000) * 200
    net_amount = amount + extra
    return amount, extra, net_amount

def badge_status(order: Dict[str, Any]) -> str:
    if order.get("status") == "new":
        return "🟦 جديد"
    if order.get("status") == "done":
        return "🟢 منفّذ" if order.get("paid") else "🔴 منفّذ (بدون دفع)"
    if order.get("status") == "canceled":
        return "⚫️ مُلغى"
    return "⚪️ غير معروف"

def order_header(order_id: int, order: Dict[str, Any]) -> str:
    return f"رقم الطلب: #{order_id}"

def order_summary(order_id: int, order: Dict[str, Any]) -> str:
    paid_status = fmt_paid(order.get("paid", False))
    amount_str = str(order.get("amount", 0))
    status = badge_status(order)
    notice = ""
    if order.get("notify_msg"):
        notice = "\n\n📥 إشعار الدفع موجود."
    return (
        f"📩 ملخص الطلب\n"
        f"{order_header(order_id, order)}\n"
        f"{status}\n\n"
        f"👤 الاسم: {order.get('name', '-')}\n"
        f"📱 الرقم: {order.get('phone', '-')}\n"
        f"💰 المبلغ: {amount_str}\n"
        f"💳 حالة الدفع: {paid_status}"
        f"{notice}"
    )

def final_report_text(order_id: int, order: Dict[str, Any]) -> str:
    paid = order.get("paid", False)
    amount, extra, net_amount = calc_extra_and_net(str(order.get("amount", 0)))
    paid_status = fmt_paid(paid)
    status = badge_status(order)
    notify_line = "🚫 لا يوجد"
    if order.get("notify_msg"):
        notify_line = "✅ أُرسل"
    return (
        f"📊 التقرير النهائي\n"
        f"{order_header(order_id, order)}\n"
        f"{status}\n\n"
        f"👤 الاسم: {order.get('name', '-')}\n"
        f"📱 الرقم: {order.get('phone', '-')}\n"
        f"💰 المبلغ المطلوب: {amount}\n"
        f"➕ الزيادة: {extra}\n"
        f"💵 الصافي المطلوب: {net_amount}\n"
        f"💳 حالة الدفع: {paid_status}\n"
        f"📥 إشعار الدفع: {notify_line}"
        + (f"\n\n🧾 نص الإشعار:\n{order['notify_msg']}" if order.get("notify_msg") else "")
    )

def make_initial_keyboard(order_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("📲 تأكيد تحويل سيريتل كاش", callback_data=f"confirm_syriatel:{order_id}")],
            [InlineKeyboardButton("📥 إدخال إشعار الدفع", callback_data=f"awaitmsg:{order_id}")],
            [InlineKeyboardButton("💳 تبديل حالة الدفع", callback_data=f"togglepay:{order_id}")],
            [
                InlineKeyboardButton("✅ تنفيذ", callback_data=f"done:{order_id}"),
                InlineKeyboardButton("❌ إلغاء", callback_data=f"cancel:{order_id}"),
            ],
        ]
    )

def make_unpaid_final_keyboard(order_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton("💳 تم الدفع الآن", callback_data=f"paidnow:{order_id}")]]
    )

async def cleanup_temp(context: ContextTypes.DEFAULT_TYPE, order_id: int) -> None:
    temp_ids: List[int] = merchant_temp_msgs.get(order_id, [])
    for mid in temp_ids:
        try:
            await context.bot.delete_message(chat_id=MERCHANT_ID, message_id=mid)
        except Exception as e:
            logger.debug(f"Failed to delete temp message {mid}: {e}")
    merchant_temp_msgs[order_id] = []

async def delete_conversation_messages(context: ContextTypes.DEFAULT_TYPE, chat_id: int, order_id: int) -> None:
    key = (chat_id, order_id)
    ids = customer_conversations.get(key, [])
    for mid in ids:
        try:
            await context.bot.delete_message(chat_id=chat_id, message_id=mid)
        except Exception as e:
            logger.debug(f"Failed to delete message {mid} in chat {chat_id}: {e}")
    customer_conversations[key] = []

# ----------------- Handlers -----------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if is_merchant(user.id):
        await update.message.reply_text(
            f"👋 أهلاً بك أيها التاجر\n📞 {MERCHANT_PHONE}",
            reply_markup=merchant_keyboard,
        )
    else:
        await update.message.reply_text(
            "👋 أهلاً بك في *رصيدك فوري*",
            parse_mode="Markdown",
            reply_markup=customer_keyboard,
        )

async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    text = (update.message.text or "").strip()

    # الزبون
    if not is_merchant(user.id):
        if text == "➕ طلب تحويل":
            context.user_data["awaiting_phone"] = True
            return await update.message.reply_text("📱 أدخل رقم الهاتف الذي تريد استلام الرصيد عليه:")

        if text == "📷 باركود شام كاش":
            if MERCHANT_QR:
                return await update.message.reply_text(f"🔗 باركود شام كاش للتاجر:\n{MERCHANT_QR}")
            else:
                return await update.message.reply_text("⚠️ لا يوجد باركود مسجل حالياً.")

        if context.user_data.get("awaiting_phone"):
            context.user_data["phone"] = text
            context.user_data["awaiting_phone"] = False
            context.user_data["awaiting_amount"] = True
            return await update.message.reply_text("💰 أدخل المبلغ:")

        if context.user_data.get("awaiting_amount"):
            context.user_data["amount"] = text
            context.user_data["awaiting_amount"] = False
            context.user_data["awaiting_notify"] = True
            return await update.message.reply_text("📥 أرسل الآن إشعار الدفع أو رقم عملية التحويل من شام كاش:")

        if context.user_data.get("awaiting_notify"):
            phone = context.user_data.get("phone")
            amount = context.user_data.get("amount")
            notify_msg = text
            context.user_data.clear()

            order_id = next(_order_id_counter)
            order = {
                "order_id": order_id,
                "customer_id": user.id,
                "name": user.full_name,
                "phone": phone,
                "amount": amount,
                "status": "new",
                "paid": True,  # بما أنه أرسل إشعار الدفع
                "notify_msg": notify_msg,
                "final_msg_id": None,
            }
            ORDERS[order_id] = order

            # إرسال الطلب للتاجر
            if MERCHANT_ID:
                sent = await update.get_bot().send_message(
                    chat_id=MERCHANT_ID,
                    text=order_summary(order_id, order),
                    reply_markup=make_initial_keyboard(order_id),
                )
                merchant_final_msg_id[order_id] = sent.message_id
                order["final_msg_id"] = sent.message_id
                merchant_temp_msgs[order_id] = []

            # إشعار للزبون
            ack = await update.message.reply_text(f"✅ تم إرسال طلبك\nرقم الطلب: #{order_id}")
            customer_conversations.setdefault((user.id, order_id), []).append(ack.message_id)
        return

    # التاجر
    if is_merchant(user.id):
        # في حال انتظار إدخال إشعار دفع
        if context.user_data.get("awaiting_msg_for"):
            oid = context.user_data.pop("awaiting_msg_for")
            if oid in ORDERS:
                ORDERS[oid]["notify_msg"] = text
                merchant_temp_msgs.setdefault(oid, []).append(update.message.message_id)

                ref_msg_id = merchant_final_msg_id.get(oid)
                if ref_msg_id:
                    summary_with_notice = order_summary(oid, ORDERS[oid]) + "\n\n📥 تم استلام إشعار الدفع."
                    await update.get_bot().edit_message_text(
                        chat_id=MERCHANT_ID,
                        message_id=ref_msg_id,
                        text=summary_with_notice,
                        reply_markup=make_initial_keyboard(oid),
                    )
            return

        if text == "📋 الطلبات الجديدة":
            return await show_orders(update, context)


# عرض الطلبات للتاجر
async def show_orders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    new_orders = [(oid, o) for oid, o in ORDERS.items() if o.get("status") == "new"]
    old_orders = [(oid, o) for oid, o in ORDERS.items() if o.get("status") != "new"]

    lines = []
    lines.append("📋 *الطلبات الجديدة:*")
    if not new_orders:
        lines.append("لا توجد طلبات جديدة حالياً.")
    else:
        for oid, order in new_orders:
            lines.append(
                f"\n{order_header(oid, order)}\n"
                f"👤 {order.get('name')}\n"
                f"📱 {order.get('phone')}\n"
                f"💰 {order.get('amount')}\n"
                f"💳 {fmt_paid(order.get('paid', False))}"
            )

    lines.append("\n---\n📦 *الطلبات المنفذة/الملغاة:*")
    if not old_orders:
        lines.append("لا توجد طلبات قديمة.")
    else:
        for oid, order in old_orders:
            lines.append(
                f"\n{order_header(oid, order)} — {badge_status(order)} — {fmt_paid(order.get('paid', False))}"
            )

    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


# أزرار التاجر
async def merchant_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data or ""
    parts = data.split(":")
    if len(parts) != 2:
        return await query.edit_message_text("⚠️ أمر غير صالح")

    action, order_id_str = parts
    try:
        order_id = int(order_id_str)
    except ValueError:
        return await query.edit_message_text("⚠️ رقم طلب غير صالح")

    if order_id not in ORDERS:
        return await query.edit_message_text("⚠️ الطلب غير موجود")

    order = ORDERS[order_id]
    customer_id = order["customer_id"]
    ref_msg_id = merchant_final_msg_id.get(order_id, query.message.message_id)

    # awaitmsg: إدخال إشعار الدفع
    if action == "awaitmsg":
        context.user_data["awaiting_msg_for"] = order_id
        prompt_text = order_summary(order_id, order) + "\n\n📥 أرسل الآن إشعار الدفع هنا كرسالة نصية:"
        await context.bot.edit_message_text(
            chat_id=MERCHANT_ID,
            message_id=ref_msg_id,
            text=prompt_text,
            reply_markup=make_initial_keyboard(order_id),
        )
        return

    # togglepay: تبديل حالة الدفع
    if action == "togglepay":
        if order.get("status") != "new":
            return await query.edit_message_text(final_report_text(order_id, order))
        order["paid"] = not order.get("paid", False)
        await context.bot.edit_message_text(
            chat_id=MERCHANT_ID,
            message_id=ref_msg_id,
            text=order_summary(order_id, order),
            reply_markup=make_initial_keyboard(order_id),
        )
        return

    # confirm_syriatel: تأكيد تحويل سيريتل كاش
    if action == "confirm_syriatel":
        order["status"] = "done"
        await delete_conversation_messages(context, chat_id=customer_id, order_id=order_id)

        await context.bot.send_message(
            chat_id=customer_id,
            text=(
                f"✅ تم تحويل رصيد سيريتل كاش\n"
                f"📱 الرقم: {order.get('phone')}\n"
                f"💰 المبلغ: {order.get('amount')}\n"
                f"شكراً لاستخدامك خدمتنا."
            ),
        )

        final_text = "🟢 ✅ تم التنفيذ (تحويل سيريتل كاش)\n\n" + final_report_text(order_id, order)
        await context.bot.edit_message_text(
            chat_id=MERCHANT_ID,
            message_id=ref_msg_id,
            text=final_text,
        )

        await cleanup_temp(context, order_id)
        merchant_final_msg_id[order_id] = ref_msg_id
        order["final_msg_id"] = ref_msg_id
        return

    # تنفيذ الطلب (عام)
    if action == "done":
        order["status"] = "done"
        await delete_conversation_messages(context, chat_id=customer_id, order_id=order_id)

        paid_status = fmt_paid(order.get("paid", False))
        amount, extra, net_amount = calc_extra_and_net(str(order.get("amount", 0)))
        msg_to_customer = (
            f"✅ تم تنفيذ طلبك #{order_id}\n"
            f"📱 الرقم: {order.get('phone')}\n"
            f"💳 حالة الدفع: {paid_status}\n"
            f"💰 المبلغ: {amount}\n"
            f"➕ الزيادة: {extra}\n"
            f"📊 الصافي المطلوب: {net_amount}"
        )
        if order.get("notify_msg"):
            msg_to_customer += f"\n\n📥 إشعار الدفع:\n{order['notify_msg']}"
        await context.bot.send_message(chat_id=customer_id, text=msg_to_customer)

        report = final_report_text(order_id, order)
        if order.get("paid"):
            final_text = "🟢 ✅ تم التنفيذ (مدفوع)\n\n" + report
            await context.bot.edit_message_text(
                chat_id=MERCHANT_ID,
                message_id=ref_msg_id,
                text=final_text,
            )
        else:
            final_text = "🔴 ✅ تم التنفيذ (بدون دفع)\n\n" + report
            await context.bot.edit_message_text(
                chat_id=MERCHANT_ID,
                message_id=ref_msg_id,
                text=final_text,
                reply_markup=make_unpaid_final_keyboard(order_id),
            )

        await cleanup_temp(context, order_id)
        merchant_final_msg_id[order_id] = ref_msg_id
        order["final_msg_id"] = ref_msg_id
        return

    # إلغاء الطلب
    if action == "cancel":
        order["status"] = "canceled"
        await context.bot.send_message(
            chat_id=customer_id,
            text=f"❌ تم إلغاء طلبك #{order_id}\n📱 الرقم: {order.get('phone')}",
        )
        final_text = "❌ تم الإلغاء\n\n" + final_report_text(order_id, order)
        await context.bot.edit_message_text(
            chat_id=MERCHANT_ID,
            message_id=ref_msg_id,
            text=final_text,
        )
        await cleanup_temp(context, order_id)
        await delete_conversation_messages(context, chat_id=customer_id, order_id=order_id)
        merchant_final_msg_id[order_id] = ref_msg_id
        order["final_msg_id"] = ref_msg_id
        return

    # دفع لاحقًا
    if action == "paidnow":
        if order.get("status") != "done":
            return await query.edit_message_text("⚠️ لا يمكن تحديد الدفع الآن قبل التنفيذ.")
            # دفع لاحقًا
    if action == "paidnow":
        if order.get("status") != "done":
            return await query.edit_message_text("⚠️ لا يمكن تحديد الدفع الآن قبل التنفيذ.")
        if order.get("paid"):
            return await context.bot.edit_message_text(
                chat_id=MERCHANT_ID,
                message_id=ref_msg_id,
                text="🟢 الحالة محدّثة كمدفوع.\n\n" + final_report_text(order_id, order),
            )
        order["paid"] = True
        final_text = "🟢 ✅ تم التنفيذ (مدفوع)\n\n" + final_report_text(order_id, order)
        await context.bot.edit_message_text(
            chat_id=MERCHANT_ID,
            message_id=ref_msg_id,
            text=final_text,
        )
        await context.bot.send_message(
            chat_id=order["customer_id"],
            text=(
                f"💳 تم تأكيد الدفع لطلبك #{order_id}\n"
                f"📱 الرقم: {order.get('phone')}\n"
                f"الحالة أصبحت: ✅ مدفوع"
            ),
        )
        merchant_final_msg_id[order_id] = ref_msg_id
        order["final_msg_id"] = ref_msg_id
        return

    # أمر غير معروف
    await query.edit_message_text("⚠️ أمر غير معروف")
