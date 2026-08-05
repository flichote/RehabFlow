# RehabFlow 目录结构规划（骨架蓝图）

- 版本：v0.1（规划，未创建代码）
- 状态：待评审
- 配套文档：`architecture.md`（模块边界）、`api.md`（接口）、`database.md`（模型）

> 本文档定义前后端目录骨架。**开始写码时按此创建**，命名与分层对齐架构文档 §3。

---

## 1. 仓库根

```text
RehabFlow/
├── README.md
├── .gitignore
├── docker-compose.yml            # 部署编排（M1 后）
├── docs/                         # 全部文档
│   ├── PRD.md
│   ├── architecture.md
│   ├── database.md
│   ├── api.md
│   ├── design/                   # design-system / pages / components / flows
│   └── ops/                      # 部署/监控（规划中）
├── backend/                      # FastAPI
└── frontend/                     # Next.js
```

---

## 2. 后端 `backend/`（FastAPI + SQLAlchemy 2.x）

```text
backend/
├── app/
│   ├── main.py                   # 应用入口，注册路由 + CORS
│   ├── core/
│   │   ├── config.py             # pydantic-settings（环境变量）
│   │   ├── security.py           # JWT 签发/校验、密码哈希
│   │   └── deps.py               # 依赖注入：get_db / get_current_user / 角色守卫
│   ├── api/
│   │   └── v1/
│   │       ├── router.py         # 聚合路由
│   │       ├── auth.py
│   │       ├── patients.py
│   │       ├── courses.py        # 排课 + 课程执行
│   │       ├── scheduler.py      # 资源树 / 待排池 / 日历查询
│   │       ├── tracking.py       # 位置 / 状态日志
│   │       ├── notifications.py
│   │       ├── alerts.py
│   │       ├── dashboard.py
│   │       └── resources.py      # rooms / therapists / shifts / audit
│   ├── models/                   # SQLAlchemy 模型（15 表，见 database.md）
│   │   ├── __init__.py
│   │   ├── base.py               # Base + 公共 mixin
│   │   └── models.py             # 或按域拆分：users.py / courses.py / tracking.py
│   ├── schemas/                  # Pydantic v2（请求/响应）
│   │   └── schemas.py            # 或按域拆分
│   ├── services/                 # 业务服务（架构文档 §3 模块）
│   │   ├── scheduling.py         # ★ 排课引擎：冲突检测事务
│   │   ├── courses.py            # ★ 课程执行：start/finish/pause/absent
│   │   ├── tracking.py           # ★ 软打卡状态机（唯一状态入口）
│   │   ├── notifications.py      # 模板渲染 + 多通道发送
│   │   ├── alerts.py             # 预警生成/处理
│   │   ├── dashboard.py          # 看板聚合
│   │   └── audit.py              # 审计日志写入
│   ├── tasks/
│   │   └── scheduler_tasks.py    # APScheduler：课前15min / 超时5min / 30min巡检
│   └── db/
│       ├── session.py            # 会话工厂（SQLite/PG 切换口）
│       └── init_db.py            # 建表/种子数据
├── alembic/                      # 迁移（M1 后）
├── tests/                        # pytest（M1 起并行写）
│   ├── conftest.py
│   ├── test_scheduling.py        # 冲突检测用例
│   ├── test_courses.py           # 状态机用例
│   └── test_permissions.py       # 数据权限隔离用例
├── requirements.txt
├── .env.example
└── run.py                        # 开发启动（uvicorn --reload）
```

> **关键依赖方向**：`api → services → models`，禁止 api 直接写模型状态；状态变更一律走 `services/tracking.py`。

---

## 3. 前端 `frontend/`（Next.js App Router）

```text
frontend/
├── app/
│   ├── layout.tsx                # 根布局（字体/全局样式）
│   ├── globals.css               # Tailwind + token 变量
│   ├── page.tsx                  # 落地页（品牌/登录入口）
│   ├── (auth)/
│   │   ├── login/page.tsx
│   │   ├── register/page.tsx
│   │   └── onboarding/page.tsx
│   ├── (therapist)/
│   │   ├── layout.tsx            # AppShell（康复师侧边栏）
│   │   ├── schedule/page.tsx     # ★ 我的课表
│   │   ├── patients/page.tsx
│   │   ├── patients/[id]/page.tsx   # 患者 360°（与医生共用）
│   │   ├── assessments/page.tsx
│   │   ├── messages/page.tsx
│   │   └── profile/page.tsx
│   ├── (doctor)/
│   │   ├── layout.tsx            # AppShell（医生侧边栏）
│   │   ├── patients/page.tsx
│   │   └── patients/[id]/page.tsx  # ★ 患者 360°
│   ├── (admin)/
│   │   ├── layout.tsx            # AdminShell（管理侧边栏）
│   │   ├── scheduler/page.tsx    # ★ 排课日历（核心引擎）
│   │   ├── dashboard/page.tsx    # ★ 主任看板
│   │   ├── rooms/page.tsx
│   │   ├── therapists/page.tsx
│   │   ├── alerts/page.tsx
│   │   └── audit/page.tsx
│   ├── (patient)/
│   │   ├── layout.tsx
│   │   ├── page.tsx              # 今日课程概览
│   │   ├── schedule/page.tsx     # 我的课程（周历）
│   │   └── profile/page.tsx
│   └── 403/page.tsx | 404 | 500
├── components/
│   ├── ui/                       # shadcn/ui 基础（button/card/dialog/drawer...）
│   ├── layout/                   # AppShell / AdminShell / Sidebar / Topbar / TabBar
│   ├── schedule/                 # ★ ScheduleGrid / CourseCard / CourseDrawer / ConflictDialog
│   ├── therapist/                # TimelineList / ScheduleItem / SessionNoteModal
│   ├── patient/                  # PatientLocationCard / PlanTimeline / WeekCalendar
│   ├── dashboard/                # KpiCard / DonutChart / BarChart / LineChart / AlertFeed
│   └── common/                   # StatusBadge / CourseTypeBadge / ConfirmDialog / EmptySlot
├── lib/
│   ├── api.ts                    # fetch 封装（JWT 注入 / 错误处理）
│   ├── query-keys.ts             # TanStack Query key 管理
│   ├── permissions.ts            # 前端角色/权限工具
│   └── format.ts                 # 时间格式化（15min 粒度辅助）
├── hooks/                        # useSchedule / useCourses / useDashboard...
├── proxy.ts                      # 路由守卫（Next.js 16 的 middleware，token + 角色）
├── package.json
└── tsconfig.json
```

---

## 4. 实现顺序映射（M1 → M3）

| 阶段 | 后端 | 前端 |
| :--- | :--- | :--- |
| **M1 地基** | core/ + db/ + models（15 表全量，见 database.md）+ services/scheduling 冲突检测 + auth | 骨架 + token 落地 + login/register |
| **M2 闭环** | courses/tracking/notifications/tasks 全量 | schedule 页 + scheduler 页（排课日历）+ 状态徽章 |
| **M3 决策** | dashboard/alerts/assessments | 患者 360° + 主任看板 + alerts 页 |

---

## 5. 规范约定

1. **后端**：类型标注完整；service 层返回业务异常（409 冲突带明细）；禁止裸 `db.query` 绕过权限 scope。
2. **前端**：组件只引用 token 不硬编码色值；页面数据用 TanStack Query；`proxy.ts`（Next.js 16 middleware 正式名）统一守卫；Tailwind v4 CSS-first（token 在 globals.css `@theme`，无 tailwind.config）。
3. **测试**：后端 pytest 从 M1 起并行（冲突检测是重点）；前端组件测试（可选，M2+）。
