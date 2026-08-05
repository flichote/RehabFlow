"""Course endpoints: create, start, finish."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db, require_role
from app.models.models import Course, Therapist, User
from app.schemas.schemas import CourseCreate, CourseResponse
from app.services.scheduling import create_course
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
