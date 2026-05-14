import os
from urllib.parse import urlparse, urlencode, parse_qs, urlunparse

from pydantic import field_validator
from pydantic_settings import BaseSettings


def _get_database_url() -> str:
    url = os.environ.get("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/reminders")
    if url.startswith("postgresql://") or url.startswith("postgres://"):
        parsed = urlparse(url)
        params = parse_qs(parsed.query)
        params.pop("sslmode", None)
        new_query = urlencode({k: v[0] for k, v in params.items()})
        new_parsed = parsed._replace(scheme="postgresql+asyncpg", query=new_query)
        url = urlunparse(new_parsed)
    return url


class Settings(BaseSettings):
    bot_token: str
    database_url: str = ""

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

    @field_validator("database_url", mode="before")
    @classmethod
    def fix_database_url(cls, v):
        if not v:
            v = os.environ.get("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/reminders")
        if v.startswith("postgresql://") or v.startswith("postgres://"):
            parsed = urlparse(v)
            params = parse_qs(parsed.query)
            params.pop("sslmode", None)
            new_query = urlencode({k: v2[0] for k, v2 in params.items()})
            new_parsed = parsed._replace(scheme="postgresql+asyncpg", query=new_query)
            v = urlunparse(new_parsed)
        return v


def get_settings() -> Settings:
    return Settings()
