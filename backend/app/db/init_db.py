"""建表 + 种子数据脚本。

用法：
    cd backend
    python -m app.db.init_db          # 建表（若不存在）+ 灌入演示数据

种子内容（对应 AC-DB-05）：
- 治疗室 3 间：PT大厅 / OT大厅 / ST室
- 演示账号：admin、PT/OT/ST 康复师各 1、主管医生 1
- 演示患者 3 名（分别归属 PT/OT/ST，含初始 patient_status_log=ward 日志，双写一致性）
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from sqlalchemy import func, select

from app.db.session import SessionLocal, engine
from app.models.base import Base
from app.models.models import (
    Doctor,
    Patient,
    PatientStatusLog,
    Room,
    Therapist,
    User,
)

# 演示账号密码哈希（bcrypt，明文均为 admin123）
# 说明：占位字符串必须 ≤72 字节且是合法 bcrypt 格式，否则登录验证崩溃
DEMO_PASSWORD_HASH = "$2b$12$sSwbAkOGUctMPdnl/rp15enTj5Ohs2vdY52.LD.evaR/i9GSvSTlG"


async def create_tables() -> None:
    """建表（幂等：仅创建不存在的表）。"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def seed_data() -> None:
    """灌入种子数据（幂等：已存在则跳过）。"""
    async with SessionLocal() as session:
        # --- 治疗室 ---
        room_count = await session.scalar(select(func.count()).select_from(Room))
        if room_count == 0:
            session.add_all(
                [
                    Room(name="PT大厅", room_type="PT", capacity=6),
                    Room(name="OT大厅", room_type="OT", capacity=4),
                    Room(name="ST室", room_type="ST", capacity=2),
                ]
            )
            await session.flush()
            print("seeded rooms: PT大厅 / OT大厅 / ST室")

        # --- 用户 / 康复师 / 医生 / 患者（演示账号） ---
        user_count = await session.scalar(select(func.count()).select_from(User))
        if user_count > 0:
            await session.commit()
            return

        admin = User(
            username="admin",
            password_hash=DEMO_PASSWORD_HASH,
            role="admin",
            display_name="系统管理员",
            is_active=True,
        )
        pt_user = User(
            username="pt_zhang",
            password_hash=DEMO_PASSWORD_HASH,
            role="therapist",
            display_name="张伟",
            is_active=True,
        )
        ot_user = User(
            username="ot_li",
            password_hash=DEMO_PASSWORD_HASH,
            role="therapist",
            display_name="李娜",
            is_active=True,
        )
        st_user = User(
            username="st_wang",
            password_hash=DEMO_PASSWORD_HASH,
            role="therapist",
            display_name="王芳",
            is_active=True,
        )
        dr_user = User(
            username="dr_zhao",
            password_hash=DEMO_PASSWORD_HASH,
            role="doctor",
            display_name="赵建国",
            is_active=True,
        )
        session.add_all([admin, pt_user, ot_user, st_user, dr_user])
        await session.flush()

        pt = Therapist(user_id=pt_user.id, name="张伟", group_name="PT", title="主管康复师", certified=True)
        ot = Therapist(user_id=ot_user.id, name="李娜", group_name="OT", title="康复治疗师", certified=True)
        st = Therapist(user_id=st_user.id, name="王芳", group_name="ST", title="言语治疗师", certified=True)
        dr = Doctor(user_id=dr_user.id, name="赵建国", department="康复医学科", title="主任医师")
        session.add_all([pt, ot, st, dr])
        await session.flush()

        patients = [
            Patient(
                user_id=None,
                name="陈明",
                gender="男",
                age=58,
                diagnosis="脑卒中（左侧偏瘫）",
                ward_location="住院部3楼5床",
                doctor_id=dr.id,
                therapist_id=pt.id,
                status="ward",
                external_patient_no=None,  # 备用冗余字段，种子不填业务值
            ),
            Patient(
                user_id=None,
                name="刘芳",
                gender="女",
                age=45,
                diagnosis="右肱骨骨折术后",
                ward_location="住院部2楼8床",
                doctor_id=dr.id,
                therapist_id=ot.id,
                status="ward",
            ),
            Patient(
                user_id=None,
                name="周涛",
                gender="男",
                age=62,
                diagnosis="脑外伤后言语障碍",
                ward_location="住院部5楼2床",
                doctor_id=dr.id,
                therapist_id=st.id,
                status="ward",
            ),
        ]
        session.add_all(patients)
        await session.flush()

        # --- 患者状态日志（双写：patients.status + patient_status_log，见裁决-5） ---
        now = datetime.now(timezone.utc)
        for p in patients:
            session.add(
                PatientStatusLog(
                    patient_id=p.id,
                    from_status=None,
                    to_status="ward",
                    location=p.ward_location,
                    actor_id=None,
                    source="system",
                    occurred_at=now,
                )
            )

        await session.commit()
        print(
            "seeded users: admin / pt_zhang / ot_li / st_wang / dr_zhao\n"
            "seeded therapists: 张伟(PT) / 李娜(OT) / 王芳(ST)\n"
            "seeded doctor: 赵建国(康复医学科)\n"
            "seeded patients: 陈明 / 刘芳 / 周涛 (+ ward 初始状态日志)"
        )


async def main() -> None:
    await create_tables()
    await seed_data()
    await engine.dispose()
    print("init_db done.")


if __name__ == "__main__":
    asyncio.run(main())
