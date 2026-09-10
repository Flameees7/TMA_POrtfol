import logging
from typing import Any, Dict
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.database import get_db
from backend.app.services.sheets_sync import GoogleSheetsSyncService

logger = logging.getLogger("api_sync")
router = APIRouter(prefix="/sync", tags=["Sync"])


@router.post(
    "",
    summary="Запустить синхронизацию с Google Sheets",
    description="Принудительно запускает процесс импорта и обновления товаров из Google таблицы в базу данных."
)
async def trigger_sync(
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    Triggers on-demand synchronization with Google Sheets.
    """
    logger.info("Manual Google Sheets synchronization triggered via API.")
    report = await GoogleSheetsSyncService.sync_database(db)
    return report
