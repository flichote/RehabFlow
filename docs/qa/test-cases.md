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

---

---

# RehabFlow M2 验收测试用例（test-cases — M2 追加）

- 版本：v1.0（M2 追加；全量复测基线 HEAD `9e9f2f5`，98 用例：95 通过 / 3 失败）
- 日期：2026-08-05
- 作者：rf-qa（T9）
- 验收依据：`docs/PRD.md` §3 页面功能 / §5 消息提醒、`docs/api.md` §2-§8 新增接口、`docs/design/flows.md` 状态速查表、T9 任务体
- 配套运行证据：`docs/qa/pytest_m2_run.txt`（`pytest tests/ -v` 原始输出，98 tests：95 passed / 3 failed）
- M1 基线：上文 28 条全绿（`19b841f`）；T8 新增通知/预警测试（`775b60a`/`4580202`）；T10 新增看板/患者360 测试（`9e9f2f5`）
- 分组：**查询 API / 排课日历 / 我的课表 / 通知 / 预警 / 定时任务**，另加 M2 全链路烟测
- 结果说明：❌ 用例为**验收失败**，对应缺陷 BUG-6/7/8（见 `docs/qa/test-report-m2.md` §3），属当前实现缺口，等待主控修复后转 ✅

## 8. 查询 API（M2 新增接口）

### T-QRY-01 管理员查课程列表 → 200（total + items）
- 前置：管理员登录；独立 actor_set
- 步骤：`GET /api/v1/courses`（带 Bearer）
- 预期：200；`total >= 1`；`items` 每条含 id/patient_id/therapist_id/room_id/course_type/start_at/end_at/status
- 结果：✅ 通过（`test_admin_list_courses_200`）

### T-QRY-02 康复师只见名下课程（数据权限）
- 前置：管理员为某康复师创建课程
- 步骤：该康复师登录后 `GET /api/v1/courses`
- 预期：200；`items` 中每条 `therapist_id == 本人`
- 结果：✅ 通过（`test_therapist_only_sees_own_courses`）

### T-QRY-03 管理员按康复师/组别/治疗室/时间段过滤
- 前置：管理员登录
- 步骤：`GET /courses?therapist_id=…`、`?group=PT`、`?room_id=…`、`?from=…&to=…`
- 预期：200；返回均满足过滤条件（组别过滤 PT 组只含 course_type=PT）
- 结果：✅ 通过（`test_admin_can_filter_by_therapist_id` / `_by_group` / `_by_room_id` / `_by_date_range`）

### T-QRY-04 课程详情含名称（患者/康复师/治疗室）
- 前置：已有课程
- 步骤：`GET /api/v1/courses/{id}`
- 预期：200；`patient_name` / `therapist_name` / `room_name` 非空
- 结果：✅ 通过（`test_admin_get_course_detail_200`）

### T-QRY-05 康复师不能查看他人课程详情 → 403
- 前置：种子康复师张伟的课程；另一康复师李娜登录
- 步骤：李娜 `GET /courses/{张伟的课程}`
- 预期：403（数据权限隔离）
- 结果：✅ 通过（`test_therapist_cannot_get_other_course_detail`）

### T-QRY-06 资源树（排课日历支撑）
- 前置：管理员登录
- 步骤：`GET /api/v1/scheduler/resources`
- 预期：200；`therapists` 含 PT/OT/ST 分组；`rooms` 含治疗室（id/name/room_type/is_active）
- 结果：✅ 通过（`test_admin_get_resources_200`）

### T-QRY-07 待排患者池排除今日有课患者
- 前置：管理员登录
- 步骤：为患者创建今日课程 → `GET /api/v1/scheduler/pool`
- 预期：200；该患者不在 pool 的 `items` 中
- 结果：✅ 通过（`test_pool_excludes_patients_with_courses_today`）

### T-QRY-08 查询类接口权限：非管理员 403 / 未登录 401
- 前置：无
- 步骤：康复师访问 `/scheduler/resources` → 403；无 token 访问 → 401
- 预期：403 / 401
- 结果：✅ 通过（`test_non_admin_cannot_access_resources` / `test_unauthorized_cannot_access_resources`）

## 9. 排课日历（后端支撑 + 前端构建）

### T-CAL-01 日历查询接口（from/to 区间）
- 前置：管理员登录；2030-03-12 有课
- 步骤：`GET /courses?from=2030-03-12T09:00:00&to=2030-03-12T12:00:00`
- 预期：200；`total >= 1`
- 结果：✅ 通过（`test_admin_can_filter_by_date_range`）

### T-CAL-02 排课日历页前端构建（T7 交付复核）
- 前置：`frontend/` 依赖已装
- 步骤：`cd frontend && npm run build`
- 预期：`✓ Compiled successfully`；24 条静态路由（含 `/admin/scheduler` 排课日历、`/therapist/schedule` 我的课表）；Proxy 路由守卫启用
- 结果：✅ 通过（2026-08-05 复测，见 test-report-m2 §5；路由数 24）

## 10. 我的课表（therapist/schedule）

### T-SCHED-01 课表聚合 → 200（overview + items + free_slots）
- 前置：某康复师当日两节课（09:00-09:45、11:00-11:45，中间 60min 空档）
- 步骤：`GET /api/v1/therapist/schedule?date=YYYY-MM-DD`
- 预期：200；`overview.total >= 2`；`items` 含 course_id/start_at/end_at/patient_name/course_type/room_name/status；`free_slots` 非空且 `minutes > 15`
- 结果：✅ 通过（`test_therapist_schedule_200_with_free_slots`）

### T-SCHED-02 15 分钟空档不产生 free_slots
- 前置：两节课间隔恰 15min（09:45 结束、10:00 开始）
- 步骤：同上查询
- 预期：`free_slots` 中无 `minutes == 15` 条目（空闲时段须 > 15min）
- 结果：✅ 通过（`test_schedule_small_gaps_not_free_slots`）

### T-SCHED-03 课表仅显示本人课程（数据权限）
- 前置：张伟有课；李娜登录
- 步骤：李娜 `GET /therapist/schedule?date=张伟有课日`
- 预期：200；`overview.total == 0`（看不到他人课程）
- 结果：✅ 通过（`test_schedule_only_own_courses`）

### T-SCHED-04 课表接口权限：管理员 403 / 未登录 401
- 前置：无
- 步骤：管理员访问 → 403；无 token → 401
- 预期：403 / 401
- 结果：✅ 通过（`test_non_therapist_cannot_access_schedule` / `test_unauthorized_cannot_access_schedule`）

## 11. 通知（notifications）

### T-NOT-01 创建课程写 notifications（患者 + 康复师 course_new）
- 前置：管理员登录；独立 actor_set
- 步骤：`POST /api/v1/courses` 创建课程 → 康复师 `GET /notifications`；查库患者通知
- 预期：康复师与患者各收到 ≥1 条 `type == "course_new"`（PRD §5 行1：排课成功后自动推送）
- 结果：❌ 失败（`test_create_course_writes_course_new_notifications`）→ **BUG-6** 🔴：`send_course_new_notifications` 定义但从未被调用，`POST /courses` 不写任何通知

### T-NOT-02 通知列表未读优先 + unread_count
- 前置：一键提醒产生通知
- 步骤：`GET /notifications`、`GET /notifications/unread-count`
- 预期：200；`total >= 1`、`unread_count >= 1`；列表未读在前（排序校验）
- 结果：✅ 通过（`test_list_notifications_unread_first` / `test_unread_count`）

### T-NOT-03 标记单条已读 / 全部已读
- 前置：存在未读通知
- 步骤：`POST /notifications/{id}/read`；`POST /notifications/read-all`
- 预期：200；单条后该条 `is_read == true`；全部后 `unread_count == 0`
- 结果：✅ 通过（`test_mark_read` / `test_mark_all_read`）

### T-NOT-04 不能标记他人通知 → 404
- 前置：康复师有通知；管理员登录
- 步骤：管理员 `POST /notifications/{康复师的通知}/read`
- 预期：404（数据权限：只能操作自己的通知）
- 结果：✅ 通过（`test_mark_read_not_own`）

### T-NOT-05 通知仅返回本人（数据权限）
- 前置：一键提醒只发给康复师/患者
- 步骤：管理员 `GET /notifications`
- 预期：200；列表不含发给康复师/患者的提醒（`course_reminder*`）
- 结果：✅ 通过（`test_list_notifications_only_own`）

### T-NOT-06 一键提醒 → 通知 + 状态流转（reminded/en_route）
- 前置：已创建课程
- 步骤：康复师 `POST /courses/{id}/remind`
- 预期：200；课程 `status == "reminded"`；患者 `status == "en_route"`；通知含 `course_reminder*`
- 结果：✅ 通过（`test_remind_creates_notifications_and_transitions`）

## 12. 预警（alerts）

### T-ALT-01 预警列表（?status=open）仅管理员
- 前置：管理员/康复师登录
- 步骤：`GET /alerts?status=open`；康复师 `GET /alerts`
- 预期：管理员 200 且所有项 `status == "open"`；康复师 403
- 结果：✅ 通过（`test_list_alerts_open_only` / `test_list_alerts_admin_only`）

### T-ALT-02 超时课程自动生成 alert + 课程→abnormal
- 前置：构造 start_at 已超 5min 的 scheduled 课程
- 步骤：手动触发 `_overdue_detection()`
- 预期：课程 `status == "abnormal"`；存在 open 的 `course_overdue` 预警
- 结果：✅ 通过（`test_overdue_detection_creates_alert`）

### T-ALT-03 resolve 处理 → resolved（记录处理人）
- 前置：存在 open 预警
- 步骤：管理员 `POST /alerts/{id}/resolve`
- 预期：200；`status == "resolved"`；`resolved_by` 非空
- 结果：✅ 通过（`test_resolve_alert`）

### T-ALT-04 ignore 忽略 → ignored
- 前置：存在 open 预警
- 步骤：管理员 `POST /alerts/{id}/ignore`
- 预期：200；`status == "ignored"`
- 结果：✅ 通过（`test_ignore_alert`）

### T-ALT-05 同课程同类型预警幂等（只 1 条 open）
- 前置：存在课程
- 步骤：对同一课程连续两次 `create_course_overdue_alert`
- 预期：open 预警计数 == 1
- 结果：✅ 通过（`test_alert_idempotent`）

### T-ALT-06 超时后康复师收到 course_overdue 站内信
- 前置：构造超时课程
- 步骤：触发 `_overdue_detection()` → 康复师 `GET /notifications`
- 预期：康复师收到 ≥1 条 `type == "course_overdue"`（PRD §5 行4：超时5min → 康复师、主管医生站内信）
- 结果：❌ 失败（`test_overdue_detection_notifies_therapist`）→ **BUG-7** 🟡：`send_course_overdue_notification` 定义但从未被调用；当前只生成 admin 看板 alert，康复师/医生无站内信

## 13. 定时任务（手动触发，不依赖真实时钟）

> 约束：所有定时任务测试**手动触发 task 函数**，用 `monkeypatch` 注入固定时钟 `FIXED=2030-01-07 09:00 UTC`（巡检用例按生产路径用真实 now，因巡检幂等依赖 DB 真实时钟的 `created_at`）；本模块先停掉后台 APScheduler 避免竞态。

### T-TSK-01 课前15min：scheduled→reminded + 患者→en_route + 双通知
- 前置：课程 start_at = FIXED+15min（窗口内）；monkeypatch `_now`
- 步骤：触发 `_pre_class_reminder()`
- 预期：课程 `reminded`；患者 `en_route`；康复师 1 条 `course_reminder_therapist`、患者 1 条 `course_reminder`
- 结果：✅ 通过（`test_pre_class_reminder_idempotent` 前半）

### T-TSK-02 课前15min 幂等：跑两遍只提醒一次
- 前置：同 T-TSK-01
- 步骤：连续两次触发 `_pre_class_reminder()`
- 预期：`course_status_log` 中 `reminded` 恰 1 条；康复师/患者各恰 1 条提醒（不重复）
- 结果：✅ 通过（`test_pre_class_reminder_idempotent`）

### T-TSK-03 超时5min 幂等：跑两遍只 1 条 open 预警
- 前置：课程 start_at = FIXED-30min；monkeypatch `_now`
- 步骤：连续两次触发 `_overdue_detection()`
- 预期：课程 `abnormal`；open `course_overdue` 预警恰 1 条
- 结果：✅ 通过（`test_overdue_detection_idempotent`）

### T-TSK-04 30min 巡检幂等：跑两遍只 1 条结束确认提醒
- 前置：ongoing 课程 end_at 已过 45min（真实 now 构造）；停后台调度器
- 步骤：连续两次触发 `_patrol_ongoing()`
- 预期：康复师 `course_end_reminder` 恰 1 条
- 结果：✅ 通过（`test_patrol_idempotent`）

## 14. M2 全链路烟测

### T-SMOKE-M2-01 注册→登录→排课→查课表→开始→结束→看通知
- 前置：独立账号
- 步骤：
  1. 注册+登录 admin / therapist；`/auth/me` 校验角色
  2. admin 为种子张伟排两节课（09:00-10:00、11:00-12:00）→ 201
  3. pt_zhang（张伟）`GET /therapist/schedule?date=2030-01-07` → 查课表
  4. pt_zhang `POST /courses/{id}/start` → ongoing
  5. pt_zhang `POST /courses/{id}/finish` → completed
  6. pt_zhang `GET /notifications` + `GET /notifications/unread-count` → 看通知
- 预期：全程 2xx；课表 `overview.total >= 2` 且含刚排课程；`free_slots` 含 60min 空档；通知接口返回结构正确
- 结果：✅ 通过（`test_full_chain_smoke_m2`）
- 备注：当前「看通知」内容为空是 BUG-6 的直接表现（排课不写 course_new 通知），修复后该步应能读到课程通知

## 15. M2 缺陷-用例映射（等待主控修复）

| 缺陷 | 级别 | 位置 | 影响用例 | 期望行为（验收依据） |
| :--- | :--- | :--- | :--- | :--- |
| BUG-6 | 🔴 阻塞 | `app/services/notifications.py:send_course_new_notifications` 定义未调用；`app/api/v1/courses.py` 创建路径未接入 | T-NOT-01 / T-SMOKE-M2-01 备注 | PRD §5 行1 + flows.md 流程1：排课成功 → 患者+康复师收到 course_new 站内信 |
| BUG-7 | 🟡 建议 | `app/services/notifications.py:send_course_overdue_notification` 定义未调用；`app/tasks/scheduler_tasks.py:_overdue_detection` 只建 alert | T-ALT-06 | PRD §5 行4 + flows.md 流程2 异常分支：超时5min → 康复师/主管医生站内信 |
| BUG-8 | 🔴 阻塞 | `app/services/tracking.py:start_course` 仅允许 `scheduled`（第 98 行） | T-NOT-06 后续步骤（reminded→start） | flows.md 速查表 + api.md §10：提醒发出(reminded) → 开始上课(ongoing) |

> 详细复现步骤与修复建议见 `docs/qa/test-report-m2.md` §3 缺陷清单。