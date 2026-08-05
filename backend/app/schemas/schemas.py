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
        """Validate 15-minute alignment and normalize to timezone-aware UTC.

        存储约定（架构裁决）：数据库统一存 UTC 墙钟。naive 输入按应用时区
        （APP_TZ）补时区后转 UTC；aware 输入直接转 UTC。这样 SQLite 存出的
        naive 墙钟永远是 UTC 语义，冲突检测/课时计算不会因时区混存出错。
        """
        from datetime import timedelta as _td, timezone as _tz
        from app.core.config import settings as _st

        if v.minute % 15 != 0 or v.second != 0 or v.microsecond != 0:
            raise ValueError(f"Time must align to 15-minute boundaries, got {v}")
        if v.tzinfo is None:
            v = v.replace(tzinfo=_tz(_td(hours=_st.APP_TZ_OFFSET_HOURS)))
        return v.astimezone(_tz.utc)

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


# ── Course list query ──────────────────────────────────────────────


class CourseListResponse(BaseModel):
    """课程列表响应：包含分页信息与 items 列表。"""
    total: int
    items: list[CourseResponse]


class CourseDetailResponse(CourseResponse):
    """课程详情：包含关联名称。"""
    patient_name: str = ""
    therapist_name: str = ""
    room_name: str = ""


# ── Scheduler resources ───────────────────────────────────────────


class TherapistInfo(BaseModel):
    id: int
    name: str
    group_name: str  # PT/OT/ST
    title: Optional[str] = None

    model_config = {"from_attributes": True}


class RoomInfo(BaseModel):
    id: int
    name: str
    room_type: str  # PT/OT/ST
    is_active: bool

    model_config = {"from_attributes": True}


class ResourceTreeResponse(BaseModel):
    """排课页资源树。"""
    therapists: dict[str, list[TherapistInfo]]  # {"PT": [...], "OT": [...], "ST": [...]}
    rooms: list[RoomInfo]


# ── Scheduler pool ─────────────────────────────────────────────────


class PatientPoolItem(BaseModel):
    id: int
    name: str
    gender: Optional[str] = None
    age: Optional[int] = None
    diagnosis: Optional[str] = None
    ward_location: Optional[str] = None
    doctor_name: Optional[str] = None
    therapist_name: Optional[str] = None

    model_config = {"from_attributes": True}


class PoolResponse(BaseModel):
    """待排患者池。"""
    date: str  # ISO date
    total: int
    items: list[PatientPoolItem]


# ── Therapist schedule ─────────────────────────────────────────────


class ScheduleCourseItem(BaseModel):
    """课表时间线中的课程条目。"""
    course_id: int
    start_at: datetime
    end_at: datetime
    patient_name: str
    course_type: str
    room_name: str
    status: str
    actual_start_at: Optional[datetime] = None
    actual_end_at: Optional[datetime] = None


class FreeSlot(BaseModel):
    """两个课程之间的空闲时段。"""
    start: datetime
    end: datetime
    minutes: int


class ScheduleOverview(BaseModel):
    total: int
    completed: int
    remaining: int


class ScheduleResponse(BaseModel):
    """康复师课表聚合。"""
    date: str
    overview: ScheduleOverview
    items: list[ScheduleCourseItem]
    free_slots: list[FreeSlot]


# ── Notifications (§5) ────────────────────────────────────────────


class NotificationResponse(BaseModel):
    id: int
    type: str
    title: str
    content: str
    link: Optional[str] = None
    is_read: bool
    channel: str
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class NotificationListResponse(BaseModel):
    """通知列表（分页，未读优先）。"""
    total: int
    unread_count: int
    items: list[NotificationResponse]


class UnreadCountResponse(BaseModel):
    unread_count: int


# ── Alerts (§6) ───────────────────────────────────────────────────


class AlertResponse(BaseModel):
    id: int
    alert_type: str
    ref_course_id: Optional[int] = None
    ref_patient_id: Optional[int] = None
    summary: str
    status: str
    resolved_by: Optional[int] = None
    resolved_at: Optional[datetime] = None
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class AlertListResponse(BaseModel):
    """预警列表。"""
    total: int
    items: list[AlertResponse]
