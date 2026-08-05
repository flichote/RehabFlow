"""课程状态机 + 患者软打卡状态机测试。

依据：flows.md 状态速查表（排课→scheduled；开始→ongoing+treating+治疗室；
结束→completed+ward+病房）+ api.md §10 对照表 + m1-acceptance AC-QA-03。

注意（裁决-1）：排课成功不改变患者状态，不得断言「待排课」。
每个测试使用独立 patient/therapist（actor_set fixture），互不污染。
"""
from __future__ import annotations

import asyncio

from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.models import Course, CourseStatusLog, Patient, PatientStatusLog

from tests.conftest import course_body, make_time


def _create_course(client, headers, pid, tid, rid, day_offset=20, hour=9):
    start = make_time(day_offset=day_offset, hour=hour)
    end = make_time(day_offset=day_offset, hour=hour, minute=45)
    r = client.post("/api/v1/courses", json=course_body(pid, tid, rid, start, end), headers=headers)
    assert r.status_code == 201, r.text
    return r.json()["id"]


async def _get_course(course_id):
    async with SessionLocal() as s:
        return (await s.execute(select(Course).where(Course.id == course_id))).scalar_one()


async def _get_patient(patient_id):
    async with SessionLocal() as s:
        return (await s.execute(select(Patient).where(Patient.id == patient_id))).scalar_one()


async def _status_logs(course_id):
    async with SessionLocal() as s:
        return (
            await s.execute(
                select(CourseStatusLog).where(CourseStatusLog.course_id == course_id)
            )
        ).scalars().all()


async def _patient_logs(patient_id):
    async with SessionLocal() as s:
        return (
            await s.execute(
                select(PatientStatusLog)
                .where(PatientStatusLog.patient_id == patient_id)
                .order_by(PatientStatusLog.id)
            )
        ).scalars().all()


# ── 课程状态机（flows.md：待执行→进行中→已完成） ─────────────────────


def test_course_state_machine_scheduled_ongoing_completed(client, actor_set):
    """创建(scheduled)→开始(ongoing)→结束(completed)，记录实际起止时间。"""
    H_admin, H_ther, pid, tid, rid = actor_set
    cid = _create_course(client, H_admin, pid, tid, rid)

    # 创建后：scheduled
    c = asyncio.run(_get_course(cid))
    assert c.status == "scheduled"
    assert c.actual_start_at is None
    assert c.actual_end_at is None

    # 开始上课（本测试注册的康复师，名下课程）
    r = client.post(f"/api/v1/courses/{cid}/start", headers=H_ther)
    assert r.status_code == 200, f"start 失败：{r.status_code} {r.text}"
    body = r.json()
    assert body["status"] == "ongoing"
    assert body["actual_start_at"] is not None

    # 开始后：DB 持久化
    c = asyncio.run(_get_course(cid))
    assert c.status == "ongoing"
    assert c.actual_start_at is not None

    # 结束上课
    r = client.post(f"/api/v1/courses/{cid}/finish", headers=H_ther)
    assert r.status_code == 200, f"finish 失败：{r.status_code} {r.text}"
    body = r.json()
    assert body["status"] == "completed"
    assert body["actual_end_at"] is not None
    assert body["minutes_consumed"] is not None and body["minutes_consumed"] > 0

    c = asyncio.run(_get_course(cid))
    assert c.status == "completed"
    assert c.actual_end_at is not None


def test_start_requires_scheduled_only(client, actor_set):
    """非 scheduled 状态不能开始（flows.md：只有待执行可开始）→ 应 4xx 非 500。"""
    H_admin, H_ther, pid, tid, rid = actor_set
    cid = _create_course(client, H_admin, pid, tid, rid)

    r = client.post(f"/api/v1/courses/{cid}/start", headers=H_ther)
    assert r.status_code == 200

    # 重复 start → 后端应返回 4xx（409/400），而非 500 或未捕获 ValueError
    r = client.post(f"/api/v1/courses/{cid}/start", headers=H_ther)
    assert r.status_code in (400, 409), (
        f"重复 start 应 4xx，实际 {r.status_code}；响应：{r.text[:200]}"
    )


def test_finish_requires_ongoing_only(client, actor_set):
    """未开始（scheduled）不能结束 → 应 4xx 非 500。"""
    H_admin, H_ther, pid, tid, rid = actor_set
    cid = _create_course(client, H_admin, pid, tid, rid)

    r = client.post(f"/api/v1/courses/{cid}/finish", headers=H_ther)
    assert r.status_code in (400, 409), (
        f"scheduled 状态 finish 应 4xx，实际 {r.status_code}；响应：{r.text[:200]}"
    )


# ── 患者软打卡状态机（flows.md：开始→treating+治疗室；结束→ward+病房） ──


def test_patient_soft_checkin_treating_ward(client, actor_set):
    """开始上课→患者 treating + 位置=治疗室；结束→患者 ward + 位置=病房。"""
    H_admin, H_ther, pid, tid, rid = actor_set
    cid = _create_course(client, H_admin, pid, tid, rid)

    # 排课成功后患者状态不变（裁决-1：不得存在「待排课」）
    p0 = asyncio.run(_get_patient(pid))
    assert p0.status == "ward", f"排课成功患者状态应不变（ward），实际 {p0.status}"

    # 开始上课 → treating
    r = client.post(f"/api/v1/courses/{cid}/start", headers=H_ther)
    assert r.status_code == 200, r.text
    p = asyncio.run(_get_patient(pid))
    assert p.status == "treating", f"开始上课后患者应 treating，实际 {p.status}"

    # 最新一条 patient_status_log：location = 治疗室（PT大厅）
    logs = asyncio.run(_patient_logs(pid))
    last = logs[-1]
    assert last.to_status == "treating"
    assert last.location == "PT大厅"
    assert last.source == "course_action"

    # 结束上课 → ward
    r = client.post(f"/api/v1/courses/{cid}/finish", headers=H_ther)
    assert r.status_code == 200, f"finish 失败：{r.status_code} {r.text}"
    p = asyncio.run(_get_patient(pid))
    assert p.status == "ward", f"结束上课后患者应 ward，实际 {p.status}"

    logs = asyncio.run(_patient_logs(pid))
    last = logs[-1]
    assert last.to_status == "ward"
    assert last.location == "ward" or last.location == "住院部3楼5床"
    assert last.source == "course_action"


def test_status_logs_written(client, actor_set):
    """开始/结束均写 course_status_log 与 patient_status_log（AC-BE-07）。"""
    H_admin, H_ther, pid, tid, rid = actor_set
    cid = _create_course(client, H_admin, pid, tid, rid)

    r = client.post(f"/api/v1/courses/{cid}/start", headers=H_ther)
    assert r.status_code == 200
    r = client.post(f"/api/v1/courses/{cid}/finish", headers=H_ther)
    assert r.status_code == 200

    clog = asyncio.run(_status_logs(cid))
    assert len(clog) >= 2
    transitions = [(x.from_status, x.to_status) for x in clog]
    assert ("scheduled", "ongoing") in transitions
    assert ("ongoing", "completed") in transitions
    # actor 应为康复师用户
    for x in clog:
        assert x.actor_id is not None

    plog = asyncio.run(_patient_logs(pid))
    plog_trans = [(x.from_status, x.to_status, x.location) for x in plog]
    assert ("ward", "treating", "PT大厅") in plog_trans
    assert any(to == "ward" for _, to, _ in plog_trans)
