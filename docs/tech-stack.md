# RehabFlow 技术选型（Tech Stack）

- 版本：v0.2（2026-08-05 经 context7 MCP 核实最新版本）
- 状态：**已确认**（用户拍板）
- 配套文档：`architecture.md`（架构）、`structure.md`（目录）、`PRD.md`（需求）

> 选型原则：**全部使用较新的开源资源**，版本以 context7 MCP 实时查询为准，不用过时/停止维护的库。

---

## 1. 前端技术栈（rf-frontend 负责）

| 技术 | 版本 | 说明 | context7 核实 |
| :--- | :--- | :--- | :--- |
| **Next.js** | **v16.2.9**（v16 系列最新） | App Router + React Server Components，全栈框架 | ✅ /vercel/next.js |
| React | v19（随 Next 16 内置） | 前端框架 | ✅ |
| TypeScript | v5.x | 类型系统 | ✅ |
| **Tailwind CSS** | **v4** | **CSS-first 配置**（`@import "tailwindcss"` + `@tailwindcss/postcss`，**不再需要 tailwind.config.ts**） | ✅ /websites/tailwindcss |
| shadcn/ui | latest | 组件库（Radix 之上，Tailwind v4 兼容版） | ✅ |
| **TanStack Query** | **v5.90.3**（v5 最新） | 服务端状态管理 | ✅ /tanstack/query |
| lucide-react | latest | 图标库 | ✅ |
| recharts | latest | 看板图表（候选，实现时再定） | ✅ |

### ⚠️ Next.js 16 关键变化（影响现有文档，已修正）

1. **`middleware.ts` 改名 `proxy.ts`**（15.6 canary 起，16 正式）——路由守卫文件命名必须用 `proxy.ts`。
2. **`next lint` 命令移除**——改用 ESLint CLI（`eslint` 命令）。
3. **`unstable_` 前缀 API 已稳定**（16.0 起）；`experimental_ppr` 已移除。
4. Tailwind v4 是 CSS-first 配置，**无 `tailwind.config.ts`**——token 直接写在 `globals.css` 的 `@theme` 中。

> 相应修正：`structure.md`、`pages.md`、`flows.md` 中的 `middleware.ts` → `proxy.ts`；`tailwind.config.ts` 已从目录规划中移除。

---

## 2. 后端技术栈（rf-backend 负责）

| 技术 | 版本 | 说明 | context7 核实 |
| :--- | :--- | :--- | :--- |
| **Python** | 3.11+（本机 3.11.14） | 运行时 | ✅ |
| **FastAPI** | latest（0.128+，**强制 Pydantic v2**） | Web 框架；0.128 起移除 pydantic.v1 支持 | ✅ /websites/fastapi_tiangolo |
| **Pydantic** | **v2.x**（>=2.7,<3.0） | 数据校验 | ✅ |
| **SQLAlchemy** | **2.x**（async 模式） | ORM；`AsyncSession` + `async_sessionmaker` + `AsyncAttrs` | ✅ /websites/sqlalchemy_en_20 |
| Alembic | latest | 数据库迁移 | ✅ |
| APScheduler | latest | 定时任务（课前 15min/超时 5min/30min 巡检） | ✅ |
| uvicorn | latest | ASGI 服务器 | ✅ |
| httpx | latest | 异步 HTTP（浏览器通知等） | ✅ |

### SQLAlchemy 2.x 关键模式（已按官方文档核实）

- **Async 风格**：`create_async_engine` + `async_sessionmaker(engine, expire_on_commit=False)`。
- **SQLite 驱动**：`aiosqlite`（官方支持，SQLite 3.12+）。
- **PostgreSQL 驱动**（生产）：`asyncpg`。
- **切换方式**：仅改连接串 URL scheme——`sqlite+aiosqlite:///./rehabflow.db` ⇄ `postgresql+asyncpg://user:pass@host/db`，代码零改动（SQLAlchemy 抽象层）。

---

## 3. 数据库策略（用户拍板 ✅）

> **开发期用 SQLite（轻量零依赖）→ 业务量上来后切换开源关系库（PostgreSQL 16）。**

| 阶段 | 数据库 | 驱动 | 理由 |
| :--- | :--- | :--- | :--- |
| **M1-M3 开发/演示** | **SQLite** | `aiosqlite` | 零安装零配置，文件即库，开发/测试/演示最快路径 |
| **生产上线（业务增长后）** | **PostgreSQL 16** | `asyncpg` | 开源、成熟、并发强；SQLAlchemy 让切换只需改 URL |

### 切换保障（写入架构纪律）

1. **代码层零方言依赖**：模型/查询全部走 SQLAlchemy 抽象，不写 SQLite 特有 SQL（如 `PRAGMA`）。
2. **连接串单点配置**：`DATABASE_URL` 环境变量，切换只改它。
3. **迁移工具统一**：Alembic 迁移脚本两库兼容（避免 `server_default` 等方言差异陷阱）。
4. **注意点**：
   - SQLite 的 `FOR UPDATE` 行锁**不支持**（冲突检测事务策略在 SQLite 下退化为应用层锁——开发期可接受，生产切 PG 后启用真行锁）。
   - 并发写入在 SQLite 下受限（单写者），排课并发测试应在 PG 环境做最终验证。
   - 时间类型：SQLAlchemy `DateTime(timezone=True)` 两库行为一致。

---

## 4. 版本选型依据（context7 查询记录）

| 查询 | 结果 | 结论 |
| :--- | :--- | :--- |
| Next.js 最新版本 | v16.2.9（v16 系列活跃） | 用 v16，不走 v15 |
| Next.js 16 codemod | middleware→proxy、next lint 移除、PPR 变更 | 文档已修正 |
| Tailwind CSS v4 | CSS-first 配置、`@tailwindcss/postcss` | 用 v4，无 config 文件 |
| TanStack Query | v5.90.3 | 用 v5 |
| FastAPI 版本 | 0.128+ 强制 Pydantic v2 | 用最新 stable |
| SQLAlchemy 2.0 | async 模式 + AsyncAttrs | 全异步后端 |
| SQLite 支持 | 官方支持 3.12+，aiosqlite | 开发期策略成立 |

---

## 5. 与 CCN 技术栈的关系

| 层 | CCN | RehabFlow | 变化 |
| :--- | :--- | :--- | :--- |
| 前端框架 | Next.js 16 | Next.js 16.2.9 | 同代，更新到最新 |
| 样式 | Tailwind | Tailwind **v4** | **升级**（v4 CSS-first） |
| 后端 | FastAPI | FastAPI latest | 同 |
| ORM | SQLAlchemy | SQLAlchemy 2.x async | 同 |
| 数据库 | PG16（嵌入式） | **SQLite 起步 → PG16** | 新策略（用户拍板） |

---

## 6. 待定项（TBD）

1. 图表库最终选型：recharts vs 其他（主任看板折线/柱状/环形图）。
2. 拖拽排课实现：原生 HTML5 DnD vs @dnd-kit（排课日历核心交互）。
3. shadcn/ui 在 Tailwind v4 下的初始化方式（`npx shadcn@latest init` 确认）。
