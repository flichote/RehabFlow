"""排课冲突检测测试：患者冲突 / 康复师冲突 / 无冲突 / 15min 粒度。

依据：api.md §11（409 冲突带明细）+ m1-acceptance AC-QA-02。
时间参数按 api.md 约定一律 ISO8601（UTC）。
"""
from __future__ import annotations

from tests.conftest import auth_headers, course_body, make_time, register_and_login, seed_ids


def _admin_headers(client):
    tok, _, _ = register_and_login(client, "admin")
    return auth_headers(tok)


def test_create_course_no_conflict_201(client):
    """无冲突 → 201，状态 scheduled，患者状态不变（裁决-1：无「待排课」状态）。"""
    pid, tid, rid = seed_ids()
    H = _admin_headers(client)
    start = make_time(day_offset=10, hour=9)
    end = make_time(day_offset=10, hour=10)
    r = client.post("/api/v1/courses", json=course_body(pid, tid, rid, start, end), headers=H)
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["status"] == "scheduled"
    assert body["patient_id"] == pid
    assert body["therapist_id"] == tid
    assert body["actual_start_at"] is None


def test_patient_conflict_same_time_409(client):
    """同一患者同一时段两节课 → 409，响应体带冲突明细（api.md §11）。"""
    pid, tid, rid = seed_ids()
    H = _admin_headers(client)
    start = make_time(day_offset=11, hour=9)
    end = make_time(day_offset=11, hour=9, minute=45)
    body = course_body(pid, tid, rid, start, end)

    r1 = client.post("/api/v1/courses", json=body, headers=H)
    assert r1.status_code == 201, r1.text

    r2 = client.post("/api/v1/courses", json=body, headers=H)
    assert r2.status_code == 409, (
        f"同一患者同一时段应 409，实际 {r2.status_code}；响应：{r2.text}"
    )
    detail = r2.json()["detail"]
    assert detail["error"] == "patient_conflict"
    assert len(detail["conflicts"]) >= 1
    assert "conflicting_course_id" in detail["conflicts"][0]


def test_therapist_conflict_same_time_409(client):
    """同一康复师同一时段（不同患者）→ 409。"""
    pid, tid, rid = seed_ids()
    H = _admin_headers(client)
    start = make_time(day_offset=12, hour=9)
    end = make_time(day_offset=12, hour=10)
    body = course_body(pid, tid, rid, start, end)

    r1 = client.post("/api/v1/courses", json=body, headers=H)
    assert r1.status_code == 201, r1.text

    # 换一个患者（种子：刘芳），同一康复师同时段
    import asyncio
    from sqlalchemy import select
    from app.db.session import SessionLocal
    from app.models.models import Patient

    async def _patient2_id():
        async with SessionLocal() as s:
            p = (await s.execute(select(Patient).where(Patient.name == "刘芳"))).scalar_one()
            return p.id
    pid2 = asyncio.run(_patient2_id())

    body2 = course_body(pid2, tid, rid, start, end)
    r2 = client.post("/api/v1/courses", json=body2, headers=H)
    assert r2.status_code == 409, f"同一康复师同时段应 409，实际 {r2.status_code}；响应：{r2.text}"
    detail = r2.json()["detail"]
    assert detail["error"] == "therapist_conflict"


def test_patient_different_time_no_conflict_201(client):
    """同一患者不同时段 → 201（不误报）。"""
    pid, tid, rid = seed_ids()
    H = _admin_headers(client)
    start = make_time(day_offset=13, hour=9)
    end = make_time(day_offset=13, hour=10)
    r1 = client.post("/api/v1/courses", json=course_body(pid, tid, rid, start, end), headers=H)
    assert r1.status_code == 201

    # 下午另一时段
    start2 = make_time(day_offset=13, hour=14)
    end2 = make_time(day_offset=13, hour=15)
    r2 = client.post("/api/v1/courses", json=course_body(pid, tid, rid, start2, end2), headers=H)
    assert r2.status_code == 201, f"不同时段应 201，实际 {r2.status_code}；响应：{r2.text}"


def test_course_15min_granularity_422(client):
    """start_at 非 15min 对齐 → 422（api.md §11）。"""
    pid, tid, rid = seed_ids()
    H = _admin_headers(client)
    start = make_time(day_offset=14, hour=9, minute=7)  # 9:07 非法
    end = make_time(day_offset=14, hour=10)
    r = client.post("/api/v1/courses", json=course_body(pid, tid, rid, start, end), headers=H)
    assert r.status_code == 422, f"非 15min 粒度应 422，实际 {r.status_code}；响应：{r.text}"


def test_course_end_before_start_422(client):
    """end_at <= start_at → 422。"""
    pid, tid, rid = seed_ids()
    H = _admin_headers(client)
    start = make_time(day_offset=15, hour=10)
    end = make_time(day_offset=15, hour=9)  # 早于 start
    r = client.post("/api/v1/courses", json=course_body(pid, tid, rid, start, end), headers=H)
    assert r.status_code == 422


def test_create_course_requires_admin_403(client):
    """非管理员创建课程 → 403（权限前置，见 test_permissions 详测）。"""
    pid, tid, rid = seed_ids()
    tok, _, _ = register_and_login(client, "patient")
    start = make_time(day_offset=16, hour=9)
    end = make_time(day_offset=16, hour=10)
    r = client.post(
        "/api/v1/courses",
        json=course_body(pid, tid, rid, start, end),
        headers=auth_headers(tok),
    )
    assert r.status_code == 403
