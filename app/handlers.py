import logging
from typing import List

from telegram import (
    Update,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ReplyKeyboardMarkup,
)
from telegram.ext import ContextTypes

from .utils import (
    MERCHANT_ID,
    MERCHANT_PHONE,
    MERCHANT_QR,
    is_merchant,
    fmt_paid,
    calc_extra_and_net,
    badge_status,
    order_header,
    order_summary,
    final_report_text,
    next_order_id,
    ORDERS,
    merchant_final_msg_id,
    customer_conversations,
    merchant_temp_msgs,
)

logger = logging.getLogger(__name__)

customer_keyboard = ReplyKeyboardMarkup(
    [["➕ طلب تحويل", "📷 باركود شام كاش"]],
    resize_keyboard=True
)
merchant_keyboard = ReplyKeyboardMarkup([["📋 الطلبات الجديدة"]], resize_keyboard=True)

def make_initial_keyboard(order_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("🧾 مطابقة الإشعار", callback_data=f"match:{order_id}")],
            [InlineKeyboardButton("📥 إدخال/تعديل إشعار الدفع", callback_data=f"awaitmsg:{order_id}")],
            [InlineKeyboardButton("🔢 إدخال/تعديل رقم العملية", callback_data=f"awaittrx:{order_id}")],
            [InlineKeyboardButton("💳 تبديل حالة الدفع", callback_data=f"togglepay:{order_id}")],
            [InlineKeyboardButton("📲 تأكيد تحويل سيريتل كاش", callback_data=f"confirm_syriatel:{order_id}")],
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

# -------- Handlers --------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if is_merchant(user.id):
        await update.message.reply_text(
            f"👋 أهلاً بك أيها التاجر\n📞 {MERCHANT_PHONE}",
            reply_markup=merchant_keyboard,
        )
    else:
        await update.message.reply_text(
            "👋 أهلاً بك في رصيدك فوري\nاختر من القائمة:",
            reply_markup=customer_keyboard,
        )

async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    text = (update.message.text or "").strip()

    # الزبون
    if not is_merchant(user.id):
        if text == "➕ طلب تحويل":
            context.user_data.clear()
            context.user_data["flow"] = "order"
            context.user_data["awaiting_phone"] = True
            await update.message.reply_text("📱 أدخل رقم الهاتف الذي تريد استلام الرصيد عليه:")
            return

        if text == "📷 باركود شام كاش":
            if MERCHANT_QR:
                return await update.message.reply_text(f"🔗 باركود شام كاش للتاجر:\n{MERCHANT_QR}")
            else:
                return await update.message.reply_text("⚠️ لا يوجد باركود مسجل حالياً.")

        # متابعة تدفق الطلب
        if context.user_data.get("flow") == "order":
            if context.user_data.get("awaiting_phone"):
                phone = text
                if not phone.isdigit() or len(phone) < 9:
                    return await update.message.reply_text("⚠️ رقم غير صالح. أعد إدخال الرقم.")
                context.user_data["phone"] = phone
                context.user_data["awaiting_phone"] = False
                context.user_data["awaiting_network"] = True
                return await update.message.reply_text("🟡 اختر الشبكة: اكتب سيريتل أو MTN")

            if context.user_data.get("awaiting_network"):
                net = text.strip().lower()
                if net in ["سيريتل", "سيرياتيل", "syriatel", "syria tel", "س"]:
                    network = "Syriatel"
                elif net in ["mtn", "ام تي ان", "إم تي إن", "MTN"]:
                    network = "MTN"
                else:
                    return await update.message.reply_text("⚠️ اكتب سيريتل أو MTN فقط.")
                context.user_data["network"] = network
                context.user_data["awaiting_network"] = False
                context.user_data["awaiting_amount"] = True
                return await update.message.reply_text("💰 أدخل المبلغ المطلوب:")

            if context.user_data.get("awaiting_amount"):
                amount_text = text.replace(" ", "")
                if not amount_text.isdigit():
                    return await update.message.reply_text("⚠️ المبلغ يجب أن يكون رقماً صحيحاً. أدخل المبلغ مرة أخرى.")
                context.user_data["amount"] = amount_text
                context.user_data["awaiting_amount"] = False
                context.user_data["awaiting_notify"] = True
                return await update.message.reply_text("📥 أرسل الآن نص إشعار الدفع من شام كاش:")

            if context.user_data.get("awaiting_notify"):
                notify_msg = text
                if len(notify_msg) < 6:
                    return await update.message.reply_text("⚠️ إشعار قصير. أرسل نص الإشعار كما ظهر لك في شام كاش.")
                context.user_data["notify_msg"] = notify_msg
                context.user_data["awaiting_notify"] = False
                context.user_data["awaiting_trx"] = True
                return await update.message.reply_text("🔢 أرسل رقم عملية شام كاش (Transaction ID):")

            if context.user_data.get("awaiting_trx"):
                trx = text.strip().replace(" ", "")
                if not trx.isdigit() or len(trx) < 6:
                    return await update.message.reply_text("⚠️ رقم عملية غير صالح. أعد إرسال رقم العملية (أرقام فقط).")
                phone = context.user_data.get("phone")
                amount = context.user_data.get("amount")
                network = context.user_data.get("network")
                notify_msg = context.user_data.get("notify_msg")
                context.user_data.clear()

                order_id = next_order_id()
                order = {
                    "order_id": order_id,
                    "customer_id": user.id,
                    "name": user.full_name,
                    "phone": phone,
                    "network": network,
                    "amount": amount,
                    "status": "new",
                    "paid": True,  # أرسل إشعار ورقم عملية
                    "notify_msg": notify_msg,
                    "transaction_id": trx,
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

                ack_lines = [
                    "✅ تم إرسال طلبك",
                    f"رقم الطلب: #{order_id}",
                    f"📱 الرقم: {order['phone']}",
                    f"🟡 الشبكة: {order['network']}",
                    f"💰 المبلغ: {order['amount']}",
                    f"🔢 رقم العملية: {trx}",
                ]
                ack = await update.message.reply_text("\n".join(ack_lines))
                customer_conversations.setdefault((user.id, order_id), []).append(ack.message_id)
                return
        return

    # التاجر
    if is_merchant(user.id):
        # انتظار إدخال إشعار دفع
        if context.user_data.get("awaiting_msg_for"):
            oid = context.user_data.pop("awaiting_msg_for")
            if oid in ORDERS:
                ORDERS[oid]["notify_msg"] = text
                merchant_temp_msgs.setdefault(oid, []).append(update.message.message_id)
                ref_msg_id = merchant_final_msg_id.get(oid)
                if ref_msg_id:
                    summary = order_summary(oid, ORDERS[oid])
                    await update.get_bot().edit_message_text(
                        chat_id=MERCHANT_ID,
                        message_id=ref_msg_id,
                        text=summary,
                        reply_markup=make_initial_keyboard(oid),
                    )
            return

        # انتظار إدخال/تعديل رقم العملية
        if context.user_data.get("awaiting_trx_for"):
            oid = context.user_data.pop("awaiting_trx_for")
            trx = text.strip().replace(" ", "")
            if not trx.isdigit() or len(trx) < 6:
                await update.message.reply_text("⚠️ رقم عملية غير صالح. أرسل أرقام فقط (6+ خانات).")
                context.user_data["awaiting_trx_for"] = oid
                return
            if oid in ORDERS:
                ORDERS[oid]["transaction_id"] = trx
                merchant_temp_msgs.setdefault(oid, []).append(update.message.message_id)
                ref_msg_id = merchant_final_msg_id.get(oid)
                if ref_msg_id:
                    summary = order_summary(oid, ORDERS[oid])
                    await update.get_bot().edit_message_text(
                        chat_id=MERCHANT_ID,
                        message_id=ref_msg_id,
                        text=summary,
                        reply_markup=make_initial_keyboard(oid),
                    )
            return

        if text == "📋 الطلبات الجديدة":
            return await show_orders(update, context)

async def show_orders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    new_orders = [(oid, o) for oid, o in ORDERS.items() if o.get("status") == "new"]
    old_orders = [(oid, o) for oid, o in ORDERS.items() if o.get("status") != "new"]

    lines = []
    lines.append("📋 الطلبات الجديدة:")
    if not new_orders:
        lines.append("لا توجد طلبات جديدة حالياً.")
    else:
        for oid, order in new_orders:
            lines.append(
                f"\n{order_header(oid, order)}\n"
                f"👤 {order.get('name')}\n"
                f"📱 {order.get('phone')}\n"
                f"🟡 {order.get('network')}\n"
                f"💰 {order.get('amount')}\n"
                f"💳 {fmt_paid(order.get('paid', False))}"
            )

    lines.append("\n---\n📦 الطلبات المنفذة/الملغاة:")
    if not old_orders:
        lines.append("لا توجد طلبات قديمة.")
    else:
        for oid, order in old_orders:
            lines.append(
                f"\n{order_header(oid, order)} — {badge_status(order)} — {fmt_paid(order.get('paid', False))}"
            )

    await update.message.reply_text("\n".join(lines))

async def merchant_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = (query.data or "").strip()
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

    # مطالبة التاجر بالمطابقة اليدوية
    if action == "match":
        tips = [
            "🧾 التحقق اليدوي (مطابقة الإشعار):",
            "1) تأكد أن اسم المرسل في إشعار شام كاش مطابق للمشترك المعروف لديك.",
            "2) تأكد من رقم الهاتف أو آخر 4 أرقام إن وجدت.",
            f"3) المبلغ في الإشعار يساوي المطلوب: {order.get('amount')}.",
            f"4) رقم العملية يطابق المدخل: {order.get('transaction_id','غير مدخل')}.",
            "5) وقت العملية ضمن فترة مقبولة.",
            "بعد التأكد يمكنك الضغط على ✅ تنفيذ أو 📲 تأكيد تحويل سيريتل كاش.",
        ]
        await context.bot.edit_message_text(
            chat_id=MERCHANT_ID,
            message_id=ref_msg_id,
            text=order_summary(order_id, order) + "\n\n" + "\n".join(tips),
            reply_markup=make_initial_keyboard(order_id),
        )
        return

    # إدخال/تعديل إشعار الدفع
    if action == "awaitmsg":
        context.user_data["awaiting_msg_for"] = order_id
        prompt_text = order_summary(order_id, order) + "\n\n📥 أرسل الآن نص إشعار الدفع هنا:"
        await context.bot.edit_message_text(
            chat_id=MERCHANT_ID,
            message_id=ref_msg_id,
            text=prompt_text,
            reply_markup=make_initial_keyboard(order_id),
        )
        return

    # إدخال/تعديل رقم العملية
    if action == "awaittrx":
        context.user_data["awaiting_trx_for"] = order_id
        prompt_text = order_summary(order_id, order) + "\n\n🔢 أرسل الآن رقم عملية شام كاش هنا (أرقام فقط):"
        await context.bot.edit_message_text(
            chat_id=MERCHANT_ID,
            message_id=ref_msg_id,
            text=prompt_text,
            reply_markup=make_initial_keyboard(order_id),
        )
        return

    # تبديل حالة الدفع
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

    # تأكيد سيريتل كاش
    if action == "confirm_syriatel":
        # بإمكانك فرض شرط وجود transaction_id قبل التأكيد
        # if not order.get("transaction_id"):
        #     return await query.edit_message_text("⚠️ أدخل رقم العملية أولاً قبل التأكيد.")
        order["status"] = "done"
        try:
            await delete_conversation_messages(context, chat_id=customer_id, order_id=order_id)
        except Exception:
            pass

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

    # تنفيذ عام
    if action == "done":
        order["status"] = "done"
        try:
            await delete_conversation_messages(context, chat_id=customer_id, order_id=order_id)
        except Exception:
            pass

        paid_status = fmt_paid(order.get("paid", False))
        amount, extra, net_amount = calc_extra_and_net(str(order.get("amount", 0)))
        msg_to_customer = (
            f"✅ تم تنفيذ طلبك #{order_id}\n"
            f"📱 الرقم: {order.get('phone')}\n"
            f"🟡 الشبكة: {order.get('network')}\n"
            f"💳 حالة الدفع: {paid_status}\n"
            f"💰 المبلغ: {amount}\n"
            f"➕ الزيادة: {extra}\n"
            f"📊 الصافي المطلوب: {net_amount}"
        )
        if order.get("notify_msg"):
            msg_to_customer += f"\n\n📥 إشعار الدفع:\n{order['notify_msg']}"
        if order.get("transaction_id"):
            msg_to_customer += f"\n🔢 رقم العملية: {order['transaction_id']}"
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

    # إلغاء
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
        try:
            await delete_conversation_messages(context, chat_id=customer_id, order_id=order_id)
        except Exception:
            pass
        merchant_final_msg_id[order_id] = ref_msg_id
        order["final_msg_id"] = ref_msg_id
        return

    # دفع لاحقاً
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

    await query.edit_message_text("⚠️ أمر غير معروف")