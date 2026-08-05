"""预警生成与处理服务。

依据：architecture.md §4.3、docs/api.md §6 预警。
预警类型：course_overdue / patient_absent / conflict_unresolved。
预警必须可标记处理（resolve/ignore），处理后从看板消失。
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import Alert, Course, Patient


def _now() -> datetime:
    return datetime.now(timezone.utc)


async def create_alert(
    db: AsyncSession,
    *,
    alert_type: str,
    summary: str,
    ref_course_id: int | None = None,
    ref_patient_id: int | None = None,
) -> Alert:
    """创建一条预警记录（幂等：同一课程+同一类型只存在一条 open 状态）。

    如果已存在 open 状态的同类型预警，则不重复创建，返回已有记录。
    """
    # 幂等去重：同课程+同类型+open
    if ref_course_id and alert_type:
        existing = (
            await db.execute(
                select(Alert).where(
                    Alert.ref_course_id == ref_course_id,
                    Alert.alert_type == alert_type,
                    Alert.status == "open",
                )
            )
        ).scalar_one_or_none()
        if existing:
            return existing

    alert = Alert(
        alert_type=alert_type,
        ref_course_id=ref_course_id,
        ref_patient_id=ref_patient_id,
        summary=summary,
        status="open",
    )
    db.add(alert)
    await db.flush()
    return alert


async def resolve_alert(
    db: AsyncSession,
    alert: Alert,
    resolved_by: int,
) -> Alert:
    """处理预警（标记为 resolved）。"""
    alert.status = "resolved"
    alert.resolved_by = resolved_by
    alert.resolved_at = _now()
    await db.flush()
    return alert


async def ignore_alert(
    db: AsyncSession,
    alert: Alert,
    resolved_by: int,
) -> Alert:
    """忽略预警（标记为 ignored）。"""
    alert.status = "ignored"
    alert.resolved_by = resolved_by
    alert.resolved_at = _now()
    await db.flush()
    return alert


async def create_course_overdue_alert(
    db: AsyncSession,
    course: Course,
    patient: Patient,
    therapist_name: str,
) -> Alert | None:
    """课程超时未开始 → 生成 course_overdue 预警 + 通知康复师。

    幂等：同一课程只生成一次 open 预警。
    """
    summary = (
        f"患者 {patient.name} 的 {course.course_type} 课程"
        f"（计划 {course.start_at.strftime('%H:%M')}，康复师 {therapist_name}）"
        f"已超时未开始"
    )
    alert = await create_alert(
        db,
        alert_type="course_overdue",
        summary=summary,
        ref_course_id=course.id,
        ref_patient_id=patient.id,
    )
    return alert
