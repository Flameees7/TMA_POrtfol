import logging
from aiogram import F, Router
from aiogram.types import CallbackQuery
from sqlalchemy import func, select
from backend.app.bot.keyboards.admin_kb import get_admin_order_actions_keyboard
from backend.app.bot.services.notifier import (
    format_admin_order_message,
    notify_customer_status_change
)
from backend.app.config import get_settings
from backend.app.database import AsyncSessionLocal
from backend.app.models.order import Order, OrderStatus
from backend.app.services.order_service import OrderService
from backend.app.services.sheets_sync import GoogleSheetsSyncService

logger = logging.getLogger("bot_admin_handlers")
settings = get_settings()
router = Router(name="admin_orders")


@router.callback_query(F.data.startswith("adm_ord:"))
async def handle_admin_order_action(callback: CallbackQuery):
    """
    Handles interactive admin status transitions:
    pay -> assembling
    transit -> in_transit
    complete -> completed
    cancel -> cancelled
    """
    user_id = callback.from_user.id
    if user_id != settings.ADMIN_CHAT_ID:
        await callback.answer("⛔️ У вас нет прав администратора.", show_alert=True)
        return

    data = callback.data or ""
    parts = data.split(":")
    if len(parts) != 3:
        await callback.answer("Некорректные параметры кнопки.", show_alert=True)
        return

    action = parts[1]
    try:
        order_id = int(parts[2])
    except ValueError:
        await callback.answer("Некорректный ID заказа.", show_alert=True)
        return

    target_status = None
    if action == "pay":
        target_status = OrderStatus.ASSEMBLING
    elif action == "transit":
        target_status = OrderStatus.IN_TRANSIT
    elif action == "complete":
        target_status = OrderStatus.COMPLETED
    elif action == "cancel":
        target_status = OrderStatus.CANCELLED

    if not target_status:
        await callback.answer("Неизвестное действие.")
        return

    async with AsyncSessionLocal() as db:
        try:
            order = await OrderService.update_order_status(
                db=db,
                order_id=order_id,
                new_status=target_status
            )
        except Exception as e:
            logger.error(f"Failed to update order status: {e}")
            await callback.answer(f"Ошибка при обновлении: {e}", show_alert=True)
            return

    # Update admin message text and buttons
    new_text = format_admin_order_message(order)
    new_keyboard = get_admin_order_actions_keyboard(order.id, order.status)

    try:
        if callback.message.caption:
            await callback.message.edit_caption(caption=new_text, reply_markup=new_keyboard)
        else:
            await callback.message.edit_text(text=new_text, reply_markup=new_keyboard)
    except Exception as e:
        logger.debug(f"Message already up to date: {e}")

    await callback.answer(f"Статус заказа изменен на: {target_status.label_ru}")

    # Send push notification to customer
    await notify_customer_status_change(order, target_status)


@router.callback_query(F.data == "adm_sync_sheets")
async def handle_admin_sync_sheets(callback: CallbackQuery):
    """
    Handles on-demand Google Sheets synchronization trigger from bot.
    """
    user_id = callback.from_user.id
    if user_id != settings.ADMIN_CHAT_ID:
        await callback.answer("⛔️ У вас нет прав администратора.", show_alert=True)
        return

    await callback.answer("⏳ Синхронизация запущена...", show_alert=False)

    async with AsyncSessionLocal() as db:
        report = await GoogleSheetsSyncService.sync_database(db)

    status_str = report.get("status", "unknown")
    total = report.get("total", 0)
    created = report.get("created", 0)
    updated = report.get("updated", 0)

    result_msg = (
        f"✅ <b>Синхронизация завершена!</b>\n\n"
        f"• Результат: <code>{status_str}</code>\n"
        f"• Добавлено товаров: {created}\n"
        f"• Обновлено товаров: {updated}\n"
        f"• Всего товаров в базе: {total}"
    )

    await callback.message.answer(result_msg)


@router.callback_query(F.data == "adm_stats")
async def handle_admin_stats(callback: CallbackQuery):
    """
    Displays brief order statistics to administrator.
    """
    user_id = callback.from_user.id
    if user_id != settings.ADMIN_CHAT_ID:
        await callback.answer("⛔️ У вас нет прав администратора.", show_alert=True)
        return

    async with AsyncSessionLocal() as db:
        # Total orders
        total_res = await db.execute(select(func.count(Order.id)))
        total_count = total_res.scalar() or 0

        # Pending orders
        pending_res = await db.execute(
            select(func.count(Order.id)).where(Order.status == OrderStatus.PENDING)
        )
        pending_count = pending_res.scalar() or 0

        # Completed revenue
        rev_res = await db.execute(
            select(func.sum(Order.product_price)).where(Order.status == OrderStatus.COMPLETED)
        )
        completed_revenue = rev_res.scalar() or 0.0

    stats_text = (
        "📊 <b>Статистика магазина</b>\n\n"
        f"• Всего заказов: <b>{total_count}</b>\n"
        f"• Ожидают подтверждения: <b>{pending_count}</b>\n"
        f"• Выручка (выполненные): <b>{completed_revenue:,.0f} ₽</b>"
    )

    await callback.message.answer(stats_text)
    await callback.answer()


@router.callback_query(F.data == "adm_noop")
async def handle_admin_noop(callback: CallbackQuery):
    """Acknowledges buttons for finalized orders."""
    await callback.answer("Статус заказа зафиксирован.")
