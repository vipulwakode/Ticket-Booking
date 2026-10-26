from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    environment: str = "local"
    database_url: str = "postgresql+psycopg://ticketing:ticketing@localhost:5432/ticketing"
    test_database_url: str = (
        "postgresql+psycopg://ticketing:ticketing@localhost:5432/ticketing_test"
    )
    jwt_secret: str = "change-me"
    jwt_expire_minutes: int = 60
    cors_origins: list[str] = ["http://localhost:3000"]

    razorpay_key_id: str = ""
    razorpay_key_secret: str = ""
    razorpay_webhook_secret: str = ""


@lru_cache
def get_settings() -> Settings:
    return Settings()
