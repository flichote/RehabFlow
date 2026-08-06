"""pytest 共享夹具：测试库隔离 + TestClient + 种子数据 + 角色注册/登录。

设计说明（T5 验收依据：docs/qa/m1-acceptance.md AC-QA-01~04）：
- 测试库独立 SQLite 文件（backend/tests/_test_rehabflow.db），不污染开发库 rehabflow.db
- 必须在导入 app 之前设置 DATABASE_URL（app.core.config.settings 是模块级单例）
- TestClient 走 FastAPI lifespan（create_all），种子数据手动灌入（init_db.seed_data）
- 每个测试用唯一用户名，避免跨用例数据污染
"""
from __future__ import annotations

import os
import uuid
from datetime import datetime, timedelta, timezone

# ── 测试库隔离（必须在 import app 之前）────────────────────────────
TEST_DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_test_rehabflow.db")
if os.path.exists(TEST_DB):
    os.remove(TEST_DB)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{TEST_DB.replace(os.sep, '/')}"

import asyncio  # noqa: E402

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import select  # noqa: E402

from app.db.init_db import create_tables, seed_data  # noqa: E402
from app.db.session import SessionLocal  # noqa: E402
from app.main import app  # noqa: E402
from app.models.models import Patient, Room, Therapist  # noqa: E402

TZ8 = timezone(timedelta(hours=8))

# 演示种子账号（init_db.py 固定密码 admin123）
SEED_ADMIN = {"username": "admin", "password": "admin123"}


@pytest.fixture(scope="session")
def client():
    """会话级 TestClient：先建表+种子，再起 app。"""
    asyncio.run(create_tables())
    asyncio.run(seed_data())
    with TestClient(app) as c:
        yield c


def _unique(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:8]}"


def _test_phone(seed: str) -> str:
    """从种子字符串派生稳定 11 位纯数字手机号（1 开头）。"""
    import hashlib

    h = hashlib.md5(seed.encode()).hexdigest()  # 32 hex chars
    # a-f → 0-5，保证全数字且长度足够（32 位）
    digits = "".join(str(int(c, 16) % 10) for c in h)
    return "13" + digits[:9]  # 13 + 9 位 = 11 位


def register_and_login(client: TestClient, role: str, username: str | None = None):
    """注册并登录，返回 (access_token, refresh_token, user_id)。"""
    uname = username or _unique(role)
    pwd = "secret123"
    r = client.post(
        "/api/v1/auth/register",
        json={
            "username": uname,
            "password": pwd,
            "display_name": uname,
            "role": role,
            "phone": _test_phone(uname),
        },
    )
    assert r.status_code == 201, f"register {role} failed: {r.status_code} {r.text}"
    user_id = r.json()["user_id"]
    r = client.post("/api/v1/auth/login", json={"username": uname, "password": pwd})
    assert r.status_code == 200, f"login {role} failed: {r.status_code} {r.text}"
    body = r.json()
    return body["access_token"], body["refresh_token"], user_id


def auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


async def _seed_ids():
    """种子数据中的第一个患者/康复师/治疗室（PT 组）。"""
    async with SessionLocal() as s:
        patient = (await s.execute(select(Patient).where(Patient.name == "陈明"))).scalar_one()
        therapist = (await s.execute(select(Therapist).where(Therapist.name == "张伟"))).scalar_one()
        room = (await s.execute(select(Room).where(Room.name == "PT大厅"))).scalar_one()
        return patient.id, therapist.id, room.id


def seed_ids() -> tuple[int, int, int]:
    return asyncio.run(_seed_ids())


def make_time(day_offset: int = 0, hour: int = 9, minute: int = 0, tz=timezone.utc) -> datetime:
    """生成 15min 对齐的未来时间（UTC 基准，day_offset 避免跨用例重叠）。"""
    base = datetime(2030, 1, 7, hour, minute, tzinfo=tz)  # 2030-01-07 是周一
    return base + timedelta(days=day_offset)


def course_body(
    patient_id: int,
    therapist_id: int,
    room_id: int,
    start: datetime,
    end: datetime,
    course_type: str = "PT",
) -> dict:
    return {
        "patient_id": patient_id,
        "therapist_id": therapist_id,
        "room_id": room_id,
        "course_type": course_type,
        "start_at": start.isoformat(),
        "end_at": end.isoformat(),
    }


# ── 独立角色组 fixture（避免测试间共享种子患者状态） ────────────────


@pytest.fixture()
def actor_set(client):
    """为每个测试创建独立 admin + therapist + patient 账号，返回：
    (H_admin, H_ther, patient_id, therapist_id, room_id)

    说明：注册 patient 会自动建 Patient 档案（user_id 关联）；
    注册 therapist 会自动建 Therapist 档案（group_name=PT，name=display_name）。
    这样每个测试都在自己的患者/康复师上操作，互不污染。
    """
    import asyncio as _aio
    from sqlalchemy import select as _select

    from app.models.models import Patient as _Patient, Room as _Room, Therapist as _Therapist

    admin_tok, _, _ = register_and_login(client, "admin")
    ther_tok, _, _ = register_and_login(client, "therapist")
    pat_tok, _, _ = register_and_login(client, "patient")

    async def _refs():
        from app.db.session import SessionLocal as _SL

        async with _SL() as s:
            # therapist 档案：display_name 唯一 -> 用 therapist token 查 user_id
            from app.models.models import User as _User

            # 取注册的最新 therapist/patient（本测试内唯一的 display_name 前缀不同）
            t_user = (
                await s.execute(
                    _select(_User).where(
                        _User.username.like("therapist_%")
                    ).order_by(_User.id.desc())
                )
            ).scalars().first()
            p_user = (
                await s.execute(
                    _select(_User).where(
                        _User.username.like("patient_%")
                    ).order_by(_User.id.desc())
                )
            ).scalars().first()
            ther = (
                await s.execute(_select(_Therapist).where(_Therapist.user_id == t_user.id))
            ).scalar_one()
            pat = (
                await s.execute(_select(_Patient).where(_Patient.user_id == p_user.id))
            ).scalar_one()
            room = (
                await s.execute(_select(_Room).where(_Room.name == "PT大厅"))
            ).scalar_one()
            return pat.id, ther.id, room.id

    pid, tid, rid = _aio.run(_refs())
    return auth_headers(admin_tok), auth_headers(ther_tok), pid, tid, rid
