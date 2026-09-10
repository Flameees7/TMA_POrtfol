from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator
from backend.app.models.order import DeliveryType, OrderStatus, PaymentMethod


class OrderCreate(BaseModel):
    """
    Schema for creating a new order from TMA frontend checkout.
    """
    product_id: int = Field(..., description="ID of the selected product")
    delivery_type: DeliveryType = Field(..., description="pickup or delivery")
    delivery_provider: Optional[str] = Field(None, description="e.g., 'СДЭК', 'Почта России'")
    delivery_address: str = Field(..., min_length=2, description="PVZ address, full home address, or pickup notes")
    customer_name: str = Field(..., min_length=2, max_length=255, description="Customer full name")
    customer_phone: str = Field(..., min_length=6, max_length=32, description="Customer phone number")
    payment_method: PaymentMethod = Field(..., description="cash, sbp, usdt_ton, usdt_trc20, ton")
    crypto_tx_id: Optional[str] = Field(None, max_length=255, description="Transaction hash if paid with crypto")

    @field_validator("payment_method")
    @classmethod
    def validate_payment_for_delivery(cls, payment_method: PaymentMethod, info) -> PaymentMethod:
        delivery_type = info.data.get("delivery_type")
        if delivery_type == DeliveryType.DELIVERY and payment_method == PaymentMethod.CASH:
            raise ValueError("Оплата наличными доступна только при выборе самовывоза.")
        return payment_method


class OrderStatusUpdate(BaseModel):
    """
    Schema for updating order status from Telegram admin actions or customer.
    """
    status: OrderStatus = Field(..., description="New order status")
    admin_notes: Optional[str] = Field(None, description="Optional notes or tracking number")


class OrderResponse(BaseModel):
    """
    Full order representation returned to client and admin.
    """
    model_config = ConfigDict(from_attributes=True)

    id: int
    order_number: str
    telegram_id: int
    product_id: Optional[int]
    product_title: str
    product_price: float
    delivery_type: DeliveryType
    delivery_type_label: str
    delivery_provider: Optional[str]
    delivery_address: str
    customer_name: str
    customer_phone: str
    payment_method: PaymentMethod
    payment_method_label: str
    crypto_tx_id: Optional[str]
    status: OrderStatus
    status_label: str
    admin_notes: Optional[str]
    product_photos: List[str] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_orm_model(cls, order_obj) -> "OrderResponse":
        photos = []
        if order_obj.product:
            photos = order_obj.product.photo_list

        return cls(
            id=order_obj.id,
            order_number=order_obj.order_number,
            telegram_id=order_obj.telegram_id,
            product_id=order_obj.product_id,
            product_title=order_obj.product_title,
            product_price=order_obj.product_price,
            delivery_type=order_obj.delivery_type,
            delivery_type_label=order_obj.delivery_type.label_ru,
            delivery_provider=order_obj.delivery_provider,
            delivery_address=order_obj.delivery_address,
            customer_name=order_obj.customer_name,
            customer_phone=order_obj.customer_phone,
            payment_method=order_obj.payment_method,
            payment_method_label=order_obj.payment_method.label_ru,
            crypto_tx_id=order_obj.crypto_tx_id,
            status=order_obj.status,
            status_label=order_obj.status.label_ru,
            admin_notes=order_obj.admin_notes,
            product_photos=photos,
            created_at=order_obj.created_at,
            updated_at=order_obj.updated_at
        )
