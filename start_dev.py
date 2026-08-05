#!/usr/bin/env python3
"""RehabFlow 一键开发启动脚本（conda 环境，跨平台：Windows / macOS / Linux）。

用法：
    python start_dev.py                  # 一键启动（conda 环境+依赖+DB+前后端并行）
    python start_dev.py --no-seed        # 跳过种子数据
    python start_dev.py --no-frontend    # 只启动后端
    python start_dev.py --force-deps     # 强制重装依赖

conda 环境：
    环境名：rehabflow（Python 3.11）
    创建：conda create -n rehabflow python=3.11 -y（脚本自动做，幂等）
    依赖：conda 环境内 pip install -r requirements.txt（幂等，有标记文件）

做了什么：
    1. 检查 Python / Node / conda 环境
    2. 创建/复用 conda 环境 rehabflow 并安装依赖
    3. 初始化数据库（建表，幂等）+ 灌种子数据（默认）
    4. 并行启动：后端 uvicorn :8000 + 前端 Next.js :3000
    5. 健康检查：/healthz 与前端首页，就绪后打印访问地址
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BACKEND = ROOT / "backend"
FRONTEND = ROOT / "frontend"
REQ = BACKEND / "requirements.txt"
DB = BACKEND / "rehabflow.db"

CONDA_ENV_NAME = "rehabflow"
CONDA_ENV_PY = os.path.join(
    os.environ.get("CONDA_PREFIX", ""),
    "envs",
    CONDA_ENV_NAME,
    "python.exe" if os.name == "nt" else "bin/python",
)
# conda 安装根（用于拼接 env 路径）
CONDA_ROOT = None
MARKER = BACKEND / ".conda-deps-installed"

GREEN, YELLOW, RED, CYAN, RESET = "\033[32m", "\033[33m", "\033[31m", "\033[36m", "\033[0m"


def log(msg: str, color: str = "") -> None:
    print(f"{color}{msg}{RESET}")


def run(cmd: list[str], cwd: Path | None = None, **kw) -> subprocess.CompletedProcess:
    log(f"  $ {' '.join(str(c) for c in cmd)}", CYAN)
    return subprocess.run(cmd, cwd=cwd or ROOT, **kw)


def find_conda() -> str | None:
    """定位 conda 可执行文件。"""
    c = shutil.which("conda")
    if c:
        return c
    for cand in (
        Path.home() / "miniconda3" / "Scripts" / "conda.exe",
        Path.home() / "anaconda3" / "Scripts" / "conda.exe",
        Path.home() / "AppData" / "Local" / "miniconda3" / "Scripts" / "conda.exe",
        Path.home() / "AppData" / "Local" / "anaconda3" / "Scripts" / "conda.exe",
        Path("/c/ProgramData/miniconda3/Scripts/conda.exe"),
        Path("/c/ProgramData/anaconda3/Scripts/conda.exe"),
    ):
        if cand.exists():
            return str(cand)
    return None


def conda_env_python(conda: str) -> str:
    """返回 conda 环境 rehabflow 的 python 路径（用 conda info --base 定位根）。

    不能用 Path(conda).parent.parent 推断——conda.exe 可能位于 Scripts/ 或
    Library/bin/，两种情况下父目录层级不同，推断会错（如 Library\\envs\\）。
    """
    try:
        r = subprocess.run([conda, "info", "--base"], capture_output=True, text=True, timeout=30)
        base = r.stdout.strip().splitlines()[-1].strip() if r.stdout.strip() else ""
    except Exception:
        base = ""
    if not base or not Path(base).exists():
        # 兜底：从 conda 可执行文件反推
        base = str(Path(conda).resolve().parent.parent)
    exe = "python.exe" if os.name == "nt" else "bin/python"
    return os.path.join(base, "envs", CONDA_ENV_NAME, exe)


def check_env() -> None:
    """检查 Python / Node / conda 可用性。"""
    conda = find_conda()
    if conda is None:
        log("✗ 未找到 conda。请安装 Miniconda/Anaconda 后重试。", RED)
        sys.exit(1)
    log(f"✓ conda: {conda}", GREEN)
    node = shutil.which("node")
    if node is None:
        log("✗ 未找到 node，前端无法启动。请先安装 Node.js ≥ 20。", RED)
        sys.exit(1)
    try:
        ver = subprocess.run([node, "--version"], capture_output=True, text=True).stdout.strip()
        log(f"✓ Node: {ver}", GREEN)
    except Exception:
        pass


def ensure_conda_env(conda: str, force_deps: bool) -> str:
    """确保 conda 环境 rehabflow 存在，返回其 python 路径。"""
    env_py = conda_env_python(conda)
    env_py_path = Path(env_py)

    if not env_py_path.exists():
        log(f"· 创建 conda 环境 {CONDA_ENV_NAME}（python 3.11，首次较慢）...", YELLOW)
        r = run([conda, "create", "-n", CONDA_ENV_NAME, "python=3.11", "-y"])
        if r.returncode != 0 or not env_py_path.exists():
            log("✗ conda 环境创建失败", RED)
            sys.exit(1)
        log(f"✓ conda 环境 {CONDA_ENV_NAME} 创建完成", GREEN)
    else:
        log(f"✓ conda 环境 {CONDA_ENV_NAME} 已存在", GREEN)

    # 安装依赖（幂等：有标记文件且非 force 则跳过）
    if MARKER.exists() and not force_deps:
        log("✓ 依赖已安装（标记存在）", GREEN)
        return env_py

    log("· 安装后端依赖（首次较慢，之后秒过）...", YELLOW)
    r = run([env_py, "-m", "pip", "install", "-r", str(REQ)], cwd=BACKEND)
    if r.returncode != 0:
        log("✗ 依赖安装失败", RED)
        sys.exit(1)
    # 验证关键包真实可导入（防止静默安装不完整就写标记）
    verify = run([env_py, "-c",
                  "import fastapi, sqlalchemy, aiosqlite, pydantic, uvicorn, alembic"],
                 cwd=BACKEND)
    if verify.returncode != 0:
        log("✗ 依赖验证失败（部分包未装上），请重试 --force-deps", RED)
        sys.exit(1)
    MARKER.write_text("ok", encoding="utf-8")
    log("✓ 依赖安装完成并通过导入验证", GREEN)
    return env_py


def init_db(env_py: str, seed: bool = True) -> None:
    """初始化数据库（建表幂等）+ 可选种子数据。"""
    log("· 初始化数据库（建表 + 种子数据）...", YELLOW)
    if seed:
        r = run([env_py, "-m", "app.db.init_db"], cwd=BACKEND)
    else:
        r = run([env_py, "-c",
                 "import asyncio; from app.db.init_db import create_tables; asyncio.run(create_tables())"],
                cwd=BACKEND)
    if r.returncode != 0:
        log("✗ 数据库初始化失败", RED)
        sys.exit(1)
    log(f"✓ 数据库就绪（{DB.name if DB.exists() else '已建表'}）", GREEN)


def wait_health(url: str, name: str, timeout: int = 60) -> bool:
    """轮询健康检查直到 2xx 或超时。"""
    import urllib.request

    log(f"· 等待 {name} 就绪（{url}）...", YELLOW)
    for _ in range(timeout // 2):
        try:
            with urllib.request.urlopen(url, timeout=3) as resp:
                if resp.status < 500:
                    log(f"✓ {name} 已就绪（HTTP {resp.status}）", GREEN)
                    return True
        except Exception:
            pass
        time.sleep(2)
    log(f"✗ {name} 健康检查超时（{timeout}s）", RED)
    return False


def start_servers(env_py: str, with_frontend: bool) -> tuple[list[subprocess.Popen], list[Path]]:
    """并行启动前后端，返回 (进程列表, 日志文件列表)。"""
    log("· 启动后端 uvicorn :8000 ...", YELLOW)
    backend_log = ROOT / "logs" / "backend.log"
    backend_log.parent.mkdir(exist_ok=True)
    be = subprocess.Popen(
        [env_py, "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"],
        cwd=BACKEND,
        stdout=open(backend_log, "a", encoding="utf-8"),
        stderr=subprocess.STDOUT,
    )

    procs: list[subprocess.Popen] = [be]
    logs: list[Path] = [backend_log]

    if with_frontend:
        log("· 启动前端 Next.js :3000 ...", YELLOW)
        if not (FRONTEND / "node_modules").exists():
            log("· 安装前端依赖（npm install，首次较慢）...", YELLOW)
            npm_cmd = "npm.cmd" if os.name == "nt" else "npm"
            r = run([npm_cmd, "install"], cwd=FRONTEND)
            if r.returncode != 0:
                log("✗ npm install 失败", RED)
        frontend_log = ROOT / "logs" / "frontend.log"
        # Windows 上 npm 是 npm.cmd，subprocess 找不到裸 "npm"（WinError 2）
        npm_cmd = "npm.cmd" if os.name == "nt" else "npm"
        fe = subprocess.Popen(
            [npm_cmd, "run", "dev"],
            cwd=FRONTEND,
            stdout=open(frontend_log, "a", encoding="utf-8"),
            stderr=subprocess.STDOUT,
        )
        procs.append(fe)
        logs.append(frontend_log)

    return procs, logs


def main() -> None:
    parser = argparse.ArgumentParser(description="RehabFlow 一键开发启动（conda）")
    parser.add_argument("--no-seed", action="store_true", help="跳过种子数据")
    parser.add_argument("--no-frontend", action="store_true", help="只启动后端")
    parser.add_argument("--force-deps", action="store_true", help="强制重装依赖")
    args = parser.parse_args()

    log("═══ RehabFlow 开发环境启动（conda） ═══", GREEN)
    check_env()
    conda = find_conda()
    assert conda is not None
    env_py = ensure_conda_env(conda, force_deps=args.force_deps)
    init_db(env_py, seed=not args.no_seed)
    procs, logs = start_servers(env_py, with_frontend=not args.no_frontend)

    backend_ok = wait_health("http://127.0.0.1:8000/healthz", "后端")
    frontend_ok = True
    if not args.no_frontend:
        frontend_ok = wait_health("http://127.0.0.1:3000", "前端", timeout=120)

    log("\n═══ 访问地址 ═══", GREEN)
    if backend_ok:
        log("  后端 API:   http://127.0.0.1:8000", CYAN)
        log("  API 文档:   http://127.0.0.1:8000/docs", CYAN)
    if frontend_ok:
        log("  前端页面:   http://127.0.0.1:3000", CYAN)
    log("  演示账号:   admin / admin123（管理员）", CYAN)
    log("  日志:       logs/backend.log、logs/frontend.log", CYAN)

    log("\n· 按 Ctrl+C 停止所有服务 ...", YELLOW)
    try:
        while True:
            time.sleep(1)
            for p in procs:
                if p.poll() is not None:
                    log(f"✗ 服务进程退出（code {p.returncode}），查看日志", RED)
                    for lp in logs:
                        log(f"  日志: {lp}", CYAN)
                    for p2 in procs:
                        p2.terminate()
                    sys.exit(1)
    except KeyboardInterrupt:
        log("\n· 正在停止所有服务 ...", YELLOW)
        for p in procs:
            p.terminate()
        log("✓ 已停止", GREEN)


if __name__ == "__main__":
    main()
