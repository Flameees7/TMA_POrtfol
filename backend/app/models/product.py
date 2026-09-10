import json
from datetime import datetime
from typing import TYPE_CHECKING, List, Optional
from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.app.database import Base

if TYPE_CHECKING:
    from backend.app.models.order import Order


class Product(Base):
    """
    Product model synchronized with Google Sheets.
    """
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    external_id: Mapped[str] = mapped_column(String(128), unique=True, index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    price: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    photos: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON or comma-separated URLs
    is_available: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    stock_status: Mapped[str] = mapped_column(String(64), default="in_stock", nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False
    )

    # Relationships
    orders: Mapped[List["Order"]] = relationship("Order", back_populates="product")

    @property
    def photo_list(self) -> List[str]:
        """
        Parses stored photos string into a list of clean URLs.
        Supports both JSON array and comma-separated/newline-separated URLs.
        """
        if not self.photos:
            return []
        raw = self.photos.strip()
        if not raw:
            return []

        # Attempt JSON decoding
        if raw.startswith("[") and raw.endswith("]"):
            try:
                parsed = json.loads(raw)
                if isinstance(parsed, list):
                    return [str(item).strip() for item in parsed if str(item).strip()]
            except json.JSONDecodeError:
                pass

        # Split by comma or newline
        urls = []
        for part in raw.replace("\n", ",").split(","):
            cleaned = part.strip()
            if cleaned:
                urls.append(cleaned)
        return urls

    def __repr__(self) -> str:
        return f"<Product(id={self.id}, external_id='{self.external_id}', title='{self.title[:30]}', price={self.price})>"
