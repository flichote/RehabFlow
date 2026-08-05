# RehabFlow API 接口大纲

- 版本：v0.1（接口蓝图，未实现）
- 状态：待评审
- 配套文档：`architecture.md`、`database.md`、`PRD.md`
- 对应交付物：`API_接口文档.html`（Swagger，规划产出）

> 约定：
> - 统一前缀 `/api/v1`；JSON；`Authorization: Bearer <JWT>`。
> - 错误响应：`{"detail": "..."}`（FastAPI 默认）。
> - 权限标注：🔓公开 / 👤登录 / 🩺医生 / 💆康复师 / 🛡️管理员。
> - 数据权限：服务端强制行级过滤（医生只见名下患者，康复师只见名下课程）。
> - 时间参数一律 ISO8601（UTC）。

---

## 1. 认证 Auth

| 方法 | 路径 | 权限 | 说明 |
| :--- | :--- | :--- | :--- |
| POST | `/auth/register` | 🔓 | 注册（角色选择） |
| POST | `/auth/login` | 🔓 | 登录 → access + refresh token |
| POST | `/auth/refresh` | 🔓 | 刷新 token |
| GET | `/auth/me` | 👤 | 当前用户信息 + 角色 |
| POST | `/auth/logout` | 👤 | 注销（吊销 refresh） |

---

## 2. 患者 Patients

| 方法 | 路径 | 权限 | 说明 |
| :--- | :--- | :--- | :--- |
| GET | `/patients` | 🩺🛡️ | 患者列表（医生=名下；管理员=全部，可分页/搜索） |
| POST | `/patients` | 🛡️ | 创建患者档案 |
| GET | `/patients/{id}` | 🩺💆🛡️ | 患者详情 |
| PUT | `/patients/{id}` | 🩺🛡️ | 更新档案 |
| GET | `/patients/{id}/overview` | 🩺💆🛡️ | **患者 360° 聚合**（基本信息+当前位置+计划时间轴+本周课程） |
| GET | `/patients/{id}/assessments` | 🩺💆🛡️ | 评估记录列表 |
| POST | `/patients/{id}/assessments` | 💆 | 新增评估记录 |
| GET | `/patients/{id}/assessments/trend?type=FM` | 🩺💆🛡️ | 评估趋势折线数据 |
| POST | `/patients/{id}/location` | 🩺 | **手动修正位置**（写 patient_status_log） |

---

## 3. 排课 Scheduling（核心）

| 方法 | 路径 | 权限 | 说明 |
| :--- | :--- | :--- | :--- |
| GET | `/courses` | 💆🛡️ | 课程列表（日历查询：`?from&to&therapist_id&group&room_id`；康复师=名下） |
| POST | `/courses` | 🛡️ | **创建课程**（事务内双重冲突检测；冲突→409 + 冲突明细） |
| GET | `/courses/{id}` | 💆🛡️ | 课程详情 |
| PUT | `/courses/{id}` | 🛡️ | 修改课程时间（重新冲突检测；改后强提醒） |
| DELETE | `/courses/{id}` | 🛡️ | 取消课程（通知双方） |
| POST | `/courses/{id}/force` | 🛡️ | **强制替换**（覆盖冲突课程，写审计） |
| GET | `/scheduler/resources` | 🛡️ | 排课页资源树（康复师分组 + 治疗室） |
| GET | `/scheduler/pool` | 🛡️ | 待排患者池（无课程患者） |
| POST | `/courses/{id}/remind` | 💆🛡️ | 一键提醒（立即推送上课提醒） |

---

## 4. 课程执行 Courses（康复师核心）

| 方法 | 路径 | 权限 | 说明 |
| :--- | :--- | :--- | :--- |
| POST | `/courses/{id}/start` | 💆 | **开始上课**（→进行中；患者→治疗中+位置=治疗室） |
| POST | `/courses/{id}/finish` | 💆 | **结束上课**（→已完成；患者→在病房；算课时） |
| POST | `/courses/{id}/pause` | 💆 | 临时暂停（患者不适） |
| POST | `/courses/{id}/resume` | 💆 | 恢复 |
| POST | `/courses/{id}/absent` | 💆 | 标记缺席（→未完成-缺席；患者→absent；生成 alert） |
| PUT | `/courses/{id}/note` | 💆 | 填写/更新治疗记录（session_note） |
| GET | `/therapist/schedule?date=` | 💆 | **我的课表**（今日概览 + 时间线 + 空闲时段） |

> 权限校验：课程必须 `therapist_id = current_user.id`（或管理员）。

---

## 5. 软打卡 Tracking

| 方法 | 路径 | 权限 | 说明 |
| :--- | :--- | :--- | :--- |
| GET | `/patients/{id}/location` | 🩺💆🛡️ | 当前实时位置（最近一条状态日志） |
| GET | `/patients/{id}/status-log?from&to` | 🩺🛡️ | 状态流转历史（审计查询） |
| POST | `/patients/{id}/location` | 🩺 | 手动修正（见 §2） |
| — | （内部）系统巡检任务 | — | 课程结束 30min 仍治疗中 → 提醒康复师 |

---

## 6. 提醒 Notifications

| 方法 | 路径 | 权限 | 说明 |
| :--- | :--- | :--- | :--- |
| GET | `/notifications` | 👤 | 我的消息（分页，未读优先） |
| GET | `/notifications/unread-count` | 👤 | 未读数（Topbar 红点） |
| POST | `/notifications/{id}/read` | 👤 | 标记已读 |
| POST | `/notifications/read-all` | 👤 | 全部已读 |

---

## 7. 预警 Alerts

| 方法 | 路径 | 权限 | 说明 |
| :--- | :--- | :--- | :--- |
| GET | `/alerts` | 🛡️ | 预警列表（`?status=open`，看板右栏） |
| GET | `/alerts/feed` | 🛡️ | **实时推送流**（SSE 候选；或 30s 轮询） |
| POST | `/alerts/{id}/resolve` | 🛡️ | 处理（resolved，写处理人） |
| POST | `/alerts/{id}/ignore` | 🛡️ | 忽略 |

---

## 8. 主任看板 Dashboard

| 方法 | 路径 | 权限 | 说明 |
| :--- | :--- | :--- | :--- |
| GET | `/dashboard/kpis` | 🛡️ | ①在院患者总数 ②今日已排课程 ③治疗中人数 ④康复师出勤率 |
| GET | `/dashboard/patient-distribution` | 🛡️ | 患者分布（病房/PT/OT/ST）→ 环形图 |
| GET | `/dashboard/therapist-workload?date=` | 🛡️ | 治疗师今日课时 → 柱状图 |
| GET | `/dashboard/course-trend?days=7` | 🛡️ | 近 7 天课程总量 → 折线图 |

---

## 9. 资源管理 Resources

| 方法 | 路径 | 权限 | 说明 |
| :--- | :--- | :--- | :--- |
| GET/POST/PUT/DELETE | `/rooms` | 🛡️ | 治疗室 CRUD |
| GET/POST/PUT | `/therapists` | 🛡️ | 康复师管理（组别/资质） |
| GET/POST | `/therapist-shifts` | 🛡️ | 排班（出勤率数据源） |
| GET | `/admin/audit-log` | 🛡️ | 审计日志查询 |

---

## 10. 状态流转 → 接口对照（开发必读）

| 动作 | 接口 | 课程状态 | 患者状态 | 位置 |
| :--- | :--- | :--- | :--- | :--- |
| 排课成功 | POST /courses | scheduled | — | — |
| 课前 15min（系统） | 定时任务 | reminded | en_route | — |
| 开始上课 | POST /courses/{id}/start | ongoing | treating | 治疗室 |
| 临时暂停 | POST /courses/{id}/pause | ongoing | paused | 治疗室 |
| 恢复 | POST /courses/{id}/resume | ongoing | treating | 治疗室 |
| 结束上课 | POST /courses/{id}/finish | completed | ward | 病房 |
| 标记缺席 | POST /courses/{id}/absent | absent | absent | 病房 |
| 超时未开始（系统） | 定时任务 | abnormal | — | — |

---

## 11. 错误码约定

| HTTP | 场景 |
| :--- | :--- |
| 401 | 未登录 / token 失效 |
| 403 | 角色无权 |
| 404 | 资源不存在 |
| **409** | **排课冲突**（响应体带冲突明细列表） |
| 422 | 参数校验失败（15min 粒度违规等） |
| 429 | 限流 |
