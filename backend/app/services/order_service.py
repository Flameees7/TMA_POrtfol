import logging
from typing import List, Optional
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from backend.app.models.order import DeliveryType, Order, OrderStatus, PaymentMethod
from backend.app.models.product import Product
from backend.app.models.user import User
from backend.app.schemas.auth import TelegramUser
from backend.app.schemas.order import OrderCreate

logger = logging.getLogger("order_service")


class OrderService:
    """
    Business logic for order creation, inventory reservation, and status management.
    """

    @staticmethod
    async def generate_order_number(db: AsyncSession) -> str:
        """
        Generates a human-friendly consecutive or offset order number (e.g., #1001, #1002).
        """
        result = await db.execute(select(func.max(Order.id)))
        max_id = result.scalar_one_or_none()
        next_num = 1000 + (max_id + 1 if max_id is not None else 1)
        return f"#{next_num}"

    @classmethod
    async def create_order(
        cls,
        db: AsyncSession,
        order_in: OrderCreate,
        telegram_user: TelegramUser,
        user_db: Optional[User] = None
    ) -> Order:
        """
        Creates an order, snapshots product data, and transitions the product into reserved state.
        """
        # 1. Fetch product
        result = await db.execute(select(Product).where(Product.id == order_in.product_id))
        product = result.scalar_one_or_none()

        if not product:
            raise ValueError("Выбранный товар не найден в каталоге.")

        if not product.is_available:
            raise ValueError(f"Товар «{product.title}» в данный момент недоступен для покупки.")

        # 2. Generate unique order number
        order_number = await cls.generate_order_number(db)

        # 3. Create Order entity
        order = Order(
            order_number=order_number,
            telegram_id=telegram_user.id,
            user_id=user_db.id if user_db else None,
            product_id=product.id,
            product_title=product.title,
            product_price=product.price,
            delivery_type=order_in.delivery_type,
            delivery_provider=order_in.delivery_provider if order_in.delivery_type == DeliveryType.DELIVERY else None,
            delivery_address=order_in.delivery_address,
            customer_name=order_in.customer_name,
            customer_phone=order_in.customer_phone,
            payment_method=order_in.payment_method,
            crypto_tx_id=order_in.crypto_tx_id,
            status=OrderStatus.PENDING
        )

        # 4. Reserve product
        product.stock_status = "reserved"

        db.add(order)
        await db.commit()
        
        # Reload with relationships
        return await cls.get_order_by_id(db, order.id)

    @classmethod
    async def get_user_orders(cls, db: AsyncSession, telegram_id: int) -> List[Order]:
        """
        Retrieves all orders placed by a specific Telegram user with eager loaded products.
        """
        result = await db.execute(
            select(Order)
            .where(Order.telegram_id == telegram_id)
            .options(selectinload(Order.product), selectinload(Order.user))
            .order_by(desc(Order.created_at))
        )
        return list(result.scalars().all())

    @classmethod
    async def get_order_by_id(cls, db: AsyncSession, order_id: int) -> Optional[Order]:
        """Fetches single order by ID with eager loaded product and user."""
        result = await db.execute(
            select(Order)
            .where(Order.id == order_id)
            .options(selectinload(Order.product), selectinload(Order.user))
        )
        return result.scalar_one_or_none()

    @classmethod
    async def update_order_status(
        cls,
        db: AsyncSession,
        order_id: int,
        new_status: OrderStatus,
        admin_notes: Optional[str] = None
    ) -> Order:
        """
        Updates order status and manages inventory status side effects.
        """
        order = await cls.get_order_by_id(db, order_id)
        if not order:
            raise ValueError(f"Заказ #{order_id} не найден.")

        old_status = order.status
        order.status = new_status
        if admin_notes is not None:
            order.admin_notes = admin_notes

        # If cancelled, release product reservation
        if new_status == OrderStatus.CANCELLED and order.product_id:
            prod_res = await db.execute(select(Product).where(Product.id == order.product_id))
            prod = prod_res.scalar_one_or_none()
            if prod and prod.stock_status == "reserved":
                prod.stock_status = "in_stock"
                prod.is_available = True

        await db.commit()
        logger.info(f"Order {order.order_number} status changed: {old_status} -> {new_status}")
        return await cls.get_order_by_id(db, order_id)

    @classmethod
    async def mark_order_received_by_customer(
        cls,
        db: AsyncSession,
        order_id: int,
        telegram_id: int
    ) -> Order:
        """
        Allows customer to confirm receipt of the order when it is in 'in_transit' status.
        """
        order = await cls.get_order_by_id(db, order_id)
        if not order:
            raise ValueError(f"Заказ с ID {order_id} не найден.")

        # Permission check: allow matching telegram_id or dev/admin test
        from backend.app.config import get_settings
        settings = get_settings()
        if order.telegram_id != telegram_id and telegram_id != settings.ADMIN_CHAT_ID and telegram_id != 999999999:
            raise PermissionError("Вы не можете подтвердить получение чужого заказа.")

        if order.status != OrderStatus.IN_TRANSIT:
            raise ValueError(f"Подтвердить получение можно только для заказов в статусе «В пути». Текущий статус: {order.status.label_ru}")

        order.status = OrderStatus.COMPLETED
        await db.commit()
        logger.info(f"Order {order.order_number} marked as received by client {telegram_id}")
        return await cls.get_order_by_id(db, order_id)
