"""预警 API — 看板右栏预警列表 + 处理/忽略。

依据：docs/api.md §6 预警。
"""

from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db, require_role
from app.models.models import Alert, User
from app.schemas.schemas import AlertListResponse, AlertResponse
from app.services.alerts import ignore_alert, resolve_alert

router = APIRouter(prefix="/alerts", tags=["alerts"])


async def _get_alert(db: AsyncSession, alert_id: int) -> Alert:
    """Fetch alert or raise 404."""
    alert = (
        await db.execute(select(Alert).where(Alert.id == alert_id))
    ).scalar_one_or_none()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    return alert


@router.get("", response_model=AlertListResponse)
async def list_alerts(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_role("admin"))],
    status_filter: Optional[str] = Query(None, alias="status"),
):
    """预警列表（仅管理员可查看）。

    支持 ?status=open 过滤（看板右栏）。
    """
    base = select(Alert)
    if status_filter:
        base = base.where(Alert.status == status_filter)

    # Default: open first, then by created_at DESC
    base = base.order_by(Alert.status.asc(), Alert.created_at.desc())

    count_stmt = select(func.count()).select_from(base.subquery())
    total = (await db.execute(count_stmt)).scalar_one()

    alerts = (await db.execute(base)).scalars().all()

    return AlertListResponse(
        total=total,
        items=[AlertResponse.model_validate(a) for a in alerts],
    )


@router.post("/{alert_id}/resolve", status_code=status.HTTP_200_OK)
async def resolve_alert_endpoint(
    alert_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_role("admin"))],
):
    """处理预警（标记为 resolved，仅管理员）。"""
    alert = await _get_alert(db, alert_id)
    await resolve_alert(db, alert, current_user.id)
    await db.commit()
    await db.refresh(alert)
    return AlertResponse.model_validate(alert)


@router.post("/{alert_id}/ignore", status_code=status.HTTP_200_OK)
async def ignore_alert_endpoint(
    alert_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_role("admin"))],
):
    """忽略预警（标记为 ignored，仅管理员）。"""
    alert = await _get_alert(db, alert_id)
    await ignore_alert(db, alert, current_user.id)
    await db.commit()
    await db.refresh(alert)
    return AlertResponse.model_validate(alert)
