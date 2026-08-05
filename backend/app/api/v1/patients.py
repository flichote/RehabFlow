"""Patient endpoints: list, detail, patient 360° overview, assessments.

Data permission (architecture.md §4.4):
- Doctor: only patients where Patient.doctor_id = current_user.doctor_id
- Therapist: only patients where Patient.therapist_id = current_user.therapist_id
- Admin: all patients
"""

from datetime import date, datetime, timedelta, timezone
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db, require_role
from app.models.models import (
    Assessment,
    Course,
    Doctor,
    Patient,
    PatientStatusLog,
    Therapist,
    User,
)
from app.schemas.schemas import (
    AssessmentCreate,
    AssessmentListResponse,
    AssessmentResponse,
    AssessmentTrendItem,
    AssessmentTrendResponse,
    CourseTrendItem,
    PatientCourseItem,
    PatientOverviewResponse,
)

router = APIRouter(prefix="/patients", tags=["patients"])


# ── Helpers ────────────────────────────────────────────────────────────


async def _get_patient_or_404(db: AsyncSession, patient_id: int) -> Patient:
    """Fetch patient or raise 404."""
    result = await db.execute(
        select(Patient).where(Patient.id == patient_id)
    )
    patient = result.scalar_one_or_none()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    return patient


async def _check_patient_access(
    patient: Patient,
    user: User,
    db: AsyncSession,
) -> None:
    """Enforce row-level data permission: doctor/therapist only their patients."""
    if user.role == "admin":
        return  # admin sees all

    if user.role == "doctor":
        # Get doctor profile
        dr_result = await db.execute(
            select(Doctor).where(Doctor.user_id == user.id)
        )
        doctor = dr_result.scalar_one_or_none()
        if not doctor:
            raise HTTPException(status_code=403, detail="Doctor profile not found")
        if patient.doctor_id != doctor.id:
            raise HTTPException(status_code=404, detail="Patient not found")
        return

    if user.role == "therapist":
        # Get therapist profile
        t_result = await db.execute(
            select(Therapist).where(Therapist.user_id == user.id)
        )
        therapist = t_result.scalar_one_or_none()
        if not therapist:
            raise HTTPException(status_code=403, detail="Therapist profile not found")
        if patient.therapist_id != therapist.id:
            raise HTTPException(status_code=404, detail="Patient not found")
        return

    raise HTTPException(status_code=403, detail="Insufficient permissions")


async def _get_doctor_id(db: AsyncSession, user: User) -> Optional[int]:
    """Get doctor.id for the given user if they are a doctor."""
    if user.role != "doctor":
        return None
    dr_result = await db.execute(
        select(Doctor).where(Doctor.user_id == user.id)
    )
    doctor = dr_result.scalar_one_or_none()
    return doctor.id if doctor else None


async def _get_therapist_id(db: AsyncSession, user: User) -> Optional[int]:
    """Get therapist.id for the given user if they are a therapist."""
    if user.role != "therapist":
        return None
    t_result = await db.execute(
        select(Therapist).where(Therapist.user_id == user.id)
    )
    therapist = t_result.scalar_one_or_none()
    return therapist.id if therapist else None


# ── GET /patients/{id}/overview — 患者 360° 聚合 ────────────────────────


@router.get("/{patient_id}/overview", response_model=PatientOverviewResponse)
async def patient_overview(
    patient_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_role("doctor", "therapist", "admin"))],
):
    """患者 360° 聚合：基本信息 + 当前位置 + 计划时间轴 + 本周课程分布。

    Access: doctor/therapist see own patients; admin sees all.
    """
    patient = await _get_patient_or_404(db, patient_id)
    await _check_patient_access(patient, current_user, db)

    # Latest status log for current location
    latest_log_result = await db.execute(
        select(PatientStatusLog)
        .where(PatientStatusLog.patient_id == patient_id)
        .order_by(PatientStatusLog.occurred_at.desc())
        .limit(1)
    )
    latest_log = latest_log_result.scalar_one_or_none()

    # Courses (time axis): all courses for this patient, reversed chronological
    courses_result = await db.execute(
        select(Course)
        .where(Course.patient_id == patient_id)
        .order_by(Course.start_at.desc())
    )
    courses = courses_result.scalars().all()

    course_items: list[PatientCourseItem] = []
    for c in courses:
        course_items.append(
            PatientCourseItem(
                course_id=c.id,
                course_type=c.course_type,
                start_at=c.start_at,
                end_at=c.end_at,
                status=c.status,
                therapist_name=c.therapist.name if c.therapist else None,
                room_name=c.room.name if c.room else None,
            )
        )

    # Weekly distribution: last 7 days course count per day
    today = datetime.now(timezone.utc).date()
    week_start = today - timedelta(days=6)
    week_start_dt = datetime(
        week_start.year, week_start.month, week_start.day, tzinfo=timezone.utc
    )
    week_end_dt = datetime(
        today.year, today.month, today.day, 23, 59, 59, tzinfo=timezone.utc
    )

    weekly_stmt = (
        select(
            func.date(Course.start_at).label("dt"),
            func.count(Course.id).label("cnt"),
        )
        .where(
            Course.patient_id == patient_id,
            Course.start_at >= week_start_dt,
            Course.start_at <= week_end_dt,
        )
        .group_by(func.date(Course.start_at))
        .order_by(func.date(Course.start_at).asc())
    )
    weekly_rows = (await db.execute(weekly_stmt)).all()
    weekly_map = {r.dt: r.cnt for r in weekly_rows}

    weekly_dist: list[CourseTrendItem] = []
    for i in range(7):
        d = week_start + timedelta(days=i)
        iso = d.isoformat()
        weekly_dist.append(CourseTrendItem(date=iso, count=weekly_map.get(iso, 0)))

    return PatientOverviewResponse(
        id=patient.id,
        name=patient.name,
        gender=patient.gender,
        age=patient.age,
        diagnosis=patient.diagnosis,
        admission_date=patient.admission_date.isoformat() if patient.admission_date else None,
        ward_location=patient.ward_location,
        status=patient.status,
        doctor_name=patient.doctor.name if patient.doctor else None,
        therapist_name=patient.therapist.name if patient.therapist else None,
        current_location=latest_log.location if latest_log else None,
        current_status=latest_log.to_status if latest_log else None,
        courses=course_items,
        weekly_distribution=weekly_dist,
    )


# ── Assessments ─────────────────────────────────────────────────────────


@router.get("/{patient_id}/assessments", response_model=AssessmentListResponse)
async def list_assessments(
    patient_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_role("doctor", "therapist", "admin"))],
):
    """列出患者所有评估记录，按时间倒序。

    Access: doctor/therapist see own patients; admin sees all.
    """
    patient = await _get_patient_or_404(db, patient_id)
    await _check_patient_access(patient, current_user, db)

    stmt = (
        select(Assessment)
        .where(Assessment.patient_id == patient_id)
        .order_by(Assessment.assessed_at.desc())
    )
    assessments = (await db.execute(stmt)).scalars().all()

    items: list[AssessmentResponse] = []
    for a in assessments:
        items.append(
            AssessmentResponse(
                id=a.id,
                patient_id=a.patient_id,
                template_id=a.template_id,
                assess_type=a.assess_type,
                score=float(a.score) if a.score is not None else None,
                detail=a.detail,
                assessor_id=a.assessor_id,
                assessor_name=a.assessor.display_name if a.assessor else None,
                assessed_at=a.assessed_at,
                created_at=a.created_at,
            )
        )

    return AssessmentListResponse(total=len(items), items=items)


@router.post(
    "/{patient_id}/assessments",
    response_model=AssessmentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_assessment(
    patient_id: int,
    body: AssessmentCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_role("therapist"))],
):
    """康复师填写评估记录。

    Writer: therapist only.
    Data permission: therapist must be the patient's assigned therapist.
    """
    patient = await _get_patient_or_404(db, patient_id)

    # Therapist must be the patient's assigned therapist
    t_result = await db.execute(
        select(Therapist).where(Therapist.user_id == current_user.id)
    )
    therapist = t_result.scalar_one_or_none()
    if not therapist:
        raise HTTPException(status_code=403, detail="Therapist profile not found")
    if patient.therapist_id != therapist.id:
        raise HTTPException(
            status_code=404,
            detail="Patient not found or not assigned to you",
        )

    assessment = Assessment(
        patient_id=patient_id,
        assess_type=body.assess_type,
        score=body.score,
        detail=body.detail,
        assessor_id=current_user.id,
        assessed_at=body.assessed_at,
    )
    db.add(assessment)
    await db.commit()
    await db.refresh(assessment)

    return AssessmentResponse(
        id=assessment.id,
        patient_id=assessment.patient_id,
        template_id=assessment.template_id,
        assess_type=assessment.assess_type,
        score=float(assessment.score) if assessment.score is not None else None,
        detail=assessment.detail,
        assessor_id=assessment.assessor_id,
        assessor_name=current_user.display_name,
        assessed_at=assessment.assessed_at,
        created_at=assessment.created_at,
    )


@router.get("/{patient_id}/assessments/trend", response_model=AssessmentTrendResponse)
async def assessment_trend(
    patient_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_role("doctor", "therapist", "admin"))],
    assess_type: str = Query(..., alias="type", description="量表类型 e.g. Fugl-Meyer"),
):
    """指定量表类型的历史评分序列（折线图数据）。

    Returns assessments of the given type, ordered by assessed_at ascending.
    """
    patient = await _get_patient_or_404(db, patient_id)
    await _check_patient_access(patient, current_user, db)

    stmt = (
        select(Assessment)
        .where(
            Assessment.patient_id == patient_id,
            Assessment.assess_type == assess_type,
        )
        .order_by(Assessment.assessed_at.asc())
    )
    assessments = (await db.execute(stmt)).scalars().all()

    items: list[AssessmentTrendItem] = []
    for a in assessments:
        items.append(
            AssessmentTrendItem(
                assessed_at=a.assessed_at,
                score=float(a.score) if a.score is not None else None,
                assessor_name=a.assessor.display_name if a.assessor else None,
            )
        )

    return AssessmentTrendResponse(
        patient_id=patient_id,
        assess_type=assess_type,
        items=items,
    )
