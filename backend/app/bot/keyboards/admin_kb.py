from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from backend.app.models.order import OrderStatus


def get_admin_order_actions_keyboard(order_id: int, current_status: OrderStatus) -> InlineKeyboardMarkup:
    """
    Constructs contextual action buttons for administrative order processing.
    """
    buttons = []

    if current_status == OrderStatus.PENDING:
        buttons.append([
            InlineKeyboardButton(
                text="✅ Подтвердить оплату",
                callback_data=f"adm_ord:pay:{order_id}"
            )
        ])
        buttons.append([
            InlineKeyboardButton(
                text="❌ Отклонить заказ",
                callback_data=f"adm_ord:cancel:{order_id}"
            )
        ])

    elif current_status == OrderStatus.ASSEMBLING:
        buttons.append([
            InlineKeyboardButton(
                text="🚚 Отправлен (В пути)",
                callback_data=f"adm_ord:transit:{order_id}"
            )
        ])
        buttons.append([
            InlineKeyboardButton(
                text="❌ Отменить заказ",
                callback_data=f"adm_ord:cancel:{order_id}"
            )
        ])

    elif current_status == OrderStatus.IN_TRANSIT:
        buttons.append([
            InlineKeyboardButton(
                text="🎉 Выполнен (Доставлен)",
                callback_data=f"adm_ord:complete:{order_id}"
            )
        ])
        buttons.append([
            InlineKeyboardButton(
                text="❌ Отменить заказ",
                callback_data=f"adm_ord:cancel:{order_id}"
            )
        ])

    elif current_status == OrderStatus.COMPLETED:
        buttons.append([
            InlineKeyboardButton(
                text="✅ Заказ успешно завершен",
                callback_data="adm_noop"
            )
        ])

    elif current_status == OrderStatus.CANCELLED:
        buttons.append([
            InlineKeyboardButton(
                text="🚫 Заказ отменен",
                callback_data="adm_noop"
            )
        ])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_admin_main_keyboard() -> InlineKeyboardMarkup:
    """
    Returns general admin panel management keyboard.
    """
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🔄 Синхронизация Google Sheets",
                    callback_data="adm_sync_sheets"
                )
            ],
            [
                InlineKeyboardButton(
                    text="📊 Статистика заказов",
                    callback_data="adm_stats"
                )
            ]
        ]
    )
    return keyboard
