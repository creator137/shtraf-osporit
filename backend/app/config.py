from functools import lru_cache
from pathlib import Path
from typing import Literal
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from pydantic import PostgresDsn, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    database_url: PostgresDsn
    bot_token: SecretStr | None = None
    telegram_proxy: str | None = None
    document_storage: Literal["local", "telegram"] = "local"
    admin_origin: str = "http://localhost:5173"
    ocr_provider: Literal["none", "ocrspace"] = "none"
    ocr_space_api_key: SecretStr | None = None
    ocr_space_language: str = "rus"

    model_config = SettingsConfigDict(
        env_file=REPOSITORY_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def async_database_url(self) -> str:
        url = str(self.database_url)
        if url.startswith("postgresql://"):
            url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
        parts = urlsplit(url)
        query = [
            (key, value)
            for key, value in parse_qsl(parts.query, keep_blank_values=True)
            if key not in {"channel_binding", "sslmode"}
        ]
        return urlunsplit(parts._replace(query=urlencode(query)))

    @property
    def database_connect_args(self) -> dict[str, bool]:
        return {"ssl": True} if "sslmode=require" in str(self.database_url) else {}


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
