"""Query API tests: course list/detail, scheduler resources/pool, therapist schedule.

Each test verifies:
- Correct HTTP status codes
- Data permission isolation (therapist only sees own courses)
- Response schema correctness
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.models import Course
from tests.conftest import (
    auth_headers,
    course_body,
    make_time,
    register_and_login,
    seed_ids,
)


def _admin_headers(client):
    tok, _, _ = register_and_login(client, "admin")
    return auth_headers(tok)


def _therapist_headers(client):
    tok, _, _ = register_and_login(client, "therapist")
    return auth_headers(tok)


def _create_course(client, headers, pid, tid, rid, day_offset=50, hour=9):
    start = make_time(day_offset=day_offset, hour=hour)
    end = make_time(day_offset=day_offset, hour=hour, minute=45)
    r = client.post(
        "/api/v1/courses",
        json=course_body(pid, tid, rid, start, end),
        headers=headers,
    )
    assert r.status_code == 201, f"Create course failed: {r.status_code} {r.text}"
    return r.json()["id"]


# ── Course list ─────────────────────────────────────────────────────────


def test_admin_list_courses_200(client, actor_set):
    """Admin lists all courses → 200 with total and items."""
    H_admin, H_ther, pid, tid, rid = actor_set
    _create_course(client, H_admin, pid, tid, rid, day_offset=60)

    r = client.get("/api/v1/courses", headers=H_admin)
    assert r.status_code == 200, r.text
    body = r.json()
    assert "total" in body
    assert "items" in body
    assert body["total"] >= 1
    assert isinstance(body["items"], list)
    assert len(body["items"]) >= 1
    # Each item has required fields
    item = body["items"][0]
    for key in ("id", "patient_id", "therapist_id", "room_id", "course_type",
                "start_at", "end_at", "status"):
        assert key in item, f"Missing key: {key}"


def test_admin_can_filter_by_therapist_id(client, actor_set):
    """Admin filters courses by therapist_id → only matching courses."""
    H_admin, H_ther, pid, tid, rid = actor_set
    _create_course(client, H_admin, pid, tid, rid, day_offset=61)

    r = client.get(f"/api/v1/courses?therapist_id={tid}", headers=H_admin)
    assert r.status_code == 200, r.text
    body = r.json()
    for item in body["items"]:
        assert item["therapist_id"] == tid


def test_admin_can_filter_by_group(client, actor_set):
    """Admin filters courses by therapist group → only matching."""
    H_admin, H_ther, pid, tid, rid = actor_set
    _create_course(client, H_admin, pid, tid, rid, day_offset=62)

    r = client.get("/api/v1/courses?group=PT", headers=H_admin)
    assert r.status_code == 200, r.text
    body = r.json()
    for item in body["items"]:
        assert item["course_type"] == "PT"  # therapist is PT group


def test_admin_can_filter_by_room_id(client, actor_set):
    """Admin filters courses by room_id → only matching."""
    H_admin, H_ther, pid, tid, rid = actor_set
    _create_course(client, H_admin, pid, tid, rid, day_offset=63)

    r = client.get(f"/api/v1/courses?room_id={rid}", headers=H_admin)
    assert r.status_code == 200, r.text
    body = r.json()
    for item in body["items"]:
        assert item["room_id"] == rid


def test_admin_can_filter_by_date_range(client, actor_set):
    """Admin filters courses by date range (from/to)."""
    H_admin, H_ther, pid, tid, rid = actor_set
    _create_course(client, H_admin, pid, tid, rid, day_offset=64, hour=10)

    # from/to filter — use naive ISO format to avoid URL encoding issues
    start = "2030-03-12T09:00:00"
    end = "2030-03-12T12:00:00"

    r = client.get(
        f"/api/v1/courses?from={start}&to={end}",
        headers=H_admin,
    )
    assert r.status_code == 200, f"Filter by date range failed: {r.status_code} {r.text}"
    body = r.json()
    assert body["total"] >= 1


def test_therapist_only_sees_own_courses(client, actor_set):
    """Therapist lists courses → only their own courses (data permission)."""
    H_admin, H_ther, pid, tid, rid = actor_set
    _create_course(client, H_admin, pid, tid, rid, day_offset=65)

    r = client.get("/api/v1/courses", headers=H_ther)
    assert r.status_code == 200, r.text
    body = r.json()
    # Every course should belong to this therapist
    for item in body["items"]:
        assert item["therapist_id"] == tid, (
            f"Therapist should only see own courses, got therapist_id={item['therapist_id']}"
        )


# ── Course detail ───────────────────────────────────────────────────────


def test_admin_get_course_detail_200(client, actor_set):
    """Admin gets course detail → 200 with names."""
    H_admin, H_ther, pid, tid, rid = actor_set
    cid = _create_course(client, H_admin, pid, tid, rid, day_offset=70)

    r = client.get(f"/api/v1/courses/{cid}", headers=H_admin)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["id"] == cid
    assert body["patient_name"]  # should have patient name
    assert body["therapist_name"]  # should have therapist name
    assert body["room_name"]  # should have room name


def test_therapist_get_own_course_detail_200(client, actor_set):
    """Therapist gets own course detail → 200."""
    H_admin, H_ther, pid, tid, rid = actor_set
    cid = _create_course(client, H_admin, pid, tid, rid, day_offset=71)

    r = client.get(f"/api/v1/courses/{cid}", headers=H_ther)
    assert r.status_code == 200, r.text
    assert r.json()["id"] == cid


def test_therapist_cannot_get_other_course_detail(client):
    """Therapist cannot see another therapist's course detail → 403."""
    # Create course for seed therapist "张伟" (pt)
    pid, tid, rid = seed_ids()
    H_admin = _admin_headers(client)
    cid = _create_course(client, H_admin, pid, tid, rid, day_offset=72)

    # Another therapist (ot_li / 李娜) tries to access
    r = client.post(
        "/api/v1/auth/login",
        json={"username": "ot_li", "password": "admin123"},
    )
    assert r.status_code == 200
    H_other = auth_headers(r.json()["access_token"])

    r = client.get(f"/api/v1/courses/{cid}", headers=H_other)
    assert r.status_code == 403, (
        f"Should be 403 for other therapist, got {r.status_code}: {r.text}"
    )


def test_course_detail_404(client, actor_set):
    """Non-existent course → 404."""
    H_admin, _, _, _, _ = actor_set
    r = client.get("/api/v1/courses/99999", headers=H_admin)
    assert r.status_code == 404


# ── Scheduler resources ────────────────────────────────────────────────


def test_admin_get_resources_200(client):
    """Admin gets resource tree → 200 with therapists grouped and rooms."""
    H = _admin_headers(client)

    r = client.get("/api/v1/scheduler/resources", headers=H)
    assert r.status_code == 200, r.text
    body = r.json()
    assert "therapists" in body
    assert "rooms" in body
    assert isinstance(body["therapists"], dict)
    # Groups should exist
    for group in ("PT", "OT", "ST"):
        assert group in body["therapists"], f"Missing group: {group}"
        assert isinstance(body["therapists"][group], list)
    # Rooms should have items
    assert isinstance(body["rooms"], list)
    assert len(body["rooms"]) >= 1
    for room in body["rooms"]:
        for key in ("id", "name", "room_type", "is_active"):
            assert key in room, f"Room missing key: {key}"


def test_non_admin_cannot_access_resources(client, actor_set):
    """Therapist cannot access scheduler resources → 403."""
    _, H_ther, _, _, _ = actor_set
    r = client.get("/api/v1/scheduler/resources", headers=H_ther)
    assert r.status_code == 403


def test_unauthorized_cannot_access_resources(client):
    """No token → 401 for scheduler resources."""
    r = client.get("/api/v1/scheduler/resources")
    assert r.status_code == 401


# ── Scheduler pool ─────────────────────────────────────────────────────


def test_admin_get_pool_200(client, actor_set):
    """Admin gets patient pool → 200 with total and items."""
    H_admin, _, _, _, _ = actor_set

    r = client.get("/api/v1/scheduler/pool", headers=H_admin)
    assert r.status_code == 200, r.text
    body = r.json()
    assert "date" in body
    assert "total" in body
    assert "items" in body
    assert isinstance(body["items"], list)
    # Pool items have required fields
    if body["items"]:
        item = body["items"][0]
        for key in ("id", "name"):
            assert key in item, f"Pool item missing key: {key}"


def test_pool_excludes_patients_with_courses_today(client, actor_set):
    """Patients with today's courses should NOT appear in pool."""
    H_admin, H_ther, pid, tid, rid = actor_set
    # Create a course for today
    now = datetime.now(timezone.utc)
    today_start = datetime(now.year, now.month, now.day, 9, 0, tzinfo=timezone.utc)
    today_end = datetime(now.year, now.month, now.day, 9, 45, tzinfo=timezone.utc)

    r = client.post(
        "/api/v1/courses",
        json=course_body(pid, tid, rid, today_start, today_end),
        headers=H_admin,
    )
    assert r.status_code == 201, r.text
    course_patient_id = r.json()["patient_id"]

    # Pool should NOT contain this patient
    r = client.get("/api/v1/scheduler/pool", headers=H_admin)
    assert r.status_code == 200, r.text
    pool_ids = [item["id"] for item in r.json()["items"]]
    assert course_patient_id not in pool_ids, (
        f"Patient {course_patient_id} with today's course should not be in pool"
    )


# ── Therapist schedule ────────────────────────────────────────────────


def test_therapist_schedule_200_with_free_slots(client, actor_set):
    """Therapist gets schedule → 200 with overview, items, and free_slots."""
    H_admin, H_ther, pid, tid, rid = actor_set

    # Create two courses with a gap > 15 min
    _create_course(client, H_admin, pid, tid, rid, day_offset=80, hour=9)
    _create_course(client, H_admin, pid, tid, rid, day_offset=80, hour=11)

    date_str = make_time(day_offset=80, hour=0).strftime("%Y-%m-%d")
    r = client.get(f"/api/v1/therapist/schedule?date={date_str}", headers=H_ther)
    assert r.status_code == 200, r.text
    body = r.json()

    assert body["date"] == date_str
    assert "overview" in body
    assert body["overview"]["total"] >= 2
    assert "items" in body
    assert isinstance(body["items"], list)
    assert len(body["items"]) >= 2

    # Check item schema
    item = body["items"][0]
    for key in (
        "course_id", "start_at", "end_at", "patient_name",
        "course_type", "room_name", "status",
    ):
        assert key in item, f"Schedule item missing key: {key}"

    # Free slots should exist (gap between 9:45 and 11:00 > 15 min)
    assert "free_slots" in body
    assert isinstance(body["free_slots"], list)
    if body["free_slots"]:
        slot = body["free_slots"][0]
        for key in ("start", "end", "minutes"):
            assert key in slot, f"Free slot missing key: {key}"
        assert slot["minutes"] > 15, f"Free slot should be > 15 min, got {slot['minutes']}"


def test_schedule_small_gaps_not_free_slots(client, actor_set):
    """Gaps ≤ 15 minutes should NOT appear as free slots."""
    H_admin, H_ther, pid, tid, rid = actor_set

    # Create two courses with exactly 15 min gap
    start1 = make_time(day_offset=90, hour=9, minute=0)
    end1 = make_time(day_offset=90, hour=9, minute=45)
    start2 = make_time(day_offset=90, hour=10, minute=0)  # 15 min gap
    end2 = make_time(day_offset=90, hour=10, minute=45)

    r = client.post(
        "/api/v1/courses",
        json=course_body(pid, tid, rid, start1, end1),
        headers=H_admin,
    )
    assert r.status_code == 201, r.text
    r = client.post(
        "/api/v1/courses",
        json=course_body(pid, tid, rid, start2, end2),
        headers=H_admin,
    )
    assert r.status_code == 201, r.text

    date_str = make_time(day_offset=90, hour=0).strftime("%Y-%m-%d")
    r = client.get(f"/api/v1/therapist/schedule?date={date_str}", headers=H_ther)
    assert r.status_code == 200, r.text
    body = r.json()

    # No free slot with exactly 15 min gap
    for slot in body["free_slots"]:
        assert slot["minutes"] > 15, f"15-min gap should not be a free slot, got {slot['minutes']}"


def test_non_therapist_cannot_access_schedule(client, actor_set):
    """Admin cannot access therapist schedule → 403."""
    H_admin, _, _, _, _ = actor_set
    date_str = make_time(day_offset=91, hour=0).strftime("%Y-%m-%d")
    r = client.get(f"/api/v1/therapist/schedule?date={date_str}", headers=H_admin)
    assert r.status_code == 403


def test_unauthorized_cannot_access_schedule(client):
    """No token → 401 for therapist schedule."""
    r = client.get("/api/v1/therapist/schedule?date=2030-01-07")
    assert r.status_code == 401


def test_schedule_only_own_courses(client):
    """Therapist schedule only shows own courses, not other therapists'."""
    # Create a course for seed therapist 张伟 (pt_zhang)
    pid, tid, rid = seed_ids()
    H_admin = _admin_headers(client)
    _create_course(client, H_admin, pid, tid, rid, day_offset=94, hour=9)

    # Another therapist (ot_li) should not see 张伟's courses
    r = client.post(
        "/api/v1/auth/login",
        json={"username": "ot_li", "password": "admin123"},
    )
    assert r.status_code == 200
    H_ot = auth_headers(r.json()["access_token"])

    date_str = make_time(day_offset=94, hour=0).strftime("%Y-%m-%d")
    r = client.get(f"/api/v1/therapist/schedule?date={date_str}", headers=H_ot)
    assert r.status_code == 200, r.text
    body = r.json()
    # Should have no items (ot_li has no courses on this date)
    assert body["overview"]["total"] == 0, (
        f"ot_li should not see pt_zhang's courses, got {body['overview']['total']}"
    )


def test_course_list_401_unauthenticated(client):
    """Unauthenticated course list → 401."""
    r = client.get("/api/v1/courses")
    assert r.status_code == 401
