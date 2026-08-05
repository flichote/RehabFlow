"""预警 API 测试：列表/过滤/处理/忽略 + 超时自动生成。

依据：api.md §6 预警 + T8 交付要求。
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.models import Alert, Course, Patient
from app.services.alerts import create_course_overdue_alert
from app.services.scheduling import _as_utc

from tests.conftest import (
    auth_headers,
    course_body,
    make_time,
    register_and_login,
    seed_ids,
)


def _create_course(client, headers, pid, tid, rid, day_offset=40, hour=9):
    start = make_time(day_offset=day_offset, hour=hour)
    end = make_time(day_offset=day_offset, hour=hour, minute=45)
    r = client.post(
        "/api/v1/courses",
        json=course_body(pid, tid, rid, start, end),
        headers=headers,
    )
    assert r.status_code == 201, r.text
    return r.json()["id"]


# ── 预警列表 ───────────────────────────────────────────────────


def test_list_alerts_open_only(client, actor_set):
    """预警列表支持 ?status=open 过滤。"""
    H_admin, H_ther, pid, tid, rid = actor_set

    # 管理员查看预警列表
    r = client.get("/api/v1/alerts?status=open", headers=H_admin)
    assert r.status_code == 200
    body = r.json()
    assert "total" in body
    assert "items" in body
    # 所有返回项都应为 open
    for item in body["items"]:
        assert item["status"] == "open"


def test_list_alerts_admin_only(client, actor_set):
    """预警列表仅管理员可查看（权限隔离）。"""
    H_admin, H_ther, pid, tid, rid = actor_set

    # 康复师无权查看预警列表
    r = client.get("/api/v1/alerts", headers=H_ther)
    assert r.status_code == 403, f"therapist should be forbidden, got {r.status_code}"


# ── 预警处理 ───────────────────────────────────────────────────


def test_resolve_alert(client, actor_set):
    """管理员处理预警 → resolved。"""
    H_admin, H_ther, pid, tid, rid = actor_set

    # 先创建课程 + 手动生成预警
    cid = _create_course(client, H_admin, pid, tid, rid, day_offset=41)

    async def _gen_alert():
        async with SessionLocal() as db:
            course = (
                await db.execute(select(Course).where(Course.id == cid))
            ).scalar_one()
            patient = (
                await db.execute(select(Patient).where(Patient.id == course.patient_id))
            ).scalar_one()
            alert = await create_course_overdue_alert(
                db, course, patient, "test_therapist"
            )
            await db.commit()
            return alert.id

    aid = asyncio.run(_gen_alert())

    # 处理预警
    r = client.post(f"/api/v1/alerts/{aid}/resolve", headers=H_admin)
    assert r.status_code == 200
    assert r.json()["status"] == "resolved"
    assert r.json()["resolved_by"] is not None


def test_ignore_alert(client, actor_set):
    """管理员忽略预警 → ignored。"""
    H_admin, H_ther, pid, tid, rid = actor_set

    cid = _create_course(client, H_admin, pid, tid, rid, day_offset=42)

    async def _gen_alert():
        async with SessionLocal() as db:
            course = (
                await db.execute(select(Course).where(Course.id == cid))
            ).scalar_one()
            patient = (
                await db.execute(select(Patient).where(Patient.id == course.patient_id))
            ).scalar_one()
            alert = await create_course_overdue_alert(
                db, course, patient, "test_therapist"
            )
            await db.commit()
            return alert.id

    aid = asyncio.run(_gen_alert())

    r = client.post(f"/api/v1/alerts/{aid}/ignore", headers=H_admin)
    assert r.status_code == 200
    assert r.json()["status"] == "ignored"


def test_resolve_nonexistent_alert(client, actor_set):
    """处理不存在的预警 → 404。"""
    H_admin, H_ther, pid, tid, rid = actor_set
    r = client.post("/api/v1/alerts/99999/resolve", headers=H_admin)
    assert r.status_code == 404


# ── 幂等：同课程不重复生成预警 ───────────────────────────────


def test_alert_idempotent(client, actor_set):
    """同一课程同一类型只生成一条 open 预警（幂等）。"""
    H_admin, H_ther, pid, tid, rid = actor_set

    cid = _create_course(client, H_admin, pid, tid, rid, day_offset=43)

    async def _gen_and_count():
        async with SessionLocal() as db:
            course = (
                await db.execute(select(Course).where(Course.id == cid))
            ).scalar_one()
            patient = (
                await db.execute(select(Patient).where(Patient.id == course.patient_id))
            ).scalar_one()
            await create_course_overdue_alert(db, course, patient, "test_therapist")
            await create_course_overdue_alert(db, course, patient, "test_therapist")
            await db.commit()

            from sqlalchemy import func

            count = (
                await db.execute(
                    select(func.count()).where(
                        Alert.ref_course_id == cid,
                        Alert.alert_type == "course_overdue",
                        Alert.status == "open",
                    )
                )
            ).scalar_one()
            return count

    count = asyncio.run(_gen_and_count())
    assert count == 1, f"should be exactly 1 open alert, got {count}"


# ── 一键提醒 → 写 notice + 状态流转 ──────────────────────────


def test_remind_creates_notifications_and_transitions(client, actor_set):
    """一键提醒：写 notifications → 课程→reminded + 患者→en_route。"""
    H_admin, H_ther, pid, tid, rid = actor_set

    cid = _create_course(client, H_admin, pid, tid, rid, day_offset=44)

    # 一键提醒
    r = client.post(f"/api/v1/courses/{cid}/remind", headers=H_ther)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "reminded"

    # 验证课程状态
    async def _check():
        async with SessionLocal() as db:
            course = (
                await db.execute(select(Course).where(Course.id == cid))
            ).scalar_one()
            return course.status

    status = asyncio.run(_check())
    assert status == "reminded", f"course status should be reminded, got {status}"

    # 验证患者状态
    async def _check_patient():
        async with SessionLocal() as db:
            course = (
                await db.execute(select(Course).where(Course.id == cid))
            ).scalar_one()
            patient = (
                await db.execute(
                    select(Patient).where(Patient.id == course.patient_id)
                )
            ).scalar_one()
            return patient.status

    p_status = asyncio.run(_check_patient())
    assert p_status == "en_route", f"patient status should be en_route, got {p_status}"

    # 验证通知已写入
    r = client.get("/api/v1/notifications", headers=H_ther)
    assert r.status_code == 200
    items = r.json()["items"]
    reminder_items = [i for i in items if i["type"] in ("course_reminder", "course_reminder_therapist")]
    assert len(reminder_items) >= 1, "should have at least 1 reminder notification"


# ── 超时检测 → 预警 + 状态→abnormal ──────────────────────────


def test_overdue_detection_creates_alert(client, actor_set):
    """超时 5min：课程→abnormal + 生成 open 预警。

    通过直接调用 overdue 检测函数（而非等定时任务）验证核心逻辑。
    """
    from app.tasks.scheduler_tasks import _overdue_detection
    import asyncio as _aio

    H_admin, H_ther, pid, tid, rid = actor_set

    # 创建已过时的课程（start_at 是 15 分钟前）
    async def _create_past_course():
        from app.db.session import SessionLocal as _SL

        async with _SL() as db:
            from app.models.models import Course as _C

            now = datetime.now(timezone.utc)
            past = now - timedelta(minutes=20)
            end_past = now - timedelta(minutes=5)
            course = _C(
                patient_id=pid,
                therapist_id=tid,
                room_id=rid,
                course_type="PT",
                start_at=past,
                end_at=end_past,
                status="scheduled",
            )
            db.add(course)
            await db.commit()
            await db.refresh(course)
            return course.id

    cid = _aio.run(_create_past_course())

    # 执行超时检测
    _aio.run(_overdue_detection())

    # 验证课程状态
    async def _check():
        async with SessionLocal() as db:
            course = (
                await db.execute(select(Course).where(Course.id == cid))
            ).scalar_one()
            return course.status

    status = _aio.run(_check())
    assert status == "abnormal", f"course should be abnormal, got {status}"

    # 验证预警已生成
    async def _check_alert():
        async with SessionLocal() as db:
            from sqlalchemy import exists as _ex

            has_alert = await db.execute(
                select(_ex().where(
                    Alert.ref_course_id == cid,
                    Alert.alert_type == "course_overdue",
                    Alert.status == "open",
                ))
            )
            return has_alert.scalar_one()

    has_alert = _aio.run(_check_alert())
    assert has_alert, "should have an open course_overdue alert"
