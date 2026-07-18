"""
Application configuration via Pydantic Settings.

All configuration is loaded from environment variables (or .env file).
Provides typed, validated access to every config value in the system.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Any

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import load_dotenv
load_dotenv()

class Settings(BaseSettings):
    """Central configuration for the Options Intelligence Platform."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ---- Application ----
    app_env: str = "development"
    app_debug: bool = True
    app_log_level: str = "INFO"
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    frontend_url: str = "http://localhost:3000"
    cors_origins: list[str] = ["http://localhost:3000"]

    # ---- PostgreSQL ----
    postgres_host: str = "postgres"
    postgres_port: int = 5432
    postgres_user: str = "aibot"
    postgres_password: str = "change_this_password"
    postgres_db: str = "options_intel"
    database_url: str = "postgresql+asyncpg://aibot:change_this_password@postgres:5432/options_intel"

    # ---- Redis ----
    redis_host: str = "redis"
    redis_port: int = 6379
    redis_password: str = ""
    redis_url: str = "redis://redis:6379/0"
    celery_broker_url: str = "redis://redis:6379/1"
    celery_result_backend: str = "redis://redis:6379/2"

    # ---- FYERS API ----
    fyers_app_id: str = ""
    fyers_secret_key: str = ""
    fyers_redirect_uri: str = "http://localhost:8000/api/v1/auth/callback"
    fyers_access_token: str = ""
    fyers_refresh_token: str = ""

    # ---- Groq AI ----
    groq_api_key: str = ""
    groq_model: str = "llama-3.3-70b-versatile"

    # ---- Alerts: Telegram ----
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""

    # ---- Alerts: Discord ----
    discord_webhook_url: str = ""

    # ---- Alerts: Email ----
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    alert_email_to: str = ""

    # ---- Market Config ----
    watchlist_indices: str = "NSE:NIFTY50-INDEX,NSE:NIFTYBANK-INDEX,NSE:FINNIFTY-INDEX,BSE:SENSEX-INDEX"
    watchlist_stocks: str = "NSE:RELIANCE-EQ,NSE:TCS-EQ,NSE:HDFCBANK-EQ,NSE:INFY-EQ,NSE:ICICIBANK-EQ"
    option_chain_strike_count: int = 20
    data_buffer_ms: int = 100
    option_chain_poll_interval_s: int = 3

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: Any) -> list[str]:
        if isinstance(v, str):
            import json
            try:
                return json.loads(v)
            except (json.JSONDecodeError, TypeError):
                return [s.strip() for s in v.split(",")]
        return v

    @property
    def watchlist_indices_list(self) -> list[str]:
        return [s.strip() for s in self.watchlist_indices.split(",") if s.strip()]

    @property
    def watchlist_stocks_list(self) -> list[str]:
        return [s.strip() for s in self.watchlist_stocks.split(",") if s.strip()]

    @property
    def all_watchlist_symbols(self) -> list[str]:
        return self.watchlist_indices_list + self.watchlist_stocks_list

    @property
    def sync_database_url(self) -> str:
        return self.database_url.replace("+asyncpg", "")


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
