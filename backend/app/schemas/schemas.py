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
    # 手机号必填（医院联系/短信提醒；PRD §5 短信通道预留）
    phone: str = Field(min_length=11, max_length=20, pattern=r"^1\d{10}$")


class LoginRequest(BaseModel):
    username: str
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class LogoutRequest(BaseModel):
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


# ── Dashboard (§8) ───────────────────────────────────────────────────


class DashboardKpiResponse(BaseModel):
    """主任看板 KPI 聚合。"""
    inpatient_count: int  # ① 在院患者总数（status != discharged）
    today_course_count: int  # ② 今日已排课程总数
    treating_count: int  # ③ 当前治疗中人数（status=treating）
    therapist_attendance_rate: float  # ④ 康复师今日出勤率 0.0-1.0


class PatientDistributionItem(BaseModel):
    """患者分布项。"""
    location: str
    count: int


class PatientDistributionResponse(BaseModel):
    """患者位置分布。"""
    items: list[PatientDistributionItem]


class TherapistWorkloadItem(BaseModel):
    """康复师工作量项。"""
    therapist_id: int
    therapist_name: str
    group_name: str
    course_count: int


class TherapistWorkloadResponse(BaseModel):
    """康复师今日工作量。"""
    date: str
    items: list[TherapistWorkloadItem]


class CourseTrendItem(BaseModel):
    """课程趋势项。"""
    date: str
    count: int


class CourseTrendResponse(BaseModel):
    """课程趋势。"""
    days: int
    items: list[CourseTrendItem]


# ── Patient 360° (§2) ────────────────────────────────────────────────


class PatientOverviewResponse(BaseModel):
    """患者 360° 聚合视图。"""
    id: int
    name: str
    gender: Optional[str] = None
    age: Optional[int] = None
    diagnosis: Optional[str] = None
    admission_date: Optional[str] = None  # ISO date
    ward_location: Optional[str] = None
    status: str
    doctor_name: Optional[str] = None
    therapist_name: Optional[str] = None
    # 当前位置（patient_status_log 最新一条）
    current_location: Optional[str] = None
    current_status: Optional[str] = None
    # 康复计划时间轴（课程列表，按时间倒序）
    courses: list["PatientCourseItem"] = []
    # 本周课程分布（7天计数）
    weekly_distribution: list[CourseTrendItem] = []


class PatientCourseItem(BaseModel):
    """患者 360° 中的课程摘要条目。"""
    course_id: int
    course_type: str
    start_at: datetime
    end_at: datetime
    status: str
    therapist_name: Optional[str] = None
    room_name: Optional[str] = None


# ── Assessments (§2) ──────────────────────────────────────────────────


class AssessmentCreate(BaseModel):
    """新增评估记录请求。"""
    assess_type: str = Field(min_length=1, max_length=64)
    score: Optional[float] = None
    detail: Optional[dict] = None
    assessed_at: datetime


class AssessmentResponse(BaseModel):
    """评估记录响应。"""
    id: int
    patient_id: int
    template_id: Optional[int] = None
    assess_type: str
    score: Optional[float] = None
    detail: Optional[dict] = None
    assessor_id: Optional[int] = None
    assessor_name: Optional[str] = None
    assessed_at: datetime
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class AssessmentListResponse(BaseModel):
    """评估记录列表。"""
    total: int
    items: list[AssessmentResponse]


class AssessmentTrendItem(BaseModel):
    """评估趋势数据点。"""
    assessed_at: datetime
    score: Optional[float] = None
    assessor_name: Optional[str] = None


class AssessmentTrendResponse(BaseModel):
    """指定量表类型的历史评分序列。"""
    patient_id: int
    assess_type: str
    items: list[AssessmentTrendItem]
