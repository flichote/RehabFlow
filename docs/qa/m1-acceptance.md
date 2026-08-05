# RehabFlow M1 里程碑验收标准（m1-acceptance）

- 版本：v1.0
- 日期：2026-08-05
- 作者：rf-arch（T1 架构确认）
- 状态：**已评审通过，作为 M1 验收唯一依据**
- 关联任务：T2 数据库（t_5e0b3770）/ T3 后端（t_b39963aa）/ T4 前端（t_deb32bf0）/ T5 测试（t_3b301a6f）

> 本文档是对 `docs/architecture.md`、`docs/database.md`、`docs/api.md`、`docs/structure.md`、
> `docs/tech-stack.md`、`docs/PRD.md`、`docs/design/*`、`docs/ops/*` 全量通读后的验收清单。
> **每一条验收标准都附带验收命令与期望输出**；无法用命令验证的条目（如代码注释、命名）标注「人工评审」。

---

## 0. 文档一致性裁决（通读结论）

通读全部文档，确认技术选型（tech-stack v0.2 已确认）与架构约束（architecture §9 HIS 独立）全局一致，无互相冲突的
**选型级**矛盾。发现 5 处**表述/范围级**不一致，裁决如下（前 2 处已同步修正文档，见 §8 提交清单）：

| # | 不一致点 | 涉及文档 | 裁决 |
| :--- | :--- | :--- | :--- |
| 裁决-1 | 「排课成功 → 患者状态=待排课」 | flows.md 速查表 vs database.md 患者 6 态枚举 | **已修正**：排课成功**不改变**患者状态（api.md §10 的「—」正确）；「待排课」是 PRD §2.1 入院流程叙述阶段，非存储枚举。flows.md 已改为「—（不变）」。T5 验收时**不得**断言存在「待排课」患者状态 |
| 裁决-2 | M1 模型范围「3 核心表」 | structure.md §4 vs T2 任务（15 表全量） | **已修正**：M1 按 T2 任务实现**全部 15 张表**，structure.md §4 已改为「models（15 表）」。Alembic 初始迁移含全部 15 表 |
| 裁决-3 | 管理员注册「不可自助」 | components.md §1.2 vs T3/T4 任务（角色含 admin） | **M1 允许 admin 自助注册**（演示便利，T3/T4 任务为准）；生产期改邀请制，记入后续 ADR 候选。验收按任务体：注册角色 = patient/therapist/doctor/admin |
| 裁决-4 | JSONB 类型两库兼容 | database.md（assessments.detail / audit_log.detail / assessment_templates.fields） | **实现约束**：SQLite 起步必须用 SQLAlchemy 通用 `JSON` 类型 + `with_variant(JSONB, "postgresql")`，禁止无条件使用 PG 方言 JSONB，否则 SQLite 建表失败。见 AC-DB-06 |
| 裁决-5 | 患者 status 冗余列 vs 日志推导 | database.md §2.2/§2.8 vs architecture ADR-2 | **M1 采用双写**：`patients.status` 冗余列 + `patient_status_log` 日志，tracking service 单入口同步更新两者（读冗余列、日志兜底审计）。TBD #3 就此关闭 |

其余交叉核对项（状态机对照表、权限矩阵、目录规划、HIS 隔离纪律、Next.js 16 proxy.ts / Tailwind v4 无 config）全部一致，**无选型级矛盾**。

---

## 1. 总入口（先跑通，再逐项验收）

```bash
# 后端（T2/T3 完成后）
cd backend && python -m venv .venv && . .venv/Scripts/activate && pip install -r requirements.txt
python -m pytest tests/ -v

# 前端（T4 完成后）
cd frontend && npm install && npm run build

# 种子库冒烟（T2 完成后）
cd backend && python -m app.db.init_db
```

---

## 2. T2 数据库地基验收（rf-db / t_5e0b3770）

| ID | 验收标准 | 验收命令 | 期望结果 |
| :--- | :--- | :--- | :--- |
| AC-DB-01 | `backend/` 骨架存在：`app/core/config.py`、`app/db/session.py`、`app/db/init_db.py`、`app/models/`、`alembic/`、`requirements.txt`、`.env.example` | `ls backend/app/core backend/app/db backend/app/models backend/alembic` | 文件齐全 |
| AC-DB-02 | **15 张表模型全部定义**：users/patients/therapists/doctors/rooms/courses/course_status_log/patient_status_log/therapist_shifts/assessments/assessment_templates/notifications/alerts/audit_log/refresh_tokens | `cd backend && python -c "from app.models.models import Base; print(len(Base.metadata.tables), sorted(Base.metadata.tables))"` | 输出 15 个表名，集合与 database.md §1 完全一致 |
| AC-DB-03 | `DATABASE_URL` 默认 `sqlite+aiosqlite:///./rehabflow.db`，pydantic-settings 可被环境变量覆盖 | `cd backend && python -c "from app.core.config import settings; print(settings.DATABASE_URL)"` 与 `DATABASE_URL=postgresql+asyncpg://u:p@h/db python -c "from app.core.config import settings; print(settings.DATABASE_URL)"` | 前者输出默认 SQLite URL；后者输出 PG URL |
| AC-DB-04 | `db/session.py`：`create_async_engine` + `async_sessionmaker(engine, expire_on_commit=False)`（SQLAlchemy 2.x async） | `cd backend && python -c "from app.db.session import engine, SessionLocal; print(type(engine).__name__)"` | 输出 `AsyncEngine` 且无异常 |
| AC-DB-05 | `init_db.py` 建表 + 种子数据：**PT大厅 / OT大厅 / ST室** 3 个治疗室 + 演示患者/康复师/医生 | `cd backend && python -m app.db.init_db && python - <<'PY'\nfrom sqlalchemy import create_engine, text\neng = create_engine('sqlite:///./rehabflow.db')\nwith eng.connect() as c:\n    print('tables:', c.execute(text(\"select count(*) from sqlite_master where type='table'\")).scalar())\n    print('rooms:', c.execute(text('select count(*) from rooms')).scalar())\n    print('users:', c.execute(text('select count(*) from users')).scalar())\nPY` | tables ≥ 15；rooms ≥ 3（含 PT大厅/OT大厅/ST室）；users ≥ 3 |
| AC-DB-06 | **courses 冲突索引**：`idx_courses_patient_time (patient_id, start_at, end_at)`、`idx_courses_therapist_time (therapist_id, start_at, end_at)` | `cd backend && python - <<'PY'\nfrom sqlalchemy import create_engine, inspect\ninsp = inspect(create_engine('sqlite:///./rehabflow.db'))\nprint([i['name'] for i in insp.get_indexes('courses')])\nPY` | 输出包含 `idx_courses_patient_time` 与 `idx_courses_therapist_time` |
| AC-DB-07 | **Alembic 初始化 + 初始迁移两库可跑**：`alembic upgrade head` 在 SQLite 上成功 | `cd backend && rm -f rehabflow_mig.db && DATABASE_URL=sqlite+aiosqlite:///./rehabflow_mig.db alembic upgrade head && python - <<'PY'\nfrom sqlalchemy import create_engine, inspect\nprint(len(inspect(create_engine('sqlite:///./rehabflow_mig.db')).get_table_names()))\nPY` | 迁移无报错；迁移库表数 = 15 |
| AC-DB-08 | **两库方言兼容**：模型/迁移不写 SQLite 特有 SQL（PRAGMA 等）；JSONB 用通用 `JSON().with_variant(JSONB, "postgresql")` | `cd backend && grep -rn "PRAGMA" app/ alembic/ || echo NO_PRAGMA` 与 `python - <<'PY'\nfrom sqlalchemy.schema import CreateTable\nfrom sqlalchemy.dialects import sqlite, postgresql\nimport app.models.models as m\nfor t in m.Base.metadata.sorted_tables:\n    CreateTable(t).compile(dialect=sqlite.dialect())\n    CreateTable(t).compile(dialect=postgresql.dialect())\nprint('dialect compile OK:', len(m.Base.metadata.sorted_tables))\nPY` | `NO_PRAGMA`；两方言 DDL 编译均无异常 |
| AC-DB-09 | **时间一律 `DateTime(timezone=True)`**（TIMESTAMPTZ 语义） | `cd backend && python - <<'PY'\nfrom sqlalchemy import DateTime\nimport app.models.models as m\nbad = [f'{t.name}.{c.name}' for t in m.Base.metadata.sorted_tables for c in t.columns if type(c.type) is DateTime and not c.type.timezone]\nprint('non-tz DateTime:', bad or 'NONE')\nPY` | 输出 `NONE` |
| AC-DB-10 | **状态枚举与 database.md 一致**：患者 6 态（ward/en_route/treating/paused/absent/discharged）、课程 7 态（scheduled/reminded/ongoing/completed/leave/absent/abnormal） | 实现为 Python 常量时：`cd backend && python -c "from app.models.models import PATIENT_STATUS, COURSE_STATUS; print(PATIENT_STATUS, COURSE_STATUS)"`；实现为字符串列时：grep 比对 | 集合与文档完全一致（T5 按此断言） |
| AC-DB-11 | `patients.external_patient_no` 仅冗余字段，**不参与任何业务逻辑**（无查询/索引/服务引用） | `cd backend && grep -rn "external_patient_no" app/ | grep -v "models/" || echo ONLY_IN_MODELS` | 输出 `ONLY_IN_MODELS`（或仅模型定义/注释处出现） |
| AC-DB-12 | **HIS 完全独立**：代码零 HIS 连接串/表名/接口地址 | `cd backend && grep -rniE 'his_api|hisdb|hospital_info|(^|[^a-z])his([^a-z]|$)' app/ alembic/ requirements.txt .env.example 2>/dev/null || echo CLEAN` | 输出 `CLEAN`（排除「this/history」等误匹配，人工复核） |
| AC-DB-13 | `requirements.txt` 含：sqlalchemy[asyncio]、aiosqlite、pydantic-settings、alembic、asyncpg（生产切换口） | `cd backend && grep -iE "sqlalchemy|aiosqlite|pydantic-settings|alembic|asyncpg" requirements.txt` | 5 项均在 |
| AC-DB-14 | 提交物：仅 `backend/` 目录，comment 附提交 hash + 建表验证输出 | `cd .. && git show --stat --oneline HEAD` | 变更仅限 `backend/` |

**T2 出口**：AC-DB-01 ~ AC-DB-14 全部通过。

---

## 3. T3 后端地基验收（rf-backend / t_b39963aa）

前置：T2 的 `config.py / session.py / models` 已合并则直接复用；未合并则先自建最小版本（merge 以 T2 为准），**提交前先 `git pull`**。

| ID | 验收标准 | 验收命令 | 期望结果 |
| :--- | :--- | :--- | :--- |
| AC-BE-01 | FastAPI 入口 `app/main.py`（CORS + `/healthz`）可启动 | `cd backend && uvicorn app.main:app --port 8000 & sleep 3 && curl -s http://127.0.0.1:8000/healthz` | HTTP 200，返回 `{"status":"ok"}` 类 JSON |
| AC-BE-02 | **注册** `/api/v1/auth/register`：角色 patient/therapist/doctor/admin，密码 bcrypt 哈希入库 | `cd backend && python -m pytest tests/test_auth.py -v`（或 curl POST 后 `grep -c "\\$2" 注册返回`） | 各角色注册成功；密码字段为 bcrypt 哈希（`$2b$...`） |
| AC-BE-03 | **登录** `/api/v1/auth/login` → access+refresh JWT；`/auth/me` 返回角色；`/auth/refresh` 换新 token | `cd backend && python -m pytest tests/test_auth.py -v` | 用例通过；me 返回 role 正确 |
| AC-BE-04 | **创建课程** `POST /api/v1/courses`：事务内双重冲突检测；**患者冲突 → 409**、**康复师冲突 → 409**、**无冲突 → 201**；409 响应体带冲突明细 | `cd backend && python -m pytest tests/test_scheduling.py -v` | 三种场景断言通过；409 响应含冲突课程列表（明细） |
| AC-BE-05 | **SQLite 应用层锁模拟 FOR UPDATE**：scheduling 服务含锁机制 + 注释说明「PG 下启用真行锁 FOR UPDATE」 | `cd backend && grep -n "Lock\|FOR UPDATE\|应用层锁" app/services/scheduling.py` | 有锁实现 + 明确注释（人工评审注释质量） |
| AC-BE-06 | **15min 粒度校验**：`start_at/end_at` 非 15min 对齐 → 422（api.md §11） | `cd backend && python -m pytest tests/test_scheduling.py -k granularity -v` | 422 用例通过 |
| AC-BE-07 | **services/tracking.py 唯一状态入口**：开始上课 → 课程 `ongoing`（记 actual_start_at）+ 患者 `treating` + 位置=治疗室；结束上课 → 课程 `completed`（记 actual_end_at）+ 患者 `ward`；同步写 `course_status_log` / `patient_status_log` | `cd backend && python -m pytest tests/test_courses.py -v`，并查日志表行数 | 用例通过；两条日志表各 ≥1 行（from/to/actor/occurred_at 正确） |
| AC-BE-08 | **权限守卫**：未登录访问受保护路由 → 401；patient 角色访问 admin-only 路由（如 `/api/v1/dashboard/kpis`）→ 403 | `cd backend && python -m pytest tests/test_permissions.py -v` | 401/403 用例通过 |
| AC-BE-09 | **pytest 全量通过**（注册→登录→创建课程→冲突→开始→结束 全链路冒烟） | `cd backend && python -m pytest tests/ -v` | 全部 passed，无 skipped 阻塞项 |
| AC-BE-10 | **HIS 完全独立**：代码禁现 HIS 连接串/表名/接口地址 | `cd backend && grep -rniE 'his_api|hisdb|hospital_info|(^|[^a-z])his([^a-z]|$)' app/ tests/ requirements.txt .env.example 2>/dev/null || echo CLEAN` | 输出 `CLEAN` |
| AC-BE-11 | 提交物：仅 `backend/` 目录，comment 附提交 hash + pytest 输出（通过数）+ 冒烟结果 | `cd .. && git show --stat --oneline HEAD` | 变更仅限 `backend/` |

**T3 出口**：AC-BE-01 ~ AC-BE-11 全部通过（`/auth/logout` 属 api.md 但不在 T3 任务体，M1 可选，不阻塞）。

---

## 4. T4 前端骨架验收（rf-frontend / t_deb32bf0）

前置：T2 + T3 完成后自动放行（kanban 已设 parents）。后端未就绪时可用 mock/TODO 对接，但**不阻塞本任务验收**（构建与 token 落地为主）。

| ID | 验收标准 | 验收命令 | 期望结果 |
| :--- | :--- | :--- | :--- |
| AC-FE-01 | `create-next-app` 骨架（App Router + TypeScript + **Tailwind v4**），**无 `tailwind.config.ts`** | `cd frontend && test ! -f tailwind.config.ts && echo NO_CONFIG` 与 `grep -c '"tailwindcss"' package.json` | `NO_CONFIG`；package.json 含 tailwindcss v4 |
| AC-FE-02 | **路由分组 layout 占位**：`(auth)/(therapist)/(doctor)/(admin)/(patient)` | `cd frontend && find app -name "layout.tsx" \| sort` | 5 个分组 layout 均存在（可按 pages.md 结构） |
| AC-FE-03 | **设计 token 落地**：`globals.css` 的 `@theme` 定义靛蓝主色 `--primary-50/100/200/500/600/700/800`、课程三色 `--pt-500/#3B82F6 --ot-500/#22C55E --st-500/#F97316`、状态色 `--success-500/--warning-500/--danger-500/--neutral-400`、中性色 | `cd frontend && grep -cE "primary-(50|100|200|500|600|700|800)|pt-500|ot-500|st-500|success-500|warning-500|danger-500|neutral-400" app/globals.css` | 计数 ≥ 12（各 token 至少出现一次）；色值与 design-system.md 一致（人工比对） |
| AC-FE-04 | **proxy.ts 路由守卫**（Next.js 16 middleware 正式名，**非 middleware.ts**）：校验 JWT + 角色；未登录 → `/login`；角色不匹配 → `/403` | `cd frontend && test -f proxy.ts && test ! -f middleware.ts && echo PROXY_OK` | `PROXY_OK`；守卫逻辑人工评审（token 读取 + 角色匹配 + 重定向） |
| AC-FE-05 | `lib/api.ts`（fetch 封装，JWT 注入 + 错误处理）、`lib/permissions.ts`（角色工具） | `cd frontend && test -f lib/api.ts && test -f lib/permissions.ts && echo LIB_OK` | `LIB_OK` |
| AC-FE-06 | `/login` 与 `/register` 页面：注册含角色选择卡片（患者/康复师/医生/管理员），对接后端 API（或 mock/TODO 标注） | `cd frontend && test -f "app/(auth)/login/page.tsx" && test -f "app/(auth)/register/page.tsx" && echo PAGES_OK` | `PAGES_OK`；角色卡片含 4 角色（人工评审） |
| AC-FE-07 | **`npm run build` 通过**（Next.js 16 编译全路由） | `cd frontend && npm run build` | 构建成功（Route 全部 compiled，无类型错误） |
| AC-FE-08 | **与 CCN 视觉区分**：不用 teal 主色（`#14B8A6` 系） | `cd frontend && grep -riE "14B8A6|teal" app lib proxy.ts components 2>/dev/null \|\| echo CLEAN` | 输出 `CLEAN`（或仅注释性提及） |
| AC-FE-09 | **组件只引用 token 不硬编码色值** | `cd frontend && grep -rnE "style=\\{[^}]*#[0-9a-fA-F]{3,6}" app components lib 2>/dev/null \|\| echo NO_HARDCODE` | `NO_HARDCODE`（人工评审兜底） |
| AC-FE-10 | 提交物：仅 `frontend/` 目录，comment 附提交 hash + `npm run build` 输出 | `cd .. && git show --stat --oneline HEAD` | 变更仅限 `frontend/` |

**T4 出口**：AC-FE-01 ~ AC-FE-10 全部通过。

---

## 5. T5 验收测试（rf-qa / t_3b301a6f）

前置：T3 完成（parents 已设）。前端若未完成，构建验证项降级为「记录 N/A，不阻塞报告」。

| ID | 验收标准 | 验收命令 | 期望结果 |
| :--- | :--- | :--- | :--- |
| AC-QA-01 | `docs/qa/test-cases.md`：按功能分组（认证/排课冲突/课程状态机/患者状态机/权限隔离），每条含前置条件/步骤/预期结果 | `test -f docs/qa/test-cases.md` | 文件存在；分组齐全；每条三要素完整（人工评审） |
| AC-QA-02 | **排课冲突**（按 api.md 409 约定）：同一患者同时段两节课 → 409；同一康复师同时段 → 409；无冲突 → 201 | `cd backend && python -m pytest tests/test_scheduling.py -v` | 用例通过，附运行输出 |
| AC-QA-03 | **课程状态机**：创建(scheduled)→开始上课(ongoing)→结束上课(completed)；**患者状态机/软打卡**：开始→treating+位置=治疗室；结束→ward（**按 flows.md 速查表逐项核对**） | `cd backend && python -m pytest tests/test_courses.py -v` | 用例通过；与 flows.md 速查表一致 |
| AC-QA-04 | **权限隔离**：患者访问 `/admin/*` → 403；未登录访问受保护路由 → 401 | `cd backend && python -m pytest tests/test_permissions.py -v` | 用例通过 |
| AC-QA-05 | **前端构建验证**（若前端已完成）：`npm run build` | `cd frontend && npm run build` | 构建成功；若未完成则报告标注 N/A |
| AC-QA-06 | `docs/qa/test-report.md`：**通过率 + 缺陷列表**（🔴阻塞 / 🟡建议 / ⚪疑问，附复现步骤） | `test -f docs/qa/test-report.md` | 文件存在；每结论附运行输出（证据说话） |
| AC-QA-07 | **M1 出口判定**：无 🔴 阻塞缺陷（或阻塞缺陷有明确处理计划与责任人） | 人工评审报告 | 可放行进入 M2 或列出阻断项 |
| AC-QA-08 | 提交物：仅 `docs/qa/` 与 `backend/tests/`，comment 附测试通过数、缺陷摘要、提交 hash | `cd .. && git show --stat --oneline HEAD` | 变更范围符合 |

**T5 出口**：AC-QA-01 ~ AC-QA-08 全部完成（AC-QA-05 允许 N/A）。

> 建议（不阻塞）：SQLite 下单写者限制下，两个管理员并发排同一时段的**最终并发验证在 PG 环境**做（tech-stack.md §3 注意点），M1 记入报告 ⚪ 疑问即可。

---

## 6. 文件归属与冲突规避（M1 并行任务必须遵守）

| 文件/目录 | 归属任务 | 说明 |
| :--- | :--- | :--- |
| `backend/app/core/config.py` | **T2** | T3 复用；若 T2 未合并，T3 先建最小版，merge 以 T2 为准 |
| `backend/app/db/session.py`、`init_db.py` | **T2** | 同上 |
| `backend/app/models/*` | **T2** | 15 表全量 |
| `backend/app/main.py`、`app/api/*` | **T3** | — |
| `backend/app/services/*` | **T3** | scheduling.py + tracking.py（M1 内 courses 执行并入 tracking.py，M2 再拆） |
| `backend/app/core/security.py`、`deps.py` | **T3** | — |
| `backend/tests/*` | **T3 写 / T5 复核扩展** | T5 以运行验证为主 |
| `frontend/*` | **T4** | T4 在 T2+T3 之后放行 |
| `docs/qa/*` | **T5** | test-cases.md / test-report.md |
| `docs/qa/m1-acceptance.md` | **T1（本文档）** | 唯一验收依据 |

**纪律**：T2/T3 并行时，各自提交前 `git pull --rebase origin main`；遇到对方文件已合并，优先复用而非重写。

---

## 7. M1 出口条件（全部满足 → 进入 M2 排课闭环）

1. T2：AC-DB-01~14 全过（15 表 + 种子 + Alembic 两库可跑）。
2. T3：AC-BE-01~11 全过（auth + 409 冲突检测 + tracking 状态机 + 权限 401/403 + pytest 全绿）。
3. T4：AC-FE-01~10 全过（token 落地 + proxy.ts 守卫 + 登录注册 + build 通过）。
4. T5：AC-QA-01~08 完成，test-report 无 🔴 阻塞（或阻塞有处理计划）。
5. 每任务 comment 附提交 hash 与关键验证输出。

---

## 8. 修订记录

| 版本 | 日期 | 内容 |
| :--- | :--- | :--- |
| v1.0 | 2026-08-05 | 初版：通读 11 份文档产出验收清单；修正 structure.md §4（15 表）与 flows.md 速查表（排课成功患者状态不变）；记录 5 项一致性裁决 |
