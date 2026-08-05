"""Dashboard endpoints — admin-only aggregation queries (§8).

Refresh frequency semantics (architecture.md §3.1):
- KPI / distribution: real-time (no cache, frontend polls)
- Therapist workload: ~30 min refresh
- Course trend: daily refresh
"""

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db, require_role
from app.models.models import User
from app.schemas.schemas import (
    CourseTrendItem,
    CourseTrendResponse,
    DashboardKpiResponse,
    PatientDistributionItem,
    PatientDistributionResponse,
    TherapistWorkloadItem,
    TherapistWorkloadResponse,
)
from app.services.dashboard import (
    get_course_trend,
    get_kpis,
    get_patient_distribution,
    get_therapist_workload,
)

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/kpis", response_model=DashboardKpiResponse)
async def dashboard_kpis(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_role("admin"))],
):
    """Return 4 KPIs: inpatient count, today's courses, treating patients, attendance rate."""
    data = await get_kpis(db)
    return DashboardKpiResponse(**data)


@router.get("/patient-distribution", response_model=PatientDistributionResponse)
async def patient_distribution(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_role("admin"))],
):
    """Return patient count grouped by location (latest status log)."""
    items = await get_patient_distribution(db)
    return PatientDistributionResponse(
        items=[PatientDistributionItem(**it) for it in items]
    )


@router.get("/therapist-workload", response_model=TherapistWorkloadResponse)
async def therapist_workload(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_role("admin"))],
    date_str: str = Query(..., alias="date", description="ISO date e.g. 2026-08-05"),
):
    """Return per-therapist course count for a given date."""
    target_date = date.fromisoformat(date_str)
    items = await get_therapist_workload(db, target_date)
    return TherapistWorkloadResponse(
        date=date_str,
        items=[TherapistWorkloadItem(**it) for it in items],
    )


@router.get("/course-trend", response_model=CourseTrendResponse)
async def course_trend(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_role("admin"))],
    days: int = Query(7, ge=1, le=90, description="Number of days to look back"),
):
    """Return daily course count for the last `days` days."""
    items = await get_course_trend(db, days)
    return CourseTrendResponse(
        days=days,
        items=[CourseTrendItem(**it) for it in items],
    )
