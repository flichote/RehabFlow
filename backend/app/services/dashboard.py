"""Dashboard aggregation service — admin-only dashboard queries.

Uses SQL group_by/count for all aggregations (architecture.md §3.1).
No Python-level loops for grouping — all heavy lifting is in the database.
"""

from datetime import date, datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import (
    Course,
    Patient,
    PatientStatusLog,
    Therapist,
    TherapistShift,
)


def _today_utc_range() -> tuple[datetime, datetime]:
    """Return (start, end) of today in UTC."""
    today = datetime.now(timezone.utc).date()
    day_start = datetime(today.year, today.month, today.day, tzinfo=timezone.utc)
    day_end = datetime(today.year, today.month, today.day, 23, 59, 59, tzinfo=timezone.utc)
    return day_start, day_end


async def get_kpis(db: AsyncSession) -> dict:
    """Return 4 KPIs: inpatient_count, today_course_count, treating_count, attendance_rate."""
    day_start, day_end = _today_utc_range()
    today_date = date.today()

    # ① Inpatient count: status != 'discharged'
    inpatient_count = await db.scalar(
        select(func.count()).select_from(Patient).where(Patient.status != "discharged")
    )

    # ② Today's course count: start_at within today
    today_course_count = await db.scalar(
        select(func.count())
        .select_from(Course)
        .where(Course.start_at >= day_start, Course.start_at <= day_end)
    )

    # ③ Currently treating: status = 'treating'
    treating_count = await db.scalar(
        select(func.count())
        .select_from(Patient)
        .where(Patient.status == "treating")
    )

    # ④ Therapist attendance rate: on_duty / (on_duty + scheduled) for today
    total_shifts = await db.scalar(
        select(func.count())
        .select_from(TherapistShift)
        .where(
            TherapistShift.work_date == today_date,
            TherapistShift.status.in_(["on_duty", "scheduled"]),
        )
    )
    on_duty = await db.scalar(
        select(func.count())
        .select_from(TherapistShift)
        .where(
            TherapistShift.work_date == today_date,
            TherapistShift.status == "on_duty",
        )
    )
    rate = (on_duty / total_shifts) if total_shifts and total_shifts > 0 else 0.0

    return {
        "inpatient_count": inpatient_count or 0,
        "today_course_count": today_course_count or 0,
        "treating_count": treating_count or 0,
        "therapist_attendance_rate": round(rate, 4),
    }


async def get_patient_distribution(db: AsyncSession) -> list[dict]:
    """Group patients by location from patient_status_log (latest entry per patient).

    Uses a subquery to find the latest status log for each non-discharged patient,
    then groups by location.
    """
    # Subquery: latest status log per patient
    latest_sub = (
        select(
            PatientStatusLog.patient_id,
            func.max(PatientStatusLog.occurred_at).label("max_occurred"),
        )
        .group_by(PatientStatusLog.patient_id)
        .subquery()
    )

    # Join to get the latest location, filter non-discharged
    stmt = (
        select(
            func.coalesce(PatientStatusLog.location, "未知").label("location"),
            func.count().label("cnt"),
        )
        .select_from(PatientStatusLog)
        .join(
            latest_sub,
            (PatientStatusLog.patient_id == latest_sub.c.patient_id)
            & (PatientStatusLog.occurred_at == latest_sub.c.max_occurred),
        )
        .join(Patient, Patient.id == PatientStatusLog.patient_id)
        .where(Patient.status != "discharged")
        .group_by(func.coalesce(PatientStatusLog.location, "未知"))
        .order_by(func.count().desc())
    )

    rows = (await db.execute(stmt)).all()
    return [{"location": r.location, "count": r.cnt} for r in rows]


async def get_therapist_workload(
    db: AsyncSession,
    target_date: date | None = None,
) -> list[dict]:
    """Return per-therapist course count for a given date (default today).

    Groups courses by therapist_id where start_at falls within the target day.
    """
    if target_date is None:
        target_date = date.today()

    day_start = datetime(
        target_date.year, target_date.month, target_date.day, tzinfo=timezone.utc
    )
    day_end = day_start.replace(hour=23, minute=59, second=59)

    stmt = (
        select(
            Course.therapist_id,
            func.count(Course.id).label("course_count"),
        )
        .where(Course.start_at >= day_start, Course.start_at <= day_end)
        .group_by(Course.therapist_id)
        .order_by(func.count(Course.id).desc())
    )

    rows = (await db.execute(stmt)).all()

    # Fetch therapist names
    therapist_ids = [r.therapist_id for r in rows]
    therapist_map: dict[int, Therapist] = {}
    if therapist_ids:
        t_result = await db.execute(
            select(Therapist).where(Therapist.id.in_(therapist_ids))
        )
        for t in t_result.scalars().all():
            therapist_map[t.id] = t

    result: list[dict] = []
    for r in rows:
        t = therapist_map.get(r.therapist_id)
        result.append({
            "therapist_id": r.therapist_id,
            "therapist_name": t.name if t else "Unknown",
            "group_name": t.group_name if t else "N/A",
            "course_count": r.course_count,
        })

    return result


async def get_course_trend(
    db: AsyncSession,
    days: int = 7,
) -> list[dict]:
    """Return daily course count for the last N days.

    Groups by date(start_at). Uses SQL group_by — no Python loops.
    """
    end_date = datetime.now(timezone.utc).date()
    start_date = end_date - timedelta(days=days - 1)

    day_start = datetime(
        start_date.year, start_date.month, start_date.day, tzinfo=timezone.utc
    )
    day_end = datetime(
        end_date.year, end_date.month, end_date.day, 23, 59, 59, tzinfo=timezone.utc
    )

    # Group by date (SQLite: date() function works on datetime strings)
    stmt = (
        select(
            func.date(Course.start_at).label("dt"),
            func.count(Course.id).label("cnt"),
        )
        .where(Course.start_at >= day_start, Course.start_at <= day_end)
        .group_by(func.date(Course.start_at))
        .order_by(func.date(Course.start_at).asc())
    )

    rows = (await db.execute(stmt)).all()
    actual = {r.dt: r.cnt for r in rows}

    # Fill missing days with 0
    result: list[dict] = []
    for i in range(days):
        d = start_date + timedelta(days=i)
        iso = d.isoformat()
        result.append({"date": iso, "count": actual.get(iso, 0)})

    return result
