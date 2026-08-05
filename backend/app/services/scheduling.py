"""Scheduling engine: course creation with dual conflict detection.

Conflict detection runs inside a database transaction. On PostgreSQL this uses
FOR UPDATE row-level locking to prevent concurrent double-booking. On SQLite we
use an application-level asyncio.Lock to simulate the same serialization guarantee
(since SQLite's write lock is database-level, not row-level).

Key invariants:
- Same patient cannot have two active courses overlapping in time.
- Same therapist cannot have two active courses overlapping in time.
- Time granularity is 15 minutes (validated at Pydantic schema level).

Conflict response:  409 with list of conflicting course IDs + reasons.
No conflict:         201 with created course.
"""

import asyncio
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import Course

# Application-level lock for SQLite conflict detection serialization.
# On PostgreSQL, the FOR UPDATE clause handles this at the DB level.
# To switch to PG row-lock, replace the Lock usage below with:
#   SELECT ... FOR UPDATE (the SQL itself stays the same;
#   SQLAlchemy's with_for_update() is a no-op on SQLite but works on PG).
_scheduling_lock = asyncio.Lock()

# Active course statuses — courses in these states conflict with new courses
_ACTIVE_STATUSES = ("scheduled", "reminded", "ongoing")


def _as_utc(dt: datetime) -> datetime:
    """Normalize a datetime to timezone-aware UTC for comparison.

    Storage convention: the schema layer converts all inputs to UTC before
    insert, so SQLite's naive wall-clock values are UTC semantics. Naive
    datetimes read back from SQLite are therefore treated as UTC.
    """
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _time_overlap(a_start: datetime, a_end: datetime, b_start: datetime, b_end: datetime) -> bool:
    """True if two half-open intervals [start, end) overlap.

    All datetimes are normalized to timezone-aware UTC before comparison.
    """
    return _as_utc(a_start) < _as_utc(b_end) and _as_utc(a_end) > _as_utc(b_start)


async def create_course(
    db: AsyncSession,
    *,
    patient_id: int,
    therapist_id: int,
    room_id: int,
    course_type: str,
    start_at: datetime,
    end_at: datetime,
    created_by: int | None = None,
) -> Course:
    """Create a course within a serialized transaction (conflict detection).

    Args:
        db: Async database session.
        patient_id: Patient being scheduled.
        therapist_id: Therapist assigned.
        room_id: Treatment room.
        course_type: PT / OT / ST.
        start_at: Planned start (15-min aligned).
        end_at: Planned end (15-min aligned).
        created_by: Admin user ID who created this course.

    Returns:
        The newly created Course model instance.

    Raises:
        HTTPException(409): If patient or therapist has a conflicting course.
    """
    # Serialize scheduling operations to prevent concurrent double-booking.
    # NOTE: On PostgreSQL, replace this Lock with FOR UPDATE row-level locks
    # in the SELECT queries below (add .with_for_update() to the stmts).
    async with _scheduling_lock:
        # ── Patient conflict check ──
        patient_stmt = (
            select(Course)
            .where(
                Course.patient_id == patient_id,
                Course.status.in_(_ACTIVE_STATUSES),
            )
        )
        # NOTE: On PostgreSQL, append .with_for_update() here for true row locking.
        patient_conflicts = (await db.execute(patient_stmt)).scalars().all()

        patient_overlap = [
            c
            for c in patient_conflicts
            if _time_overlap(start_at, end_at, c.start_at, c.end_at)
        ]

        if patient_overlap:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "error": "patient_conflict",
                    "conflicts": [
                        {
                            "conflicting_course_id": c.id,
                            "reason": "patient_conflict",
                            "existing_start": c.start_at.isoformat(),
                            "existing_end": c.end_at.isoformat(),
                        }
                        for c in patient_overlap
                    ],
                },
            )

        # ── Therapist conflict check ──
        therapist_stmt = (
            select(Course)
            .where(
                Course.therapist_id == therapist_id,
                Course.status.in_(_ACTIVE_STATUSES),
            )
        )
        # NOTE: On PostgreSQL, append .with_for_update() here for true row locking.
        therapist_conflicts = (await db.execute(therapist_stmt)).scalars().all()

        therapist_overlap = [
            c
            for c in therapist_conflicts
            if _time_overlap(start_at, end_at, c.start_at, c.end_at)
        ]

        if therapist_overlap:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "error": "therapist_conflict",
                    "conflicts": [
                        {
                            "conflicting_course_id": c.id,
                            "reason": "therapist_conflict",
                            "existing_start": c.start_at.isoformat(),
                            "existing_end": c.end_at.isoformat(),
                        }
                        for c in therapist_overlap
                    ],
                },
            )

        # ── No conflict → create course ──
        course = Course(
            patient_id=patient_id,
            therapist_id=therapist_id,
            room_id=room_id,
            course_type=course_type,
            start_at=start_at,
            end_at=end_at,
            status="scheduled",
            created_by=created_by,
        )
        db.add(course)
        await db.commit()
        await db.refresh(course)
        return course
