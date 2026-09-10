import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.database import get_db
from backend.app.models.product import Product
from backend.app.schemas.product import ProductResponse

logger = logging.getLogger("api_products")
router = APIRouter(prefix="/products", tags=["Products"])


@router.get(
    "",
    response_model=List[ProductResponse],
    summary="Получить список товаров",
    description="Возвращает список доступных товаров каталога с возможностью поиска и фильтрации."
)
async def get_products(
    search: Optional[str] = Query(None, description="Поисковый запрос по названию или описанию"),
    in_stock_only: bool = Query(False, description="Показывать только товары в наличии"),
    db: AsyncSession = Depends(get_db)
) -> List[ProductResponse]:
    """
    Returns list of products from database.
    """
    query = select(Product)

    if in_stock_only:
        query = query.where(Product.is_available == True)

    if search and search.strip():
        search_pattern = f"%{search.strip().lower()}%"
        query = query.where(
            (Product.title.ilike(search_pattern)) | (Product.description.ilike(search_pattern))
        )

    query = query.order_by(desc(Product.is_available), Product.id)

    result = await db.execute(query)
    products = result.scalars().all()

    return [ProductResponse.from_orm_model(p) for p in products]


@router.get(
    "/{product_id}",
    response_model=ProductResponse,
    summary="Получить информацию о товаре по ID",
    description="Возвращает детальную информацию о конкретном товаре, включая галерею фотографий."
)
async def get_product_by_id(
    product_id: int,
    db: AsyncSession = Depends(get_db)
) -> ProductResponse:
    """
    Returns single product details by primary key ID.
    """
    result = await db.execute(select(Product).where(Product.id == product_id))
    product = result.scalar_one_or_none()

    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Товар с ID {product_id} не найден."
        )

    return ProductResponse.from_orm_model(product)
