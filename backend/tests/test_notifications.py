"""通知 API 测试：列表/未读数/已读/一键提醒。

依据：api.md §5 提醒 + T8 交付要求。
"""

from __future__ import annotations

import asyncio

from sqlalchemy import func, select

from app.db.session import SessionLocal
from app.models.models import Notification

from tests.conftest import auth_headers, course_body, make_time, register_and_login


def _create_course(client, headers, pid, tid, rid, day_offset=30, hour=9):
    start = make_time(day_offset=day_offset, hour=hour)
    end = make_time(day_offset=day_offset, hour=hour, minute=45)
    r = client.post(
        "/api/v1/courses",
        json=course_body(pid, tid, rid, start, end),
        headers=headers,
    )
    assert r.status_code == 201, r.text
    return r.json()["id"]


# ── 通知列表 ───────────────────────────────────────────────────


def test_list_notifications_unread_first(client, actor_set):
    """通知列表返回当前用户消息，未读优先排序。"""
    H_admin, H_ther, pid, tid, rid = actor_set

    # 创建课程 + 一键提醒 → 生成通知
    cid = _create_course(client, H_admin, pid, tid, rid, day_offset=31)
    r = client.post(f"/api/v1/courses/{cid}/remind", headers=H_ther)
    assert r.status_code == 200, r.text

    # 以康复师身份查询通知
    r = client.get("/api/v1/notifications", headers=H_ther)
    assert r.status_code == 200
    body = r.json()
    assert body["total"] >= 1
    assert body["unread_count"] >= 1
    assert len(body["items"]) >= 1

    # 未读在前
    for i in range(len(body["items"]) - 1):
        if body["items"][i]["is_read"] is False and body["items"][i + 1]["is_read"] is True:
            assert False, "unread should come before read"


def test_list_notifications_only_own(client, actor_set):
    """通知列表只返回当前用户的消息（数据权限隔离）。"""
    H_admin, H_ther, pid, tid, rid = actor_set

    cid = _create_course(client, H_admin, pid, tid, rid, day_offset=32)
    r = client.post(f"/api/v1/courses/{cid}/remind", headers=H_ther)
    assert r.status_code == 200

    # 管理员查询通知（没有给管理员发通知，应无关联）
    r = client.get("/api/v1/notifications", headers=H_admin)
    assert r.status_code == 200
    body = r.json()
    # 管理员的通知列表不应包含发给康复师/患者的提醒
    for item in body["items"]:
        assert item["type"] not in ("course_reminder", "course_reminder_therapist"), "admin should not see therapist's reminders"


# ── 未读数 ────────────────────────────────────────────────────


def test_unread_count(client, actor_set):
    """未读消息数正确统计。"""
    H_admin, H_ther, pid, tid, rid = actor_set

    # 初始
    r = client.get("/api/v1/notifications/unread-count", headers=H_ther)
    assert r.status_code == 200
    initial = r.json()["unread_count"]

    # 创建课程 + 提醒 → 应增加未读数
    cid = _create_course(client, H_admin, pid, tid, rid, day_offset=33)
    r = client.post(f"/api/v1/courses/{cid}/remind", headers=H_ther)
    assert r.status_code == 200

    r = client.get("/api/v1/notifications/unread-count", headers=H_ther)
    assert r.status_code == 200
    assert r.json()["unread_count"] >= initial + 1


# ── 标记已读 ──────────────────────────────────────────────────


def test_mark_read(client, actor_set):
    """标记单条通知已读。"""
    H_admin, H_ther, pid, tid, rid = actor_set

    cid = _create_course(client, H_admin, pid, tid, rid, day_offset=34)
    r = client.post(f"/api/v1/courses/{cid}/remind", headers=H_ther)
    assert r.status_code == 200

    # 获取第一条通知
    r = client.get("/api/v1/notifications?page_size=5", headers=H_ther)
    items = r.json()["items"]
    unread_items = [i for i in items if not i["is_read"]]
    assert len(unread_items) > 0, "should have unread notifications"

    nid = unread_items[0]["id"]
    # 标记已读
    r = client.post(f"/api/v1/notifications/{nid}/read", headers=H_ther)
    assert r.status_code == 200

    # 再次查询 → 该条应已读
    r = client.get("/api/v1/notifications?page_size=50", headers=H_ther)
    items2 = r.json()["items"]
    for item in items2:
        if item["id"] == nid:
            assert item["is_read"] is True, "should be marked read"


def test_mark_all_read(client, actor_set):
    """全部标记已读。"""
    H_admin, H_ther, pid, tid, rid = actor_set

    cid = _create_course(client, H_admin, pid, tid, rid, day_offset=35)
    r = client.post(f"/api/v1/courses/{cid}/remind", headers=H_ther)
    assert r.status_code == 200

    # 全部已读
    r = client.post("/api/v1/notifications/read-all", headers=H_ther)
    assert r.status_code == 200

    # 应无未读
    r = client.get("/api/v1/notifications/unread-count", headers=H_ther)
    assert r.status_code == 200
    assert r.json()["unread_count"] == 0


def test_mark_read_not_own(client, actor_set):
    """不能标记他人的通知（返回 404 而非操作他人数据）。"""
    H_admin, H_ther, pid, tid, rid = actor_set

    cid = _create_course(client, H_admin, pid, tid, rid, day_offset=36)
    r = client.post(f"/api/v1/courses/{cid}/remind", headers=H_ther)
    assert r.status_code == 200

    # 获取康复师的通知 ID
    r = client.get("/api/v1/notifications?page_size=5", headers=H_ther)
    nid = r.json()["items"][0]["id"]

    # 用管理员身份标记康复师的通知 → 应返回 404
    r = client.post(f"/api/v1/notifications/{nid}/read", headers=H_admin)
    assert r.status_code == 404, f"should not be able to mark other's notification, got {r.status_code}"
