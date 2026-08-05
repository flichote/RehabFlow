"""通知模板与多通道发送服务。

依据：architecture.md §4.3 提醒与预警、docs/api.md §5 提醒、PRD §5 模板文案。
每个触发事件有对应模板，生成的 Notification 记录可追溯。
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import Notification


def _now() -> datetime:
    return datetime.now(timezone.utc)


# ── 通知模板常量 ──────────────────────────────────────────────────

# 模板结构：(title_template, content_template)
# 使用 .format(**ctx) 渲染，ctx 包含 patient_name, therapist_name, course_type, time 等。
TEMPLATES: dict[str, tuple[str, str]] = {
    "course_new": (
        "新课程安排",
        "您好 {patient_name}，已为您安排 {course_type} 治疗课程。\n"
        "时间：{start_time} - {end_time}\n"
        "康复师：{therapist_name}\n"
        "地点：{room_name}\n"
        "请按时前往，如有疑问请联系康复科。",
    ),
    "course_change": (
        "课程变更通知",
        "您好 {patient_name}，您的 {course_type} 课程时间已变更。\n"
        "新时间：{start_time} - {end_time}\n"
        "康复师：{therapist_name}\n"
        "地点：{room_name}",
    ),
    "course_reminder": (
        "上课提醒",
        "{patient_name}，您的 {course_type} 治疗课程将在 15 分钟后开始。\n"
        "时间：{start_time}\n"
        "康复师：{therapist_name}\n"
        "地点：{room_name}\n"
        "请前往治疗室准备。",
    ),
    "course_reminder_therapist": (
        "上课提醒",
        "您有一节 {course_type} 课程将在 15 分钟后开始。\n"
        "患者：{patient_name}\n"
        "时间：{start_time}\n"
        "地点：{room_name}",
    ),
    "course_overdue": (
        "课程超时未开始",
        "患者 {patient_name} 的 {course_type} 课程（计划 {start_time}）已超时 5 分钟未开始。\n"
        "康复师：{therapist_name}\n"
        "请关注处理。",
    ),
    "course_end_reminder": (
        "请确认课程状态",
        "您的 {course_type} 课程（患者：{patient_name}，开始于 {start_time}）已超过计划结束时间 30 分钟，状态仍为进行中。\n"
        "请确认是否忘记点击「结束上课」，或及时更新状态。",
    ),
    "assessment_todo": (
        "评估待办",
        "患者 {patient_name} 需进行 {assess_type} 评估，请及时处理。",
    ),
    "alert": (
        "系统预警",
        "{summary}",
    ),
}


async def create_notification(
    db: AsyncSession,
    *,
    user_id: int,
    type: str,
    ctx: dict,
    link: str | None = None,
    channel: str = "inbox",
) -> Notification:
    """渲染模板并写入 Notification 记录。

    Args:
        db: 异步数据库会话。
        user_id: 接收人用户 ID。
        type: 通知类型（course_new / course_change / course_reminder / ...）。
        ctx: 模板上下文（patient_name, therapist_name, course_type 等）。
        link: 可选跳转路由。
        channel: 通道（inbox / browser / sms）。

    Returns:
        创建的 Notification 实例。
    """
    title_tpl, content_tpl = TEMPLATES.get(
        type, ("系统通知", "{summary}")
    )
    title = title_tpl.format(**ctx)
    content = content_tpl.format(**ctx)

    notif = Notification(
        user_id=user_id,
        type=type,
        title=title,
        content=content,
        link=link,
        is_read=False,
        channel=channel,
    )
    db.add(notif)
    await db.flush()
    return notif


async def send_course_new_notifications(
    db: AsyncSession,
    *,
    patient_user_id: int | None,
    therapist_user_id: int,
    patient_name: str,
    therapist_name: str,
    course_type: str,
    start_time: str,
    end_time: str,
    room_name: str,
    course_id: int,
) -> None:
    """排课成功 → 通知患者 + 康复师。"""
    ctx = {
        "patient_name": patient_name,
        "therapist_name": therapist_name,
        "course_type": course_type,
        "start_time": start_time,
        "end_time": end_time,
        "room_name": room_name,
    }
    if patient_user_id:
        await create_notification(
            db,
            user_id=patient_user_id,
            type="course_new",
            ctx=ctx,
            link=f"/courses/{course_id}",
        )
    await create_notification(
        db,
        user_id=therapist_user_id,
        type="course_new",
        ctx=ctx,
        link=f"/courses/{course_id}",
    )


async def send_course_reminder_notifications(
    db: AsyncSession,
    *,
    patient_user_id: int | None,
    therapist_user_id: int,
    patient_name: str,
    therapist_name: str,
    course_type: str,
    start_time: str,
    room_name: str,
    course_id: int,
) -> None:
    """课前 15 分钟 → 通知患者 + 康复师。"""
    # 患者提醒
    ctx_patient = {
        "patient_name": patient_name,
        "therapist_name": therapist_name,
        "course_type": course_type,
        "start_time": start_time,
        "room_name": room_name,
    }
    if patient_user_id:
        await create_notification(
            db,
            user_id=patient_user_id,
            type="course_reminder",
            ctx=ctx_patient,
            link=f"/courses/{course_id}",
        )

    # 康复师提醒
    ctx_therapist = {
        "patient_name": patient_name,
        "course_type": course_type,
        "start_time": start_time,
        "room_name": room_name,
    }
    await create_notification(
        db,
        user_id=therapist_user_id,
        type="course_reminder_therapist",
        ctx=ctx_therapist,
        link=f"/courses/{course_id}",
    )


async def send_course_overdue_notification(
    db: AsyncSession,
    *,
    therapist_user_id: int,
    patient_name: str,
    therapist_name: str,
    course_type: str,
    start_time: str,
    course_id: int,
) -> None:
    """超时 5 分钟 → 通知康复师。"""
    ctx = {
        "patient_name": patient_name,
        "therapist_name": therapist_name,
        "course_type": course_type,
        "start_time": start_time,
    }
    await create_notification(
        db,
        user_id=therapist_user_id,
        type="course_overdue",
        ctx=ctx,
        link=f"/courses/{course_id}",
    )


async def send_course_end_reminder(
    db: AsyncSession,
    *,
    therapist_user_id: int,
    patient_name: str,
    course_type: str,
    start_time: str,
    course_id: int,
) -> None:
    """课程超时结束 30 分钟 → 通知康复师确认。"""
    ctx = {
        "patient_name": patient_name,
        "course_type": course_type,
        "start_time": start_time,
    }
    await create_notification(
        db,
        user_id=therapist_user_id,
        type="course_end_reminder",
        ctx=ctx,
        link=f"/courses/{course_id}",
    )
