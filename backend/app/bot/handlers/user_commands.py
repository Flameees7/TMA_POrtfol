import logging
from aiogram import Router
from aiogram.filters import Command, CommandStart
from aiogram.types import Message
from sqlalchemy import select
from backend.app.bot.keyboards.admin_kb import get_admin_main_keyboard
from backend.app.bot.keyboards.user_kb import (
    get_main_webapp_keyboard,
    get_reply_webapp_keyboard
)
from backend.app.config import get_settings
from backend.app.database import AsyncSessionLocal
from backend.app.models.user import User

logger = logging.getLogger("bot_user_handlers")
settings = get_settings()
router = Router(name="user_commands")


@router.message(CommandStart())
async def cmd_start(message: Message):
    """
    Handles /start command: greets user and shows TMA launch buttons.
    """
    user = message.from_user
    if not user:
        return

    # Upsert user record in database
    async with AsyncSessionLocal() as db:
        res = await db.execute(select(User).where(User.telegram_id == user.id))
        db_user = res.scalar_one_or_none()
        if not db_user:
            db_user = User(
                telegram_id=user.id,
                username=user.username,
                first_name=user.first_name,
                last_name=user.last_name,
                language_code=user.language_code,
                is_admin=(user.id == settings.ADMIN_CHAT_ID)
            )
            db.add(db_user)
            await db.commit()

    first_name = user.first_name or "дорогой клиент"
    welcome_text = (
        f"👋 Здравствуйте, <b>{first_name}</b>!\n\n"
        f"Добро пожаловать в наш онлайн-магазин. Здесь вы найдете эксклюзивные товары с быстрой доставкой и удобной оплатой.\n\n"
        f"✨ <b>Возможности магазина:</b>\n"
        f"• Актуальный каталог с качественными фото и деталями\n"
        f"• Удобная оплата (СБП, Криптовалюта, Наличные при самовывозе)\n"
        f"• Доставка (СДЭК, Почта России) или Самовывоз\n"
        f"• Отслеживание статуса каждого заказа в реальном времени\n\n"
        f"Нажмите кнопку <b>«🛍 Открыть магазин»</b> ниже для перехода в каталог:"
    )

    # Send message with inline WebApp button and persistent reply keyboard
    await message.answer(
        text=welcome_text,
        reply_markup=get_main_webapp_keyboard()
    )

    # Set bottom keyboard
    await message.answer(
        text="👇 Вы также можете открывать магазин в любое время через кнопку внизу:",
        reply_markup=get_reply_webapp_keyboard()
    )


@router.message(Command("help"))
async def cmd_help(message: Message):
    """
    Handles /help command.
    """
    help_text = (
        "ℹ️ <b>Справка и поддержка</b>\n\n"
        f"📍 <b>Пункт самовывоза:</b> {settings.PICKUP_ADDRESS}\n"
        f"⏰ <b>Часы работы:</b> {settings.PICKUP_WORKING_HOURS}\n"
        f"📝 <b>Правила посещения:</b> {settings.PICKUP_INSTRUCTIONS}\n\n"
        "💳 <b>Оплата:</b> СБП (перевод по номеру), Криптовалюта (TON, USDT), Наличные при получении.\n\n"
        "Для просмотра ваших покупок откройте Mini App и перейдите во вкладку <b>«📦 Мои заказы»</b>."
    )
    await message.answer(help_text, reply_markup=get_main_webapp_keyboard())


@router.message(Command("admin"))
async def cmd_admin(message: Message):
    """
    Handles /admin command for authorized store managers.
    """
    user_id = message.from_user.id if message.from_user else 0
    if user_id != settings.ADMIN_CHAT_ID:
        await message.answer("⛔️ У вас нет прав доступа к панели администратора.")
        return

    admin_text = (
        "⚙️ <b>Панель управления магазином</b>\n\n"
        "Здесь вы можете управлять синхронизацией товаров с Google Таблицей и просматривать заказы."
    )
    await message.answer(admin_text, reply_markup=get_admin_main_keyboard())
