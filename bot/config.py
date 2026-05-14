import os
from pydantic_settings import BaseSettings


def _get_database_url() -> str:
    url = os.environ.get("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/reminders")
    if url.startswith("postgresql://") or url.startswith("postgres://"):
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
        url = url.replace("postgres://", "postgresql+asyncpg://", 1)
    return url


class Settings(BaseSettings):
    bot_token: str
    database_url: str = ""

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

    def model_post_init(self, __context):
        if not self.database_url:
            object.__setattr__(self, "database_url", _get_database_url())


def get_settings() -> Settings:
    return Settings()
