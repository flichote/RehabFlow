"""声明式基类与公共 mixin。

- Base：AsyncAttrs + DeclarativeBase（SQLAlchemy 2.x async 标准写法）
- TimestampMixin：created_at TIMESTAMPTZ，默认 now()
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, func
from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(AsyncAttrs, DeclarativeBase):
    """所有 ORM 模型的基类。"""


class TimestampMixin:
    """公共 created_at 字段（TIMESTAMPTZ 语义）。"""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="创建时间",
    )
