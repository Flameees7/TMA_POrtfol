import logging
from typing import Optional
from backend.app.bot.bot_instance import get_bot
from backend.app.bot.keyboards.admin_kb import get_admin_order_actions_keyboard
from backend.app.config import get_settings
from backend.app.models.order import DeliveryType, Order, OrderStatus

logger = logging.getLogger("notifier")
settings = get_settings()


def format_admin_order_message(order: Order) -> str:
    """
    Formats comprehensive HTML text for admin notifications.
    """
    delivery_type_str = "🚶‍♂️ Самовывоз" if order.delivery_type == DeliveryType.PICKUP else "🚚 Доставка"
    provider_str = f" ({order.delivery_provider})" if order.delivery_provider else ""

    tg_contact = f'<a href="tg://user?id={order.telegram_id}">Профиль Telegram</a>'
    if order.user and order.user.username:
        tg_contact = f"@{order.user.username} ({tg_contact})"

    tx_id_str = ""
    if order.crypto_tx_id:
        tx_id_str = f"\n🔗 <b>TxID:</b> <code>{order.crypto_tx_id}</code>"

    status_icon = "⏳"
    if order.status == OrderStatus.ASSEMBLING:
        status_icon = "📦"
    elif order.status == OrderStatus.IN_TRANSIT:
        status_icon = "🚚"
    elif order.status == OrderStatus.COMPLETED:
        status_icon = "✅"
    elif order.status == OrderStatus.CANCELLED:
        status_icon = "🚫"

    text = (
        f"🛒 <b>ЗАКАЗ: {order.order_number}</b>\n\n"
        f"🏷 <b>Товар:</b> {order.product_title}\n"
        f"💰 <b>Сумма к оплате:</b> {order.product_price:,.0f} ₽\n\n"
        f"👤 <b>Покупатель:</b> {order.customer_name}\n"
        f"📞 <b>Телефон:</b> <code>{order.customer_phone}</code>\n"
        f"💬 <b>Telegram:</b> {tg_contact}\n\n"
        f"📍 <b>Получение:</b> {delivery_type_str}{provider_str}\n"
        f"🏢 <b>Адрес / ПВЗ:</b> {order.delivery_address}\n\n"
        f"💳 <b>Оплата:</b> {order.payment_method.label_ru}{tx_id_str}\n\n"
        f"📊 <b>Текущий статус:</b> {status_icon} <b>{order.status.label_ru}</b>"
    )
    return text


async def notify_admin_new_order(order: Order) -> None:
    """
    Sends new order card with actionable inline buttons to the admin chat.
    """
    bot = get_bot()
    if not bot or not settings.ADMIN_CHAT_ID:
        logger.debug("Admin notification skipped: bot or ADMIN_CHAT_ID not configured.")
        return

    text = format_admin_order_message(order)
    keyboard = get_admin_order_actions_keyboard(order.id, order.status)

    try:
        photos = []
        if order.product:
            photos = order.product.photo_list

        if photos and photos[0].startswith("http"):
            try:
                await bot.send_photo(
                    chat_id=settings.ADMIN_CHAT_ID,
                    photo=photos[0],
                    caption=text,
                    reply_markup=keyboard
                )
                return
            except Exception as pe:
                logger.debug(f"Could not send photo to admin, falling back to text: {pe}")

        await bot.send_message(
            chat_id=settings.ADMIN_CHAT_ID,
            text=text,
            reply_markup=keyboard,
            disable_web_page_preview=True
        )
        logger.info(f"Admin notified about new order {order.order_number}")
    except Exception as e:
        logger.error(f"Failed to send admin notification for order {order.order_number}: {e}")


async def notify_customer_status_change(
    order: Order,
    new_status: OrderStatus,
    custom_message: Optional[str] = None
) -> None:
    """
    Sends push notification to customer regarding their order status updates.
    """
    bot = get_bot()
    if not bot or not order.telegram_id:
        return

    messages = {
        OrderStatus.ASSEMBLING: (
            f"✅ <b>Оплата подтверждена!</b>\n\n"
            f"Ваш заказ <b>{order.order_number}</b> (<i>{order.product_title}</i>) передан в сборку.\n"
            f"Мы уведомим вас, когда посылка будет отправлена."
        ),
        OrderStatus.IN_TRANSIT: (
            f"🚚 <b>Заказ передан в доставку!</b>\n\n"
            f"Ваш заказ <b>{order.order_number}</b> уже в пути.\n"
            f"📍 <b>Адрес:</b> {order.delivery_address}\n\n"
            f"Как только посылка прибудет, вы сможете подтвердить получение в приложении, нажав кнопку «Заказ получен»."
        ),
        OrderStatus.COMPLETED: (
            f"🎉 <b>Заказ выполнен!</b>\n\n"
            f"Заказ <b>{order.order_number}</b> успешно завершен.\n"
            f"Спасибо, что выбрали наш магазин! Будем рады вашим новым заказам."
        ),
        OrderStatus.CANCELLED: (
            f"🚫 <b>Заказ отменен</b>\n\n"
            f"Ваш заказ <b>{order.order_number}</b> был отменен.\n"
            f"Если у вас есть вопросы, пожалуйста, свяжитесь с поддержкой."
        )
    }

    text = messages.get(new_status)
    if not text:
        text = f"ℹ️ Статус вашего заказа <b>{order.order_number}</b> изменен на: <b>{new_status.label_ru}</b>"

    if custom_message:
        text += f"\n\n💬 <i>Комментарий: {custom_message}</i>"

    try:
        await bot.send_message(
            chat_id=order.telegram_id,
            text=text,
            disable_web_page_preview=True
        )
        logger.info(f"Customer {order.telegram_id} notified of status update {new_status} for {order.order_number}")
    except Exception as e:
        logger.warning(f"Could not send Telegram message to user {order.telegram_id}: {e}")


async def notify_admin_status_update(order: Order) -> None:
    """
    Notifies admin when customer confirms receipt of order.
    """
    bot = get_bot()
    if not bot or not settings.ADMIN_CHAT_ID:
        return

    text = (
        f"🎉 <b>Клиент подтвердил получение заказа!</b>\n\n"
        f"🏷 <b>Заказ:</b> {order.order_number}\n"
        f"📦 <b>Товар:</b> {order.product_title}\n"
        f"👤 <b>Клиент:</b> {order.customer_name}\n"
        f"📊 <b>Статус:</b> ✅ <b>Завершен</b>"
    )

    try:
        await bot.send_message(
            chat_id=settings.ADMIN_CHAT_ID,
            text=text,
            disable_web_page_preview=True
        )
    except Exception as e:
        logger.error(f"Failed to send status update notification to admin: {e}")
