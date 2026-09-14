import asyncio
import logging
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from backend.app.api.orders import router as orders_router
from backend.app.api.products import router as products_router
from backend.app.api.store_info import router as store_router
from backend.app.api.sync import router as sync_router
from backend.app.config import get_settings
from backend.app.database import AsyncSessionLocal, init_db
from backend.app.services.sheets_sync import (
    GoogleSheetsSyncService,
    start_periodic_sync_task,
    stop_periodic_sync_task
)

# Logging configuration
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("tma_shop_app")

settings = get_settings()
_bot_task: asyncio.Task = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager:
    1. Initializes database tables.
    2. Performs initial Google Sheets sync or demo seed.
    3. Starts background synchronization task.
    4. Starts Telegram Bot polling in background (if configured).
    5. Cleans up background tasks on shutdown.
    """
    logger.info("Starting TMA Store Backend Application...")

    # 1. Initialize database tables and upload folders
    await init_db()
    (settings.BASE_DIR / "frontend" / "uploads").mkdir(parents=True, exist_ok=True)

    # 2. Perform initial synchronization or seed demo items
    try:
        async with AsyncSessionLocal() as db:
            report = await GoogleSheetsSyncService.sync_database(db)
            logger.info(f"Startup sync report: {report}")
    except Exception as e:
        logger.error(f"Startup sync encountered an error: {e}", exc_info=True)

    # 3. Start background periodic sync task
    start_periodic_sync_task()

    # 4. Start Telegram bot in background if token is provided
    global _bot_task
    try:
        from backend.app.bot.bot_instance import start_bot_polling, stop_bot_polling
        _bot_task = asyncio.create_task(start_bot_polling())
        logger.info("Telegram Bot polling task started.")
    except Exception as e:
        logger.warning(f"Telegram Bot module could not be started at this stage: {e}")

    yield

    # Shutdown sequence
    logger.info("Shutting down TMA Store Backend...")
    stop_periodic_sync_task()

    try:
        from backend.app.bot.bot_instance import stop_bot_polling
        await stop_bot_polling()
    except Exception:
        pass

    if _bot_task and not _bot_task.done():
        _bot_task.cancel()

    logger.info("Application shutdown complete.")


app = FastAPI(
    title="Telegram Mini App Shop API",
    description="Backend REST API and Telegram Bot for TMA Online Store with Google Sheets integration.",
    version="1.0.0",
    lifespan=lifespan
)

# CORS configuration allowing TMA and web clients
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API Routers
app.include_router(products_router, prefix="/api")
app.include_router(orders_router, prefix="/api")
app.include_router(store_router, prefix="/api")
app.include_router(sync_router, prefix="/api")


@app.get("/api/health", tags=["Health"], summary="Проверка работоспособности сервиса")
async def health_check():
    """Healthcheck endpoint for monitoring."""
    return {
        "status": "healthy",
        "debug": settings.DEBUG,
        "database": "connected"
    }


# Frontend static files mounting
frontend_dir = settings.BASE_DIR / "frontend"
if frontend_dir.exists():
    app.mount("/static", StaticFiles(directory=str(frontend_dir)), name="static")

    @app.get("/", include_in_schema=False)
    async def serve_index():
        index_file = frontend_dir / "index.html"
        if index_file.exists():
            return FileResponse(str(index_file))
        return JSONResponse({"message": "Telegram Mini App Frontend is under development."})
