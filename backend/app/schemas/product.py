from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class ProductBase(BaseModel):
    title: str = Field(..., max_length=512, description="Product title")
    description: Optional[str] = Field(None, description="Detailed product description")
    price: float = Field(..., ge=0, description="Product price in RUB")
    is_available: bool = Field(True, description="Whether product is available for purchase")
    stock_status: str = Field("in_stock", description="Stock status label (in_stock, out_of_stock, reserved)")


class ProductCreate(ProductBase):
    external_id: str = Field(..., max_length=128, description="Unique ID from Google Sheet")
    photos: Optional[str] = Field(None, description="Raw photos data (comma separated or JSON array)")


class ProductUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = None
    photos: Optional[str] = None
    is_available: Optional[bool] = None
    stock_status: Optional[str] = None


class ProductResponse(ProductBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    external_id: str
    photos: List[str] = Field(default_factory=list, description="Parsed list of photo URLs")
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_orm_model(cls, product_obj) -> "ProductResponse":
        """Converts an ORM Product instance, parsing photo_list automatically."""
        return cls(
            id=product_obj.id,
            external_id=product_obj.external_id,
            title=product_obj.title,
            description=product_obj.description,
            price=product_obj.price,
            photos=product_obj.photo_list,
            is_available=product_obj.is_available,
            stock_status=product_obj.stock_status,
            created_at=product_obj.created_at,
            updated_at=product_obj.updated_at
        )
