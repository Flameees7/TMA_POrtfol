from backend.app.bot.handlers.user_commands import router as user_commands_router
from backend.app.bot.handlers.admin_orders import router as admin_orders_router
from backend.app.bot.handlers.admin_products import router as admin_products_router

__all__ = [
    "user_commands_router",
    "admin_orders_router",
    "admin_products_router"
]

