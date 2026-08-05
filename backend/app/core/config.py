"""Application config (pydantic-settings v2).

DATABASE_URL is the single switch between SQLite (dev) and PG16 (prod).
Hard constraint: zero HIS-related environment variables (architecture.md §9.4).
"""
from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """RehabFlow global configuration."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Database
    # 默认 SQLite 用绝对路径（backend/rehabflow.db）：相对路径会随 cwd 变化，
    # 导致 init_db（backend/ 下跑）与服务启动（其他 cwd）连到不同文件。
    DATABASE_URL: str = ""

    @property
    def resolved_database_url(self) -> str:
        """返回实际使用的 DATABASE_URL（未配置时用 backend/rehabflow.db 绝对路径）。"""
        if self.DATABASE_URL:
            return self.DATABASE_URL
        backend_dir = Path(__file__).resolve().parent.parent.parent  # backend/
        db_path = backend_dir / "rehabflow.db"
        return f"sqlite+aiosqlite:///{db_path.as_posix()}"

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
