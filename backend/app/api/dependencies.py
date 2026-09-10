import hashlib
import hmac
import json
import logging
import urllib.parse
from typing import Optional
from fastapi import Depends, Header, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.config import get_settings
from backend.app.database import get_db
from backend.app.models.user import User
from backend.app.schemas.auth import TelegramAuthData, TelegramUser

logger = logging.getLogger(__name__)
settings = get_settings()


def verify_telegram_init_data(init_data: str, bot_token: str) -> TelegramAuthData:
    """
    Validates Telegram WebApp initData string using HMAC-SHA256 signature verification.
    """
    if not init_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Отсутствуют данные аутентификации Telegram (initData)."
        )

    try:
        parsed_data = dict(urllib.parse.parse_qsl(init_data, keep_blank_values=True))
    except Exception as e:
        logger.error(f"Error parsing initData query string: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Некорректный формат initData."
        )

    provided_hash = parsed_data.pop("hash", None)
    if not provided_hash:
        # Dev bypass if running in DEBUG and dummy token
        if settings.DEBUG and "dummy" in bot_token:
            logger.warning("DEBUG mode: bypassing Telegram HMAC check with dummy token.")
            user_json = parsed_data.get("user")
            if user_json:
                user_dict = json.loads(user_json)
                return TelegramAuthData(
                    query_id=parsed_data.get("query_id"),
                    user=TelegramUser(**user_dict),
                    auth_date=int(parsed_data.get("auth_date", 0)),
                    hash="dev_mock_hash"
                )
            # Default dev mock user
            return TelegramAuthData(
                query_id="dev_query_id",
                user=TelegramUser(
                    id=999999999,
                    first_name="Тестовый",
                    last_name="Пользователь",
                    username="test_dev_user"
                ),
                auth_date=0,
                hash="dev_mock_hash"
            )

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Хеш подписи Telegram отсутствует."
        )

    # Sort key-value pairs alphabetically
    sorted_items = sorted(parsed_data.items(), key=lambda item: item[0])
    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted_items)

    # Calculate secret key: HMAC_SHA256("WebAppData", bot_token)
    secret_key = hmac.new(
        key=b"WebAppData",
        msg=bot_token.encode("utf-8"),
        digestmod=hashlib.sha256
    ).digest()

    # Calculate data hash: HMAC_SHA256(secret_key, data_check_string)
    calculated_hash = hmac.new(
        key=secret_key,
        msg=data_check_string.encode("utf-8"),
        digestmod=hashlib.sha256
    ).hexdigest()

    # Compare hashes safely
    if not hmac.compare_digest(calculated_hash, provided_hash):
        logger.warning("Telegram initData HMAC hash mismatch.")
        # Allow dev fallback if in DEBUG mode
        if not settings.DEBUG:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Недействительная подпись данных Telegram."
            )

    user_json = parsed_data.get("user")
    if not user_json:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Данные пользователя отсутствуют в initData."
        )

    try:
        user_dict = json.loads(user_json)
        telegram_user = TelegramUser(**user_dict)
    except Exception as e:
        logger.error(f"Error parsing Telegram user JSON: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Некорректный JSON пользователя Telegram."
        )

    return TelegramAuthData(
        query_id=parsed_data.get("query_id"),
        user=telegram_user,
        auth_date=int(parsed_data.get("auth_date", 0)),
        hash=provided_hash
    )


async def get_current_telegram_user(
    x_telegram_init_data: Optional[str] = Header(None, alias="X-Telegram-Init-Data"),
    authorization: Optional[str] = Header(None, alias="Authorization"),
    init_data_query: Optional[str] = Query(None, alias="init_data")
) -> TelegramUser:
    """
    Extracts and verifies Telegram user from HTTP Header or Query Parameter.
    """
    raw_init_data = x_telegram_init_data or init_data_query
    if not raw_init_data and authorization:
        if authorization.startswith("Bearer "):
            raw_init_data = authorization[7:].strip()
        else:
            raw_init_data = authorization.strip()

    if not raw_init_data:
        # If in debug mode, provide a default mock user for convenient direct browser preview
        if settings.DEBUG:
            return TelegramUser(
                id=settings.ADMIN_CHAT_ID or 100000001,
                first_name="Гость",
                last_name="Web",
                username="guest_web_user"
            )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Заголовок 'X-Telegram-Init-Data' не предоставлен."
        )

    auth_data = verify_telegram_init_data(raw_init_data, settings.BOT_TOKEN)
    return auth_data.user


async def get_current_user_db(
    telegram_user: TelegramUser = Depends(get_current_telegram_user),
    db: AsyncSession = Depends(get_db)
) -> User:
    """
    Retrieves or creates/synchronizes the User entity in the database.
    """
    result = await db.execute(
        select(User).where(User.telegram_id == telegram_user.id)
    )
    db_user = result.scalar_one_or_none()

    if not db_user:
        db_user = User(
            telegram_id=telegram_user.id,
            username=telegram_user.username,
            first_name=telegram_user.first_name,
            last_name=telegram_user.last_name,
            language_code=telegram_user.language_code,
            is_admin=(telegram_user.id == settings.ADMIN_CHAT_ID)
        )
        db.add(db_user)
        await db.commit()
        await db.refresh(db_user)
    else:
        # Update user metadata if changed
        updated = False
        if db_user.username != telegram_user.username:
            db_user.username = telegram_user.username
            updated = True
        if db_user.first_name != telegram_user.first_name:
            db_user.first_name = telegram_user.first_name
            updated = True
        if db_user.last_name != telegram_user.last_name:
            db_user.last_name = telegram_user.last_name
            updated = True
        if telegram_user.id == settings.ADMIN_CHAT_ID and not db_user.is_admin:
            db_user.is_admin = True
            updated = True

        if updated:
            await db.commit()
            await db.refresh(db_user)

    return db_user
