"""Course endpoints: create, list, detail, start, finish, therapist schedule."""

from datetime import date, datetime, timezone
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db, require_role
from app.models.models import Course, Patient, Room, Therapist, User
from app.schemas.schemas import (
    CourseCreate,
    CourseDetailResponse,
    CourseListResponse,
    CourseResponse,
    FreeSlot,
    ScheduleCourseItem,
    ScheduleOverview,
    ScheduleResponse,
)
from app.services.scheduling import _as_utc, create_course
from app.services.tracking import finish_course, start_course

router = APIRouter(prefix="/courses", tags=["courses"])


@router.post(
    "",
    response_model=CourseResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        409: {"description": "Scheduling conflict", "model": dict},
        422: {"description": "Validation error (15min granularity, etc.)"},
    },
)
async def create_course_endpoint(
    body: CourseCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_role("admin"))],
):
    """Create a new course with dual conflict detection (admin only).

    Returns 201 on success, 409 with conflict details on overlap.
    """
    course = await create_course(
        db,
        patient_id=body.patient_id,
        therapist_id=body.therapist_id,
        room_id=body.room_id,
        course_type=body.course_type,
        start_at=body.start_at,
        end_at=body.end_at,
        created_by=current_user.id,
    )
    return course


def _check_therapist_access(course: Course, therapist: Therapist | None) -> None:
    """Verify a therapist can only act on their own courses."""
    if not therapist or therapist.id != course.therapist_id:
        raise HTTPException(
            status_code=403,
            detail="You can only manage your own courses",
        )


async def _get_course(db: AsyncSession, course_id: int) -> Course:
    """Fetch course or raise 404."""
    course = (
        await db.execute(select(Course).where(Course.id == course_id))
    ).scalar_one_or_none()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    return course


async def _get_therapist(db: AsyncSession, user: User) -> Therapist | None:
    """Get therapist profile for the given user, or None."""
    result = await db.execute(
        select(Therapist).where(Therapist.user_id == user.id)
    )
    return result.scalar_one_or_none()


# ── Query endpoints ───────────────────────────────────────────────────


@router.get("", response_model=CourseListResponse)
async def list_courses(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_role("therapist", "admin"))],
    from_date: Optional[str] = Query(None, alias="from"),
    to: Optional[str] = Query(None),
    therapist_id: Optional[int] = Query(None),
    group: Optional[str] = Query(None, pattern=r"^(PT|OT|ST)$"),
    room_id: Optional[int] = Query(None),
):
    """List courses with optional filters (calendar query).

    Admin: all courses.
    Therapist: only own courses (data permission - architecture.md §4.4).
    """
    base = select(Course)

    # Data permission: therapist only sees own courses
    if current_user.role == "therapist":
        tp = await _get_therapist(db, current_user)
        if not tp:
            raise HTTPException(status_code=403, detail="Therapist profile not found")
        base = base.where(Course.therapist_id == tp.id)

    # Optional filters
    if from_date:
        # URL-decoded '+' (timezone offset) may come as space; normalize
        cleaned = from_date.replace(" ", "+")
        base = base.where(Course.end_at >= _as_utc(datetime.fromisoformat(cleaned)))
    if to:
        cleaned_to = to.replace(" ", "+")
        base = base.where(Course.start_at <= _as_utc(datetime.fromisoformat(cleaned_to)))
    if therapist_id:
        base = base.where(Course.therapist_id == therapist_id)
    if group:
        base = base.join(Course.therapist).where(Therapist.group_name == group)
    if room_id:
        base = base.where(Course.room_id == room_id)

    # Count total
    count_stmt = select(func.count()).select_from(base.subquery())
    total = (await db.execute(count_stmt)).scalar_one()

    # Fetch items ordered by start_at
    items_stmt = base.order_by(Course.start_at.asc())
    courses = (await db.execute(items_stmt)).scalars().all()

    return CourseListResponse(
        total=total,
        items=[CourseResponse.model_validate(c) for c in courses],
    )


@router.get("/{course_id}", response_model=CourseDetailResponse)
async def get_course(
    course_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_role("therapist", "admin"))],
):
    """Get course detail with associated names.

    Admin: any course.
    Therapist: only own courses.
    """
    course = await _get_course(db, course_id)

    # Data permission: therapist only sees own courses
    if current_user.role == "therapist":
        tp = await _get_therapist(db, current_user)
        _check_therapist_access(course, tp)

    # Eager load related names (selectinload is set on model, but we re-query for safety)
    return CourseDetailResponse(
        id=course.id,
        patient_id=course.patient_id,
        therapist_id=course.therapist_id,
        room_id=course.room_id,
        course_type=course.course_type,
        start_at=course.start_at,
        end_at=course.end_at,
        status=course.status,
        actual_start_at=course.actual_start_at,
        actual_end_at=course.actual_end_at,
        minutes_consumed=course.minutes_consumed,
        session_note=course.session_note,
        created_by=course.created_by,
        created_at=course.created_at,
        patient_name=course.patient.name if course.patient else "",
        therapist_name=course.therapist.name if course.therapist else "",
        room_name=course.room.name if course.room else "",
    )


# ── Action endpoints ──────────────────────────────────────────────────


@router.post("/{course_id}/start", response_model=CourseResponse)
async def start_course_endpoint(
    course_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_role("therapist", "admin"))],
):
    """Start a course session (therapist or admin).

    Transitions: course → ongoing, patient → treating.
    """
    course = await _get_course(db, course_id)
    if current_user.role == "therapist":
        tp = await _get_therapist(db, current_user)
        _check_therapist_access(course, tp)
    await start_course(db, course, current_user.id)
    await db.refresh(course)
    return course


@router.post("/{course_id}/finish", response_model=CourseResponse)
async def finish_course_endpoint(
    course_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_role("therapist", "admin"))],
):
    """Finish a course session (therapist or admin).

    Transitions: course → completed, patient → ward.
    """
    course = await _get_course(db, course_id)
    if current_user.role == "therapist":
        tp = await _get_therapist(db, current_user)
        _check_therapist_access(course, tp)
    await finish_course(db, course, current_user.id)
    await db.refresh(course)
    return course


# ── Therapist schedule ────────────────────────────────────────────────

therapist_schedule_router = APIRouter(prefix="/therapist", tags=["therapist"])


@therapist_schedule_router.get("/schedule", response_model=ScheduleResponse)
async def therapist_schedule(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_role("therapist"))],
    date_str: str = Query(..., alias="date"),
):
    """Therapist's daily schedule aggregation.

    Returns overview (total, completed, remaining), timeline items,
    and free slots (> 15 min gaps between courses).
    Data permission: only current therapist's own courses.
    """
    tp = await _get_therapist(db, current_user)
    if not tp:
        raise HTTPException(status_code=403, detail="Therapist profile not found")

    # Parse date range (UTC day)
    target_date = date.fromisoformat(date_str)
    day_start = datetime(target_date.year, target_date.month, target_date.day, tzinfo=timezone.utc)
    day_end = datetime(target_date.year, target_date.month, target_date.day, 23, 59, 59, tzinfo=timezone.utc)

    # Fetch courses for this therapist on this date
    stmt = (
        select(Course)
        .where(
            Course.therapist_id == tp.id,
            Course.end_at >= day_start,
            Course.start_at <= day_end,
        )
        .order_by(Course.start_at.asc())
    )
    courses = (await db.execute(stmt)).scalars().all()

    # Build items
    items: list[ScheduleCourseItem] = []
    for c in courses:
        items.append(
            ScheduleCourseItem(
                course_id=c.id,
                start_at=c.start_at,
                end_at=c.end_at,
                patient_name=c.patient.name if c.patient else "Unknown",
                course_type=c.course_type,
                room_name=c.room.name if c.room else "Unknown",
                status=c.status,
                actual_start_at=c.actual_start_at,
                actual_end_at=c.actual_end_at,
            )
        )

    # Overview
    completed = sum(1 for c in courses if c.status == "completed")
    total = len(courses)
    remaining = total - completed

    # Free slots: gaps between consecutive courses > 15 minutes
    free_slots: list[FreeSlot] = []
    for i in range(len(courses) - 1):
        gap_start = _as_utc(courses[i].end_at)
        gap_end = _as_utc(courses[i + 1].start_at)
        gap_minutes = int((gap_end - gap_start).total_seconds() / 60)
        if gap_minutes > 15:
            free_slots.append(
                FreeSlot(
                    start=courses[i].end_at,
                    end=courses[i + 1].start_at,
                    minutes=gap_minutes,
                )
            )

    return ScheduleResponse(
        date=date_str,
        overview=ScheduleOverview(total=total, completed=completed, remaining=remaining),
        items=items,
        free_slots=free_slots,
    )
