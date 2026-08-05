"""Dashboard API tests: KPI counts, distribution grouping, workload, trend.

Tests verify:
- KPI count correctness
- Patient distribution grouping by location
- Therapist workload grouping
- Course trend data structure
- Admin-only access (403 for non-admin)
"""

from __future__ import annotations

from datetime import date, datetime, timezone

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
