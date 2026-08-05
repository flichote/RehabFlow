"""Scheduler resource endpoints: resource tree, patient pool.

Admin-only endpoints for scheduling page data.
"""

from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db, require_role
from app.models.models import (
    Course,
    Doctor,
    Patient,
    Room,
    Therapist,
    User,
)
from app.schemas.schemas import (
    PatientPoolItem,
    PoolResponse,
    ResourceTreeResponse,
    RoomInfo,
    TherapistInfo,
)

router = APIRouter(prefix="/scheduler", tags=["scheduler"])


@router.get("/resources", response_model=ResourceTreeResponse)
async def get_resources(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_role("admin"))],
):
    """Get resource tree for scheduling page (admin only).

    Returns therapists grouped by PT/OT/ST and room list.
    """
    # All therapists
    therapists = (
        (await db.execute(select(Therapist).order_by(Therapist.group_name, Therapist.name)))
        .scalars()
        .all()
    )

    grouped: dict[str, list[TherapistInfo]] = {"PT": [], "OT": [], "ST": []}
    for t in therapists:
        info = TherapistInfo(id=t.id, name=t.name, group_name=t.group_name, title=t.title)
        grouped[t.group_name].append(info)

    # All active rooms
    rooms = (
        (await db.execute(select(Room).where(Room.is_active == True).order_by(Room.room_type, Room.name)))
        .scalars()
        .all()
    )

    room_infos = [
        RoomInfo(id=r.id, name=r.name, room_type=r.room_type, is_active=r.is_active)
        for r in rooms
    ]

    return ResourceTreeResponse(therapists=grouped, rooms=room_infos)


@router.get("/pool", response_model=PoolResponse)
async def get_pool(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_role("admin"))],
):
    """Get patient pool — patients with no courses today (admin only).

    Finds all non-discharged patients that don't have any active
    (non-completed, non-leave, non-absent) courses scheduled for today.
    """
    today = datetime.now(timezone.utc).date()
    day_start = datetime(today.year, today.month, today.day, tzinfo=timezone.utc)
    day_end = datetime(today.year, today.month, today.day, 23, 59, 59, tzinfo=timezone.utc)

    # Patients who have at least one course today
    occupied_stmt = (
        select(Course.patient_id)
        .where(
            Course.end_at >= day_start,
            Course.start_at <= day_end,
            Course.status.notin_(["completed", "leave", "absent"]),
        )
        .distinct()
    )
    occupied_ids = {row[0] for row in (await db.execute(occupied_stmt)).all()}

    # All non-discharged patients
    patients = (
        (await db.execute(
            select(Patient)
            .where(Patient.status != "discharged")
            .order_by(Patient.name)
        ))
        .scalars()
        .all()
    )

    # Filter to those without courses today
    pool_patients = [p for p in patients if p.id not in occupied_ids]

    items: list[PatientPoolItem] = []
    for p in pool_patients:
        items.append(
            PatientPoolItem(
                id=p.id,
                name=p.name,
                gender=p.gender,
                age=p.age,
                diagnosis=p.diagnosis,
                ward_location=p.ward_location,
                doctor_name=p.doctor.name if p.doctor else None,
                therapist_name=p.therapist.name if p.therapist else None,
            )
        )

    return PoolResponse(
        date=today.isoformat(),
        total=len(items),
        items=items,
    )
