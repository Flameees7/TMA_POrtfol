import asyncio
import logging
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.api.dependencies import get_current_telegram_user, get_current_user_db
from backend.app.database import get_db
from backend.app.models.user import User
from backend.app.schemas.auth import TelegramUser
from backend.app.schemas.order import OrderCreate, OrderResponse
from backend.app.services.order_service import OrderService

logger = logging.getLogger("api_orders")
router = APIRouter(prefix="/orders", tags=["Orders"])


async def _safe_notify_admin_new_order(order) -> None:
    """Helper to dispatch admin bot notification in background without blocking response."""
    try:
        from backend.app.bot.services.notifier import notify_admin_new_order
        asyncio.create_task(notify_admin_new_order(order))
    except Exception as e:
        logger.debug(f"Notifier not available or failed: {e}")


async def _safe_notify_admin_status_changed(order) -> None:
    """Helper to dispatch admin notification when customer marks order received."""
    try:
        from backend.app.bot.services.notifier import notify_admin_status_update
        asyncio.create_task(notify_admin_status_update(order))
    except Exception as e:
        logger.debug(f"Notifier not available or failed: {e}")


@router.post(
    "",
    response_model=OrderResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Оформить заказ",
    description="Создает новый заказ, бронирует товар в каталоге и отправляет уведомление администратору."
)
async def create_order(
    order_in: OrderCreate,
    telegram_user: TelegramUser = Depends(get_current_telegram_user),
    user_db: User = Depends(get_current_user_db),
    db: AsyncSession = Depends(get_db)
) -> OrderResponse:
    """
    Creates a new order from WebApp checkout.
    """
    try:
        order = await OrderService.create_order(
            db=db,
            order_in=order_in,
            telegram_user=telegram_user,
            user_db=user_db
        )
    except ValueError as val_err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(val_err)
        )
    except Exception as e:
        logger.error(f"Error creating order: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Произошла ошибка при создании заказа. Пожалуйста, попробуйте снова."
        )

    # Dispatch bot notification asynchronously
    await _safe_notify_admin_new_order(order)

    return OrderResponse.from_orm_model(order)


@router.get(
    "/my",
    response_model=List[OrderResponse],
    summary="Получить список моих заказов",
    description="Возвращает историю заказов текущего авторизованного пользователя Telegram."
)
async def get_my_orders(
    telegram_user: TelegramUser = Depends(get_current_telegram_user),
    db: AsyncSession = Depends(get_db)
) -> List[OrderResponse]:
    """
    Retrieves orders placed by the current user.
    """
    orders = await OrderService.get_user_orders(db=db, telegram_id=telegram_user.id)
    return [OrderResponse.from_orm_model(o) for o in orders]


@router.get(
    "/{order_id}",
    response_model=OrderResponse,
    summary="Получить детали заказа по ID",
    description="Возвращает подробную информацию о заказе. Доступно только владельцу заказа или администратору."
)
async def get_order_details(
    order_id: int,
    telegram_user: TelegramUser = Depends(get_current_telegram_user),
    db: AsyncSession = Depends(get_db)
) -> OrderResponse:
    """
    Retrieves a single order by ID with ownership verification.
    """
    order = await OrderService.get_order_by_id(db=db, order_id=order_id)
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Заказ #{order_id} не найден."
        )

    # Permission check: must be owner or admin
    from backend.app.config import get_settings
    settings = get_settings()
    if order.telegram_id != telegram_user.id and telegram_user.id != settings.ADMIN_CHAT_ID:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="У вас нет доступа к просмотру этого заказа."
        )

    return OrderResponse.from_orm_model(order)


@router.patch(
    "/{order_id}/received",
    response_model=OrderResponse,
    summary="Подтвердить получение заказа клиентом",
    description="Переводит заказ из статуса «В пути» в статус «Завершен»."
)
async def mark_order_received(
    order_id: int,
    telegram_user: TelegramUser = Depends(get_current_telegram_user),
    db: AsyncSession = Depends(get_db)
) -> OrderResponse:
    """
    Allows customer to confirm that their order has arrived and was received.
    """
    try:
        order = await OrderService.mark_order_received_by_customer(
            db=db,
            order_id=order_id,
            telegram_id=telegram_user.id
        )
    except PermissionError as perm_err:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(perm_err)
        )
    except ValueError as val_err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(val_err)
        )
    except Exception as e:
        logger.error(f"Error marking order as received: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Не удалось обновить статус заказа."
        )

    # Dispatch bot notification about customer confirmation
    await _safe_notify_admin_status_changed(order)

    return OrderResponse.from_orm_model(order)
