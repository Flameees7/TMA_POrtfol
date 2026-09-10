from functools import lru_cache
from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application configuration settings loaded from environment variables and .env file.
    """
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # Base Paths
    BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent

    # Telegram Bot
    BOT_TOKEN: str = "1234567890:ABCdefGHIjklMNOpqrsTUVwxyz"
    ADMIN_CHAT_ID: int = 0
    WEBAPP_URL: str = "http://localhost:8000"

    # Server Settings
    SERVER_HOST: str = "0.0.0.0"
    SERVER_PORT: int = 8000
    DEBUG: bool = True

    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./shop.db"

    # Google Sheets Integration
    GOOGLE_SERVICE_ACCOUNT_FILE: str = "credentials/google_service_account.json"
    GOOGLE_SPREADSHEET_ID: str = ""
    GOOGLE_SHEET_NAME: str = "Товары"
    SYNC_INTERVAL_SECONDS: int = 300

    # Store & Payment Requisites (SBP)
    SBP_PHONE: str = "+7 (999) 000-00-00"
    SBP_BANK: str = "Т-Банк / Сбер"
    SBP_RECEIVER_NAME: str = "Иван И."

    # Store & Payment Requisites (Crypto)
    CRYPTO_TON_WALLET: str = "EQD1234567890abcdef1234567890abcdef1234567890abc"
    CRYPTO_USDT_TON_WALLET: str = "EQD1234567890abcdef1234567890abcdef1234567890abc"
    CRYPTO_USDT_TRC20_WALLET: str = "TXYZ1234567890abcdef1234567890abcdef123"

    # Store Pickup Requisites
    PICKUP_ADDRESS: str = "г. Москва, ул. Примерная, д. 10, оф. 205"
    PICKUP_WORKING_HOURS: str = "Пн-Пт: 10:00 - 20:00, Сб-Вс: 11:00 - 18:00"
    PICKUP_INSTRUCTIONS: str = "Для входа наберите на домофоне 205 или позвоните менеджеру."

    @property
    def google_credentials_path(self) -> Path:
        """Returns resolved absolute path to Google service account credentials."""
        file_path = Path(self.GOOGLE_SERVICE_ACCOUNT_FILE)
        if not file_path.is_absolute():
            file_path = self.BASE_DIR / file_path
        return file_path


@lru_cache()
def get_settings() -> Settings:
    """Cached singleton for application settings."""
    return Settings()
