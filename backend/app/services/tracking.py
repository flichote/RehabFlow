"""Soft check-in state machine — the single entry point for all status transitions.

Per architecture.md §4.2 and api.md §10:
- start_course:  course → ongoing (record actual_start_at),
                 patient → treating, location = treatment room.
- finish_course: course → completed (record actual_end_at),
                 patient → ward, location = ward.
- pause_course:  course stays ongoing, patient → paused.
- resume_course: course stays ongoing, patient → treating.
- mark_absent:   course → absent, patient → absent.

Every status change writes both course_status_log AND patient_status_log.
No other code may change course.status or patient.status directly.
"""

from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import (
    Course,
    CourseStatusLog,
    Patient,
    PatientStatusLog,
    Room,
)

def _now() -> datetime:
    """当前时间（UTC aware）。

    存储约定：schema 层把输入统一转 UTC，SQLite 存的 naive 墙钟即 UTC 语义；
    这里写入的 UTC aware 时间与其一致（PG 的 TIMESTAMPTZ 同理）。
    """
    return datetime.now(timezone.utc)


def _as_utc(dt: datetime) -> datetime:
    """归一化为 timezone-aware UTC（naive 按 UTC 补，见存储约定）。"""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


async def _log_course_status(
    db: AsyncSession,
    course: Course,
    to_status: str,
    actor_id: int | None = None,
    note: str | None = None,
) -> None:
    db.add(
        CourseStatusLog(
            course_id=course.id,
            from_status=course.status,
            to_status=to_status,
            actor_id=actor_id,
            note=note,
            occurred_at=_now(),
        )
    )


async def _log_patient_status(
    db: AsyncSession,
    patient: Patient,
    to_status: str,
    location: str | None = None,
    actor_id: int | None = None,
    source: str = "course_action",
) -> None:
    db.add(
        PatientStatusLog(
            patient_id=patient.id,
            from_status=patient.status,
            to_status=to_status,
            location=location,
            actor_id=actor_id,
            source=source,
            occurred_at=_now(),
        )
    )


async def start_course(
    db: AsyncSession,
    course: Course,
    actor_id: int,
) -> None:
    """Begin a course session.

    Side effects:
    - course.status = "ongoing", course.actual_start_at = now
    - patient.status = "treating", patient location = room name
    - Logs written to course_status_log and patient_status_log.
    """
    if course.status not in ("scheduled", "reminded"):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot start course in '{course.status}' status. Expected 'scheduled' or 'reminded'.",
        )

    patient = (
        await db.execute(select(Patient).where(Patient.id == course.patient_id))
    ).scalar_one()

    # Get room name for location tracking
    room = (
        await db.execute(select(Room).where(Room.id == course.room_id))
    ).scalar_one()
    location = room.name

    # Transition
    await _log_course_status(db, course, "ongoing", actor_id=actor_id)
    course.status = "ongoing"
    course.actual_start_at = _now()

    await _log_patient_status(db, patient, "treating", location=location, actor_id=actor_id)
    patient.status = "treating"

    await db.commit()


async def finish_course(
    db: AsyncSession,
    course: Course,
    actor_id: int,
) -> None:
    """End a course session.

    Side effects:
    - course.status = "completed", course.actual_end_at = now
    - course.minutes_consumed = calculated
    - patient.status = "ward", patient location = ward_location
    - Logs written to course_status_log and patient_status_log.
    """
    if course.status != "ongoing":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot finish course in '{course.status}' status. Expected 'ongoing'.",
        )

    patient = (
        await db.execute(select(Patient).where(Patient.id == course.patient_id))
    ).scalar_one()

    now = _now()

    # Calculate minutes consumed（时区统一：_as_utc 归一化 naive 墙钟与 aware）
    if course.actual_start_at:
        delta = _as_utc(now) - _as_utc(course.actual_start_at)
        course.minutes_consumed = max(1, int(delta.total_seconds() / 60))

    # Transition
    await _log_course_status(db, course, "completed", actor_id=actor_id)
    course.status = "completed"
    course.actual_end_at = now

    await _log_patient_status(
        db,
        patient,
        "ward",
        location=patient.ward_location or "ward",
        actor_id=actor_id,
    )
    patient.status = "ward"

    await db.commit()


async def remind_course(
    db: AsyncSession,
    course: Course,
    actor_id: int | None = None,
) -> None:
    """Send pre-class reminder (15 min before start).

    Side effects:
    - course.status = "reminded" (from "scheduled")
    - patient.status = "en_route"
    - Logs written to course_status_log and patient_status_log.

    Idempotent: does nothing if course is not in "scheduled" status.
    Only transitions courses that haven't been reminded yet (checks
    course_status_log for an existing "reminded" entry).
    """
    if course.status not in ("scheduled",):
        return

    # Idempotency: check if already reminded (via course_status_log)
    from sqlalchemy import exists as _exists

    already = await db.execute(
        select(_exists().where(
            CourseStatusLog.course_id == course.id,
            CourseStatusLog.to_status == "reminded",
        ))
    )
    if already.scalar_one():
        return

    patient = (
        await db.execute(select(Patient).where(Patient.id == course.patient_id))
    ).scalar_one()

    # Transition course
    await _log_course_status(db, course, "reminded", actor_id=actor_id)
    course.status = "reminded"

    # Transition patient → en_route
    await _log_patient_status(
        db, patient, "en_route", location=None, actor_id=actor_id, source="system"
    )
    patient.status = "en_route"

    await db.commit()
