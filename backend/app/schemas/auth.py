from typing import Optional
from pydantic import BaseModel, Field


class TelegramUser(BaseModel):
    """
    User details parsed from Telegram.WebApp.initData.
    """
    id: int = Field(..., description="Telegram User ID")
    first_name: str = Field(..., description="First name of the user")
    last_name: Optional[str] = Field(None, description="Last name of the user")
    username: Optional[str] = Field(None, description="Telegram username without @")
    language_code: Optional[str] = Field(None, description="IETF language tag")
    is_premium: Optional[bool] = Field(False, description="True if user is a Telegram Premium subscriber")
    photo_url: Optional[str] = Field(None, description="URL of user profile photo")

    @property
    def full_name(self) -> str:
        if self.last_name:
            return f"{self.first_name} {self.last_name}".strip()
        return self.first_name

    @property
    def mention(self) -> str:
        if self.username:
            return f"@{self.username}"
        return f'<a href="tg://user?id={self.id}">{self.first_name}</a>'


class TelegramAuthData(BaseModel):
    """
    Full parsed and validated Telegram WebApp auth data.
    """
    query_id: Optional[str] = None
    user: TelegramUser
    auth_date: int
    hash: str
