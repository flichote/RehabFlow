# RehabFlow（康复流程流）

> 院内康复治疗排课与执行管理系统 —— 排课 → 提醒 → 治疗执行 → 软打卡定位 → 异常预警 → 数据看板

**RehabFlow 是一个全新独立项目**，与 Continuum-Care-Network（延续康护，CCN）定位区分，并且**独立于医院现有 HIS 系统运行**：

| 维度 | CCN（延续康护） | **RehabFlow（康复流程流）** |
| :--- | :--- | :--- |
| 核心场景 | 院外康复管理（患者-康复师匹配、健康数据上报、远程计划跟踪） | **院内康复治疗执行**（排课引擎、课表、软打卡、主任看板） |
| 核心动作 | 匹配 / 上报 / 跟踪 | **排课 / 上课 / 定位 / 预警** |
| 关键角色 | 患者、康复师、管理员 | 排课管理员、康复师、主管医生、科室主任 |
| 差异化能力 | 健康指标告警 | **状态机流转 + 软打卡定位（不依赖硬件）+ 实时排课冲突检测** |
| 与 HIS 关系 | — | **完全独立**：独立数据库、独立账号体系、独立部署，不读 HIS 库、不调 HIS 接口（详见 `docs/architecture.md` §9） |

---

## 系统定位（一句话）

> 把「康复计划」从纸面变成**可执行、可追踪、可预警**的院内排课闭环。

## 核心能力

1. **排课引擎** — 拖拽排课、15 分钟粒度、双重冲突检测（患者 + 康复师）、事务级并发安全
2. **我的课表** — 日程清单式，当前课程高亮闪烁，一键开始/结束上课，一键提醒
3. **软打卡定位** — 不依赖蓝牙信标，由业务动作自动推导患者位置（治疗中→对应治疗室），医生可人工修正
4. **患者 360°** — 实时位置卡片、康复计划时间轴、评估记录趋势
5. **主任看板** — KPI 卡片 + 患者分布环形图 + 治疗师工作量 + 异常预警列表 + 7 天趋势
6. **状态机驱动** — 患者状态（病房/前往/治疗中/暂停/缺席）× 课程状态（待执行/进行中/已完成/异常）双状态机

## 技术栈（规划）

| 层 | 选型 |
| :--- | :--- |
| 前端 | Next.js 16.2.9 (App Router) + Tailwind CSS **v4** + shadcn/ui + TanStack Query v5 |
| 后端 | FastAPI（Pydantic v2）+ SQLAlchemy 2.x（async） |
| 数据库 | **SQLite 起步（aiosqlite）→ 业务增长后切 PostgreSQL 16（asyncpg）** |
| 缓存 | Redis（排课缓存，写穿策略，生产期） |
| 部署 | Docker Compose |

> 版本已通过 context7 MCP 核实（详见 `docs/tech-stack.md`）；开发期 SQLite 零依赖跑通，切换 PG 只改 `DATABASE_URL`。

## 快速开始（开发期）

> 需要：conda（Miniconda/Anaconda）+ Node.js ≥ 20。**一条命令搞定全部**：

```bash
# 一键启动（自动：创建 conda 环境 rehabflow → 装依赖 → 初始化数据库 → 前后端并行）
python start_dev.py

# 常用参数
python start_dev.py --no-seed       # 跳过种子数据（只要空表）
python start_dev.py --no-frontend   # 只启动后端 API
python start_dev.py --force-deps    # 强制重装依赖
```

启动后自动输出：

```
✓ 后端 API:   http://127.0.0.1:8000   （API 文档: /docs）
✓ 前端页面:   http://127.0.0.1:3000
✓ 演示账号:   admin / admin123（管理员）
```

**环境说明**：conda 环境名为 `rehabflow`（Python 3.11），首次运行自动创建+装依赖（较慢），之后秒启动。数据库为 `backend/rehabflow.db`（SQLite），日志在 `logs/`。

> 完整部署（PostgreSQL + Redis）见 `docs/ops/`（规划中）。

## 文档索引

- `docs/PRD.md` — 产品需求文档（完整版）
- `docs/tech-stack.md` — **技术选型**（context7 核实的最新版本 + SQLite→PG 策略）
- `docs/architecture.md` — **系统架构**（分层/模块/关键机制/部署）
- `docs/database.md` — **数据模型**（15 张核心表，字段级）
- `docs/api.md` — **API 接口大纲**（REST 端点 + 权限标注）
- `docs/structure.md` — **目录结构规划**（前后端骨架蓝图）
- `docs/design/design-system.md` — 设计系统（视觉 token）
- `docs/design/pages.md` — 页面结构与信息架构
- `docs/design/components.md` — 页面级组件规范
- `docs/design/flows.md` — 核心交互流程

## 里程碑（M1 → M3）

- **M1 地基**：数据模型（courses / rooms / patient_status_log）+ 角色扩展（doctor）+ 事务级冲突检测
- **M2 核心闭环**：排课日历 → 我的课表 → 开始/结束上课 → 软打卡状态机 → 提醒系统
- **M3 决策层**：患者 360° + 评估记录 + 主任看板 + 异常预警闭环
