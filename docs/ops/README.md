# RehabFlow 运维与部署文档

- 状态：**已发布**（Docker Compose 生产编排 + Linux 部署指南）
- 配套文档：`docs/PRD.md`（需求）、`docs/design/`（设计）、`docs/ops/deployment.md`（部署）

## 文档

| 文档 | 说明 | 状态 |
| :--- | :--- | :--- |
| `deployment.md` | **Linux 部署全流程**：方案 A 常规（systemd+nginx+conda 一键脚本）/ 方案 B Docker Compose；PG 迁移、安全加固 | ✅ |
| `monitoring.md` | 日志、健康检查、告警监控方案 | 规划中 |
| `env.md` | 环境变量清单（已并入 deployment.md §环境变量 + `.env.example`） | ✅ |

## 部署快速入口

```bash
# 方案 A：常规部署（systemd + nginx + conda，无 Docker）
git clone https://github.com/flichote/RehabFlow.git && cd RehabFlow
sudo bash deploy/install_linux.sh

# 方案 B：Docker Compose
cp .env.example .env && vim .env        # 改 SECRET_KEY！
docker compose up -d --build
# 访问 http://<服务器IP>/   健康检查 /healthz
```

> 详见 `docs/ops/deployment.md`；systemd 单元文件在 `deploy/systemd/`，nginx 配置在 `deploy/nginx/`。

> ⚠️ **HIS 隔离纪律**：环境变量清单中**禁止出现**任何 HIS 相关配置项（如 `HIS_API_URL`、HIS 连接串）。RehabFlow 与医院 HIS 完全独立（见 `docs/architecture.md` §9）。

## 技术栈部署基线

- 前端：Next.js 16 standalone + Nginx（静态直出 + 反代）
- 后端：FastAPI + Uvicorn（4 worker）+ 独立调度器容器（APScheduler）
- 数据：SQLite 卷持久化（开发/起步）→ PostgreSQL 16 + Redis（业务增长，配置已预留）
