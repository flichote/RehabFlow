"""M2 全链路烟测：注册→登录→排课→查课表→开始上课→结束上课→看通知。

覆盖 T9 任务要求的主干闭环（api.md §3/§4/§6 + flows.md 流程2）：
- 排课（管理员）→ 201
- 查课表（康复师 GET /therapist/schedule）→ 200，含 overview/items/free_slots
- 开始上课 → ongoing；结束上课 → completed
- 看通知（GET /notifications + /unread-count）→ 200，结构正确
"""

from __future__ import annotations

import asyncio

from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.models import Patient, Room, Therapist

from tests.conftest import auth_headers, course_body, make_time, register_and_login

DATE_STR = "2030-01-07"  # make_time(day_offset=0) 对应日期（周一）


def test_full_chain_smoke_m2(client):
    """注册 → 登录 → 排课 → 查课表 → 开始 → 结束 → 看通知。"""
    # 1. 注册 + 登录 admin / therapist
    admin_tok, _, _ = register_and_login(client, "admin", username="m2_smoke_admin")
    _, _, _ = register_and_login(client, "therapist", username="m2_smoke_ther")
    H_admin = auth_headers(admin_tok)

    # 2. me 校验角色
    r = client.get("/api/v1/auth/me", headers=H_admin)
    assert r.status_code == 200 and r.json()["role"] == "admin"

    # 3. 排课：种子康复师张伟 / 患者陈明 / PT大厅，两节（09:00-10:00、11:00-12:00）
    async def _seed_refs():
        async with SessionLocal() as s:
            p = (await s.execute(select(Patient).where(Patient.name == "陈明"))).scalar_one()
            t = (await s.execute(select(Therapist).where(Therapist.name == "张伟"))).scalar_one()
            r_ = (await s.execute(select(Room).where(Room.name == "PT大厅"))).scalar_one()
            return p.id, t.id, r_.id

    pid, tid, rid = asyncio.run(_seed_refs())
    cids = []
    for hour in (9, 11):
        start = make_time(day_offset=0, hour=hour)
        end = make_time(day_offset=0, hour=hour + 1)
        r = client.post(
            "/api/v1/courses",
            json=course_body(pid, tid, rid, start, end),
            headers=H_admin,
        )
        assert r.status_code == 201, f"排课失败：{r.status_code} {r.text}"
        cids.append(r.json()["id"])
    cid = cids[0]

    # 4. 查课表（pt_zhang = 种子康复师张伟的登录账号）
    r = client.post("/api/v1/auth/login", json={"username": "pt_zhang", "password": "admin123"})
    assert r.status_code == 200, r.text
    H_pt = auth_headers(r.json()["access_token"])

    r = client.get(f"/api/v1/therapist/schedule?date={DATE_STR}", headers=H_pt)
    assert r.status_code == 200, f"查课表失败：{r.status_code} {r.text}"
    body = r.json()
    assert body["date"] == DATE_STR
    assert body["overview"]["total"] >= 2
    assert any(it["course_id"] == cid for it in body["items"]), "课表应包含刚排的课程"
    # free_slots：10:00-11:00 空档 ≥ 60min
    assert isinstance(body["free_slots"], list) and len(body["free_slots"]) >= 1, (
        "schedule 聚合应含 free_slots（10:00-11:00 空档）"
    )
    assert body["free_slots"][0]["minutes"] >= 60, body["free_slots"]

    # 5. 开始上课
    r = client.post(f"/api/v1/courses/{cid}/start", headers=H_pt)
    assert r.status_code == 200, f"开始上课失败：{r.status_code} {r.text}"
    assert r.json()["status"] == "ongoing"

    # 6. 结束上课
    r = client.post(f"/api/v1/courses/{cid}/finish", headers=H_pt)
    assert r.status_code == 200, f"结束上课失败：{r.status_code} {r.text}"
    assert r.json()["status"] == "completed"

    # 7. 看通知（API 可用 + 响应结构正确）
    r = client.get("/api/v1/notifications", headers=H_pt)
    assert r.status_code == 200, f"看通知失败：{r.status_code} {r.text}"
    nbody = r.json()
    assert "total" in nbody and "unread_count" in nbody and "items" in nbody

    r = client.get("/api/v1/notifications/unread-count", headers=H_pt)
    assert r.status_code == 200
    assert "unread_count" in r.json()
