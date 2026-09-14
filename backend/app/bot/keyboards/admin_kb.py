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
                    text="📦 Управление товарами",
                    callback_data="adm_products_menu"
                )
            ],
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


def get_admin_products_menu_keyboard() -> InlineKeyboardMarkup:
    """
    Submenu for product catalog management in bot.
    """
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="➕ Добавить новый товар",
                    callback_data="adm_prod_add"
                )
            ],
            [
                InlineKeyboardButton(
                    text="📋 Список товаров и редактирование",
                    callback_data="adm_prod_list:0"
                )
            ],
            [
                InlineKeyboardButton(
                    text="⬅️ Назад в главное меню",
                    callback_data="adm_back_main"
                )
            ]
        ]
    )
    return keyboard


def get_admin_product_list_keyboard(products: list, page: int, total_pages: int) -> InlineKeyboardMarkup:
    """
    Paginated list of products for admin.
    """
    rows = []
    for p in products:
        status_icon = "🟢" if p.is_available and p.stock_status == "in_stock" else ("🟡" if p.stock_status == "preorder" else "🔴")
        title_snippet = p.title[:26] + "..." if len(p.title) > 26 else p.title
        btn_text = f"{status_icon} {title_snippet} — {p.price:,.0f} ₽"
        rows.append([
            InlineKeyboardButton(
                text=btn_text,
                callback_data=f"adm_prod_view:{p.id}"
            )
        ])

    # Pagination row
    nav_buttons = []
    if page > 0:
        nav_buttons.append(
            InlineKeyboardButton(text="⬅️ Назад", callback_data=f"adm_prod_list:{page - 1}")
        )
    nav_buttons.append(
        InlineKeyboardButton(text=f"📄 {page + 1}/{max(1, total_pages)}", callback_data="adm_noop")
    )
    if page < total_pages - 1:
        nav_buttons.append(
            InlineKeyboardButton(text="Вперед ➡️", callback_data=f"adm_prod_list:{page + 1}")
        )
    if nav_buttons:
        rows.append(nav_buttons)

    # Actions row
    rows.append([
        InlineKeyboardButton(text="➕ Добавить товар", callback_data="adm_prod_add"),
        InlineKeyboardButton(text="⬅️ Меню товаров", callback_data="adm_products_menu")
    ])

    return InlineKeyboardMarkup(inline_keyboard=rows)


def get_admin_product_card_keyboard(product_id: int, is_available: bool, stock_status: str) -> InlineKeyboardMarkup:
    """
    Action buttons for a single product card.
    """
    status_label = "✅ В наличии" if stock_status == "in_stock" else ("⏳ Под заказ" if stock_status == "preorder" else "❌ Нет в наличии")

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📸 Загрузить / Заменить фото",
                    callback_data=f"adm_prod_photo:{product_id}"
                )
            ],
            [
                InlineKeyboardButton(
                    text="💰 Изменить цену",
                    callback_data=f"adm_prod_price:{product_id}"
                ),
                InlineKeyboardButton(
                    text=f"🔄 Статус: {status_label}",
                    callback_data=f"adm_prod_toggle_status:{product_id}"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🗑 Удалить товар",
                    callback_data=f"adm_prod_delete:{product_id}"
                )
            ],
            [
                InlineKeyboardButton(
                    text="⬅️ Назад к списку",
                    callback_data="adm_prod_list:0"
                )
            ]
        ]
    )
    return keyboard


def get_product_status_selection_keyboard() -> InlineKeyboardMarkup:
    """
    Status selector during product creation.
    """
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ В наличии (in_stock)", callback_data="prod_status:in_stock"),
            ],
            [
                InlineKeyboardButton(text="⏳ Под заказ (preorder)", callback_data="prod_status:preorder"),
            ],
            [
                InlineKeyboardButton(text="❌ Нет в наличии (out_of_stock)", callback_data="prod_status:out_of_stock"),
            ],
            [
                InlineKeyboardButton(text="❌ Отменить", callback_data="adm_fsm_cancel")
            ]
        ]
    )
    return keyboard


def get_photo_upload_done_keyboard(has_photos: bool = True) -> InlineKeyboardMarkup:
    """
    Buttons while uploading multiple photos.
    """
    buttons = []
    if has_photos:
        buttons.append([
            InlineKeyboardButton(text="✅ Готово (сохранить фото)", callback_data="adm_photo_done")
        ])
    else:
        buttons.append([
            InlineKeyboardButton(text="⏭ Пропустить (без фото)", callback_data="adm_photo_skip")
        ])
    buttons.append([
        InlineKeyboardButton(text="❌ Отмена", callback_data="adm_fsm_cancel")
    ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_cancel_fsm_keyboard() -> InlineKeyboardMarkup:
    """
    Simple cancel button for text input FSM states.
    """
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="❌ Отмена", callback_data="adm_fsm_cancel")
            ]
        ]
    )
