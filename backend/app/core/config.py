"""Application config (pydantic-settings v2).

DATABASE_URL is the single switch between SQLite (dev) and PG16 (prod).
Hard constraint: zero HIS-related environment variables (architecture.md §9.4).
"""
from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """RehabFlow global configuration."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./rehabflow.db"

    # JWT
    SECRET_KEY: str = "change-me-in-production-use-openssl-rand-hex-32"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # App
    APP_NAME: str = "RehabFlow"
    # 应用时区（医院场景默认中国 +08:00）。SQLite 存 DateTime(timezone=True)
    # 会丢失偏移（naive 墙钟），冲突检测比较前需按此补时区再转 UTC。
    APP_TZ_OFFSET_HOURS: int = 8


settings = Settings()
