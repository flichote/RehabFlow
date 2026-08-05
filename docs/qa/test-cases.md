# RehabFlow M1 验收测试用例（test-cases）

- 版本：v1.1（全量复测基线 = HEAD `19b841f`，28/28 全绿）
- 日期：2026-08-05
- 作者：rf-qa（T5）
- 验收依据：`docs/qa/m1-acceptance.md` §5（AC-QA-01~08）+ `docs/design/flows.md` 状态速查表 + `docs/api.md` §10/§11
- 配套运行证据：`docs/qa/pytest_m1_run.txt`（`pytest tests/ -v` 原始输出，28 passed）

## 0. 说明

- 技术栈：pytest + TestClient（fastapi.testclient），测试库独立 SQLite（`backend/tests/_test_rehabflow.db`，不污染开发库）
- 用例按功能分 5 组：**认证 / 排课冲突 / 课程状态机 / 患者状态机 / 权限隔离**，另加全链路烟测
- 每条用例含：前置条件 / 步骤 / 预期结果
- 执行结果栏：✅ 通过 / ❌ 失败（对应缺陷编号 BUG-x，见 test-report）
- **全量结果**：28/28 passed（`backend/.venv/Scripts/python.exe -m pytest tests/ -v`，18.26s）
  - 首轮（HEAD `f62cd60`）19/28（9 failed：BUG-1~4）
  - 复测基线（HEAD `19b841f`，主控已提交 BUG-1~5 修复）28/28 全绿

---

## 1. 认证（auth）

### T-AUTH-01 注册四角色
- 前置：空测试库；`client` fixture 已建表+种子
- 步骤：以 patient/therapist/doctor/admin 各注册一个用户（`POST /api/v1/auth/register`）
- 预期：4 次均 201；返回 `{"message": "User registered", "user_id": N}`
- 结果：✅ 通过（`test_register_all_roles`）

### T-AUTH-02 重复用户名注册 → 409
- 前置：已有用户 `dup_user`
- 步骤：再次以同名注册
- 预期：409（api.md §11 用户名冲突）
- 结果：✅ 通过（`test_register_duplicate_username_409`）

### T-AUTH-03 非法角色 → 422
- 前置：无
- 步骤：注册 `role="superman"`
- 预期：422（schemas 正则 `^(patient|therapist|doctor|admin)$`）
- 结果：✅ 通过（`test_register_invalid_role_422`）

### T-AUTH-04 登录 + me 返回角色
- 前置：已注册 doctor 用户
- 步骤：`POST /auth/login` → `GET /auth/me`（带 Bearer）
- 预期：login 200 返回 access+refresh token；me 200 且 `role == "doctor"`
- 结果：✅ 通过（`test_login_and_me_returns_role`）

### T-AUTH-05 错误密码登录 → 401
- 前置：已注册用户 `pwd_check`
- 步骤：错误密码登录
- 预期：401
- 结果：✅ 通过（`test_login_wrong_password_401`）

### T-AUTH-06 未登录访问 /auth/me → 401
- 前置：无 token
- 步骤：`GET /api/v1/auth/me`
- 预期：401（HTTPBearer）
- 结果：✅ 通过（`test_me_without_token_401`）

### T-AUTH-07 refresh token 换新
- 前置：已注册并登录，持有 refresh_token
- 步骤：`POST /auth/refresh` 传 refresh_token
- 预期：200 返回新 access + refresh
- 结果：✅ 通过（`test_refresh_token_flow`；首轮 BUG-1 hash_token 未导入 + BUG-5 同秒重复 token → UNIQUE 冲突 500，均由主控 `19b841f` 修复：`auth.py` 补 import、`security.py` refresh token 加 `jti=uuid4().hex`）

### T-AUTH-08 用 access token 冒充 refresh → 401
- 前置：已登录，持有 access_token
- 步骤：`POST /auth/refresh` 传 access_token
- 预期：401（token type 校验）
- 结果：✅ 通过（`test_refresh_with_access_token_401`）

---

## 2. 排课冲突（scheduling）

> 依据 api.md §11：409 冲突响应体带冲突明细列表；时间参数 ISO8601（UTC）。

### T-SCH-01 无冲突创建 → 201
- 前置：种子数据（患者陈明 / 康复师张伟 / PT大厅）；管理员登录
- 步骤：`POST /api/v1/courses`（未来时段 09:00-10:00）
- 预期：201；`status == "scheduled"`；`actual_start_at is None`
- 结果：✅ 通过（`test_create_course_no_conflict_201`）

### T-SCH-02 同一患者同一时段 → 409
- 前置：T-SCH-01 已创建一节课
- 步骤：同一患者/同一康复师/完全相同的起止时间再次创建
- 预期：409；`detail.error == "patient_conflict"`；`detail.conflicts` 含 `conflicting_course_id`
- 结果：✅ 通过（复测 28/28；首轮 BUG-3 UTC 漏检已由主控 `19b841f` 修复：`schemas.py` 输入统一转 UTC、`scheduling._as_utc` naive 按 UTC 解释）
  - 复现（首轮）：`make_time()` 默认 `timezone.utc`（`isoformat()` 输出 `+00:00`）；SQLite 存 UTC 墙上时间，旧 `scheduling._as_utc` 把 naive 当 `APP_TZ(+08:00)` 补 8 小时 → 与请求的 UTC 比较偏移 8 小时 → 不重叠 → 误报 201
  - 补充证据：传入 `+08:00` 时区（本地时间）再试 → 409 正常（见 `test-report` ⚪Q-2）

### T-SCH-03 同一康复师同一时段（不同患者）→ 409
- 前置：T-SCH-02 同款，患者换成种子「刘芳」
- 步骤：同一康复师/同一时段，不同患者创建
- 预期：409；`detail.error == "therapist_conflict"`
- 结果：✅ 通过（`test_therapist_conflict_same_time_409`，修复后）

### T-SCH-04 同一患者不同时段 → 201
- 前置：已创建 09:00-10:00 课程
- 步骤：同患者 14:00-15:00 再建一节
- 预期：201（不误报冲突）
- 结果：✅ 通过（`test_patient_different_time_no_conflict_201`）

### T-SCH-05 非 15min 粒度 → 422
- 前置：管理员登录
- 步骤：`start_at=09:07` 创建课程
- 预期：422（api.md §11 粒度校验）
- 结果：✅ 通过（`test_course_15min_granularity_422`）

### T-SCH-06 end_at <= start_at → 422
- 前置：管理员登录
- 步骤：`end_at` 早于 `start_at`
- 预期：422（`end_after_start` validator）
- 结果：✅ 通过（`test_course_end_before_start_422`）

### T-SCH-07 非管理员创建 → 403
- 前置：patient 登录
- 步骤：patient token 调 `POST /api/v1/courses`
- 预期：403（`require_role("admin")`）
- 结果：✅ 通过（`test_create_course_requires_admin_403`）

---

## 3. 课程状态机（course state machine）

> 依据 flows.md 速查表：排课成功→scheduled；开始上课→ongoing；结束上课→completed。

### T-CRS-01 创建→开始→结束 全生命周期
- 前置：独立 actor_set（admin+therapist+patient，隔离数据）
- 步骤：
  1. admin 创建课程 → 查库 `status == "scheduled"`，`actual_start_at/end_at` 为空
  2. therapist 调 `POST /courses/{id}/start` → 200，`status == "ongoing"`，`actual_start_at` 非空
  3. therapist 调 `POST /courses/{id}/finish` → 200，`status == "completed"`，`actual_end_at` 非空，`minutes_consumed > 0`
- 预期：三态流转 + 实际时间记录
- 结果：✅ 通过（`test_course_state_machine_scheduled_ongoing_completed`；首轮 BUG-2 finish naive/aware 相减 TypeError 已由主控修复：`tracking.py` 加 `_as_utc()`）

### T-CRS-02 重复开始（ongoing 再 start）→ 4xx
- 前置：课程已开始
- 步骤：再次 `POST /courses/{id}/start`
- 预期：4xx（409/400），不应 500
- 结果：✅ 通过（`test_start_requires_scheduled_only`；首轮 BUG-4 裸 ValueError→500 已改 HTTPException 409）

### T-CRS-03 未开始直接 finish → 4xx
- 前置：课程刚创建（scheduled）
- 步骤：直接 `POST /courses/{id}/finish`
- 预期：4xx（409/400），不应 500
- 结果：✅ 通过（`test_finish_requires_ongoing_only`，修复后）

---

## 4. 患者状态机 / 软打卡（patient state machine）

> 依据 flows.md 速查表：开始上课→患者 treating+位置=治疗室；结束上课→患者 ward+位置=病房；
> 排课成功**不改变**患者状态（裁决-1，不得断言「待排课」）。

### T-PAT-01 排课成功患者状态不变
- 前置：独立患者（注册 patient 账号建档案，初始 ward）
- 步骤：admin 为其创建课程后查 `patients.status`
- 预期：仍为 `ward`
- 结果：✅ 通过（`test_patient_soft_checkin_treating_ward` 中 `p0.status == "ward"` 断言通过）

### T-PAT-02 开始上课 → treating + 位置=治疗室
- 前置：课程已创建（T-PAT-01 后）
- 步骤：therapist `POST /courses/{id}/start`
- 预期：患者 `status == "treating"`；`patient_status_log` 最新一条 `to_status=="treating"`、`location=="PT大厅"`、`source=="course_action"`
- 结果：✅ 通过（start 部分断言成功）

### T-PAT-03 结束上课 → ward + 位置=病房
- 前置：课程已开始（treating）
- 步骤：therapist `POST /courses/{id}/finish`
- 预期：患者 `status == "ward"`；日志 `to_status=="ward"`、`location=="住院部3楼5床"`、`source=="course_action"`
- 结果：✅ 通过（BUG-2 修复后 finish 正常）

### T-PAT-04 状态日志双写（course_status_log + patient_status_log）
- 前置：完整走完 start→finish
- 步骤：查两张日志表
- 预期：course_status_log ≥2 行，含 `(scheduled→ongoing)` 与 `(ongoing→completed)`，actor_id 非空；patient_status_log 含 `(ward→treating, PT大厅)` 与 `(treating→ward, 住院部3楼5床)`
- 结果：✅ 通过（`test_status_logs_written`，BUG-2 修复后双日志断言通过）

---

## 5. 权限隔离（permissions）

> 依据 architecture.md §4.4：管理员全量 / 康复师名下课程 / 未登录 401 / 角色无权 403。

### T-PERM-01 未登录访问受保护路由 → 401
- 前置：无 token
- 步骤：`GET /auth/me`、`POST /courses`
- 预期：均 401
- 结果：✅ 通过（`test_unauthenticated_protected_routes_401`）

### T-PERM-02 patient 访问 admin-only → 403
- 前置：patient 登录
- 步骤：patient token 调 `POST /api/v1/courses`（admin-only）
- 预期：403
- 结果：✅ 通过（`test_patient_access_admin_route_403`）

### T-PERM-03 therapist 访问 admin-only → 403
- 前置：therapist 登录
- 步骤：therapist token 调 `POST /api/v1/courses`
- 预期：403
- 结果：✅ 通过（`test_therapist_access_admin_route_403`）

### T-PERM-04 doctor 访问 admin-only → 403
- 前置：doctor 登录
- 步骤：doctor token 调 `POST /api/v1/courses`
- 预期：403
- 结果：✅ 通过（`test_doctor_access_admin_route_403`）

### T-PERM-05 康复师不能操作他人课程 → 403
- 前置：种子康复师张伟的课程；登录另一康复师李娜（ot_li）
- 步骤：李娜调 `POST /courses/{id}/start`（张伟名下课程）
- 预期：403（`_check_therapist_access`）
- 结果：✅ 通过（`test_therapist_cannot_start_other_therapists_course_403`）

### T-PERM-06 康复师可操作自己课程 → 200
- 前置：种子康复师张伟的课程；登录张伟（pt_zhang）
- 步骤：张伟调 `POST /courses/{id}/start`
- 预期：200
- 结果：✅ 通过（`test_own_therapist_can_start_200`）

### T-PERM-07 管理员可操作任意课程 → 200
- 前置：管理员登录
- 步骤：管理员调 `POST /courses/{id}/start`
- 预期：200
- 结果：✅ 通过（`test_admin_can_start_any_course_200`）

---

## 6. 全链路烟测（smoke）

### T-SMOKE-01 注册→登录→排课→开始→结束→日志
- 前置：独立账号
- 步骤：注册 admin/therapist → me 校验 → admin 排课（种子张伟）→ pt_zhang 开始 → pt_zhang 结束 → 查 course_status_log 行数
- 预期：全程 2xx；日志 ≥2 行
- 结果：✅ 通过（`test_full_chain_smoke`；首轮 BUG-2 finish 500 已由主控修复）

---

## 7. 缺陷-用例映射（全部已修复，基线 19b841f）

| 缺陷 | 级别 | 位置 | 影响用例 | 修复提交 |
| :--- | :--- | :--- | :--- | :--- |
| BUG-1 | 🔴 阻塞 | `app/api/v1/auth.py:129` 未导入 `hash_token` | T-AUTH-07 | `19b841f` |
| BUG-2 | 🔴 阻塞 | `app/services/tracking.py` finish 时区 naive/aware 相减 | T-CRS-01 / T-PAT-03 / T-PAT-04 / T-SMOKE-01 | `19b841f` |
| BUG-3 | 🔴 阻塞 | `app/services/scheduling.py:_as_utc` UTC 输入偏移 8h → 冲突漏检 | T-SCH-02 / T-SCH-03 | `19b841f` |
| BUG-4 | 🟡 建议 | `app/services/tracking.py` 裸 ValueError → 500 | T-CRS-02 / T-CRS-03 | `19b841f` |
| BUG-5 | 🟡 建议 | `app/core/security.py:create_refresh_token` 无 jti → 同秒重复 token → 500 | T-AUTH-07 | `19b841f` |

> 详细复现步骤与修复建议见 `docs/qa/test-report.md` §3 缺陷清单。
