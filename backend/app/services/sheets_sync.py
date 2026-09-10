import asyncio
import json
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
import gspread
from google.oauth2.service_account import Credentials
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.config import get_settings
from backend.app.database import AsyncSessionLocal
from backend.app.models.product import Product

logger = logging.getLogger("sheets_sync")
settings = get_settings()

# Default Google API Scopes for Sheets & Drive
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets.readonly",
    "https://www.googleapis.com/auth/drive.readonly"
]

# High quality sample products for initial database seeding if Google Sheets is not yet linked
SAMPLE_PRODUCTS = [
    {
        "external_id": "SKU-001",
        "title": "Беспроводные наушники Pro Wireless Max",
        "description": "Премиальные накладные наушники с активным шумоподавлением нового поколения, пространственным аудио и временем работы до 40 часов от одного заряда. Идеальный баланс басов и чистых высоких частот.",
        "price": 14990.0,
        "photos": "https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=800&q=80,https://images.unsplash.com/photo-1484704849700-f032a568e944?w=800&q=80,https://images.unsplash.com/photo-1546435770-a3e426bf472b?w=800&q=80",
        "is_available": True,
        "stock_status": "in_stock"
    },
    {
        "external_id": "SKU-002",
        "title": "Смарт-часы Titanium Ultra 49mm",
        "description": "Флагманский титановый корпус, сверхъяркий OLED-дисплей 2000 нит, датчик кислорода в крови, ЭКГ и двухчастотный GPS. Водонепроницаемость до 100 метров.",
        "price": 27900.0,
        "photos": "https://images.unsplash.com/photo-1523275335684-37898b6baf30?w=800&q=80,https://images.unsplash.com/photo-1546868871-7041f2a55e12?w=800&q=80",
        "is_available": True,
        "stock_status": "in_stock"
    },
    {
        "external_id": "SKU-003",
        "title": "Кожаный рюкзак Urban Nomad",
        "description": "Стильный городской рюкзак из натуральной итальянской кожи растительного дубления. Отделение для ноутбука до 16 дюймов с защитой от ударов, потайные карманы для документов и влагозащитные молнии YKK.",
        "price": 9500.0,
        "photos": "https://images.unsplash.com/photo-1553062407-98eeb64c6a62?w=800&q=80,https://images.unsplash.com/photo-1622560480605-d83c853bc5c3?w=800&q=80",
        "is_available": True,
        "stock_status": "in_stock"
    },
    {
        "external_id": "SKU-004",
        "title": "Портативная акустика SoundWave Pulse",
        "description": "Компактная колонка с мощным объемным звуком 360°, глубоким басом и динамической подсветкой. Защита от воды IP67, режим TWS для стереопары.",
        "price": 6490.0,
        "photos": "https://images.unsplash.com/photo-1608043152269-423dbba4e7e1?w=800&q=80,https://images.unsplash.com/photo-1545454675-3531b543be5d?w=800&q=80",
        "is_available": True,
        "stock_status": "in_stock"
    },
    {
        "external_id": "SKU-005",
        "title": "Механическая клавиатура Stealth Pro Wireless",
        "description": "Кастомная беспроводная клавиатура 75% формата. Смазанные тактильные переключатели, шумоизоляция из порона, PBT-кейкапы и подключение по 2.4Ghz / Bluetooth / Type-C.",
        "price": 11200.0,
        "photos": "https://images.unsplash.com/photo-1587829741301-dc798b83add3?w=800&q=80,https://images.unsplash.com/photo-1618384887929-16ec33fab9ef?w=800&q=80",
        "is_available": True,
        "stock_status": "in_stock"
    },
    {
        "external_id": "SKU-006",
        "title": "Минималистичный кошелек-кардхолдер MagSafe",
        "description": "Ультратонкий картхолдер из авиационного алюминия и матовой кожи. Вмещает до 8 карт с защитой RFID от считывания. Магнитная фиксация к смартфону.",
        "price": 2800.0,
        "photos": "https://images.unsplash.com/photo-1627123424574-724758594e93?w=800&q=80",
        "is_available": True,
        "stock_status": "in_stock"
    }
]


class GoogleSheetsSyncService:
    """
    Service responsible for reading Google Spreadsheet data and synchronizing
    it with the local database.
    """

    @staticmethod
    def _parse_price(raw_val: Any) -> float:
        """Parses price values removing currency symbols, spaces, and commas."""
        if raw_val is None:
            return 0.0
        if isinstance(raw_val, (int, float)):
            return float(raw_val)

        val_str = str(raw_val).strip()
        # Remove currency symbols (₽, $, €, etc.) and whitespaces
        cleaned = re.sub(r"[^\d.,]", "", val_str)
        if not cleaned:
            return 0.0
        # Replace comma with dot
        cleaned = cleaned.replace(",", ".")
        try:
            return float(cleaned)
        except ValueError:
            logger.warning(f"Could not parse price from value: '{raw_val}'")
            return 0.0

    @staticmethod
    def _parse_availability_and_status(raw_val: Any) -> tuple[bool, str]:
        """
        Parses status/availability column.
        Returns (is_available: bool, stock_status: str).
        """
        if raw_val is None:
            return True, "in_stock"

        val_str = str(raw_val).strip().lower()

        if val_str in ("в наличии", "есть", "да", "yes", "true", "1", "in_stock", "available"):
            return True, "in_stock"
        elif val_str in ("резерв", "reserved", "забронировано"):
            return True, "reserved"
        elif val_str in ("нет в наличии", "нет", "no", "false", "0", "out_of_stock", "sold_out", "закончился"):
            return False, "out_of_stock"
        elif val_str in ("под заказ", "preorder"):
            return True, "preorder"

        # Default fallback: if any text present and not explicitly out of stock
        return True, "in_stock"

    @classmethod
    def _find_column_value(cls, row_dict: Dict[str, Any], candidate_keys: List[str]) -> Optional[Any]:
        """Finds dictionary value matching any of the candidate column header names (case-insensitive)."""
        normalized_row = {str(k).strip().lower(): v for k, v in row_dict.items()}
        for candidate in candidate_keys:
            cand_lower = candidate.strip().lower()
            if cand_lower in normalized_row:
                return normalized_row[cand_lower]
        return None

    @classmethod
    def _fetch_sheet_records_sync(cls) -> List[Dict[str, Any]]:
        """
        Synchronous worker that connects to Google Sheets API and downloads rows.
        Supports both Service Account JSON authentication and public Sheet CSV export.
        """
        cred_path = settings.google_credentials_path
        spreadsheet_id = settings.GOOGLE_SPREADSHEET_ID.strip()

        if not spreadsheet_id:
            logger.info("GOOGLE_SPREADSHEET_ID is not configured.")
            return []

        # Method 1: Google Service Account Credentials
        if cred_path.exists():
            try:
                credentials = Credentials.from_service_account_file(
                    str(cred_path),
                    scopes=SCOPES
                )
                gc = gspread.authorize(credentials)
                sheet = gc.open_by_key(spreadsheet_id)
                worksheet = sheet.worksheet(settings.GOOGLE_SHEET_NAME)
                records = worksheet.get_all_records()
                logger.info(f"Fetched {len(records)} rows from Google Sheet '{settings.GOOGLE_SHEET_NAME}' via Service Account.")
                return records
            except gspread.WorksheetNotFound:
                logger.error(f"Worksheet '{settings.GOOGLE_SHEET_NAME}' not found in spreadsheet {spreadsheet_id}.")
            except Exception as e:
                logger.error(f"Error fetching data via Google Service Account: {e}", exc_info=True)

        # Method 2: Public Google Sheets CSV Export (if shared with 'Anyone with link')
        try:
            import csv
            import io
            import urllib.parse
            import httpx

            sheet_name_encoded = urllib.parse.quote(settings.GOOGLE_SHEET_NAME)
            url = f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/gviz/tq?tqx=out:csv&sheet={sheet_name_encoded}"
            
            with httpx.Client(follow_redirects=True, timeout=10.0) as client:
                res = client.get(url)
                if res.status_code == 200 and not res.text.strip().startswith("<!DOCTYPE html>"):
                    reader = csv.DictReader(io.StringIO(res.text))
                    records = [row for row in reader if any(row.values())]
                    logger.info(f"Fetched {len(records)} rows from Google Sheet via public CSV export.")
                    return records
                elif res.status_code == 401 or "<!DOCTYPE html>" in res.text:
                    logger.warning(
                        "Google Sheet is private. To enable automatic sync, click 'Share' (Поделиться) in Google Sheets and set access to 'Anyone with the link' (Все, у кого есть ссылка - Читатель), OR provide google_service_account.json."
                    )
        except Exception as e:
            logger.error(f"Error fetching public Google Sheet CSV: {e}")

        return []

    @classmethod
    async def fetch_sheet_records(cls) -> List[Dict[str, Any]]:
        """Asynchronously fetches rows from Google Sheet."""
        return await asyncio.to_thread(cls._fetch_sheet_records_sync)

    @classmethod
    async def sync_database(cls, db: AsyncSession) -> Dict[str, Any]:
        """
        Synchronizes products in the database with Google Sheets or fallback seeds.
        """
        records = await cls.fetch_sheet_records()

        # If Google Sheets is not configured or returned 0 records, check if DB has products
        if not records:
            count_result = await db.execute(select(Product))
            existing_products = count_result.scalars().all()

            if not existing_products:
                logger.info("Database is empty and Google Sheets is not configured. Seeding sample portfolio products...")
                created_count = 0
                for item in SAMPLE_PRODUCTS:
                    product = Product(
                        external_id=item["external_id"],
                        title=item["title"],
                        description=item["description"],
                        price=item["price"],
                        photos=item["photos"],
                        is_available=item["is_available"],
                        stock_status=item["stock_status"]
                    )
                    db.add(product)
                    created_count += 1
                await db.commit()
                return {
                    "status": "seeded_samples",
                    "created": created_count,
                    "updated": 0,
                    "total": created_count,
                    "timestamp": datetime.now().isoformat()
                }

            return {
                "status": "skipped",
                "message": "No Google Sheets data received; existing database records retained.",
                "total": len(existing_products),
                "timestamp": datetime.now().isoformat()
            }

        created_count = 0
        updated_count = 0
        sheet_external_ids = set()

        for idx, row in enumerate(records, start=1):
            raw_id = cls._find_column_value(row, ["id", "ID", "артикул", "sku", "код"])
            raw_title = cls._find_column_value(row, ["название", "наименование", "title", "name", "товар"])
            raw_desc = cls._find_column_value(row, ["описание", "description", "информация", "детали"])
            raw_price = cls._find_column_value(row, ["цена", "стоимость", "price", "rub", "руб"])
            raw_photos = cls._find_column_value(row, ["ссылки на фото через запятую", "фото", "photos", "photo", "картинки", "изображения", "images"])
            raw_status = cls._find_column_value(row, ["наличие/статус", "наличие", "статус", "status", "stock", "в наличии"])

            # Skip row if title is missing
            if not raw_title or not str(raw_title).strip():
                continue

            external_id = str(raw_id).strip() if raw_id else f"ROW-{idx}"
            sheet_external_ids.add(external_id)

            title = str(raw_title).strip()
            description = str(raw_desc).strip() if raw_desc else ""
            price = cls._parse_price(raw_price)
            photos = str(raw_photos).strip() if raw_photos else ""
            is_available, stock_status = cls._parse_availability_and_status(raw_status)

            # Query existing product by external_id
            result = await db.execute(select(Product).where(Product.external_id == external_id))
            product = result.scalar_one_or_none()

            if product:
                # Update existing product
                product.title = title
                product.description = description
                product.price = price
                product.photos = photos
                product.is_available = is_available
                product.stock_status = stock_status
                updated_count += 1
            else:
                # Create new product
                product = Product(
                    external_id=external_id,
                    title=title,
                    description=description,
                    price=price,
                    photos=photos,
                    is_available=is_available,
                    stock_status=stock_status
                )
                db.add(product)
                created_count += 1

        # Optionally mark products not in sheet as unavailable
        all_products_res = await db.execute(select(Product))
        all_products = all_products_res.scalars().all()
        for p in all_products:
            if p.external_id not in sheet_external_ids and p.is_available:
                p.is_available = False
                p.stock_status = "out_of_stock"
                updated_count += 1

        await db.commit()
        logger.info(f"Google Sheets sync completed. Created: {created_count}, Updated: {updated_count}, Total in DB: {len(all_products)}")

        return {
            "status": "success",
            "created": created_count,
            "updated": updated_count,
            "total": len(all_products),
            "timestamp": datetime.now().isoformat()
        }


# Background task runner for periodic synchronization
_sync_task: Optional[asyncio.Task] = None


async def _periodic_sync_loop() -> None:
    """Continuous background loop triggering synchronization at configured intervals."""
    logger.info(f"Periodic sync loop started. Interval: {settings.SYNC_INTERVAL_SECONDS}s")
    while True:
        try:
            async with AsyncSessionLocal() as db:
                await GoogleSheetsSyncService.sync_database(db)
        except asyncio.CancelledError:
            logger.info("Periodic sync task cancelled.")
            break
        except Exception as e:
            logger.error(f"Unhandled error in periodic sync task: {e}", exc_info=True)

        try:
            await asyncio.sleep(settings.SYNC_INTERVAL_SECONDS)
        except asyncio.CancelledError:
            break


def start_periodic_sync_task() -> Optional[asyncio.Task]:
    """Starts the background synchronization task if not already running."""
    global _sync_task
    if _sync_task is None or _sync_task.done():
        _sync_task = asyncio.create_task(_periodic_sync_loop())
        logger.info("Background periodic sync task spawned.")
    return _sync_task


def stop_periodic_sync_task() -> None:
    """Stops the background synchronization task cleanly."""
    global _sync_task
    if _sync_task and not _sync_task.done():
        _sync_task.cancel()
        logger.info("Background periodic sync task cancellation requested.")
    _sync_task = None
