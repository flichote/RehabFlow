# RehabFlow 部署文档（Linux）

> 目标：**Linux 服务器部署，对外提供服务**。提供两种方式，按环境自选：
>
> - **方案 A：常规部署（systemd + nginx + conda）** — 无 Docker 的服务器首选，一键脚本，资源占用低
> - **方案 B：Docker Compose** — 容器化，环境隔离强，迁移/扩容方便

两种方案架构一致：**nginx(80) 统一入口 → 前端 Next.js + 后端 FastAPI 多 worker + 独立调度器**。

---

## 方案 A：常规部署（systemd + nginx + conda）

### 架构

```
:80 nginx
 ├── /api/*        → 127.0.0.1:8000  FastAPI（4 worker，rehabflow-backend.service）
 ├── /_next/static → 127.0.0.1:3000  Next.js（rehabflow-frontend.service，长缓存）
 └── 页面/*        → 127.0.0.1:3000
调度器（单进程）→ 127.0.0.1:8001（rehabflow-scheduler.service，定时任务）
数据：backend/rehabflow.db（SQLite）→ 业务增长切 PostgreSQL 16
```

### 一键部署

```bash
# 前置：Ubuntu/Debian 示例
sudo apt update && sudo apt install -y git nginx
# Node.js ≥ 20（用 NodeSource 或 nvm）
curl -fsSL https://deb.nodesource.com/setup_22.x | sudo -E bash - && sudo apt install -y nodejs
# conda（Miniconda，装到 /opt/miniconda3 或任意位置）
wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh
sudo bash Miniconda3-latest-Linux-x86_64.sh -b -p /opt/miniconda3

# 克隆 + 一键部署
git clone https://github.com/flichote/RehabFlow.git && cd RehabFlow
sudo bash deploy/install_linux.sh

# 完成：访问 http://<服务器IP>/
```

脚本自动完成：建运行用户 → conda 环境 rehabflow → 依赖 → 数据库初始化 → 前端构建 → 生成 .env（随机 SECRET_KEY）→ 安装 3 个 systemd 服务 → 配置 nginx → 健康验证。

### 手动部署（不跑脚本，逐步控制）

```bash
# 1. 建用户 + 目录
sudo useradd -r -m -s /usr/sbin/nologin rehabflow
sudo mkdir -p /opt/RehabFlow/logs && sudo chown -R rehabflow:rehabflow /opt/RehabFlow

# 2. 后端（conda 环境 + 依赖 + DB）
/opt/miniconda3/bin/conda create -n rehabflow python=3.11 -y
cd /opt/RehabFlow/backend
/opt/miniconda3/envs/rehabflow/bin/python -m pip install -r requirements.txt
/opt/miniconda3/envs/rehabflow/bin/python -m app.db.init_db   # 建表 + 种子

# 3. 前端构建
cd /opt/RehabFlow/frontend && npm ci && npm run build

# 4. 环境变量
cp /opt/RehabFlow/.env.example /opt/RehabFlow/.env
# 编辑 .env：SECRET_KEY 必须改为 openssl rand -hex 32 的随机值！

# 5. systemd 服务（deploy/systemd/ 下 3 个文件，改路径/用户后安装）
sudo cp deploy/systemd/rehabflow-*.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now rehabflow-backend rehabflow-scheduler rehabflow-frontend

# 6. nginx
sudo cp deploy/nginx/rehabflow.conf /etc/nginx/conf.d/
sudo nginx -t && sudo systemctl reload nginx
```

### 运维

```bash
systemctl status rehabflow-backend      # 后端状态
journalctl -u rehabflow-backend -f      # 后端日志
journalctl -u rehabflow-scheduler -f    # 调度器日志（课前提醒/超时/巡检）
systemctl restart rehabflow-frontend    # 重启前端（代码更新后）
```

**代码更新**：

```bash
cd /opt/RehabFlow && sudo -u rehabflow git pull
cd frontend && sudo -u rehabflow npm run build
sudo systemctl restart rehabflow-backend rehabflow-frontend
# DB 结构变更时：cd backend && python -m alembic upgrade head（或重跑 init_db）
```

---

## 方案 B：Docker Compose

### 架构

```
浏览器 → :80 nginx（frontend 容器）
            ├── /_next/static → 静态直出
            ├── /api/*       → backend:8000（4 worker，RUN_SCHEDULER=false）
            └── 页面/*        → frontend:3000（Next standalone）
scheduler 容器（单进程，RUN_SCHEDULER=true）→ 定时任务
数据：SQLite 卷 rehabflow-data → 可选 postgres:16-alpine + redis:7-alpine（注释即启用）
```

### 快速部署（3 步）

```bash
git clone https://github.com/flichote/RehabFlow.git && cd RehabFlow
cp .env.example .env && vim .env    # 改 SECRET_KEY！
docker compose up -d --build

# 验证
curl http://localhost/healthz
curl http://localhost/api/v1/auth/login -X POST -H "Content-Type: application/json" \
     -d '{"username":"admin","password":"admin123"}'
```

### 常用运维命令

```bash
docker compose ps                 # 状态
docker compose logs -f backend    # 后端日志
docker compose logs -f scheduler  # 调度器日志
docker compose restart backend    # 重启
docker compose down               # 停止（保留数据卷）
docker compose down -v            # 停止并删除数据（危险！）
```

---

## 环境变量（两种方案共用 .env）

| 变量 | 默认值 | 说明 |
| :--- | :--- | :--- |
| `SECRET_KEY` | change-me-in-production | **必须改**：`openssl rand -hex 32` |
| `WEB_PORT` | 80 | 对外端口（Docker 方案用） |
| `DATABASE_URL` | sqlite（内置默认） | 切 PG：`postgresql+asyncpg://...` |
| `RUN_SCHEDULER` | true | 调度器开关（backend 容器设 false，scheduler 设 true） |
| `PG_PASSWORD` | rehabflow | 启用 PG 时的密码（可选） |

> ⚠️ **HIS 隔离纪律**：禁止添加任何 HIS 相关配置（`HIS_API_URL` 等）。RehabFlow 与医院 HIS 完全独立（docs/architecture.md §9）。

---

## 数据库：SQLite → PostgreSQL 16

应用层已兼容（SQLAlchemy 2.x async + asyncpg 驱动，见 docs/tech-stack.md）。切换：

- **方案 A**：安装 PG16 → 建库建用户 → `.env` 设 `DATABASE_URL=postgresql+asyncpg://rehabflow:密码@127.0.0.1:5432/rehabflow` → 重启服务 → `cd backend && python -m alembic upgrade head`
- **方案 B**：取消 docker-compose.yml 中 postgres/redis 注释 → backend/scheduler 环境变量改 DATABASE_URL → `docker compose up -d`

## 安全加固（生产建议）

- [ ] `SECRET_KEY` 已替换
- [ ] 防火墙只开放 80（方案 A 的 8000/8001/3000 仅监听 127.0.0.1，天然不对外）
- [ ] HTTPS：方案 A 用 certbot（Let's Encrypt）；方案 B 前置 Caddy/Traefik 或云 LB
- [ ] 备份 SQLite：`cp backend/rehabflow.db backup-$(date +%F).db`（可加 cron）

## 已知事项

- **调度器唯一性**：两种方案均将调度器独立为单进程（systemd 服务 / scheduler 容器），API 多 worker 设 `RUN_SCHEDULER=false`，避免定时任务重复执行。
- **时区**：默认 +08:00（医院场景），`APP_TZ_OFFSET_HOURS` 可调。
- **SQLite 并发**：单写者，业务量上来切 PG（见上）。
