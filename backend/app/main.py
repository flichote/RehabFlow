"""FastAPI application entry point.

Creates the app with CORS middleware and registers all routers.
Starts/stops the APScheduler in the lifespan handler.
"""
from contextlib import asynccontextmanager
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import router as v1_router
from app.db.session import engine
from app.models.base import Base
from app.tasks.scheduler_tasks import start_scheduler, stop_scheduler


def _should_run_scheduler() -> bool:
    """是否在本进程运行 APScheduler（由环境变量显式控制）。

    生产部署将调度器独立为单进程服务（docker-compose 的 scheduler 服务），
    API 容器（多 worker）设 RUN_SCHEDULER=false 避免定时任务重复执行；
    开发/单进程模式默认 true。
    """
    return os.environ.get("RUN_SCHEDULER", "true").lower() != "false"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: create tables on first run, start scheduler.
    Shutdown: stop scheduler, dispose engine.
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    if _should_run_scheduler():
        start_scheduler()
    yield
    stop_scheduler()
    await engine.dispose()


app = FastAPI(
    title="RehabFlow API",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(v1_router)


@app.get("/healthz")
async def healthz():
    return {"status": "ok"}
