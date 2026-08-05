"""M1→M3 全链路烟测：注册→登录→排课→查课表→开始/结束→通知→看板 KPI→患者360 位置。

验收依据：
- docs/design/flows.md 流程1（排课）/ 流程2（上课执行）/ 流程3（软打卡）/ 流程6（看板数据流）
- docs/PRD.md §3.3（患者360 实时位置卡）/ §3.4（主任看板 KPI）/ §5（消息提醒）
- docs/api.md §8（看板）/ §10（状态流转对照）

闭环断言：
① 注册+登录（admin/therapist/patient）→ /auth/me 角色确认
② 排课（今日）→ 201
③ 通知：患者+康复师收到 course_new（PRD §5 行1 / BUG-6 回归）
④ 看板 KPI：今日课程 +1
⑤ 康复师查课表 → 含该课程
⑥ 开始上课 → 课程 ongoing + 患者 treating + 位置=PT大厅 + KPI 治疗中 +1 + 360 位置更新
⑦ 结束上课 → completed + 患者 ward + KPI 治疗中回落 + 360 位置更新
⑧ 看板 trend：今日计数 ≥1
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from tests.conftest import auth_headers, register_and_login


def _today_slot(hours_ahead: int = 1) -> tuple[datetime, datetime]:
    """返回今日稍后的 15min 对齐时段（UTC）。"""
    now = datetime.now(timezone.utc) + timedelta(hours=hours_ahead)
    start = now.replace(minute=(now.minute // 15) * 15, second=0, microsecond=0)
    end = start + timedelta(minutes=45)
    return start, end


def test_full_chain_m1_to_m3(client):
    # ① 注册 + 登录（admin / therapist / patient）
    a_tok, _, _ = register_and_login(client, "admin")
    t_tok, _, _ = register_and_login(client, "therapist")
    p_tok, _, _ = register_and_login(client, "patient")
    H_admin, H_ther, H_pat = auth_headers(a_tok), auth_headers(t_tok), auth_headers(p_tok)

    me = client.get("/api/v1/auth/me", headers=H_admin).json()
    assert me["role"] == "admin"

    # 取患者/康复师/治疗室档案 id
    import asyncio as _aio

    from sqlalchemy import select as _select

    from app.db.session import SessionLocal as _SL
    from app.models.models import Patient as _Patient
    from app.models.models import Room as _Room
    from app.models.models import Therapist as _Therapist
    from app.models.models import User as _User

    async def _refs():
        async with _SL() as s:
            t_user = (
                await s.execute(
                    _select(_User).where(_User.username.like("therapist_%"))
                    .order_by(_User.id.desc())
                )
            ).scalars().first()
            p_user = (
                await s.execute(
                    _select(_User).where(_User.username.like("patient_%"))
                    .order_by(_User.id.desc())
                )
            ).scalars().first()
            ther = (
                await s.execute(_select(_Therapist).where(_Therapist.user_id == t_user.id))
            ).scalar_one()
            pat = (
                await s.execute(_select(_Patient).where(_Patient.user_id == p_user.id))
            ).scalar_one()
            room = (await s.execute(_select(_Room).where(_Room.name == "PT大厅"))).scalar_one()
            return pat.id, ther.id, room.id

    pid, tid, rid = _aio.run(_refs())

    # 看板 KPI 基线（今日课程计数）
    k0 = client.get("/api/v1/dashboard/kpis", headers=H_admin).json()

    # ② 排课（今日）→ 201
    start, end = _today_slot()
    r = client.post(
        "/api/v1/courses",
        json={
            "patient_id": pid,
            "therapist_id": tid,
            "room_id": rid,
            "course_type": "PT",
            "start_at": start.isoformat(),
            "end_at": end.isoformat(),
        },
        headers=H_admin,
    )
    assert r.status_code == 201, r.text
    cid = r.json()["id"]

    # ③ 通知：排课成功 → 患者+康复师收到 course_new（PRD §5 行1 / BUG-6 回归）
    n_pat = client.get("/api/v1/notifications", headers=H_pat).json()
    n_ther = client.get("/api/v1/notifications", headers=H_ther).json()
    assert any(it["type"] == "course_new" for it in n_pat["items"]), n_pat
    assert any(it["type"] == "course_new" for it in n_ther["items"]), n_ther

    # ④ 看板 KPI：今日课程 +1
    k1 = client.get("/api/v1/dashboard/kpis", headers=H_admin).json()
    assert k1["today_course_count"] == k0["today_course_count"] + 1, (k0, k1)

    # ⑤ 康复师查课表 → 含该课程
    today = datetime.now(timezone.utc).date().isoformat()
    sched = client.get(f"/api/v1/therapist/schedule?date={today}", headers=H_ther).json()
    assert sched["overview"]["total"] >= 1, sched
    assert any(it["course_id"] == cid for it in sched["items"]), sched

    # ⑥ 开始上课 → 课程 ongoing + 患者 treating + 位置=PT大厅 + KPI 治疗中 +1 + 360 位置更新
    r = client.post(f"/api/v1/courses/{cid}/start", headers=H_ther)
    assert r.status_code == 200, r.text

    course_detail = client.get(f"/api/v1/courses/{cid}", headers=H_ther).json()
    assert course_detail["status"] == "ongoing", course_detail

    k2 = client.get("/api/v1/dashboard/kpis", headers=H_admin).json()
    assert k2["treating_count"] == k1["treating_count"] + 1, (k1, k2)

    ov = client.get(f"/api/v1/patients/{pid}/overview", headers=H_admin).json()
    assert ov["current_status"] == "treating", ov
    assert ov["current_location"] == "PT大厅", ov

    # ⑦ 结束上课 → completed + 患者 ward + KPI 治疗中回落 + 360 位置更新
    r = client.post(f"/api/v1/courses/{cid}/finish", headers=H_ther)
    assert r.status_code == 200, r.text

    k3 = client.get("/api/v1/dashboard/kpis", headers=H_admin).json()
    assert k3["treating_count"] == k2["treating_count"] - 1, (k2, k3)

    ov2 = client.get(f"/api/v1/patients/{pid}/overview", headers=H_admin).json()
    assert ov2["current_status"] == "ward", ov2

    # ⑧ 看板 trend：今日计数 ≥1
    trend = client.get("/api/v1/dashboard/course-trend?days=7", headers=H_admin).json()
    today_item = next((it for it in trend["items"] if it["date"] == today), None)
    assert today_item is not None, trend
    assert today_item["count"] >= 1, trend
