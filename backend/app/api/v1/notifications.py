"""通知 API — 站内信（分页，未读优先）。

依据：docs/api.md §5 提醒。
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db
from app.models.models import Notification, User
from app.schemas.schemas import (
    NotificationListResponse,
    NotificationResponse,
    UnreadCountResponse,
)

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("", response_model=NotificationListResponse)
async def list_notifications(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """我的消息列表（分页，未读优先）。

    数据权限：只返回当前用户的通知（服务端强制）。
    """
    base = select(Notification).where(Notification.user_id == current_user.id)

    # Count total
    count_stmt = select(func.count()).select_from(base.subquery())
    total = (await db.execute(count_stmt)).scalar_one()

    # Count unread
    unread_stmt = select(func.count()).where(
        Notification.user_id == current_user.id,
        Notification.is_read == False,  # noqa: E712
    )
    unread_count = (await db.execute(unread_stmt)).scalar_one()

    # Fetch items: unread first, then by created_at DESC
    items_stmt = (
        base.order_by(Notification.is_read.asc(), Notification.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    notifications = (await db.execute(items_stmt)).scalars().all()

    return NotificationListResponse(
        total=total,
        unread_count=unread_count,
        items=[NotificationResponse.model_validate(n) for n in notifications],
    )


@router.get("/unread-count", response_model=UnreadCountResponse)
async def unread_count(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """未读消息数（Topbar 红点）。

    数据权限：只统计当前用户。
    """
    stmt = select(func.count()).where(
        Notification.user_id == current_user.id,
        Notification.is_read == False,  # noqa: E712
    )
    count = (await db.execute(stmt)).scalar_one()
    return UnreadCountResponse(unread_count=count)


@router.post("/{notification_id}/read", status_code=status.HTTP_200_OK)
async def mark_read(
    notification_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """标记单条通知为已读。

    数据权限：只能标记自己的通知。
    """
    stmt = (
        update(Notification)
        .where(
            Notification.id == notification_id,
            Notification.user_id == current_user.id,
        )
        .values(is_read=True)
    )
    result = await db.execute(stmt)
    await db.commit()

    if result.rowcount == 0:
        raise HTTPException(
            status_code=404,
            detail="Notification not found or not yours",
        )
    return {"detail": "marked as read"}


@router.post("/read-all", status_code=status.HTTP_200_OK)
async def mark_all_read(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """全部标记为已读。

    数据权限：只标记当前用户的未读通知。
    """
    stmt = (
        update(Notification)
        .where(
            Notification.user_id == current_user.id,
            Notification.is_read == False,  # noqa: E712
        )
        .values(is_read=True)
    )
    result = await db.execute(stmt)
    await db.commit()
    return {"detail": f"{result.rowcount} notifications marked as read"}
