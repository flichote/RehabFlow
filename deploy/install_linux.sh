#!/usr/bin/env bash
# ============================================================
# RehabFlow 一键部署脚本 — Linux 常规方式（systemd + nginx + conda）
# 适用：Ubuntu/Debian/CentOS 等 systemd 发行版，无 Docker 的服务器
#
# 用法：
#   sudo bash deploy/install_linux.sh            # 默认 /opt/RehabFlow
#   sudo APP_DIR=/srv/rehabflow bash deploy/install_linux.sh   # 自定义目录
#
# 步骤：建用户 → conda 环境 → 依赖 → 数据库 → systemd 服务 → nginx → 验证
# ============================================================
set -euo pipefail

APP_DIR="${APP_DIR:-/opt/RehabFlow}"
APP_USER="${APP_USER:-rehabflow}"
CONDA_BIN="${CONDA_BIN:-}"   # 留空自动探测
REPO_URL="${REPO_URL:-https://github.com/flichote/RehabFlow.git}"

echo "=== RehabFlow Linux 部署开始 ==="
echo "  目录: $APP_DIR  用户: $APP_USER"

# ---------- 0. 前置检查 ----------
if [[ $EUID -ne 0 ]]; then
    echo "✗ 请用 root 或 sudo 运行" >&2; exit 1
fi
command -v git >/dev/null || { echo "✗ 缺 git" >&2; exit 1; }
command -v nginx >/dev/null || { echo "✗ 缺 nginx（apt install nginx / dnf install nginx）" >&2; exit 1; }
command -v node >/dev/null || { echo "✗ 缺 Node.js ≥ 20（见 docs/ops/deployment.md）" >&2; exit 1; }

# ---------- 1. conda 探测 ----------
if [[ -z "$CONDA_BIN" ]]; then
    for c in /opt/miniconda3/bin/conda /opt/anaconda3/bin/conda /opt/conda/bin/conda \
             "$HOME/miniconda3/bin/conda" "$HOME/anaconda3/bin/conda" /usr/local/miniconda3/bin/conda; do
        if [[ -x "$c" ]]; then CONDA_BIN="$c"; break; fi
    done
fi
if [[ -z "$CONDA_BIN" ]]; then
    echo "✗ 未找到 conda。请先安装 Miniconda（https://docs.conda.io/miniconda.html）" >&2
    exit 1
fi
CONDA_ROOT="$(dirname "$(dirname "$CONDA_BIN")")"
echo "✓ conda: $CONDA_BIN"

# ---------- 2. 克隆仓库 ----------
if [[ ! -d "$APP_DIR/.git" ]]; then
    mkdir -p "$(dirname "$APP_DIR")"
    git clone "$REPO_URL" "$APP_DIR"
    echo "✓ 仓库已克隆"
else
    cd "$APP_DIR" && git pull --ff-only || true
    echo "✓ 仓库已更新"
fi
cd "$APP_DIR"

# ---------- 3. 创建运行用户 ----------
if ! id "$APP_USER" &>/dev/null; then
    useradd -r -m -s /usr/sbin/nologin "$APP_USER"
    echo "✓ 用户 $APP_USER 已创建"
fi
mkdir -p "$APP_DIR/logs"
chown -R "$APP_USER:$APP_USER" "$APP_DIR"

# ---------- 4. conda 环境 + 依赖 ----------
ENV_PY="$CONDA_ROOT/envs/rehabflow/bin/python"
if [[ ! -x "$ENV_PY" ]]; then
    echo "· 创建 conda 环境 rehabflow (python 3.11)..."
    "$CONDA_BIN" create -n rehabflow python=3.11 -y
fi
echo "· 安装后端依赖..."
"$ENV_PY" -m pip install -r "$APP_DIR/backend/requirements.txt"
echo "✓ conda 环境就绪"

# ---------- 5. 数据库初始化（SQLite，幂等） ----------
cd "$APP_DIR/backend"
env -u PYTHONPATH -u VIRTUAL_ENV "$ENV_PY" -m app.db.init_db
chown "$APP_USER:$APP_USER" rehabflow.db 2>/dev/null || true
echo "✓ 数据库初始化完成"

# ---------- 6. 前端生产构建 ----------
echo "· 前端安装依赖 + 构建..."
cd "$APP_DIR/frontend"
npm ci --silent || npm install --silent
npm run build
echo "✓ 前端构建完成"

# ---------- 7. 环境变量 ----------
if [[ ! -f "$APP_DIR/.env" ]]; then
    cp .env.example .env
    SECRET="$(openssl rand -hex 32 2>/dev/null || head -c64 /dev/urandom | tr -dc 'a-f0-9' | head -c64)"
    sed -i "s/^SECRET_KEY=.*/SECRET_KEY=$SECRET/" .env
    echo "✓ .env 已生成（SECRET_KEY 已随机生成）"
fi

# ---------- 8. systemd 服务 ----------
for svc in rehabflow-backend rehabflow-scheduler rehabflow-frontend; do
    sed -e "s|/opt/RehabFlow|$APP_DIR|g" \
        -e "s|/opt/miniconda3|$CONDA_ROOT|g" \
        -e "s|User=rehabflow|User=$APP_USER|g" \
        -e "s|Group=rehabflow|Group=$APP_USER|g" \
        "deploy/systemd/$svc.service" > "/etc/systemd/system/$svc.service"
done
systemctl daemon-reload
systemctl enable --now rehabflow-backend rehabflow-scheduler rehabflow-frontend
echo "✓ systemd 服务已启动"

# ---------- 9. nginx 配置 ----------
cp deploy/nginx/rehabflow.conf /etc/nginx/conf.d/rehabflow.conf
nginx -t && systemctl reload nginx
echo "✓ nginx 已配置"

# ---------- 10. 验证 ----------
sleep 3
echo ""
echo "=== 部署完成 ==="
curl -sf http://127.0.0.1/healthz && echo " <- 健康检查 OK"
curl -sf -X POST http://127.0.0.1/api/v1/auth/login \
    -H "Content-Type: application/json" \
    -d '{"username":"admin","password":"admin123"}' \
    | head -c 60 && echo " <- 登录 API OK"
echo ""
echo "访问: http://$(hostname -I 2>/dev/null | awk '{print $1}')/  （演示账号 admin/admin123）"
echo "日志: journalctl -u rehabflow-backend -f"
