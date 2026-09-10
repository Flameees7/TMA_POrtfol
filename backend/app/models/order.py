import enum
from datetime import datetime
from typing import TYPE_CHECKING, Optional
from sqlalchemy import (
    BigInteger,
    DateTime,
    Enum as SQLEnum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    func
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.app.database import Base

if TYPE_CHECKING:
    from backend.app.models.user import User
    from backend.app.models.product import Product


class OrderStatus(str, enum.Enum):
    PENDING = "pending"          # Оформляется (ожидает подтверждения)
    ASSEMBLING = "assembling"    # Собирается (оплата подтверждена)
    IN_TRANSIT = "in_transit"    # В пути (передан в доставку)
    COMPLETED = "completed"      # Завершен / Доставлен
    CANCELLED = "cancelled"      # Отклонен / Отменен

    @property
    def label_ru(self) -> str:
        labels = {
            self.PENDING: "Оформляется",
            self.ASSEMBLING: "Собирается",
            self.IN_TRANSIT: "В пути",
            self.COMPLETED: "Завершен",
            self.CANCELLED: "Отменен",
        }
        return labels.get(self, self.value)


class DeliveryType(str, enum.Enum):
    PICKUP = "pickup"            # Самовывоз
    DELIVERY = "delivery"        # Доставка

    @property
    def label_ru(self) -> str:
        return "Самовывоз" if self == self.PICKUP else "Доставка"


class PaymentMethod(str, enum.Enum):
    CASH = "cash"                # Наличные при самовывозе
    SBP = "sbp"                  # СБП (Система быстрых платежей)
    USDT_TON = "usdt_ton"        # USDT (TON)
    USDT_TRC20 = "usdt_trc20"    # USDT (TRC20)
    TON = "ton"                  # TON

    @property
    def label_ru(self) -> str:
        labels = {
            self.CASH: "Наличные (при получении)",
            self.SBP: "СБП (Перевод по номеру)",
            self.USDT_TON: "Криптовалюта USDT (TON)",
            self.USDT_TRC20: "Криптовалюта USDT (TRC20)",
            self.TON: "Криптовалюта TON",
        }
        return labels.get(self, self.value)


class Order(Base):
    """
    Order model representing a customer's purchase request.
    """
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    order_number: Mapped[str] = mapped_column(String(32), unique=True, index=True, nullable=False)
    telegram_id: Mapped[int] = mapped_column(BigInteger, index=True, nullable=False)

    user_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    product_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("products.id", ondelete="SET NULL"), nullable=True)

    # Snapshot of product info at the moment of order creation
    product_title: Mapped[str] = mapped_column(String(512), nullable=False)
    product_price: Mapped[float] = mapped_column(Float, nullable=False)

    # Delivery information
    delivery_type: Mapped[DeliveryType] = mapped_column(
        SQLEnum(DeliveryType, native_enum=False, values_callable=lambda x: [e.value for e in x]),
        nullable=False
    )
    delivery_provider: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)  # СДЭК / Почта России
    delivery_address: Mapped[str] = mapped_column(Text, nullable=False)  # ПВЗ / адрес доставки или адрес самовывоза

    # Contact information
    customer_name: Mapped[str] = mapped_column(String(255), nullable=False)
    customer_phone: Mapped[str] = mapped_column(String(64), nullable=False)

    # Payment details
    payment_method: Mapped[PaymentMethod] = mapped_column(
        SQLEnum(PaymentMethod, native_enum=False, values_callable=lambda x: [e.value for e in x]),
        nullable=False
    )
    crypto_tx_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Status & Management
    status: Mapped[OrderStatus] = mapped_column(
        SQLEnum(OrderStatus, native_enum=False, values_callable=lambda x: [e.value for e in x]),
        default=OrderStatus.PENDING,
        nullable=False,
        index=True
    )
    admin_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False
    )

    # Relationships
    user: Mapped[Optional["User"]] = relationship("User", back_populates="orders")
    product: Mapped[Optional["Product"]] = relationship("Product", back_populates="orders")

    def __repr__(self) -> str:
        return f"<Order(id={self.id}, order_number='{self.order_number}', status='{self.status}', total={self.product_price})>"
