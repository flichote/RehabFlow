"""Aggregate v1 API router."""

from fastapi import APIRouter

from app.api.v1.auth import router as auth_router
from app.api.v1.courses import router as courses_router
from app.api.v1.courses import therapist_schedule_router
from app.api.v1.scheduler import router as scheduler_router

router = APIRouter(prefix="/api/v1")
router.include_router(auth_router)
router.include_router(courses_router)
router.include_router(scheduler_router)
router.include_router(therapist_schedule_router)
