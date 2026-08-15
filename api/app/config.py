"""Все настройки читаются из окружения (.env) — pydantic-settings. См. .env.example."""
from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    build_env: str = "dev"

    # Относительный sqlite-путь резолвится от текущей рабочей директории процесса —
    # предполагается запуск из api/ (см. README: `cd api && uvicorn app.main:app`).
    database_url: str = "sqlite:///./dev.db"
    pricing_path: str = "site/content/pricing.json"

    jwt_secret: str = "change-me-to-a-random-64-char-hex-string"
    admin_username: str = "admin"
    admin_password_hash: str = ""

    ip_hash_salt: str = "change-me-to-a-random-string"
    cors_origin: str = "http://localhost:8080"

    telegram_bot_token: str = ""
    telegram_chat_id: str = ""

    rate_limit_leads_per_hour: int = 5
    rate_limit_quote_per_minute: int = 30


settings = Settings()
