"""全链路烟测：注册→登录→排课→开始上课→结束上课→看板/日志（AC-QA-03/06 + m1-acceptance §1）。

以独立用户名跑通主干，任何一环失败都会让本用例失败（快速暴露回归）。
"""
from __future__ import annotations

from tests.conftest import auth_headers, course_body, make_time, register_and_login, seed_ids


def test_full_chain_smoke(client):
    """注册 → 登录 → 排课 → 开始 → 结束 → 状态日志。"""
    # 1. 注册+登录 admin / therapist
    admin_tok, _, _ = register_and_login(client, "admin", username="smoke_admin")
    ther_tok, _, _ = register_and_login(client, "therapist", username="smoke_ther")
    H_admin = auth_headers(admin_tok)
    H_ther = auth_headers(ther_tok)

    # 2. me 校验角色
    r = client.get("/api/v1/auth/me", headers=H_admin)
    assert r.status_code == 200 and r.json()["role"] == "admin"

    # 3. 排课：需要一个真实 therapist 档案 —— 使用种子康复师张伟（pt_zhang 用户）
    import asyncio
    from sqlalchemy import select
    from app.db.session import SessionLocal
    from app.models.models import Patient, Room, Therapist

    async def _seed_refs():
        async with SessionLocal() as s:
            p = (await s.execute(select(Patient).where(Patient.name == "陈明"))).scalar_one()
            t = (await s.execute(select(Therapist).where(Therapist.name == "张伟"))).scalar_one()
            r_ = (await s.execute(select(Room).where(Room.name == "PT大厅"))).scalar_one()
            return p.id, t.id, r_.id

    pid, tid, rid = asyncio.run(_seed_refs())
    start = make_time(day_offset=40, hour=9)
    end = make_time(day_offset=40, hour=10)
    r = client.post("/api/v1/courses", json=course_body(pid, tid, rid, start, end), headers=H_admin)
    assert r.status_code == 201, f"排课失败：{r.status_code} {r.text}"
    cid = r.json()["id"]

    # 4. 康复师开始上课（用种子 pt_zhang 用户登录 → 张伟本人）
    r = client.post("/api/v1/auth/login", json={"username": "pt_zhang", "password": "admin123"})
    assert r.status_code == 200
    H_pt = auth_headers(r.json()["access_token"])
    r = client.post(f"/api/v1/courses/{cid}/start", headers=H_pt)
    assert r.status_code == 200, f"开始上课失败：{r.status_code} {r.text}"
    assert r.json()["status"] == "ongoing"

    # 5. 结束上课
    r = client.post(f"/api/v1/courses/{cid}/finish", headers=H_pt)
    assert r.status_code == 200, f"结束上课失败：{r.status_code} {r.text}"
    assert r.json()["status"] == "completed"

    # 6. 状态日志存在（course_status_log ≥2 行）
    async def _log_count():
        from sqlalchemy import func
        from app.models.models import CourseStatusLog
        async with SessionLocal() as s:
            return (
                await s.execute(
                    select(func.count()).select_from(CourseStatusLog)
                )
            ).scalar()
    assert asyncio.run(_log_count()) >= 2
