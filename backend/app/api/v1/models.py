"""15 张核心表 SQLAlchemy 2.x async 模型。

唯一事实来源：docs/database.md（字段/枚举/约束/索引）。

实现要点：
- 时间一律 ``DateTime(timezone=True)``（TIMESTAMPTZ 语义）
- PK 用 ``BigInteger().with_variant(Integer, "sqlite")``：SQLite 需要 INTEGER 主键才能自增，PG 用 BIGSERIAL
- JSON 列用 ``JSON().with_variant(JSONB, "postgresql")``：SQLite 可建表，PG 用 JSONB（m1-acceptance 裁决-4）
- 状态枚举用 Python 常量（PATIENT_STATUS / COURSE_STATUS ...），数据库加 CHECK 约束兜底
- ``patients.external_patient_no`` 仅备用冗余，不参与任何业务逻辑（architecture.md §9.4）
"""
from __future__ import annotations

from datetime import date, datetime, time

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    Time,
    false,
    func,
    text,
    true,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

# ---------------------------------------------------------------------------
# 枚举常量（database.md 各表"枚举"列；T5 测试按此断言）
# ---------------------------------------------------------------------------

# 患者状态枚举（§2.2）：6 态
PATIENT_STATUS = ("ward", "en_route", "treating", "paused", "absent", "discharged")

# 课程状态枚举（§2.6）：7 态
COURSE_STATUS = (
    "scheduled", "reminded", "ongoing", "completed", "leave", "absent", "abnormal",
)

# 用户角色（§2.1）
USER_ROLE = ("patient", "therapist", "doctor", "admin")

# 组别 / 类型（PT / OT / ST）
THERAPIST_GROUP = ("PT", "OT", "ST")
ROOM_TYPE = ("PT", "OT", "ST")
COURSE_TYPE = ("PT", "OT", "ST")

# 患者状态日志来源（§2.8）
PATIENT_STATUS_LOG_SOURCE = ("course_action", "manual_fix", "system")

# 排班状态（§2.9）
SHIFT_STATUS = ("scheduled", "on_duty", "absent", "leave")

# 通知类型 / 通道（§2.12）
NOTIFICATION_TYPE = (
    "course_new", "course_change", "course_reminder", "course_reminder_therapist",
    "course_overdue", "course_end_reminder",
    "assessment_todo", "alert",
)
NOTIFICATION_CHANNEL = ("inbox", "browser", "sms")

# 预警类型 / 状态（§2.13）
ALERT_TYPE = ("course_overdue", "patient_absent", "conflict_unresolved")
ALERT_STATUS = ("open", "resolved", "ignored")

# 通用 JSON 类型：SQLite 用 JSON（TEXT），PG 用 JSONB（m1-acceptance 裁决-4）
JSON_TYPE = JSON().with_variant(JSONB, "postgresql")


# ---------------------------------------------------------------------------
# 1. users 用户（§2.1）
# ---------------------------------------------------------------------------
class User(TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True
    )
    username: Mapped[str] = mapped_column(String(64), nullable=False, comment="登录名")
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False, comment="bcrypt")
    role: Mapped[str] = mapped_column(String(20), nullable=False, comment="patient/therapist/doctor/admin")
    display_name: Mapped[str] = mapped_column(String(64), nullable=False, comment="显示名")
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True, comment="可选短信通道")

    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=true(), comment="禁用标记"
    )

    patient: Mapped["Patient | None"] = relationship(
        back_populates="user", uselist=False, lazy="selectin"
    )
    therapist: Mapped["Therapist | None"] = relationship(
        back_populates="user", uselist=False, lazy="selectin"
    )
    doctor: Mapped["Doctor | None"] = relationship(
        back_populates="user", uselist=False, lazy="selectin"
    )

    __table_args__ = (
        Index("uk_users_username", "username", unique=True),
        Index("idx_users_role", "role"),
        CheckConstraint(
            "role IN ('patient','therapist','doctor','admin')", name="ck_users_role"
        ),
    )


# ---------------------------------------------------------------------------
# 2. patients 患者档案（§2.2）
# ---------------------------------------------------------------------------
class Patient(TimestampMixin, Base):
    __tablename__ = "patients"

    id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True
    )
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"), nullable=True, unique=True, comment="登录账号"
    )
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    gender: Mapped[str | None] = mapped_column(String(8), nullable=True, comment="男/女")
    age: Mapped[int | None] = mapped_column(Integer, nullable=True)
    diagnosis: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="诊断")
    admission_date: Mapped[date | None] = mapped_column(Date, nullable=True, comment="入院日期")
    ward_location: Mapped[str | None] = mapped_column(
        String(128), nullable=True, comment="病房位置（如 住院部3楼5床）"
    )
    doctor_id: Mapped[int | None] = mapped_column(
        ForeignKey("doctors.id"), nullable=True, comment="主管医生"
    )
    therapist_id: Mapped[int | None] = mapped_column(
        ForeignKey("therapists.id"), nullable=True, comment="责任康复师"
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="ward", server_default="ward",
        comment="患者状态枚举（冗余列，与 patient_status_log 双写，见裁决-5）",
    )
    external_patient_no: Mapped[str | None] = mapped_column(
        String(64), nullable=True,
        comment="HIS 患者号（备用冗余，不参与业务逻辑，architecture.md §9.4）",
    )

    user: Mapped["User | None"] = relationship(back_populates="patient", lazy="selectin")
    doctor: Mapped["Doctor | None"] = relationship(back_populates="patients", lazy="selectin")
    therapist: Mapped["Therapist | None"] = relationship(
        back_populates="patients", lazy="selectin"
    )
    courses: Mapped[list["Course"]] = relationship(back_populates="patient")
    status_logs: Mapped[list["PatientStatusLog"]] = relationship(back_populates="patient")
    assessments: Mapped[list["Assessment"]] = relationship(back_populates="patient")

    __table_args__ = (
        Index("idx_patients_doctor_id", "doctor_id"),
        Index("idx_patients_therapist_id", "therapist_id"),
        Index("idx_patients_status", "status"),
        CheckConstraint(
            "status IN ('ward','en_route','treating','paused','absent','discharged')",
            name="ck_patients_status",
        ),
    )


# ---------------------------------------------------------------------------
# 3. therapists 康复师档案（§2.3）
# ---------------------------------------------------------------------------
class Therapist(TimestampMixin, Base):
    __tablename__ = "therapists"

    id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True
    )
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"), nullable=True, unique=True
    )
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    group_name: Mapped[str] = mapped_column(String(10), nullable=False, comment="PT/OT/ST")
    title: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="职称")
    certified: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=false(), comment="资质审核"
    )

    user: Mapped["User | None"] = relationship(back_populates="therapist", lazy="selectin")
    patients: Mapped[list["Patient"]] = relationship(back_populates="therapist")
    courses: Mapped[list["Course"]] = relationship(back_populates="therapist")
    shifts: Mapped[list["TherapistShift"]] = relationship(back_populates="therapist")

    __table_args__ = (
        CheckConstraint("group_name IN ('PT','OT','ST')", name="ck_therapists_group_name"),
    )


# ---------------------------------------------------------------------------
# 4. doctors 主管医生档案（§2.4）
# ---------------------------------------------------------------------------
class Doctor(TimestampMixin, Base):
    __tablename__ = "doctors"

    id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True
    )
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"), nullable=True, unique=True
    )
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    department: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="科室")
    title: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="职称")

    user: Mapped["User | None"] = relationship(back_populates="doctor", lazy="selectin")
    patients: Mapped[list["Patient"]] = relationship(back_populates="doctor")


# ---------------------------------------------------------------------------
# 5. rooms 治疗室（§2.5）
# ---------------------------------------------------------------------------
class Room(Base):
    __tablename__ = "rooms"

    id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True
    )
    name: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, comment="如 PT大厅 / PT-1室")
    room_type: Mapped[str] = mapped_column(String(10), nullable=False, comment="PT/OT/ST")
    capacity: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1, server_default="1", comment="容量（容量管理 TBD）"
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=true()
    )

    courses: Mapped[list["Course"]] = relationship(back_populates="room")

    __table_args__ = (
        CheckConstraint("room_type IN ('PT','OT','ST')", name="ck_rooms_room_type"),
    )


# ---------------------------------------------------------------------------
# 6. courses 课程实例 ★（§2.6）—— 业务核心
# ---------------------------------------------------------------------------
class Course(TimestampMixin, Base):
    __tablename__ = "courses"

    id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True
    )
    patient_id: Mapped[int] = mapped_column(ForeignKey("patients.id"), nullable=False)
    therapist_id: Mapped[int] = mapped_column(ForeignKey("therapists.id"), nullable=False)
    room_id: Mapped[int] = mapped_column(ForeignKey("rooms.id"), nullable=False)
    course_type: Mapped[str] = mapped_column(String(10), nullable=False, comment="PT/OT/ST（与 room 类型一致）")
    start_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, comment="计划开始（15min 粒度）")
    end_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, comment="计划结束")
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="scheduled", server_default="scheduled",
        comment="课程状态枚举",
    )
    actual_start_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="实际开始（点开始上课）"
    )
    actual_end_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="实际结束（点结束上课）"
    )
    minutes_consumed: Mapped[int | None] = mapped_column(
        Integer, nullable=True, comment="课时消耗（实际时长，向上取整 15min，TBD）"
    )
    session_note: Mapped[str | None] = mapped_column(Text, nullable=True, comment="治疗记录")
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, comment="排课人")

    patient: Mapped["Patient"] = relationship(back_populates="courses", lazy="selectin")
    therapist: Mapped["Therapist"] = relationship(back_populates="courses", lazy="selectin")
    room: Mapped["Room"] = relationship(back_populates="courses", lazy="selectin")
    creator: Mapped["User | None"] = relationship(foreign_keys=[created_by], lazy="selectin")
    status_logs: Mapped[list["CourseStatusLog"]] = relationship(back_populates="course")

    __table_args__ = (
        # 冲突检测索引（architecture.md §4.1 / database.md §2.6）：事务内 FOR UPDATE 依赖
        Index("idx_courses_patient_time", "patient_id", "start_at", "end_at"),
        Index("idx_courses_therapist_time", "therapist_id", "start_at", "end_at"),
        CheckConstraint(
            "course_type IN ('PT','OT','ST')", name="ck_courses_course_type"
        ),
        CheckConstraint(
            "status IN ('scheduled','reminded','ongoing','completed','leave','absent','abnormal')",
            name="ck_courses_status",
        ),
    )


# ---------------------------------------------------------------------------
# 7. course_status_log 课程状态流转（§2.7）
# ---------------------------------------------------------------------------
class CourseStatusLog(Base):
    __tablename__ = "course_status_log"

    id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True
    )
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id"), nullable=False)
    from_status: Mapped[str | None] = mapped_column(String(20), nullable=True)
    to_status: Mapped[str] = mapped_column(String(20), nullable=False)
    actor_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, comment="操作人（系统动作=null）")
    note: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="备注")
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), comment="流转时间"
    )

    course: Mapped["Course"] = relationship(back_populates="status_logs")

    __table_args__ = (Index("idx_course_status_log_course", "course_id", "occurred_at"),)


# ---------------------------------------------------------------------------
# 8. patient_status_log 患者状态/位置流转 ★（§2.8）
# ---------------------------------------------------------------------------
class PatientStatusLog(Base):
    __tablename__ = "patient_status_log"

    id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True
    )
    patient_id: Mapped[int] = mapped_column(ForeignKey("patients.id"), nullable=False)
    from_status: Mapped[str | None] = mapped_column(String(20), nullable=True)
    to_status: Mapped[str] = mapped_column(String(20), nullable=False)
    location: Mapped[str | None] = mapped_column(String(128), nullable=True, comment="位置快照（如 PT大厅2号床）")
    actor_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, comment="触发人")
    source: Mapped[str] = mapped_column(String(20), nullable=False, comment="course_action/manual_fix/system")
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), comment="流转时间"
    )

    patient: Mapped["Patient"] = relationship(back_populates="status_logs")

    __table_args__ = (
        # 当前状态查询：ORDER BY occurred_at DESC LIMIT 1
        Index("idx_patient_status_log_patient", "patient_id", text("occurred_at DESC")),
        CheckConstraint(
            "source IN ('course_action','manual_fix','system')",
            name="ck_patient_status_log_source",
        ),
    )


# ---------------------------------------------------------------------------
# 9. therapist_shifts 康复师排班/出勤（§2.9）
# ---------------------------------------------------------------------------
class TherapistShift(TimestampMixin, Base):
    __tablename__ = "therapist_shifts"

    id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True
    )
    therapist_id: Mapped[int] = mapped_column(ForeignKey("therapists.id"), nullable=False)
    work_date: Mapped[date] = mapped_column(Date, nullable=False)
    start_time: Mapped[time] = mapped_column(Time, nullable=False)
    end_time: Mapped[time] = mapped_column(Time, nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="scheduled", server_default="scheduled",
        comment="scheduled/on_duty/absent/leave",
    )

    therapist: Mapped["Therapist"] = relationship(back_populates="shifts")

    __table_args__ = (
        Index("uk_shifts", "therapist_id", "work_date", unique=True),
        CheckConstraint(
            "status IN ('scheduled','on_duty','absent','leave')", name="ck_therapist_shifts_status"
        ),
    )


# ---------------------------------------------------------------------------
# 10. assessments 评估记录（§2.10）
# ---------------------------------------------------------------------------
class Assessment(TimestampMixin, Base):
    __tablename__ = "assessments"

    id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True
    )
    patient_id: Mapped[int] = mapped_column(ForeignKey("patients.id"), nullable=False)
    template_id: Mapped[int | None] = mapped_column(ForeignKey("assessment_templates.id"), nullable=True)
    assess_type: Mapped[str] = mapped_column(String(64), nullable=False, comment="冗余类型名（Fugl-Meyer / Barthel…）")
    score: Mapped[float | None] = mapped_column(Numeric(6, 2), nullable=True, comment="评分")
    detail: Mapped[dict | None] = mapped_column(JSON_TYPE, nullable=True, comment="分项明细")
    assessor_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, comment="评估人（康复师）")
    assessed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    patient: Mapped["Patient"] = relationship(back_populates="assessments")
    template: Mapped["AssessmentTemplate | None"] = relationship(back_populates="assessments", lazy="selectin")
    assessor: Mapped["User | None"] = relationship(lazy="selectin")

    __table_args__ = (Index("idx_assessments_patient", "patient_id", "assessed_at"),)


# ---------------------------------------------------------------------------
# 11. assessment_templates 评估量表定义（§2.11）
# ---------------------------------------------------------------------------
class AssessmentTemplate(Base):
    __tablename__ = "assessment_templates"

    id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True
    )
    name: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, comment="量表名")
    category: Mapped[str | None] = mapped_column(String(32), nullable=True, comment="分类")
    max_score: Mapped[float | None] = mapped_column(Numeric(6, 2), nullable=True, comment="满分")
    fields: Mapped[dict | None] = mapped_column(JSON_TYPE, nullable=True, comment="分项字段定义")
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=true()
    )

    assessments: Mapped[list["Assessment"]] = relationship(back_populates="template")


# ---------------------------------------------------------------------------
# 12. notifications 消息提醒（§2.12）
# ---------------------------------------------------------------------------
class Notification(TimestampMixin, Base):
    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True
    )
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, comment="接收人")
    type: Mapped[str] = mapped_column(String(32), nullable=False)
    title: Mapped[str] = mapped_column(String(128), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False, comment="模板渲染后文本")
    link: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="跳转路由")
    is_read: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=false()
    )
    channel: Mapped[str] = mapped_column(
        String(20), nullable=False, default="inbox", server_default="inbox",
        comment="inbox/browser/sms",
    )

    user: Mapped["User"] = relationship(lazy="selectin")

    __table_args__ = (
        Index("idx_notifications_user", "user_id", "is_read", text("created_at DESC")),
        CheckConstraint(
            "type IN ('course_new','course_change','course_reminder','course_reminder_therapist','course_overdue','course_end_reminder','assessment_todo','alert')",
            name="ck_notifications_type",
        ),
        CheckConstraint("channel IN ('inbox','browser','sms')", name="ck_notifications_channel"),
    )


# ---------------------------------------------------------------------------
# 13. alerts 异常预警（§2.13）
# ---------------------------------------------------------------------------
class Alert(TimestampMixin, Base):
    __tablename__ = "alerts"

    id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True
    )
    alert_type: Mapped[str] = mapped_column(String(32), nullable=False)
    ref_course_id: Mapped[int | None] = mapped_column(ForeignKey("courses.id"), nullable=True, comment="关联课程")
    ref_patient_id: Mapped[int | None] = mapped_column(ForeignKey("patients.id"), nullable=True, comment="关联患者")
    summary: Mapped[str] = mapped_column(String(255), nullable=False, comment="摘要")
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="open", server_default="open",
        comment="open/resolved/ignored",
    )
    resolved_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    ref_course: Mapped["Course | None"] = relationship(lazy="selectin")
    ref_patient: Mapped["Patient | None"] = relationship(lazy="selectin")
    resolver: Mapped["User | None"] = relationship(lazy="selectin")

    __table_args__ = (
        Index("idx_alerts_status", "status", text("created_at DESC")),
        CheckConstraint(
            "alert_type IN ('course_overdue','patient_absent','conflict_unresolved')",
            name="ck_alerts_alert_type",
        ),
        CheckConstraint("status IN ('open','resolved','ignored')", name="ck_alerts_status"),
    )


# ---------------------------------------------------------------------------
# 14. audit_log 审计日志（§2.14）
# ---------------------------------------------------------------------------
class AuditLog(TimestampMixin, Base):
    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True
    )
    actor_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, comment="操作人")
    action: Mapped[str] = mapped_column(String(64), nullable=False, comment="如 course.force_replace")
    entity_type: Mapped[str] = mapped_column(String(32), nullable=False, comment="course/patient/alert…")
    entity_id: Mapped[int | None] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), nullable=True)
    detail: Mapped[dict | None] = mapped_column(JSON_TYPE, nullable=True, comment="变更前后快照")
    ip: Mapped[str | None] = mapped_column(String(45), nullable=True)

    actor: Mapped["User | None"] = relationship(lazy="selectin")

    __table_args__ = (
        Index("idx_audit_log_entity", "entity_type", "entity_id"),
        Index("idx_audit_log_actor", "actor_id", "created_at"),
    )


# ---------------------------------------------------------------------------
# 15. refresh_tokens 刷新令牌（§2.15）
# ---------------------------------------------------------------------------
class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True
    )
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    token_hash: Mapped[str] = mapped_column(String(128), nullable=False, unique=True, comment="SHA-256")
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=false()
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    user: Mapped["User"] = relationship(lazy="selectin")

    __table_args__ = (Index("idx_refresh_tokens_user", "user_id"),)


# ---------------------------------------------------------------------------
# 16. password_reset_codes 密码重置验证码（§2.16）
# ---------------------------------------------------------------------------
class PasswordResetCode(Base):
    __tablename__ = "password_reset_codes"

    id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True
    )
    phone: Mapped[str] = mapped_column(String(20), nullable=False, index=True, comment="手机号")
    code_hash: Mapped[str] = mapped_column(String(128), nullable=False, comment="SHA-256(验证码)")
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=false())
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        Index("idx_reset_codes_phone_created", "phone", "created_at"),
    )
