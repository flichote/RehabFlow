"""异步会话工厂（SQLite/PG 切换口）。

- create_async_engine：根据 settings.DATABASE_URL 自动选择 aiosqlite / asyncpg 驱动
- async_sessionmaker(engine, expire_on_commit=False)：提交后对象不失效（SQLAlchemy 2.x async 标准）
"""
from __future__ import annotations

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import settings

engine: AsyncEngine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    pool_pre_ping=True,
)

SessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI 依赖注入：每个请求一个会话。"""
    async with SessionLocal() as session:
        yield session
