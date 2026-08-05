"""APScheduler 定时任务：课前提醒 / 超时检测 / 巡检。

依据：architecture.md §4.3、ADR-5（APScheduler 进程内单实例）。

任务：
- 课前 15min：扫描 scheduled 状态且 start_at - 15min <= now 的课程
  → 发提醒通知、课程→reminded、患者→en_route（走 tracking 状态机）
- 超时 5min：start_at 已过 5min 仍 scheduled/reminded
  → 课程→abnormal + 生成 alert(course_overdue)
- 30min 巡检：actual_end_at 为 null 且课程结束 30min 后仍 ongoing
  → 发提醒通知给康复师

幂等：同一课程同一事件只触发一次（通过 course_status_log / alerts 去重）。
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.models import (
    Alert,
    Course,
    CourseStatusLog,
    Patient,
    Therapist,
)
from app.services.alerts import create_course_overdue_alert
from app.services.notifications import (
    send_course_end_reminder,
    send_course_reminder_notifications,
)
from app.services.tracking import remind_course

scheduler = AsyncIOScheduler()


def _now() -> datetime:
    return datetime.now(timezone.utc)


async def _pre_class_reminder():
    """课前 15 分钟扫描：scheduled → reminded。"""
    now = _now()
    cutoff = now + timedelta(minutes=15)

    async with SessionLocal() as db:
        # 扫描 scheduled 状态且 start_at 在 [now, now+15min] 区间的课程
        stmt = (
            select(Course)
            .where(
                Course.status == "scheduled",
                Course.start_at >= now,
                Course.start_at <= cutoff,
            )
        )
        courses = (await db.execute(stmt)).scalars().all()

        for course in courses:
            # 幂等：检查是否已提醒（course_status_log 有 reminded 记录）
            from sqlalchemy import exists as _exists

            already = await db.execute(
                select(_exists().where(
                    CourseStatusLog.course_id == course.id,
                    CourseStatusLog.to_status == "reminded",
                ))
            )
            if already.scalar_one():
                continue

            # 获取关联信息
            patient = (
                await db.execute(select(Patient).where(Patient.id == course.patient_id))
            ).scalar_one_or_none()
            therapist = (
                await db.execute(
                    select(Therapist).where(Therapist.id == course.therapist_id)
                )
            ).scalar_one_or_none()

            if not patient or not therapist:
                continue

            # 发通知
            await send_course_reminder_notifications(
                db,
                patient_user_id=patient.user_id,
                therapist_user_id=therapist.user_id,
                patient_name=patient.name,
                therapist_name=therapist.name,
                course_type=course.course_type,
                start_time=course.start_at.isoformat(),
                room_name=course.room.name if course.room else "Unknown",
                course_id=course.id,
            )

            # 状态机转换
            await remind_course(db, course, actor_id=None)

        if courses:
            await db.commit()


async def _overdue_detection():
    """超时 5 分钟检测：scheduled/reminded → abnormal + alert。"""
    now = _now()
    threshold = now - timedelta(minutes=5)

    async with SessionLocal() as db:
        stmt = (
            select(Course)
            .where(
                Course.status.in_(["scheduled", "reminded"]),
                Course.start_at <= threshold,
            )
        )
        courses = (await db.execute(stmt)).scalars().all()

        for course in courses:
            # 幂等：检查是否已有 open 状态的 course_overdue alert
            from sqlalchemy import exists as _exists

            already = await db.execute(
                select(_exists().where(
                    Alert.ref_course_id == course.id,
                    Alert.alert_type == "course_overdue",
                    Alert.status == "open",
                ))
            )
            if already.scalar_one():
                continue

            patient = (
                await db.execute(select(Patient).where(Patient.id == course.patient_id))
            ).scalar_one_or_none()
            therapist = (
                await db.execute(
                    select(Therapist).where(Therapist.id == course.therapist_id)
                )
            ).scalar_one_or_none()

            if not patient or not therapist:
                continue

            # 生成预警
            await create_course_overdue_alert(
                db, course, patient, therapist.name
            )

            # 课程状态 → abnormal
            db.add(
                CourseStatusLog(
                    course_id=course.id,
                    from_status=course.status,
                    to_status="abnormal",
                    actor_id=None,
                    note="超时 5 分钟未开始，系统自动标记异常",
                    occurred_at=now,
                )
            )
            course.status = "abnormal"

        if courses:
            await db.commit()


async def _patrol_ongoing():
    """30 分钟巡检：ongoing 状态超过结束时间 30min → 提醒康复师确认。"""
    now = _now()
    threshold = now - timedelta(minutes=30)

    async with SessionLocal() as db:
        stmt = (
            select(Course)
            .where(
                Course.status == "ongoing",
                Course.end_at <= threshold,
                Course.actual_end_at == None,  # noqa: E711
            )
        )
        courses = (await db.execute(stmt)).scalars().all()

        for course in courses:
            # 幂等：检查是否已发送过 "course_end_reminder" 通知（by type on this course）
            from sqlalchemy import exists as _exists
            from app.models.models import Notification

            # Use a simpler approach: check if any notification for the therapist
            # about this course with type course_end_reminder exists recently
            therapist = (
                await db.execute(
                    select(Therapist).where(Therapist.id == course.therapist_id)
                )
            ).scalar_one_or_none()
            patient = (
                await db.execute(select(Patient).where(Patient.id == course.patient_id))
            ).scalar_one_or_none()

            if not therapist or not patient:
                continue

            # Idempotency: check for a notification with "course_end_reminder" for
            # this course within the last 35 minutes
            window = now - timedelta(minutes=35)
            already = await db.execute(
                select(_exists().where(
                    Notification.user_id == therapist.user_id,
                    Notification.type == "course_end_reminder",
                    Notification.link == f"/courses/{course.id}",
                    Notification.created_at >= window,
                ))
            )
            if already.scalar_one():
                continue

            await send_course_end_reminder(
                db,
                therapist_user_id=therapist.user_id,
                patient_name=patient.name,
                course_type=course.course_type,
                start_time=course.start_at.isoformat(),
                course_id=course.id,
            )

        if courses:
            await db.commit()


def start_scheduler():
    """启动定时任务（在应用 lifespan 中调用）。"""
    if scheduler.running:
        return

    # 课前 15 分钟：每分钟扫描
    scheduler.add_job(
        _pre_class_reminder,
        "interval",
        minutes=1,
        id="pre_class_reminder",
        replace_existing=True,
        max_instances=1,
    )

    # 超时 5 分钟：每分钟扫描
    scheduler.add_job(
        _overdue_detection,
        "interval",
        minutes=1,
        id="overdue_detection",
        replace_existing=True,
        max_instances=1,
    )

    # 30 分钟巡检：每 5 分钟扫描
    scheduler.add_job(
        _patrol_ongoing,
        "interval",
        minutes=5,
        id="patrol_ongoing",
        replace_existing=True,
        max_instances=1,
    )

    scheduler.start()


def stop_scheduler():
    """停止定时任务（在应用 shutdown 中调用）。"""
    if scheduler.running:
        scheduler.shutdown(wait=False)
