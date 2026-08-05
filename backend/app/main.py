"""FastAPI application entry point.

Creates the app with CORS middleware and registers all routers.
Starts/stops the APScheduler in the lifespan handler.
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import router as v1_router
from app.db.session import engine
from app.models.base import Base
from app.tasks.scheduler_tasks import start_scheduler, stop_scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: create tables on first run, start scheduler.
    Shutdown: stop scheduler, dispose engine.
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
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
