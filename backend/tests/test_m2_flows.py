"""M2 验收测试：通知 / 预警 / 定时任务（T9）。

依据：docs/design/flows.md 状态速查表 + PRD §5 消息提醒 + docs/api.md §5-7 + T8 交付说明。

分组：
1. 通知（BUG 回归，当前预期失败，对应 BUG-6/7/8，见 docs/qa/test-report-m2.md）：
   - 排课成功 → 患者+康复师收到 course_new（PRD §5 行1 / flows.md 流程1 验收点）
   - 课前提醒(reminded) 后课程可开始上课（flows.md 速查表 reminded→ongoing）
   - 超时5min → 康复师收到 course_overdue 站内信（PRD §5 行4 / flows.md 流程2 异常分支）
2. 定时任务幂等去重（手动触发 task 函数，monkeypatch _now 不依赖真实时钟）：
   - 课前15min：跑两遍 → 课程只转 reminded 一次、患者/康复师各 1 条提醒
   - 超时5min：跑两遍 → 只生成 1 条 open course_overdue 预警
   - 30min 巡检：跑两遍 → 康复师只收到 1 条 course_end_reminder
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import func, select

from app.db.session import SessionLocal
from app.models.models import (
    Alert,
    Course,
    CourseStatusLog,
    Notification,
    Patient,
)
from app.tasks import scheduler_tasks as st

from tests.conftest import course_body, make_time

# 固定「当前时间」（周一 09:00 UTC），15min 对齐；所有课程时间均相对它构造，
# 保证测试不依赖真实时钟（硬性约束）。
FIXED = datetime(2030, 1, 7, 9, 0, tzinfo=timezone.utc)


@pytest.fixture(autouse=True, scope="module")
def _stop_background_scheduler():
    """停掉后台 APScheduler，避免真实调度器与手动触发竞态（定时任务测试确定性）。

    说明：lifespan 会启动 APScheduler（每分钟/每5分钟扫描）；本模块手动触发
    task 函数验证幂等，若后台调度器同时运行，可能产生竞态。停掉后由测试
    独占触发时机。其余模块不依赖后台调度器（均为手动调用或未来时间课程），不受影响。
    """
    if st.scheduler.running:
        st.scheduler.shutdown(wait=False)
    yield


def _create_course_api(client, headers, pid, tid, rid, day_offset, hour=9, minute=0, dur=60):
    """通过 API 创建课程（走 15min 粒度校验与冲突检测）。"""
    start = make_time(day_offset=day_offset, hour=hour, minute=minute)
    end = start + timedelta(minutes=dur)
    r = client.post(
        "/api/v1/courses",
        json=course_body(pid, tid, rid, start, end),
        headers=headers,
    )
    assert r.status_code == 201, f"创建课程失败: {r.status_code} {r.text}"
    return r.json()["id"]


async def _db_create_course(pid, tid, rid, start_at, end_at, status="scheduled"):
    """直接写库创建课程（用于构造超时/巡检场景，绕过 API 校验）。"""
    async with SessionLocal() as db:
        c = Course(
            patient_id=pid,
            therapist_id=tid,
            room_id=rid,
            course_type="PT",
            start_at=start_at,
            end_at=end_at,
            status=status,
        )
        db.add(c)
        await db.commit()
        await db.refresh(c)
        return c.id


async def _patient_notification_count(pid: int, notif_type: str) -> int:
    async with SessionLocal() as db:
        p = (await db.execute(select(Patient).where(Patient.id == pid))).scalar_one()
        return (
            await db.execute(
                select(func.count()).select_from(Notification).where(
                    Notification.user_id == p.user_id,
                    Notification.type == notif_type,
                )
            )
        ).scalar_one()


# ── 通知：排课成功 → course_new（BUG-6 回归，当前预期失败）────────────────


def test_create_course_writes_course_new_notifications(client, actor_set):
    """[BUG-6] PRD §5 / flows.md 流程1：排课成功 → 患者+康复师收到 course_new 站内信。

    当前实现：send_course_new_notifications 定义但从未被调用（grep 仅 notifications.py
    内部），POST /courses 不写任何通知 → 本用例失败即为缺陷证据。
    """
    H_admin, H_ther, pid, tid, rid = actor_set
    _create_course_api(client, H_admin, pid, tid, rid, day_offset=60)

    # 康复师应收到 course_new
    r = client.get("/api/v1/notifications", headers=H_ther)
    assert r.status_code == 200
    course_new = [i for i in r.json()["items"] if i["type"] == "course_new"]
    assert len(course_new) >= 1, "排课成功后康复师应收到 course_new 通知（当前缺失 → BUG-6）"

    # 患者应收到 course_new
    assert asyncio.run(_patient_notification_count(pid, "course_new")) >= 1, (
        "排课成功后患者应收到 course_new 通知（当前缺失 → BUG-6）"
    )


# ── 通知：课前提醒(reminded) 后课程可开始（BUG-8 回归，当前预期失败）──────


def test_reminded_course_can_start(client, actor_set):
    """[BUG-8] flows.md 速查表：提醒发出(reminded) → 开始上课(ongoing)。

    流程2.1 标准路径：课前15min 自动提醒 → 课程「提醒已发」→ 康复师点「开始上课」→ 进行中。
    当前实现 start_course 仅允许 scheduled → 409。
    """
    H_admin, H_ther, pid, tid, rid = actor_set
    cid = _create_course_api(client, H_admin, pid, tid, rid, day_offset=61)

    r = client.post(f"/api/v1/courses/{cid}/remind", headers=H_ther)
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "reminded"

    r = client.post(f"/api/v1/courses/{cid}/start", headers=H_ther)
    assert r.status_code == 200, (
        f"reminded 课程应可开始上课，实际 {r.status_code}: {r.text}（BUG-8）"
    )
    assert r.json()["status"] == "ongoing"


# ── 通知：超时5min → 康复师站内信（BUG-7 回归，当前预期失败）────────────


def test_overdue_detection_notifies_therapist(client, actor_set, monkeypatch):
    """[BUG-7] PRD §5 行4 / flows.md 流程2 异常分支：超时5min → 康复师收到站内信。

    当前实现 _overdue_detection 只生成 alert + 课程→abnormal，
    send_course_overdue_notification 从未被调用 → 康复师收不到通知。
    """
    H_admin, H_ther, pid, tid, rid = actor_set
    monkeypatch.setattr(st, "_now", lambda: FIXED)
    asyncio.run(
        _db_create_course(
            pid, tid, rid,
            FIXED - timedelta(minutes=30),  # 08:30 开始
            FIXED - timedelta(minutes=15),  # 08:45 结束（已超时）
        )
    )

    asyncio.run(st._overdue_detection())

    r = client.get("/api/v1/notifications", headers=H_ther)
    assert r.status_code == 200
    overdue = [i for i in r.json()["items"] if i["type"] == "course_overdue"]
    assert len(overdue) >= 1, "超时后康复师应收到 course_overdue 通知（当前缺失 → BUG-7）"


# ── 定时任务：课前15min 幂等去重 ───────────────────────────────────────


def test_pre_class_reminder_idempotent(client, actor_set, monkeypatch):
    """定时任务-课前15min：跑两遍只提醒一次。

    - 课程 start_at = FIXED+15min（恰在 [now, now+15min] 窗口）
    - 两遍 _pre_class_reminder() → 课程只转 reminded 一次、
      康复师恰好 1 条 course_reminder_therapist、患者恰好 1 条 course_reminder
    """
    H_admin, H_ther, pid, tid, rid = actor_set
    monkeypatch.setattr(st, "_now", lambda: FIXED)
    cid = _create_course_api(
        client, H_admin, pid, tid, rid,
        day_offset=0, hour=9, minute=15, dur=30,  # 09:15-09:45
    )

    asyncio.run(st._pre_class_reminder())
    asyncio.run(st._pre_class_reminder())

    # 课程状态 + 日志只转一次
    async def _check_course():
        async with SessionLocal() as db:
            c = (await db.execute(select(Course).where(Course.id == cid))).scalar_one()
            reminded_logs = (
                await db.execute(
                    select(func.count()).select_from(CourseStatusLog).where(
                        CourseStatusLog.course_id == cid,
                        CourseStatusLog.to_status == "reminded",
                    )
                )
            ).scalar_one()
            return c.status, reminded_logs

    status, reminded_logs = asyncio.run(_check_course())
    assert status == "reminded", f"课程应 reminded，实际 {status}"
    assert reminded_logs == 1, f"reminded 日志应恰 1 条，实际 {reminded_logs}"

    # 康复师恰好 1 条课前提醒
    r = client.get("/api/v1/notifications", headers=H_ther)
    therapist_reminders = [
        i for i in r.json()["items"] if i["type"] == "course_reminder_therapist"
    ]
    assert len(therapist_reminders) == 1, (
        f"康复师应恰好 1 条课前提醒，实际 {len(therapist_reminders)}"
    )

    # 患者恰好 1 条课前提醒
    assert asyncio.run(_patient_notification_count(pid, "course_reminder")) == 1, (
        "患者应恰好 1 条课前提醒"
    )


# ── 定时任务：超时5min 幂等去重 ───────────────────────────────────────


def test_overdue_detection_idempotent(client, actor_set, monkeypatch):
    """定时任务-超时5min：跑两遍只生成 1 条 open course_overdue 预警。"""
    H_admin, H_ther, pid, tid, rid = actor_set
    monkeypatch.setattr(st, "_now", lambda: FIXED)
    cid = asyncio.run(
        _db_create_course(
            pid, tid, rid,
            FIXED - timedelta(minutes=30),
            FIXED - timedelta(minutes=15),
        )
    )

    asyncio.run(st._overdue_detection())
    asyncio.run(st._overdue_detection())

    async def _check():
        async with SessionLocal() as db:
            c = (await db.execute(select(Course).where(Course.id == cid))).scalar_one()
            alerts = (
                await db.execute(
                    select(func.count()).select_from(Alert).where(
                        Alert.ref_course_id == cid,
                        Alert.alert_type == "course_overdue",
                        Alert.status == "open",
                    )
                )
            ).scalar_one()
            return c.status, alerts

    status, alerts = asyncio.run(_check())
    assert status == "abnormal", f"课程应 abnormal，实际 {status}"
    assert alerts == 1, f"同一课程应只有 1 条 open 预警，实际 {alerts}"


# ── 定时任务：30min 巡检幂等去重 ──────────────────────────────────────


def test_patrol_idempotent(client, actor_set):
    """定时任务-30min巡检：ongoing 超结束时间 30min → 康复师只收到 1 条确认提醒。

    巡检幂等依赖 Notification.created_at（server_default=func.now()，数据库真实时钟）
    与巡检窗口比较，因此本用例按生产路径使用真实 now 构造「已超时 ongoing 课程」，
    不注入假时钟（否则 created_at 与窗口错位，幂等失效）。
    """
    H_admin, H_ther, pid, tid, rid = actor_set
    now = datetime.now(timezone.utc)
    asyncio.run(
        _db_create_course(
            pid, tid, rid,
            now - timedelta(minutes=90),  # 开始：90 分钟前
            now - timedelta(minutes=45),  # 结束：45 分钟前（超 30min 阈值）
            status="ongoing",
        )
    )

    asyncio.run(st._patrol_ongoing())
    asyncio.run(st._patrol_ongoing())

    r = client.get("/api/v1/notifications", headers=H_ther)
    end_reminders = [
        i for i in r.json()["items"] if i["type"] == "course_end_reminder"
    ]
    assert len(end_reminders) == 1, (
        f"康复师应恰好 1 条结束确认提醒，实际 {len(end_reminders)}"
    )
