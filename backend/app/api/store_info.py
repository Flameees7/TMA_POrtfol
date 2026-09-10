from fastapi import APIRouter
from pydantic import BaseModel
from backend.app.config import get_settings

settings = get_settings()
router = APIRouter(prefix="/store", tags=["Store Info & Requisites"])


class StoreRequisitesResponse(BaseModel):
    # SBP Details
    sbp_phone: str
    sbp_bank: str
    sbp_receiver_name: str

    # Crypto Wallets
    crypto_ton_wallet: str
    crypto_usdt_ton_wallet: str
    crypto_usdt_trc20_wallet: str

    # Pickup Location
    pickup_address: str
    pickup_working_hours: str
    pickup_instructions: str


@router.get(
    "/info",
    response_model=StoreRequisitesResponse,
    summary="Получить реквизиты магазина и данные самовывоза",
    description="Возвращает актуальные банковские реквизиты, адреса криптовалютных кошельков и информацию о точке самовывоза."
)
async def get_store_requisites() -> StoreRequisitesResponse:
    """
    Returns store payment requisites and pickup details.
    """
    return StoreRequisitesResponse(
        sbp_phone=settings.SBP_PHONE,
        sbp_bank=settings.SBP_BANK,
        sbp_receiver_name=settings.SBP_RECEIVER_NAME,
        crypto_ton_wallet=settings.CRYPTO_TON_WALLET,
        crypto_usdt_ton_wallet=settings.CRYPTO_USDT_TON_WALLET,
        crypto_usdt_trc20_wallet=settings.CRYPTO_USDT_TRC20_WALLET,
        pickup_address=settings.PICKUP_ADDRESS,
        pickup_working_hours=settings.PICKUP_WORKING_HOURS,
        pickup_instructions=settings.PICKUP_INSTRUCTIONS
    )
