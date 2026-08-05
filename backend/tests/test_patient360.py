"""Patient 360° API tests: overview, assessments CRUD, trend, permissions.

Tests verify:
- Overview includes location + time axis (courses) + weekly distribution
- Assessments CRUD: list, create, trend
- Data permission: doctor can only access own patients (404)
- Role permission: only therapist can create assessments (403)
"""

from __future__ import annotations

from datetime import datetime, timezone

from tests.conftest import (
    auth_headers,
    course_body,
    make_time,
    register_and_login,
    seed_ids,
)


def _admin_h(client):
    tok, _, _ = register_and_login(client, "admin")
    return auth_headers(tok)


def _doctor_h(client):
    tok, _, _ = register_and_login(client, "doctor")
    return auth_headers(tok)


def _therapist_h(client):
    tok, _, _ = register_and_login(client, "therapist")
    return auth_headers(tok)


def _get_seed_patient_id():
    """Get seed patient '陈明' ID."""
    return seed_ids()[0]


def _setup_patient_therapist_link(client, admin_h, pid, tid):
    """Link a patient to a therapist by updating the patient via SQL.

    Uses a raw approach: we update the patient's therapist_id directly through
    the seed/init path since there's no PUT /patients endpoint yet.
    """
    import asyncio

    from sqlalchemy import update

    from app.db.session import SessionLocal
    from app.models.models import Patient

    async def _link():
        async with SessionLocal() as s:
            stmt = (
                update(Patient)
                .where(Patient.id == pid)
                .values(therapist_id=tid)
            )
            await s.execute(stmt)
            await s.commit()

    asyncio.run(_link())


# ── Overview tests ───────────────────────────────────────────────────


def test_overview_structure(client):
    """Patient overview returns correct structure with location + courses + weekly."""
    H_admin = _admin_h(client)
    pid = _get_seed_patient_id()

    r = client.get(f"/api/v1/patients/{pid}/overview", headers=H_admin)
    assert r.status_code == 200, r.text
    body = r.json()

    # Basic info
    assert body["id"] == pid
    assert body["name"] == "陈明"
    assert "status" in body
    assert "ward_location" in body
    assert "doctor_name" in body
    assert "therapist_name" in body

    # Current location (from status log)
    assert "current_location" in body
    assert "current_status" in body

    # Course time axis
    assert "courses" in body
    assert isinstance(body["courses"], list)

    # Weekly distribution (7 days)
    assert "weekly_distribution" in body
    assert isinstance(body["weekly_distribution"], list)
    assert len(body["weekly_distribution"]) == 7


def test_overview_current_location_from_status_log(client):
    """Current location should come from the latest patient_status_log."""
    H_admin = _admin_h(client)
    pid = _get_seed_patient_id()

    r = client.get(f"/api/v1/patients/{pid}/overview", headers=H_admin)
    assert r.status_code == 200
    body = r.json()
    # Seed creates status log with ward_location
    assert body["current_location"] is not None
    assert body["current_status"] == "ward"


def test_overview_includes_courses(client, actor_set):
    """After creating a course, it should appear in the overview's time axis."""
    H_admin, _, pid, tid, rid = actor_set

    # Create a course
    start = make_time(day_offset=70, hour=9)
    end = make_time(day_offset=70, hour=9, minute=45)
    r = client.post(
        "/api/v1/courses",
        json=course_body(pid, tid, rid, start, end),
        headers=H_admin,
    )
    assert r.status_code == 201, r.text
    cid = r.json()["id"]

    # Check overview
    r = client.get(f"/api/v1/patients/{pid}/overview", headers=H_admin)
    assert r.status_code == 200
    body = r.json()
    courses = body["courses"]
    course_ids = [c["course_id"] for c in courses]
    assert cid in course_ids, f"Course {cid} should be in patient overview"


def test_overview_weekly_distribution(client, actor_set):
    """Weekly distribution should have 7 daily counts."""
    H_admin, _, pid, _, _ = actor_set

    r = client.get(f"/api/v1/patients/{pid}/overview", headers=H_admin)
    assert r.status_code == 200
    body = r.json()
    dist = body["weekly_distribution"]
    assert len(dist) == 7
    for day in dist:
        assert "date" in day
        assert "count" in day
        assert isinstance(day["count"], int)
        assert day["count"] >= 0


# ── Assessments CRUD tests ──────────────────────────────────────────

# For assessment tests, use seed data to get already-linked patient+therapist:
#   - 陈明 (seed patient) is assigned to 张伟 (pt_zhang, therapist)
#   - Login as pt_zhang to create assessments for 陈明
SEED_PATIENT_NAME = "陈明"


def _login_as_seed_therapist(client):
    """Login as pt_zhang (therapist assigned to 陈明)."""
    r = client.post(
        "/api/v1/auth/login",
        json={"username": "pt_zhang", "password": "admin123"},
    )
    assert r.status_code == 200, r.text
    return auth_headers(r.json()["access_token"])


def _login_as_seed_doctor(client):
    """Login as dr_zhao (doctor assigned to 陈明)."""
    r = client.post(
        "/api/v1/auth/login",
        json={"username": "dr_zhao", "password": "admin123"},
    )
    assert r.status_code == 200, r.text
    return auth_headers(r.json()["access_token"])


def test_assessments_list_empty(client):
    """New patient (no assessments yet) should have empty list."""
    H_admin = _admin_h(client)
    pid = _get_seed_patient_id()

    r = client.get(f"/api/v1/patients/{pid}/assessments", headers=H_admin)
    assert r.status_code == 200, r.text
    body = r.json()
    # Just check the structure; may or may not have assessments
    assert "total" in body
    assert "items" in body


def test_assessments_create_and_list(client):
    """Create an assessment and verify it appears in the list."""
    H_admin = _admin_h(client)
    H_ther = _login_as_seed_therapist(client)
    pid = _get_seed_patient_id()

    # Create assessment
    now = datetime.now(timezone.utc)
    body = {
        "assess_type": "Fugl-Meyer",
        "score": 45.5,
        "detail": {"upper_extremity": 20, "lower_extremity": 25.5},
        "assessed_at": now.isoformat(),
    }
    r = client.post(
        f"/api/v1/patients/{pid}/assessments",
        json=body,
        headers=H_ther,
    )
    assert r.status_code == 201, r.text
    created = r.json()
    assert created["assess_type"] == "Fugl-Meyer"
    assert created["score"] == 45.5
    assert created["detail"] == {"upper_extremity": 20, "lower_extremity": 25.5}
    assert created["assessor_name"] is not None

    # List assessments
    r = client.get(f"/api/v1/patients/{pid}/assessments", headers=H_admin)
    assert r.status_code == 200
    body = r.json()
    assert body["total"] >= 1
    types = [item["assess_type"] for item in body["items"]]
    assert "Fugl-Meyer" in types


def test_assessments_sorted_desc(client):
    """Assessment list should be sorted by assessed_at descending."""
    H_admin = _admin_h(client)
    H_ther = _login_as_seed_therapist(client)
    pid = _get_seed_patient_id()

    # Create two assessments — older first
    t1 = datetime(2026, 1, 1, 10, 0, tzinfo=timezone.utc)
    t2 = datetime(2026, 6, 1, 10, 0, tzinfo=timezone.utc)

    r1 = client.post(
        f"/api/v1/patients/{pid}/assessments",
        json={"assess_type": "Barthel", "score": 60, "assessed_at": t1.isoformat()},
        headers=H_ther,
    )
    assert r1.status_code == 201

    r2 = client.post(
        f"/api/v1/patients/{pid}/assessments",
        json={"assess_type": "Barthel", "score": 75, "assessed_at": t2.isoformat()},
        headers=H_ther,
    )
    assert r2.status_code == 201

    # List
    r = client.get(f"/api/v1/patients/{pid}/assessments", headers=H_admin)
    assert r.status_code == 200
    items = r.json()["items"]
    # Find the two Barthel items (there may be others from other tests)
    barthel_items = [it for it in items if it["assess_type"] == "Barthel"]
    assert len(barthel_items) >= 2
    # Newest first
    assert barthel_items[0]["score"] >= barthel_items[1]["score"]


# ── Assessment trend tests ──────────────────────────────────────────


def test_assessment_trend_returns_correct_type(client):
    """Trend endpoint filters by assess_type and returns ascending order."""
    H_admin = _admin_h(client)
    H_ther = _login_as_seed_therapist(client)
    pid = _get_seed_patient_id()

    # Create Fugl-Meyer assessments at different times
    t1 = datetime(2026, 2, 1, 10, 0, tzinfo=timezone.utc)
    t2 = datetime(2026, 4, 1, 10, 0, tzinfo=timezone.utc)
    t3 = datetime(2026, 7, 1, 10, 0, tzinfo=timezone.utc)

    for t, score in [(t1, 30), (t2, 50), (t3, 70)]:
        r = client.post(
            f"/api/v1/patients/{pid}/assessments",
            json={
                "assess_type": "Fugl-Meyer-Trend",
                "score": score,
                "assessed_at": t.isoformat(),
            },
            headers=H_ther,
        )
        assert r.status_code == 201

    # Also create a different type
    r = client.post(
        f"/api/v1/patients/{pid}/assessments",
        json={
            "assess_type": "Barthel-Trend",
            "score": 80,
            "assessed_at": datetime(2026, 5, 1, 10, 0, tzinfo=timezone.utc).isoformat(),
        },
        headers=H_ther,
    )
    assert r.status_code == 201

    # Get Fugl-Meyer-Trend trend
    r = client.get(
        f"/api/v1/patients/{pid}/assessments/trend?type=Fugl-Meyer-Trend",
        headers=H_admin,
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["patient_id"] == pid
    assert body["assess_type"] == "Fugl-Meyer-Trend"
    items = body["items"]
    assert len(items) == 3
    # Ascending order
    assert items[0]["score"] == 30
    assert items[1]["score"] == 50
    assert items[2]["score"] == 70


def test_assessment_trend_empty_for_no_data(client):
    """Trend endpoint returns empty list when no data for that type."""
    H_admin = _admin_h(client)
    pid = _get_seed_patient_id()

    r = client.get(
        f"/api/v1/patients/{pid}/assessments/trend?type=NonExistentType999",
        headers=H_admin,
    )
    assert r.status_code == 200
    body = r.json()
    assert body["items"] == []


# ── Permission tests ────────────────────────────────────────────────


def test_doctor_sees_own_patients_200(client):
    """Doctor should be able to access their own patients."""
    # Seed patient 陈明 is assigned to doctor 赵建国 (dr_zhao)
    pid = _get_seed_patient_id()

    # Login as dr_zhao
    r = client.post(
        "/api/v1/auth/login",
        json={"username": "dr_zhao", "password": "admin123"},
    )
    assert r.status_code == 200
    H_dr = auth_headers(r.json()["access_token"])

    r = client.get(f"/api/v1/patients/{pid}/overview", headers=H_dr)
    assert r.status_code == 200, f"Doctor should see own patient, got {r.status_code}"


def test_doctor_cannot_see_other_doctors_patients_404(client, actor_set):
    """Doctor accessing a patient not assigned to them → 404."""
    H_admin, _, pid, _, _ = actor_set  # pid from actor_set, NOT assigned to dr_zhao

    # Login as dr_zhao (seed doctor, assigned to 陈明/刘芳/周涛, NOT actor_set patient)
    r = client.post(
        "/api/v1/auth/login",
        json={"username": "dr_zhao", "password": "admin123"},
    )
    assert r.status_code == 200
    H_dr = auth_headers(r.json()["access_token"])

    r = client.get(f"/api/v1/patients/{pid}/overview", headers=H_dr)
    assert r.status_code == 404, (
        f"Doctor should get 404 for non-assigned patient, got {r.status_code}"
    )


def test_therapist_only_can_create_assessment(client, actor_set):
    """Only therapist role can POST /patients/{id}/assessments (403 for others)."""
    H_admin, _, pid, _, _ = actor_set

    body = {
        "assess_type": "Fugl-Meyer",
        "score": 50,
        "assessed_at": datetime.now(timezone.utc).isoformat(),
    }

    # Admin cannot create assessments
    r = client.post(
        f"/api/v1/patients/{pid}/assessments",
        json=body,
        headers=H_admin,
    )
    assert r.status_code == 403, f"Admin should get 403, got {r.status_code}"


def test_unauthenticated_overview_401(client):
    """Unauthenticated access to patient overview → 401."""
    pid = _get_seed_patient_id()
    r = client.get(f"/api/v1/patients/{pid}/overview")
    assert r.status_code == 401


def test_doctor_accesses_assessments_200(client):
    """Doctor can list assessments for their own patients."""
    # dr_zhao → 陈明
    pid = _get_seed_patient_id()
    H_dr = _login_as_seed_doctor(client)

    r = client.get(f"/api/v1/patients/{pid}/assessments", headers=H_dr)
    assert r.status_code == 200


# ── M3 软打卡：overview 当前位置/状态随开始/结束流转 ─────────────────────

def test_overview_location_treating_after_start(client, actor_set):
    """软打卡：开始上课后 overview 当前位置=治疗室、状态=治疗中（PRD §3.3 实时位置卡）。"""
    H_admin, H_ther, pid, tid, rid = actor_set

    start = make_time(day_offset=100, hour=9)
    end = make_time(day_offset=100, hour=9, minute=45)
    r = client.post(
        "/api/v1/courses",
        json=course_body(pid, tid, rid, start, end),
        headers=H_admin,
    )
    assert r.status_code == 201, r.text
    cid = r.json()["id"]

    r = client.post(f"/api/v1/courses/{cid}/start", headers=H_ther)
    assert r.status_code == 200, r.text

    body = client.get(f"/api/v1/patients/{pid}/overview", headers=H_admin).json()
    assert body["current_status"] == "treating", body
    assert body["current_location"] == "PT大厅", body


def test_overview_location_ward_after_finish(client, actor_set):
    """软打卡：结束上课后 overview 当前位置=病房(ward_location)、状态=在病房（flows.md 速查表）。"""
    import asyncio as _aio

    from sqlalchemy import update as _update

    from app.db.session import SessionLocal as _SL
    from app.models.models import Patient as _Patient

    H_admin, H_ther, pid, tid, rid = actor_set

    async def _set_ward():
        async with _SL() as s:
            await s.execute(
                _update(_Patient).where(_Patient.id == pid).values(ward_location="住院部3楼5床")
            )
            await s.commit()

    _aio.run(_set_ward())

    start = make_time(day_offset=110, hour=9)
    end = make_time(day_offset=110, hour=9, minute=45)
    r = client.post(
        "/api/v1/courses",
        json=course_body(pid, tid, rid, start, end),
        headers=H_admin,
    )
    assert r.status_code == 201, r.text
    cid = r.json()["id"]

    assert client.post(f"/api/v1/courses/{cid}/start", headers=H_ther).status_code == 200
    assert client.post(f"/api/v1/courses/{cid}/finish", headers=H_ther).status_code == 200

    body = client.get(f"/api/v1/patients/{pid}/overview", headers=H_admin).json()
    assert body["current_status"] == "ward", body
    assert body["current_location"] == "住院部3楼5床", body


# ── M3 权限：患者 403 / 非责任康复师 404（三角色覆盖） ────────────────────

def test_patient_cannot_access_overview_403(client):
    """患者角色访问 overview → 403（require_role doctor/therapist/admin）。"""
    pid = _get_seed_patient_id()
    tok, _, _ = register_and_login(client, "patient")
    H = auth_headers(tok)

    r = client.get(f"/api/v1/patients/{pid}/overview", headers=H)
    assert r.status_code == 403, r.text


def test_therapist_cannot_see_unassigned_patient_404(client, actor_set):
    """数据权限：非责任康复师查看患者 overview → 404（架构 §4.4 行级隔离）。"""
    _, _, pid, _, _ = actor_set
    tok, _, _ = register_and_login(client, "therapist")
    H_other = auth_headers(tok)

    r = client.get(f"/api/v1/patients/{pid}/overview", headers=H_other)
    assert r.status_code == 404, r.text


def test_unassigned_therapist_cannot_create_assessment_404(client, actor_set):
    """数据权限：非责任康复师创建评估 → 404。"""
    _, _, pid, _, _ = actor_set
    tok, _, _ = register_and_login(client, "therapist")
    H_other = auth_headers(tok)

    body = {
        "assess_type": "Fugl-Meyer",
        "score": 40,
        "assessed_at": datetime.now(timezone.utc).isoformat(),
    }
    r = client.post(
        f"/api/v1/patients/{pid}/assessments", json=body, headers=H_other
    )
    assert r.status_code == 404, r.text


def test_assessment_update_delete_not_implemented(client, actor_set):
    """API 面核查：评估记录无 PUT/DELETE 路由。

    任务体写「评估 CRUD」，但 api.md §2 与实现均只有 list/create/trend；
    PUT/DELETE 返回 404（路由不存在）→ 记为 ⚪ 疑问，建议与 rf-arch 确认。
    """
    H_admin, _, pid, _, _ = actor_set

    r_put = client.put(
        f"/api/v1/patients/{pid}/assessments/1",
        json={"score": 99},
        headers=H_admin,
    )
    r_del = client.delete(
        f"/api/v1/patients/{pid}/assessments/1", headers=H_admin
    )
    assert r_put.status_code == 404, r_put.text
    assert r_del.status_code == 404, r_del.text
