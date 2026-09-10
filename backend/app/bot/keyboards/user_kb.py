from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
    WebAppInfo
)
from backend.app.config import get_settings

settings = get_settings()


def get_main_webapp_keyboard() -> InlineKeyboardMarkup:
    """
    Returns inline keyboard with Telegram Mini App launcher buttons.
    """
    web_app_url = settings.WEBAPP_URL.strip() or "http://localhost:8000"

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🛍 Открыть магазин",
                    web_app=WebAppInfo(url=web_app_url)
                )
            ],
            [
                InlineKeyboardButton(
                    text="📦 Мои заказы",
                    web_app=WebAppInfo(url=f"{web_app_url}#orders")
                ),
                InlineKeyboardButton(
                    text="💬 Поддержка",
                    url="https://t.me/telegram"
                )
            ]
        ]
    )
    return keyboard


def get_reply_webapp_keyboard() -> ReplyKeyboardMarkup:
    """
    Returns persistent bottom reply keyboard with Mini App launch button.
    """
    web_app_url = settings.WEBAPP_URL.strip() or "http://localhost:8000"

    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(
                    text="🛍 Каталог товаров",
                    web_app=WebAppInfo(url=web_app_url)
                )
            ]
        ],
        resize_keyboard=True,
        is_persistent=True
    )
    return keyboard
