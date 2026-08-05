# RehabFlow M3 验收测试报告（test-report-m3）

- 版本：v1.0（首轮验收 —— 112/112 全绿，无 🔴 阻塞）
- 日期：2026-08-05
- 作者：rf-qa（T12）
- 执行环境：Windows 10 / Python 3.11.14 / pytest / FastAPI / SQLAlchemy 2.0 / SQLite（aiosqlite）
- 基线提交：HEAD `dab1450`（T9 M2 验收；T10 决策层 `9e9f2f5` 已合入）
- 验收依据：`docs/PRD.md` §3.3（患者360）/§3.4（主任看板）/§5（提醒）、`docs/api.md` §2/§8/§10、`docs/design/flows.md` 流程1/2/3/6 + 状态速查表、T12 任务体
- 用例文档：`docs/qa/test-cases.md`（M1 30 条 + M2 31 条 + **M3 追加 37 条**，共 98 条用例条目；对应 pytest 112 个测试函数）
- 原始运行输出：`docs/qa/pytest_m3_run.txt`

---

## 1. 总览

| 项目 | 结果 |
| :--- | :--- |
| 全量用例数 | **112**（auth 8 / scheduling 7 / courses 5 / permissions 7 / query_api 21 / notifications 6 / alerts 8 / m2_flows 6 / **dashboard 21** / **patient360 20** / smoke 1 / smoke_m2 1 / **smoke_m3 1**） |
| 通过 | **112** |
| 失败 | **0** |
| 通过率 | **100%**（112/112） |
| 阻塞缺陷 | **0 项 🔴** |
| 建议缺陷 | **1 项 🟡**（DIST-1 患者分布未归一化，环形图无法表达 PRD 四类占比） |
| 疑问 | **2 项 ⚪**（Q-1 评估 CRUD 无 PUT/DELETE；Q-2 BUG-6/7/8 修复未提交） |
| M3 出口判定 | **✅ 通过** —— 无 🔴 阻塞；🟡/⚪ 不阻断放行，建议下个里程碑前处理 |

> 说明：
> - M1 基线（28 条）与 M2 全部用例在本轮全量中无回归。
> - T10 提供的 28 条看板/患者360 用例全绿；本轮新增 14 条（dashboard 造数验证 5 + 角色权限 2、patient360 软打卡 2 + 权限 3 + API 面核查 1、smoke_m3 1）全部通过。
> - **BUG-6/7/8（M2 遗留）在工作树验证全部修复**：对应回归用例 `test_create_course_writes_course_new_notifications` / `test_overdue_detection_notifies_therapist` / `test_reminded_course_can_start` 均 PASS（详见 §5）。

### 运行命令与输出

```bash
cd backend && .venv/Scripts/python.exe -m pytest tests/ -v
```

```text
======================= 112 passed in 92.87s (0:01:32) ========================
```

完整输出见 `docs/qa/pytest_m3_run.txt`。

### 前端构建（T11 build 声明实测复核，不采信 worker 声明）

```bash
cd frontend && npm run build
```

```text
▲ Next.js 16.3.0 (Turbopack)
✓ Compiled successfully in 397ms
  Running TypeScript ... Finished TypeScript in 1395ms
✓ Generating static pages using 19 workers (24/24) in 503ms

Route (app): 24 条静态路由
  /admin/dashboard          ← 主任看板（M3 新页）
  /admin/alerts /admin/audit /admin/rooms /admin/scheduler /admin/therapists
  /doctor/patients /doctor/patients/[id]  ← 患者 360°（M3 新页，动态路由）
  /therapist/schedule /therapist/patients /therapist/assessments /therapist/profile /therapist/messages
  /patient /patient/schedule /patient/profile
  /login /register /403 /404 ...
ƒ Proxy (Middleware)   ← proxy.ts 路由守卫启用
```

结论：**通过**。24 条路由编译成功，M3 两个新页面（`/admin/dashboard`、`/doctor/patients/[id]`）均在列，TypeScript 检查零错误。

---

## 2. 通过用例（112/112）

### M1 + M2 回归（71 条，全绿）

- M1：认证 8 / 排课冲突 7 / 课程状态机 3 / 患者状态机 2 / 权限隔离 7 / 烟测 1 —— 无回归。
- M2：query_api 21 / 通知 6 / 预警 8 / 定时任务 6 / 排课日历与课表 / smoke_m2 1 —— 无回归。

### M3 主任看板（dashboard 21 条，全绿）

- **KPI**：4 字段结构；造数验证精确差值（注册新患者→在院+1；今日排课→今日课程+1；开始上课→治疗中+1）；出勤率造数（1 on_duty + 1 scheduled → 恰 0.5）；开始上课→treating_count 增加。
- **患者分布**：结构 / 种子病房分组 / 开始上课后 PT大厅 +1。
- **工作量**：结构 / 排课后含康复师 / 同日两节课 course_count == 2。
- **趋势**：7 天结构 / 空日补 0 / 今日排课→今日计数 +1 且升序完整。

### M3 患者 360°（patient360 20 条，全绿）

- **聚合**：overview 结构（基本信息+当前位置+时间轴+周分布）；当前位置来自最新 status_log；排课后课程进入时间轴；周分布 7 天。
- **软打卡联动**：开始上课→360 位置=PT大厅、状态=treating；结束上课→位置=病房(ward_location)、状态=ward（flows.md 速查表逐项吻合）。
- **评估**：列表结构 / 创建（康复师）→列表可见 / 按 assessed_at 倒序 / 非责任康复师创建→404 / PUT/DELETE 未实现（见 ⚪Q-1）。
- **评估趋势**：按类型过滤且升序（30→50→70）；无数据→空列表。

### M3 权限隔离（三角色覆盖，全绿）

- **管理员**：dashboard 四接口 200；overview/评估 全量可见。
- **康复师**：dashboard → 403；名下患者 overview 200；**非名下患者 overview/评估创建 → 404**；非责任评估创建 → 404。
- **医生**：dashboard → 403；名下患者 overview/评估 → 200；**非名下患者 overview → 404**。
- **患者**：dashboard 四接口 → 403（任务体明确项）；overview → 403；未登录 → 401。

### M3 全链路烟测（smoke_m3 1 条，通过）

注册→登录→排课（今日）→患者+康复师收到 course_new 通知→KPI 今日课程+1→康复师课表含该课程→开始上课（课程 ongoing / KPI 治疗中+1 / 360 位置=PT大厅）→结束上课（KPI 回落 / 360 状态=ward）→趋势今日计数≥1。**M1→M3 完整闭环一次跑通**（`test_full_chain_m1_to_m3`）。

---

## 3. 缺陷清单（0 🔴 / 1 🟡 / 2 ⚪）

### 🟡 DIST-1：患者分布未归一化病房位置，环形图无法表达 PRD 四类占比 —— 建议

- **验收依据**：`docs/PRD.md` §3.4「患者分布环形图：**病房 vs PT大厅 vs OT大厅 vs ST室** 的人数占比」；T12 任务体「distribution 分组」。
- **现象**：`GET /api/v1/dashboard/patient-distribution` 返回**原始 location 字符串分组**，而非四类归一化占比。实测输出（`backend/_evid_distribution.py`，复用测试库）：

```text
location='未知' count=8
location='PT大厅' count=8
location='ward' count=4
location='住院部3楼5床' count=2
location='住院部5楼2床' count=1
location='住院部2楼8床' count=1
```

- **根因**：`backend/app/services/dashboard.py:get_patient_distribution` 按 `PatientStatusLog.location` 原文 `GROUP BY`；而病房位置的写入路径（`init_db.py` 种子 / `tracking.finish_course`）分别写 `ward_location`（如「住院部3楼5床」）或回退字符串 `"ward"`，导致同一「病房」语义出现 5 种标签（住院部3楼5床 / 住院部2楼8床 / 住院部5楼2床 / ward / 未知），无法聚合为 PRD 的「病房」一类。
- **复现**：
  1. 管理员登录，`GET /api/v1/dashboard/patient-distribution`
  2. 观察 `items`：出现 ≥3 个病房类分组（不同床号）+ `ward` + `未知`
  3. 对比 PRD §3.4：期望仅 病房 / PT大厅 / OT大厅 / ST室 四组（或 + 未知/其他兜底）
- **期望**：按 PRD 归一化为四类：`病房`（location 以「住院部」开头或 == ward 或 == ward_location 的患者）、`PT大厅`、`OT大厅`、`ST室`，另加 `未知` 兜底（en_route 等 location=None 的患者）。
- **修复建议**：在 SQL 或服务层把病房位置归一化（CASE WHEN location LIKE '住院部%' OR location='ward' THEN '病房' ...），或对治疗室按 room.name 匹配。
- **影响**：主任看板环形图（DonutChart）将显示 6+ 扇区且「病房」分裂，与 PRD 展示语义不符；不影响 KPI 数值正确性 → 🟡 建议。

### ⚪ Q-1：任务体写「评估 CRUD」，但 API 仅有 list/create/trend，无 PUT/DELETE —— 疑问

- **现象**：`PUT /api/v1/patients/{pid}/assessments/{id}` 与 `DELETE .../assessments/{id}` 均返回 404（路由不存在）。`docs/api.md` §2 也仅定义 GET 列表 / POST 创建 / GET trend。
- **影响用例**：T-ASS-05（行为符合 api.md，测试通过，仅记录面差异）。
- **疑问点**：T12 任务体明确写「assessments CRUD」。若需求确需编辑/删除评估，需 rf-arch 确认并补齐 PUT/DELETE 路由与权限矩阵（谁可改/删？历史评估是否允许修改？）；若「CRUD」为宽松表述，建议同步修正任务体措辞。
- **当前不阻断**：现有 API 面覆盖评估的创建与读取链路，满足 PRD §3.3「查看历史评估趋势折线图」。

### ⚪ Q-2：BUG-6/7/8 修复位于工作树未提交，HEAD 仍含缺陷 —— 疑问（交付风险）

- **现象**：M2 遗留 BUG-6（排课不写 course_new 通知）、BUG-7（超时不通知康复师）、BUG-8（reminded 无法开始）的修复位于**未提交工作树**：`git status` 显示 `backend/app/services/notifications.py / scheduling.py / tracking.py / backend/app/tasks/scheduler_tasks.py` 4 文件 modified（T10 修复 worker 标记 done 但未提交，与 T8 收尾同模式）。
- **本次验证**：112/112 在**含修复的工作树**运行通过；BUG-6/7/8 对应回归用例全部 PASS（§5）。
- **风险**：若主控未提交这 4 个文件，`HEAD` 状态仍含 BUG-6/7/8（M2 报告 3 个缺陷未闭环）。
- **建议**：主控尽快把 4 个 backend 服务文件提交（或确认 T10 修复已另有提交）；提交后无需重跑本套用例（本次即为含修复基线）。

---

## 4. 测试证据索引

| 证据 | 位置 |
| :--- | :--- |
| pytest 全量原始输出（112 passed） | `docs/qa/pytest_m3_run.txt` |
| 前端 build 输出（24 路由，含 dashboard/patients 新页） | 本报告 §1（实测输出） |
| 分布未归一化实测输出 | 本报告 §3 DIST-1（`backend/_evid_distribution.py` 运行结果，脚本已删除不提交） |
| 用例文档（M3 8 组 44 条） | `docs/qa/test-cases.md` §16-§25 |

---

## 5. BUG-6/7/8 回归验证（工作树修复）

| 缺陷 | 回归用例 | 结果 | 证据（pytest_m3_run.txt） |
| :--- | :--- | :--- | :--- |
| BUG-6 排课不写 course_new | `test_create_course_writes_course_new_notifications` | ✅ PASS | `test_m2_flows.py::test_create_course_writes_course_new_notifications PASSED` |
| BUG-7 超时不通知康复师 | `test_overdue_detection_notifies_therapist` | ✅ PASS | `test_m2_flows.py::test_overdue_detection_notifies_therapist PASSED` |
| BUG-8 reminded 无法开始 | `test_reminded_course_can_start` | ✅ PASS | `test_m2_flows.py::test_reminded_course_can_start PASSED` |

另在全链路烟测（`test_full_chain_m1_to_m3` 第 ③ 步）再次验证：排课后患者+康复师均收到 `course_new` 通知。

---

## 6. M3 出口判定

| 条件 | 结果 |
| :--- | :--- |
| 无 🔴 阻塞缺陷 | ✅ 满足（0 项） |
| pytest 全量通过 | ✅ 112/112（100%） |
| 前端 build 通过（24 路由，含 dashboard/patients 新页） | ✅ 实测通过 |
| 权限用例覆盖三角色（医生 404 / 患者 dashboard 403 / 康复师 404） | ✅ 覆盖 |
| 全链路烟测（M1→M3 闭环） | ✅ 通过 |
| 交付物（docs/qa/ + backend/tests/） | ✅ 提交并推送 |

**结论：M3 验收通过**。🟡 DIST-1 与 ⚪ Q-1/Q-2 不阻断放行；建议在后续里程碑中处理：DIST-1（看板环形图四类归一化）、Q-1（评估 CRUD 范围确认）、Q-2（主控提交 BUG-6/7/8 修复文件）。

---

## 7. 修订记录

| 版本 | 日期 | 内容 |
| :--- | :--- | :--- |
| v1.0 | 2026-08-05 | 首轮验收：112/112 全绿；新增 14 条 M3 用例；发现 🟡 DIST-1、⚪ Q-1、⚪ Q-2；BUG-6/7/8 工作树修复验证通过 |
