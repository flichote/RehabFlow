"""权限隔离测试：401 未登录 / 403 角色无权 / 数据范围（康复师只能操作自己课程）。

依据：architecture.md §4.4 数据权限隔离 + api.md §10 权限标注 + AC-QA-04。
"""
from __future__ import annotations

import asyncio

from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.models import Course, Patient, Therapist

from tests.conftest import auth_headers, course_body, make_time, register_and_login, seed_ids


def _admin_headers(client):
    tok, _, _ = register_and_login(client, "admin")
    return auth_headers(tok)


def _create_course(client, headers, pid, tid, rid, day_offset=30, hour=9):
    start = make_time(day_offset=day_offset, hour=hour)
    end = make_time(day_offset=day_offset, hour=hour, minute=45)
    r = client.post("/api/v1/courses", json=course_body(pid, tid, rid, start, end), headers=headers)
    assert r.status_code == 201, r.text
    return r.json()["id"]


# ── 401：未登录访问受保护路由 ───────────────────────────────────────


def test_unauthenticated_protected_routes_401(client):
    """未登录访问受保护路由 → 401（AC-QA-04）。"""
    # auth/me
    r = client.get("/api/v1/auth/me")
    assert r.status_code == 401
    # 创建课程（admin-only，但未登录先过 401）
    pid, tid, rid = seed_ids()
    start = make_time(day_offset=31, hour=9)
    end = make_time(day_offset=31, hour=10)
    r = client.post("/api/v1/courses", json=course_body(pid, tid, rid, start, end))
    assert r.status_code == 401


# ── 403：角色无权访问 admin-only ───────────────────────────────────


def test_patient_access_admin_route_403(client):
    """患者访问 /admin 范围（创建课程为 admin-only）→ 403。"""
    pid, tid, rid = seed_ids()
    tok, _, _ = register_and_login(client, "patient")
    start = make_time(day_offset=32, hour=9)
    end = make_time(day_offset=32, hour=10)
    r = client.post(
        "/api/v1/courses",
        json=course_body(pid, tid, rid, start, end),
        headers=auth_headers(tok),
    )
    assert r.status_code == 403


def test_therapist_access_admin_route_403(client):
    """康复师访问 admin-only（创建课程）→ 403。"""
    pid, tid, rid = seed_ids()
    tok, _, _ = register_and_login(client, "therapist")
    start = make_time(day_offset=33, hour=9)
    end = make_time(day_offset=33, hour=10)
    r = client.post(
        "/api/v1/courses",
        json=course_body(pid, tid, rid, start, end),
        headers=auth_headers(tok),
    )
    assert r.status_code == 403


def test_doctor_access_admin_route_403(client):
    """医生访问 admin-only（创建课程）→ 403。"""
    pid, tid, rid = seed_ids()
    tok, _, _ = register_and_login(client, "doctor")
    start = make_time(day_offset=34, hour=9)
    end = make_time(day_offset=34, hour=10)
    r = client.post(
        "/api/v1/courses",
        json=course_body(pid, tid, rid, start, end),
        headers=auth_headers(tok),
    )
    assert r.status_code == 403


# ── 403：课程执行数据范围（康复师只能操作自己名下课程） ───────────────


def test_therapist_cannot_start_other_therapists_course_403(client):
    """康复师试图开始「非自己名下」课程 → 403（architecture §4.4 行级过滤）。"""
    pid, tid, rid = seed_ids()  # tid = 张伟（种子 pt_zhang）
    H = _admin_headers(client)
    cid = _create_course(client, H, pid, tid, rid)

    # 用另一个康复师账号（ot_li → 李娜）登录，尝试开始张伟的课程
    r = client.post("/api/v1/auth/login", json={"username": "ot_li", "password": "admin123"})
    assert r.status_code == 200
    H_other = auth_headers(r.json()["access_token"])

    r = client.post(f"/api/v1/courses/{cid}/start", headers=H_other)
    assert r.status_code == 403, (
        f"非名下课程 start 应 403，实际 {r.status_code}；响应：{r.text}"
    )


def test_own_therapist_can_start_200(client, actor_set):
    """康复师可开始自己名下课程 → 200（对照正例）。"""
    H_admin, H_ther, pid, tid, rid = actor_set
    cid = _create_course(client, H_admin, pid, tid, rid)

    r = client.post(f"/api/v1/courses/{cid}/start", headers=H_ther)
    assert r.status_code == 200, f"名下课程 start 应 200，实际 {r.status_code}；响应：{r.text}"


def test_admin_can_start_any_course_200(client, actor_set):
    """管理员可开始任意课程 → 200。"""
    H_admin, _, pid, tid, rid = actor_set
    cid = _create_course(client, H_admin, pid, tid, rid)

    r = client.post(f"/api/v1/courses/{cid}/start", headers=H_admin)
    assert r.status_code == 200, f"管理员 start 应 200，实际 {r.status_code}；响应：{r.text}"
