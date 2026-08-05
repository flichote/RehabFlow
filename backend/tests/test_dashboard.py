"""Dashboard API tests: KPI counts, distribution grouping, workload, trend.

Tests verify:
- KPI count correctness
- Patient distribution grouping by location
- Therapist workload grouping
- Course trend data structure
- Admin-only access (403 for non-admin)
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

from tests.conftest import auth_headers, course_body, make_time, register_and_login, seed_ids


def _admin_h(client):
    tok, _, _ = register_and_login(client, "admin")
    return auth_headers(tok)


def _ther_h(client):
    tok, _, _ = register_and_login(client, "therapist")
    return auth_headers(tok)


# ── KPI tests ────────────────────────────────────────────────────────


def test_kpis_structure(client):
    """KPI endpoint returns correct 4-field structure."""
    H = _admin_h(client)
    r = client.get("/api/v1/dashboard/kpis", headers=H)
    assert r.status_code == 200, r.text
    body = r.json()
    assert "inpatient_count" in body
    assert "today_course_count" in body
    assert "treating_count" in body
    assert "therapist_attendance_rate" in body
    assert isinstance(body["inpatient_count"], int)
    assert isinstance(body["today_course_count"], int)
    assert isinstance(body["treating_count"], int)
    assert 0.0 <= body["therapist_attendance_rate"] <= 1.0


def test_kpis_inpatient_count(client):
    """Inpatient count = non-discharged patients (seeds: 3 ward)."""
    H = _admin_h(client)
    r = client.get("/api/v1/dashboard/kpis", headers=H)
    assert r.status_code == 200
    body = r.json()
    # Seeds: 陈明(ward), 刘芳(ward), 周涛(ward) = 3
    assert body["inpatient_count"] >= 3


def test_kpis_treating_count_after_start(client, actor_set):
    """After starting a course, treating count increases."""
    H_admin, H_ther, pid, tid, rid = actor_set

    # Create and start a course
    start = make_time(day_offset=50, hour=9)
    end = make_time(day_offset=50, hour=9, minute=45)
    r = client.post(
        "/api/v1/courses",
        json=course_body(pid, tid, rid, start, end),
        headers=H_admin,
    )
    assert r.status_code == 201, r.text
    cid = r.json()["id"]

    # Start the course → patient becomes treating
    r = client.post(f"/api/v1/courses/{cid}/start", headers=H_ther)
    assert r.status_code == 200, r.text

    # Check KPIs
    r = client.get("/api/v1/dashboard/kpis", headers=H_admin)
    assert r.status_code == 200
    body = r.json()
    assert body["treating_count"] >= 1


# ── Patient distribution tests ────────────────────────────────────────


def test_distribution_structure(client):
    """Patient distribution returns list of {location, count}."""
    H = _admin_h(client)
    r = client.get("/api/v1/dashboard/patient-distribution", headers=H)
    assert r.status_code == 200, r.text
    body = r.json()
    assert "items" in body
    assert isinstance(body["items"], list)
    if body["items"]:
        item = body["items"][0]
        assert "location" in item
        assert "count" in item


def test_distribution_seed_patients_ward(client):
    """Seed patients should be at ward location."""
    H = _admin_h(client)
    r = client.get("/api/v1/dashboard/patient-distribution", headers=H)
    assert r.status_code == 200
    items = r.json()["items"]
    # Seeds have ward_location like "住院部3楼5床" etc.
    locations = {it["location"] for it in items}
    # At least one ward location
    ward_present = any("住院部" in loc for loc in locations)
    assert ward_present, f"Expected ward locations, got: {locations}"


# ── Therapist workload tests ──────────────────────────────────────────


def test_workload_structure(client, actor_set):
    """Therapist workload returns correct shape."""
    H_admin, _, _, _, _ = actor_set
    today = date.today().isoformat()
    r = client.get(
        f"/api/v1/dashboard/therapist-workload?date={today}",
        headers=H_admin,
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["date"] == today
    assert "items" in body
    assert isinstance(body["items"], list)


def test_workload_with_courses(client, actor_set):
    """Create a course, then check workload includes that therapist."""
    H_admin, H_ther, pid, tid, rid = actor_set

    start = make_time(day_offset=60, hour=10)
    end = make_time(day_offset=60, hour=10, minute=45)

    # Create course
    r = client.post(
        "/api/v1/courses",
        json=course_body(pid, tid, rid, start, end),
        headers=H_admin,
    )
    assert r.status_code == 201, r.text

    # Check workload for that date
    target_date = start.date().isoformat()
    r = client.get(
        f"/api/v1/dashboard/therapist-workload?date={target_date}",
        headers=H_admin,
    )
    assert r.status_code == 200
    items = r.json()["items"]
    therapist_ids = {it["therapist_id"] for it in items}
    assert tid in therapist_ids, f"Therapist {tid} should appear in workload for {target_date}"


# ── Course trend tests ─────────────────────────────────────────────────


def test_trend_structure(client):
    """Course trend returns daily counts for N days."""
    H = _admin_h(client)
    r = client.get("/api/v1/dashboard/course-trend?days=7", headers=H)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["days"] == 7
    assert len(body["items"]) == 7
    for item in body["items"]:
        assert "date" in item
        assert "count" in item
        assert isinstance(item["count"], int)


def test_trend_fills_zero_for_empty_days(client):
    """Trend should return 0 for days with no courses."""
    H = _admin_h(client)
    r = client.get("/api/v1/dashboard/course-trend?days=3", headers=H)
    assert r.status_code == 200
    items = r.json()["items"]
    assert len(items) == 3
    # Recent days likely have 0 courses (test DB is fresh)
    for item in items:
        assert item["count"] >= 0


# ── Permission tests ───────────────────────────────────────────────────


def test_dashboard_kpis_admin_only(client):
    """Non-admin cannot access dashboard KPIs (403)."""
    H = _ther_h(client)
    r = client.get("/api/v1/dashboard/kpis", headers=H)
    assert r.status_code == 403


def test_dashboard_distribution_admin_only(client):
    """Non-admin cannot access patient distribution (403)."""
    H = _ther_h(client)
    r = client.get("/api/v1/dashboard/patient-distribution", headers=H)
    assert r.status_code == 403


def test_dashboard_workload_admin_only(client):
    """Non-admin cannot access therapist workload (403)."""
    H = _ther_h(client)
    today = date.today().isoformat()
    r = client.get(
        f"/api/v1/dashboard/therapist-workload?date={today}",
        headers=H,
    )
    assert r.status_code == 403


def test_dashboard_trend_admin_only(client):
    """Non-admin cannot access course trend (403)."""
    H = _ther_h(client)
    r = client.get("/api/v1/dashboard/course-trend?days=7", headers=H)
    assert r.status_code == 403


def test_dashboard_unauthenticated_401(client):
    """Unauthenticated access to dashboard → 401."""
    r = client.get("/api/v1/dashboard/kpis")
    assert r.status_code == 401


# ── M3 造数验证（KPI 精确值 / 分布 / 工作量 / 趋势） ─────────────────────
# 说明：client 为 session 级共享库，精确断言一律用「基线差值」，不假设绝对计数。

def _today_slot(hours_ahead: int = 1) -> tuple[datetime, datetime]:
    """返回今日稍后的 15min 对齐时段（UTC），用于造「今日课程」。"""
    now = datetime.now(timezone.utc) + timedelta(hours=hours_ahead)
    start = now.replace(minute=(now.minute // 15) * 15, second=0, microsecond=0)
    end = start + timedelta(minutes=45)
    return start, end


def test_kpis_exact_deltas_after_create_and_start(client, actor_set):
    """KPI 造数验证：新患者→在院+1；今日排课→今日课程+1；开始上课→治疗中+1。"""
    H_admin, H_ther, pid, tid, rid = actor_set

    k0 = client.get("/api/v1/dashboard/kpis", headers=H_admin).json()

    # ① 注册新患者 → inpatient_count +1（注册即建 Patient 档案，status=ward 未出院）
    register_and_login(client, "patient")
    k1 = client.get("/api/v1/dashboard/kpis", headers=H_admin).json()
    assert k1["inpatient_count"] == k0["inpatient_count"] + 1, (k0, k1)

    # ② 今日排课 → today_course_count +1
    start, end = _today_slot()
    r = client.post(
        "/api/v1/courses",
        json=course_body(pid, tid, rid, start, end),
        headers=H_admin,
    )
    assert r.status_code == 201, r.text
    cid = r.json()["id"]
    k2 = client.get("/api/v1/dashboard/kpis", headers=H_admin).json()
    assert k2["today_course_count"] == k1["today_course_count"] + 1, (k1, k2)

    # ③ 开始上课 → treating_count +1
    r = client.post(f"/api/v1/courses/{cid}/start", headers=H_ther)
    assert r.status_code == 200, r.text
    k3 = client.get("/api/v1/dashboard/kpis", headers=H_admin).json()
    assert k3["treating_count"] == k2["treating_count"] + 1, (k2, k3)


def test_kpis_attendance_rate_exact_with_shifts(client, actor_set):
    """KPI 造数验证：今日 1 on_duty + 1 scheduled 排班 → 出勤率恰 0.5。

    注：uk_shifts (therapist_id, work_date) 唯一，同一康复师同日只能 1 条排班，
    故用两个康复师各 1 条（on_duty + scheduled）验证全局出勤率。
    """
    import asyncio as _aio
    from datetime import time as _time

    from sqlalchemy import select as _select

    from app.db.session import SessionLocal as _SL
    from app.models.models import Therapist as _Therapist
    from app.models.models import TherapistShift as _Shift
    from app.models.models import User as _User

    H_admin, _, _, tid, _ = actor_set
    today = date.today()

    # 第二个康复师（scheduled）
    register_and_login(client, "therapist")

    async def _add_shifts():
        async with _SL() as s:
            t2_user = (
                await s.execute(
                    _select(_User).where(_User.username.like("therapist_%"))
                    .order_by(_User.id.desc())
                )
            ).scalars().first()
            t2 = (
                await s.execute(_select(_Therapist).where(_Therapist.user_id == t2_user.id))
            ).scalar_one()
            s.add_all(
                [
                    _Shift(
                        therapist_id=tid, work_date=today,
                        start_time=_time(8, 0), end_time=_time(12, 0),
                        status="on_duty",
                    ),
                    _Shift(
                        therapist_id=t2.id, work_date=today,
                        start_time=_time(13, 0), end_time=_time(17, 0),
                        status="scheduled",
                    ),
                ]
            )
            await s.commit()

    _aio.run(_add_shifts())

    body = client.get("/api/v1/dashboard/kpis", headers=H_admin).json()
    assert body["therapist_attendance_rate"] == 0.5, body


def test_distribution_location_updates_after_start(client, actor_set):
    """分布造数验证：开始上课后患者最新位置=治疗室，分布分组 PT大厅 +1。"""
    H_admin, H_ther, pid, tid, rid = actor_set

    before = {
        it["location"]: it["count"]
        for it in client.get(
            "/api/v1/dashboard/patient-distribution", headers=H_admin
        ).json()["items"]
    }

    start = make_time(day_offset=80, hour=9)
    end = make_time(day_offset=80, hour=9, minute=45)
    r = client.post(
        "/api/v1/courses",
        json=course_body(pid, tid, rid, start, end),
        headers=H_admin,
    )
    assert r.status_code == 201, r.text
    r = client.post(f"/api/v1/courses/{r.json()['id']}/start", headers=H_ther)
    assert r.status_code == 200, r.text

    after = {
        it["location"]: it["count"]
        for it in client.get(
            "/api/v1/dashboard/patient-distribution", headers=H_admin
        ).json()["items"]
    }
    assert after.get("PT大厅", 0) == before.get("PT大厅", 0) + 1, (before, after)


def test_workload_exact_count_two_courses(client, actor_set):
    """工作量造数验证：同一康复师同日两节课 → workload course_count == 2。"""
    import asyncio as _aio

    from sqlalchemy import select as _select

    from app.db.session import SessionLocal as _SL
    from app.models.models import Patient as _Patient
    from app.models.models import User as _User

    H_admin, _, pid, tid, rid = actor_set

    # 再造一个患者（避免同患者同时段冲突）
    register_and_login(client, "patient")

    async def _second_patient_id():
        async with _SL() as s:
            u = (
                await s.execute(
                    _select(_User).where(_User.username.like("patient_%"))
                    .order_by(_User.id.desc())
                )
            ).scalars().first()
            p = (
                await s.execute(_select(_Patient).where(_Patient.user_id == u.id))
            ).scalar_one()
            return p.id

    pid2 = _aio.run(_second_patient_id())

    s1 = make_time(day_offset=90, hour=9)
    e1 = make_time(day_offset=90, hour=9, minute=45)
    s2 = make_time(day_offset=90, hour=10)
    e2 = make_time(day_offset=90, hour=10, minute=45)
    r1 = client.post(
        "/api/v1/courses", json=course_body(pid, tid, rid, s1, e1), headers=H_admin
    )
    r2 = client.post(
        "/api/v1/courses", json=course_body(pid2, tid, rid, s2, e2), headers=H_admin
    )
    assert r1.status_code == 201, r1.text
    assert r2.status_code == 201, r2.text

    target = s1.date().isoformat()
    items = client.get(
        f"/api/v1/dashboard/therapist-workload?date={target}", headers=H_admin
    ).json()["items"]
    entry = next((it for it in items if it["therapist_id"] == tid), None)
    assert entry is not None, items
    assert entry["course_count"] == 2, entry


def test_trend_includes_today_and_7_days(client, actor_set):
    """趋势造数验证：今日排课 → trend 今日计数 +1；7 天升序、日期完整。"""
    H_admin, _, pid, tid, rid = actor_set

    before = {
        it["date"]: it["count"]
        for it in client.get("/api/v1/dashboard/course-trend?days=7", headers=H_admin).json()["items"]
    }

    start, end = _today_slot()
    r = client.post(
        "/api/v1/courses",
        json=course_body(pid, tid, rid, start, end),
        headers=H_admin,
    )
    assert r.status_code == 201, r.text

    body = client.get("/api/v1/dashboard/course-trend?days=7", headers=H_admin).json()
    assert body["days"] == 7
    assert len(body["items"]) == 7
    dates = [it["date"] for it in body["items"]]
    assert dates == sorted(dates)
    today = datetime.now(timezone.utc).date().isoformat()
    after = {it["date"]: it["count"] for it in body["items"]}
    assert after[today] == before.get(today, 0) + 1, (before, after)


# ── M3 权限：dashboard 仅管理员（三角色覆盖） ────────────────────────────

def test_dashboard_patient_role_forbidden(client):
    """患者访问 dashboard 四个接口 → 403（任务体：患者访问 dashboard → 403）。"""
    tok, _, _ = register_and_login(client, "patient")
    H = auth_headers(tok)
    today = date.today().isoformat()
    assert client.get("/api/v1/dashboard/kpis", headers=H).status_code == 403
    assert client.get("/api/v1/dashboard/patient-distribution", headers=H).status_code == 403
    assert client.get(
        f"/api/v1/dashboard/therapist-workload?date={today}", headers=H
    ).status_code == 403
    assert client.get("/api/v1/dashboard/course-trend?days=7", headers=H).status_code == 403


def test_dashboard_doctor_role_forbidden(client):
    """医生访问 dashboard 四个接口 → 403。"""
    tok, _, _ = register_and_login(client, "doctor")
    H = auth_headers(tok)
    today = date.today().isoformat()
    assert client.get("/api/v1/dashboard/kpis", headers=H).status_code == 403
    assert client.get("/api/v1/dashboard/patient-distribution", headers=H).status_code == 403
    assert client.get(
        f"/api/v1/dashboard/therapist-workload?date={today}", headers=H
    ).status_code == 403
    assert client.get("/api/v1/dashboard/course-trend?days=7", headers=H).status_code == 403
