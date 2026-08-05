# RehabFlow M2 验收测试报告（test-report-m2）

- 版本：v1.0（首轮验收 —— 发现 3 个缺陷，等待主控修复后复测）
- 日期：2026-08-05
- 作者：rf-qa（T9）
- 执行环境：Windows 10 / Python 3.11.14 / pytest / FastAPI / SQLAlchemy 2.0 / SQLite（aiosqlite）
- 基线提交：HEAD `9e9f2f5`（含 T8 通知/预警/定时任务 `4580202`、T10 M3 决策层）
- 验收依据：`docs/PRD.md` §3/§5、`docs/api.md` §2-§8、`docs/design/flows.md` 状态速查表、T9 任务体
- 用例文档：`docs/qa/test-cases.md`（M1 28 条 + M2 追加 31 条）
- 原始运行输出：`docs/qa/pytest_m2_run.txt`

---

## 1. 总览

| 项目 | 结果 |
| :--- | :--- |
| 全量用例数 | **98**（auth 8 / scheduling 7 / courses 5 / permissions 7 / query_api 21 / notifications 6 / alerts 8 / patient360 14 / dashboard 14 / m2_flows 6 / smoke 1 / smoke_m2 1） |
| 通过 | **95** |
| 失败 | **3**（均为本次新增验收用例，对应 BUG-6/7/8） |
| 通过率 | **96.9%**（95/98；不含 3 条验收失败用例则 100%） |
| 阻塞缺陷 | **2 项 🔴**（BUG-6 排课不写通知、BUG-8 提醒后无法开始上课） |
| 建议缺陷 | **1 项 🟡**（BUG-7 超时不通知康复师） |
| M2 出口判定 | **❌ 不通过** —— 3 个缺陷需主控修复后复测（修复点集中在通知服务接线与状态机入口，改动量小） |

> 说明：
> - M1 基线（`19b841f`）28 条全绿在本轮全量中仍全部通过，无回归。
> - T8 新增通知/预警测试（`test_notifications.py` 6 条 + `test_alerts.py` 8 条）全部通过。
> - T10 新增看板/患者360 测试（`test_dashboard.py` 14 + `test_patient360.py` 14）全部通过。
> - 本轮新增 7 条（`test_m2_flows.py` 6 + `test_smoke_m2.py` 1）：3 条通过（定时任务幂等 ×3）、1 条烟测通过、3 条失败（BUG 回归）。

### 运行命令与输出

```bash
cd backend && .venv/Scripts/python.exe -m pytest tests/ -v
```

```text
=================== 3 failed, 95 passed in 78.96s (0:01:18) ===================
```

完整输出见 `docs/qa/pytest_m2_run.txt`。

### 前端构建（T4/T7 build 声明复核）

```bash
cd frontend && npm run build
```

```text
✓ Compiled successfully in 427ms
  Generating static pages using 19 workers (24/24)
ƒ Proxy (Middleware)   ← proxy.ts 路由守卫启用
Route (app): 24 条静态路由（/login /register /admin/scheduler /therapist/schedule /doctor/* /patient/* 等）
```

结论：**通过**。24 条路由编译成功，排课日历页 `/admin/scheduler` 与我的课表页 `/therapist/schedule` 均在列（T7 声明复核一致）。

---

## 2. 通过用例（95/95）

### M1 回归（26 条，全绿）
认证 8 / 排课冲突 7 / 课程状态机 3（courses）/ 患者状态机 2 / 权限隔离 7 / 烟测 1 —— 与 `test-cases.md` M1 章节一致，无回归。

### M2 查询 API（query_api 21 条，全绿）
管理员列表 200 / 康复师仅见名下 / 按康复师·组别·治疗室·时间段过滤 / 课程详情含名称 / 他人课程 403 / 资源树分组 / 待排池排除有课患者 / 非管理员 403 / 未登录 401 等。

### M2 通知（notifications 6 条，全绿）
列表未读优先 / 未读数 / 标记单条已读 / 全部已读 / 他人通知 404 / 仅本人数据。

### M2 预警（alerts 8 条，全绿）
列表 open 过滤 / 仅 admin / resolve→resolved / ignore→ignored / 不存在 404 / 预警幂等 / 超时自动生成 alert + abnormal / 一键提醒状态流转。

### M2 定时任务（m2_flows 3 条，全绿）
课前15min 幂等（reminded 日志 1 条 + 双通知各 1 条）/ 超时5min 幂等（open 预警 1 条）/ 30min 巡检幂等（end_reminder 1 条）。

### M2 全链路烟测（smoke_m2 1 条，通过）
注册→登录→排课→查课表（free_slots 60min）→开始→结束→看通知，全程 2xx。

### T10 新增（patient360 14 + dashboard 14，全绿）
患者 360° 聚合 / 评估 / 看板 KPI / 分布 / 工作量 / 趋势。

---

## 3. 缺陷清单（3 项，等待主控修复）

### 🔴 BUG-6：排课成功不写任何通知（course_new 缺失）—— 阻塞

- **级别**：🔴 阻塞
- **验收依据**：`docs/PRD.md` §5 行1「新课程被安排 → 患者、康复师 → 站内信」；`docs/design/flows.md` 流程1 验收点「排课成功后系统自动推送提醒（患者 + 康复师，站内信）」；T9 任务体「通知：创建课程写 notifications」。
- **现象**：`POST /api/v1/courses` 创建课程成功（201），但患者与康复师的 `notifications` 表没有任何记录；康复师 `GET /notifications` 返回空列表。
- **根因**：`backend/app/services/notifications.py:120` 已实现 `send_course_new_notifications()`（含 course_new 模板），但**全仓无任何调用点**（grep 仅命中定义与模板常量）；`backend/app/api/v1/courses.py` 的 `create_course_endpoint` 与 `app/services/scheduling.py:create_course` 均未接入该函数。
- **复现**（对应用例 `test_create_course_writes_course_new_notifications`）：
  1. 管理员登录，为独立患者/康复师创建课程 → 201
  2. 康复师 `GET /api/v1/notifications` → `items` 为空（`total == 0`）
  3. 查库 `notifications` 表 → 0 行
- **期望**：创建课程后，患者与康复师各收到 1 条 `type == "course_new"`（链接 `/courses/{id}`）。
- **修复建议**：在 `create_course` 成功分支（或 `create_course_endpoint` 提交前）调用 `send_course_new_notifications`，并随创建事务一并提交。
- **证据**：`pytest_m2_run.txt` 中 `test_create_course_writes_course_new_notifications FAILED`（`assert 0 >= 1`）。

### 🟡 BUG-7：超时5分钟只生成预警，不通知康复师/主管医生

- **级别**：🟡 建议（预警闭环可用，仅站内信通道缺失）
- **验收依据**：`docs/PRD.md` §5 行4「康复师未点击开始（超时5分钟）→ 康复师、主管医生 → 站内信 + 待办任务红点」；`docs/design/flows.md` 流程2 异常分支「康复师/主管医生收到站内信 + 待办红点」。
- **现象**：超时课程被正确标记 `abnormal` 且生成 open 预警（主任看板可见），但康复师 `GET /notifications` 无 `course_overdue` 通知。
- **根因**：`backend/app/services/notifications.py:204` 已实现 `send_course_overdue_notification()`，但**从未被调用**；`backend/app/tasks/scheduler_tasks.py:_overdue_detection` 只调用 `create_course_overdue_alert`（建 alert + 状态流转），未发送站内信。
- **复现**（对应用例 `test_overdue_detection_notifies_therapist`）：
  1. 构造 start_at 已超 5min 的 scheduled 课程
  2. 手动触发 `_overdue_detection()`
  3. 康复师 `GET /api/v1/notifications` → 无 `course_overdue` 条目（alerts 表有 open 预警、课程已 abnormal）
- **期望**：超时检测时向康复师（及主管医生）写入 `course_overdue` 站内信。
- **修复建议**：在 `_overdue_detection` 生成 alert 的同时调用 `send_course_overdue_notification`（注意幂等：与 alert 同事务或复用 alert 去重键）。
- **证据**：`pytest_m2_run.txt` 中 `test_overdue_detection_notifies_therapist FAILED`（`assert 0 >= 1`）。

### 🔴 BUG-8：课程被提醒（reminded）后无法「开始上课」→ 409

- **级别**：🔴 阻塞（破坏课前15min 自动提醒→上课的标准路径）
- **验收依据**：`docs/design/flows.md` 状态速查表「提醒发出（-15min）→ 提醒已发（reminded）→ 开始上课 → 进行中（ongoing）」；`docs/api.md` §10 同表；flows.md 流程2.1「课前 15 分钟自动提醒 → 课程状态『提醒已发』→ 康复师点『开始上课』」。
- **现象**：对课程执行一键提醒（或课前15min 定时任务）后，课程状态变为 `reminded`；此时康复师点「开始上课」返回 **409**（`Cannot start course in 'reminded' status. Expected 'scheduled'.`），上课无法进行。
- **根因**：`backend/app/services/tracking.py:start_course`（第 98 行）仅允许 `course.status == "scheduled"`，未包含 `reminded`。
- **复现**（对应用例 `test_reminded_course_can_start`）：
  1. 创建课程 → `scheduled`
  2. 康复师 `POST /courses/{id}/remind` → 200，课程 `reminded`、患者 `en_route`
  3. 康复师 `POST /courses/{id}/start` → **409**（应为 200 进入 ongoing）
- **期望**：`start_course` 允许从 `scheduled` 与 `reminded` 两种状态开始。
- **修复建议**：`start_course` 状态守卫改为 `if course.status not in ("scheduled", "reminded")`。
- **证据**：`pytest_m2_run.txt` 中 `test_reminded_course_can_start FAILED`。

---

## 4. 疑问（⚪，非阻塞）

| # | 疑问 | 说明 |
| :--- | :--- | :--- |
| ⚪Q-1 | 巡检幂等的时间依赖 | `_patrol_ongoing` 幂等用 `Notification.created_at >= now-35min` 判断；`created_at` 为 DB `server_default=func.now()`（真实时钟）。单实例部署下与 `_now()` 同钟，正常；若未来多实例或时钟偏差，需改为业务幂等键（如 unique 约束或 link+type 去重表）。已按生产路径测试（真实时钟），未发现问题 |
| ⚪Q-2 | 并发巡检/提醒的非原子 check-then-insert | 定时任务幂等均为「先查后插」无唯一约束；APScheduler 单实例 + `max_instances=1` 下不会并发自撞；若多实例部署需加唯一索引兜底 |
| ⚪Q-3 | 共享工作区并发跑 pytest | 本任务执行中遇到另一 worker（T10）同时在共享目录跑 pytest，Windows 文件锁导致测试库互锁（一度误判为挂起）。已确认非代码问题；建议后续测试运行错峰或按 worker 隔离测试库路径 |
| ⚪Q-4 | 一键提醒对非 scheduled 课程的行为 | `POST /courses/{id}/remind` 对 `completed`/`ongoing` 课程仍会写提醒通知（状态不流转）。宽松行为，前端若仅在 scheduled 显示铃铛则无影响；待确认是否需要加状态守卫 |

---

## 5. 建议（非阻塞）

1. **通知接线补齐**（BUG-6/7 修复）：`send_course_new_notifications` / `send_course_overdue_notification` 已实现未接线，接入后本报告 3 项失败用例即转绿——改动集中在 `courses.py` 创建路径与 `scheduler_tasks._overdue_detection`，各约 2-5 行。
2. **状态机入口收敛**（BUG-8 修复）：`start_course` 允许 `("scheduled", "reminded")`；建议同时把允许起始状态集合抽成常量，并在 flows.md 速查表留一行注明。
3. **定时任务幂等键固化**：`course_end_reminder` 去重建议从「时间窗口」改为业务唯一键（`therapist_user_id + type + link` 唯一索引），消除对时钟窗口的依赖（见 ⚪Q-1）。
4. **测试运行隔离**：并发 worker 共用 `backend/tests/_test_rehabflow.db` 在 Windows 下会互锁，建议测试库路径加入 worker 标识或约定串行（见 ⚪Q-3）。
5. **补一个回归用例**：修复 BUG-8 后，把「remind → start → finish」完整路径并入 M2 烟测，防止再次出现提醒后无法上课。

---

## 6. 复测基线（当前）

```bash
cd backend && rm -f tests/_test_rehabflow.db && .venv/Scripts/python.exe -m pytest tests/ -v
```

结果：**95 passed / 3 failed**（`pytest_m2_run.txt`，2026-08-05，HEAD `9e9f2f5`）。前端 `npm run build` 通过（24 路由）。

**M2 出口判定**：❌ 暂不通过 —— BUG-6/BUG-8（🔴）与 BUG-7（🟡）修复后，3 条验收用例转绿即可放行 M2。修复点均为小改动，无架构性风险。

---

## 7. 提交物

- `docs/qa/test-cases.md` —— M1 28 条 + M2 追加 26 条用例（T-QRY/T-CAL/T-SCHED/T-NOT/T-ALT/T-TSK/T-SMOKE-M2）
- `docs/qa/test-report-m2.md` —— 本报告（通过率 + 缺陷清单 BUG-6/7/8 + 证据）
- `docs/qa/pytest_m2_run.txt` —— pytest 全量原始输出（98 tests：95 passed / 3 failed）
- `backend/tests/test_m2_flows.py` —— 通知/预警/定时任务 M2 验收用例（6 条：3 幂等通过 + 3 BUG 回归）
- `backend/tests/test_smoke_m2.py` —— M2 全链路烟测（1 条）
