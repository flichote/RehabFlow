# ============================================================
# RehabFlow 后端镜像 — FastAPI + Uvicorn（生产，多 worker）
# 构建：docker build -f docker/backend.Dockerfile -t rehabflow-backend .
# ============================================================
FROM python:3.11-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# 系统依赖（最小集：SQLite 无需额外库；PG 驱动 asyncpg 纯 Python）
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 依赖层（利用 Docker 层缓存）
COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# 应用代码
COPY backend/app ./app
COPY backend/alembic.ini ./alembic.ini 2>/dev/null || true
COPY backend/alembic ./alembic 2>/dev/null || true

# 非 root 运行（安全）
RUN useradd -m appuser
USER appuser

EXPOSE 8000

# 生产启动：4 worker + 优雅超时（不 --reload）
# 数据库目录挂载卷 /data（SQLite 持久化）；PG 切换只需改 DATABASE_URL
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4", "--timeout-keep-alive", "30"]
