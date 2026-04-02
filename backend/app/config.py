import json
from typing import Any
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    DATABASE_URL: str = "postgresql+asyncpg://loluser:lolpass@db:5432/loldb"
    REDIS_URL: str = "redis://redis:6379/0"
    PANDASCORE_API_KEY: str = ""
    THE_ODDS_API_KEY: str = ""
    ODDSPAPI_SECRET_KEY: str = ""
    SECRET_KEY: str = "change_this_to_a_random_secret"
    ALLOWED_USERS: list[dict[str, Any]] = [{"username": "admin", "password": "changeme"}]
    ENVIRONMENT: str = "dev"
    LOG_LEVEL: str = "INFO"

    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    def model_post_init(self, __context: Any) -> None:
        if isinstance(self.ALLOWED_USERS, str):
            object.__setattr__(self, "ALLOWED_USERS", json.loads(self.ALLOWED_USERS))


settings = Settings()
