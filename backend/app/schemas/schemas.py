"""Pydantic v2 schemas for request/response validation."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator


# ── Auth ──────────────────────────────────────────────────────────


class RegisterRequest(BaseModel):
    username: str = Field(min_length=2, max_length=64)
    password: str = Field(min_length=6, max_length=128)
    display_name: str = Field(min_length=1, max_length=64)
    role: str = Field(pattern=r"^(patient|therapist|doctor|admin)$")


class LoginRequest(BaseModel):
    username: str
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: int
    username: str
    role: str
    display_name: str
    is_active: bool


# ── Courses ───────────────────────────────────────────────────────


class CourseCreate(BaseModel):
    patient_id: int
    therapist_id: int
    room_id: int
    course_type: str = Field(pattern=r"^(PT|OT|ST)$")
    start_at: datetime
    end_at: datetime

    @field_validator("start_at", "end_at")
    @classmethod
    def check_15min_granularity(cls, v: datetime) -> datetime:
        """Validate 15-minute alignment."""
        if v.minute % 15 != 0 or v.second != 0 or v.microsecond != 0:
            raise ValueError(f"Time must align to 15-minute boundaries, got {v}")
        return v

    @field_validator("end_at")
    @classmethod
    def end_after_start(cls, v: datetime, info) -> datetime:
        start = info.data.get("start_at")
        if start and v <= start:
            raise ValueError("end_at must be after start_at")
        return v


class ConflictDetail(BaseModel):
    conflicting_course_id: int
    reason: str  # "patient_conflict" or "therapist_conflict"


class CourseResponse(BaseModel):
    id: int
    patient_id: int
    therapist_id: int
    room_id: int
    course_type: str
    start_at: datetime
    end_at: datetime
    status: str
    actual_start_at: Optional[datetime] = None
    actual_end_at: Optional[datetime] = None
    minutes_consumed: Optional[int] = None
    session_note: Optional[str] = None
    created_by: Optional[int] = None
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}
