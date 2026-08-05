# RehabFlow M1 验收测试报告（test-report）

- 版本：v1.2（终版 —— 全量复测基线 HEAD `19b841f`，28/28 全绿）
- 日期：2026-08-05
- 作者：rf-qa（T5）
- 执行环境：Windows 10 / Python 3.11.14 / pytest 9.1.1 / FastAPI 0.133.1 / SQLAlchemy 2.0.51 / SQLite（aiosqlite）
- 验收依据：`docs/qa/m1-acceptance.md` §5（AC-QA-01~08）
- 用例文档：`docs/qa/test-cases.md`
- 原始运行输出：`docs/qa/pytest_m1_run.txt`

---

## 1. 总览

| 项目 | 结果 |
| :--- | :--- |
| 测试用例数 | 28（认证 8 / 排课冲突 7 / 课程状态机 3 / 患者状态机 4 / 权限隔离 7 / 烟测 1） |
| 通过 | **28** |
| 失败 | **0** |
| 通过率 | **100%**（28/28） |
| 阻塞缺陷 | **0 项 🔴** |
| 遗留缺陷 | **0 项**（首轮 9 failed 对应 BUG-1~5 已全部由主控提交 `19b841f` 修复并复测通过） |
| M1 出口判定 | **✅ 通过** —— AC-QA-01~08 全绿，无 🔴 阻塞、无遗留缺陷 |

> 说明（v1.1 → v1.2 变更）：v1.1 时 BUG-5（refresh token 唯一性）尚在 rf-backend 工作树待提交，报告为 27/28、有条件通过。主控随后提交 `19b841f`（含 BUG-1~5 修复 + 测试文件入库），本版在 HEAD `19b841f` 上重跑全量：**28/28 passed**；同时 T4 前端已提交（`19d504e`）且 `npm run build` 通过，AC-QA-05 由 N/A 转 ✅。

### 运行命令与输出

```bash
cd backend && .venv/Scripts/python.exe -m pytest tests/ -v
```

```
============================= 28 passed in 18.26s =============================
```

完整输出见 `docs/qa/pytest_m1_run.txt`。

前端构建（AC-QA-05）：

```bash
cd frontend && npm run build
```

```
✓ Compiled successfully in 578ms
✓ Generating static pages using 19 workers (24/24) in 436ms
Route (app): 24 条静态路由（/login /register /patient/* /therapist/* /admin/* /doctor/* 等）
ƒ Proxy (Middleware)   ← proxy.ts 路由守卫已启用
```

### AC-QA 逐项结论

| ID | 验收项 | 结论 |
| :--- | :--- | :--- |
| AC-QA-01 | test-cases.md 分组齐全、三要素完整 | ✅ 见 `docs/qa/test-cases.md`（5 组 + 烟测，每条含前置/步骤/预期） |
| AC-QA-02 | 排课冲突：同患者→409 / 同康复师→409 / 无冲突→201 | ✅ 3 场景全过（BUG-3 修复后；409 响应体含冲突明细） |
| AC-QA-03 | 课程状态机 + 患者软打卡（按 flows.md 速查表） | ✅ scheduled→ongoing→completed、treating→ward+位置流转、双日志均通过 |
| AC-QA-04 | 权限隔离：患者访问 /admin/*→403；未登录→401 | ✅ 401/403 全部通过（7/7）；注：M1 后端无字面 `/admin/*` 前缀路由，以 admin-only 的 `POST /api/v1/courses` 验证 403（见 ⚪Q-3） |
| AC-QA-05 | 前端构建（若完成） | ✅ `npm run build` 通过（24 静态路由 + proxy middleware）；v1.1 的 Suspense prerender 报错已随 T4 提交 `19d504e` 修复 |
| AC-QA-06 | test-report.md 通过率 + 缺陷列表 | ✅ 本文档 |
| AC-QA-07 | M1 出口判定：无 🔴 阻塞 | ✅ 通过（无 🔴；遗留 🟡 BUG-5 亦已修复） |
| AC-QA-08 | 提交物：仅 docs/qa/ 与 backend/tests/ | ✅ 见 §7 提交清单（backend/tests/ 由主控随 `19b841f` 入库，本任务补 docs/qa/） |

---

## 2. 通过用例（28/28）

| 分组 | 用例 |
| :--- | :--- |
| 认证（8） | 注册四角色 / 重复用户名 409 / 非法角色 422 / 登录+me 角色 / 错误密码 401 / 未登录 me 401 / refresh 换新 / access 冒充 refresh 401 |
| 排课冲突（7） | 无冲突 201 / 同患者同时段 409 / 同康复师同时段 409 / 同患者不同时段 201 / 15min 粒度 422 / end<=start 422 / 非管理员 403 |
| 课程状态机（3） | 创建→开始→结束 全生命周期 / 重复开始 409 / 未开始 finish 409 |
| 患者状态机（4） | 排课成功状态不变（ward）/ 开始→treating+治疗室 / 结束→ward+病房 / 双日志写 |
| 权限隔离（7） | 未登录 401 ×2 / patient 403 / therapist 403 / doctor 403 / 康复师操作他人课程 403 / 自己课程 200 / 管理员 200 |
| 烟测（1） | 注册→登录→排课→开始→结束→日志 |

---

## 3. 缺陷清单（全部已修复，复测通过）

> 首轮（HEAD `f62cd60`）9 failed，定位 5 个缺陷；主控提交 `19b841f`（4 文件 + tests 入库）全部修复。以下为历史记录，复测基线 `19b841f` 上 28/28 全绿。

### ✅ BUG-1（🔴，已修复）：`/api/v1/auth/refresh` 500 —— `hash_token` 未导入
- **位置**：`backend/app/api/v1/auth.py:129` 调用 `hash_token` 但 import 缺失 → NameError → 500
- **复现**：`POST /auth/refresh` 传合法 refresh token → 500
- **修复**：`19b841f` 补 `hash_token` import（+1 行）
- **复测**：`test_refresh_token_flow`、`test_refresh_with_access_token_401` 通过

### ✅ BUG-2（🔴，已修复）：`/courses/{id}/finish` 500 —— naive/aware datetime 相减 TypeError
- **位置**：`backend/app/services/tracking.py:140` `now - course.actual_start_at`（now aware、actual_start_at 从 SQLite 读回 naive）→ TypeError → 500
- **复现**：therapist 对 ongoing 课程调 `POST /courses/{id}/finish` → 500
- **修复**：`19b841f` tracking 新增 `_as_utc()`，`delta = _as_utc(now) - _as_utc(actual_start_at)`
- **复测**：`test_course_state_machine_*`、`test_patient_soft_checkin_*`、`test_status_logs_written`、`test_full_chain_smoke` 全部通过

### ✅ BUG-3（🔴，已修复）：排课冲突检测在 UTC 输入下漏检（同患者/同康复师同时段返回 201 而非 409）
- **位置**：`backend/app/services/scheduling.py:_as_utc` —— SQLite `DateTime(timezone=True)` 存储丢时区，旧逻辑把 naive 一律按 `APP_TZ(+08:00)` 补时区，导致 UTC 输入偏移 8 小时 → 不重叠 → 漏检
- **复现**：以 `timezone.utc` 的 ISO8601 创建两节同患者同起止课程 → 第二次 201（应为 409）；同场景改传 `+08:00` → 409 正常
- **修复**：`19b841f` `schemas.py` CourseCreate validator 输入统一转 UTC（naive 按 APP_TZ 补后转 UTC、aware 直接转 UTC）；`scheduling._as_utc` naive 按 UTC 解释
- **复测**：`test_patient_conflict_same_time_409`、`test_therapist_conflict_same_time_409` 通过

### ✅ BUG-4（🟡，已修复）：状态机守卫抛裸 ValueError → 500（应 4xx）
- **位置**：`backend/app/services/tracking.py` start/finish 状态非法时 `raise ValueError` → FastAPI 500
- **复现**：ongoing 课程再 `start` / scheduled 课程直接 `finish` → 500
- **修复**：`19b841f` 改为 `HTTPException(409_CONFLICT, ...)`
- **复测**：`test_start_requires_scheduled_only`、`test_finish_requires_ongoing_only` 通过（409）

### ✅ BUG-5（🟡，已修复）：refresh token 无随机性 → 同秒内生成相同 token → 500
- **位置**：`backend/app/core/security.py:create_refresh_token`（payload 仅 `{sub, exp, type}`，无 `jti`/随机数）+ `refresh_tokens.token_hash` UNIQUE 约束
- **根因**：refresh token 由 JWT 生成，payload 不含随机分量；同一用户同秒内两次登录（或登录后立即 refresh），`exp` 秒级相同 → token 完全相同 → SHA-256 hash 相同 → 第二次 `INSERT refresh_tokens` 触发 UNIQUE 冲突 → 500
- **复现**：
  1. 注册并登录，拿到 refresh_token
  2. **同一秒内**再次登录（或 `POST /auth/refresh` 传上一步 token）
  3. 第二次 → 500（`sqlite3.IntegrityError: UNIQUE constraint failed: refresh_tokens.token_hash`）
  - 独立探针确认：连续登录两次，两 token 完全相等（`same refresh token? True`）
- **修复**：`19b841f` `create_refresh_token` payload 增加 `"jti": uuid4().hex`，保证每次 token 唯一
- **复测**：`test_refresh_token_flow` 通过（连续登录/refresh 不再 500）

---

## 4. 疑问（⚪，非阻塞）

| # | 疑问 | 说明 |
| :--- | :--- | :--- |
| ⚪Q-1 | 并发排课事务验证 | 探针在 SQLite 单写者锁下超时（120s 无响应），符合 m1-acceptance §5 建议「最终并发验证放 PG（tech-stack.md §3 注意点）」。当前 `_scheduling_lock` 应用层锁在 SQLite 可用；PG FOR UPDATE 语义待生产库验证 |
| ⚪Q-2 | BUG-3 时区行为差异证据 | 同一场景 +08:00 输入 → 409 正常，UTC 输入 → 201 漏检（首轮）；已在 BUG-3 复现步骤记录。测试一律按 api.md 约定传 UTC，修复后以 UTC 行为为准（409） |
| ⚪Q-3 | 「患者访问 /admin/* → 403」路由语义 | M1 后端 router 仅含 auth + courses（`app/api/v1/router.py`），无字面 `/admin/*` 前缀路由（`/admin/audit-log` 等在 api.md §9 但未实现）。403 验证以 admin-only 的 `POST /api/v1/courses`（`require_role("admin")`）等价覆盖，7/7 通过。前端 `/admin/*` 由 proxy.ts 路由守卫保护（build 通过） |
| ⚪Q-4 | 前端构建（已解决） | v1.1 记录 `/login` 页 `useSearchParams()` 缺 Suspense 边界 → prerender error；T4 提交 `19d504e` 后 `npm run build` 通过（24 路由）。本版 AC-QA-05 转 ✅ |

---

## 5. 建议（非阻塞）

1. **时区归一化收敛**：`tracking.py` 与 `scheduling.py` 目前各自实现 `_as_utc`，建议抽取共用工具（如 `app/core/timeutil.py`），避免两处行为分叉。
2. **状态机守卫层**：tracking 服务内所有状态非法转换统一抛业务异常（409），API 层兜底映射，禁止裸 `ValueError` 冒泡成 500（已修，建议固化为约定）。
3. **冲突响应体回归**：BUG-3 修复后建议补充回归用例（UTC 输入 × 患者/康复师/边界重叠），已固化在 `tests/test_scheduling.py`。
4. **并发排课**：按 tech-stack §3 在 PG 环境补 FOR UPDATE 并发用例（当前 SQLite 单写者下无法有效验证）。
5. **refresh token 轮换**：BUG-5 修复后建议后续迭代实现 refresh token 轮换/吊销（当前 jti 仅保证唯一性，未做单次使用校验）。

---

## 6. 复测基线（终版）

```bash
cd backend && rm -f tests/_test_rehabflow.db && .venv/Scripts/python.exe -m pytest tests/ -v
```

结果：**28/28 passed**（`pytest_m1_run.txt`，2026-08-05 13:59 复测，HEAD `19b841f`）。AC-QA-01~08 全绿。

---

## 7. 提交物

- `docs/qa/test-cases.md` —— M1 测试用例文档（AC-QA-01）
- `docs/qa/test-report.md` —— 本报告（AC-QA-06）
- `docs/qa/pytest_m1_run.txt` —— pytest 原始运行输出（证据，28 passed）
- `backend/tests/conftest.py`、`test_auth.py`、`test_scheduling.py`、`test_courses.py`、`test_permissions.py`、`test_smoke.py` —— pytest 自动化用例（已由主控随 `19b841f` 入库）
