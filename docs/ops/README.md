# RehabFlow 运维与部署文档

- 状态：**规划中**（M1 地基完成后编写）
- 配套文档：`docs/PRD.md`（需求）、`docs/design/`（设计）

## 规划内容

| 文档 | 说明 | 计划时间 |
| :--- | :--- | :--- |
| `deployment.md` | Docker Compose 三服务编排（frontend / backend / postgres+redis） | M1 后 |
| `monitoring.md` | 日志、健康检查、告警监控方案 | M3 |
| `env.md` | 环境变量清单（含敏感项说明） | M1 后 |

## 技术栈部署基线

- 前端：Next.js（静态导出或 Node 服务）
- 后端：FastAPI + Uvicorn（多 worker）
- 数据：PostgreSQL 16 + Redis（排课缓存，写穿策略）
- 开发期：后端可用 SQLite 零依赖起步（见 README「快速开始」）
