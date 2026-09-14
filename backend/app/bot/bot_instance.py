import asyncio
import logging
from typing import Optional
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from backend.app.config import get_settings

logger = logging.getLogger("telegram_bot")
settings = get_settings()

bot: Optional[Bot] = None
dp: Optional[Dispatcher] = None


def get_bot() -> Optional[Bot]:
    """Returns singleton Bot instance if configured."""
    global bot
    if bot is None and settings.BOT_TOKEN and "dummy" not in settings.BOT_TOKEN:
        try:
            bot = Bot(
                token=settings.BOT_TOKEN,
                default=DefaultBotProperties(parse_mode=ParseMode.HTML)
            )
        except Exception as e:
            logger.error(f"Failed to initialize Bot instance: {e}")
            bot = None
    return bot


def get_dispatcher() -> Dispatcher:
    """Returns Dispatcher instance with registered routers."""
    global dp
    if dp is None:
        dp = Dispatcher()

        # Import and register routers
        from backend.app.bot.handlers.user_commands import router as user_router
        from backend.app.bot.handlers.admin_orders import router as admin_router
        from backend.app.bot.handlers.admin_products import router as admin_products_router

        dp.include_router(user_router)
        dp.include_router(admin_router)
        dp.include_router(admin_products_router)
    return dp


async def start_bot_polling() -> None:
    """
    Starts long polling for Telegram Bot in background.
    Handles dummy tokens and connectivity gracefully.
    """
    bot_inst = get_bot()
    if not bot_inst:
        logger.info("Bot token is default/dummy or not configured. Telegram bot polling skipped.")
        return

    dispatcher = get_dispatcher()
    logger.info("Starting Telegram Bot polling with aiogram 3.x...")

    try:
        # Delete webhook before starting polling
        await bot_inst.delete_webhook(drop_pending_updates=False)
        await dispatcher.start_polling(bot_inst)
    except asyncio.CancelledError:
        logger.info("Telegram Bot polling task cancelled.")
    except Exception as e:
        logger.error(f"Telegram Bot polling error: {e}", exc_info=True)


async def stop_bot_polling() -> None:
    """
    Closes active bot session.
    """
    global bot
    if bot:
        try:
            await bot.session.close()
            logger.info("Telegram Bot session closed.")
        except Exception as e:
            logger.debug(f"Error closing bot session: {e}")
        bot = None
