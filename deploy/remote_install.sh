#!/usr/bin/env bash
# ============================================================
# RehabFlow 远程部署脚本（AutoDL/seetacloud 容器适配版）
# 用法：在实例上执行：
#   curl -sL https://raw.githubusercontent.com/flichote/RehabFlow/main/deploy/remote_install.sh -o rf_install.sh
#   bash rf_install.sh
#
# 特性：
#   · 端口按 AutoDL 平台映射（后端 6006 / 前端 6008，可用环境变量覆盖）
#   · conda python 优先（/root/miniconda3 等），避免系统 python 无 pip
#   · AutoDL 数据盘（/root/autodl-tmp，ext4）上构建前端，绕开 overlayfs 的
#     SIGBUS/Bus error（Docker overlay2 存储驱动 mmap 白洞问题）
#   · 前端构建时注入 BACKEND_URL，经 Next rewrites 同源代理访问后端，无跨域
#   · 不依赖 systemd/nginx，nohup 后台启动
# ============================================================
set -uo pipefail

# ---------- 可配置项（环境变量覆盖） ----------
BACKEND_PORT="${BACKEND_PORT:-6006}"     # AutoDL 映射：u372683-*.seetacloud.com:8443
FRONTEND_PORT="${FRONTEND_PORT:-6008}"   # AutoDL 映射：uu372683-*.seetacloud.com:8443
APP_DIR="${APP_DIR:-/root/RehabFlow}"
REPO_URL="${REPO_URL:-https://github.com/flichote/RehabFlow.git}"
NPM_REGISTRY="${NPM_REGISTRY:-https://registry.npmmirror.com}"  # 国内镜像，加快安装

echo "═══ RehabFlow 部署到 AutoDL/seetacloud ═══"
echo "时间: $(date)"
echo "系统: $(uname -a)"

# ---------- 1. 环境探测 ----------
echo ""
echo "── 1. 环境探测 ──"
echo "OS: $(cat /etc/os-release 2>/dev/null | grep PRETTY_NAME | cut -d= -f2 | tr -d '\"')"
echo "内存: $(free -h 2>/dev/null | awk '/Mem:/{print $2}')"
echo "磁盘: $(df -h / | awk 'NR==2{print $4\" 可用\"}')"
echo "CPU: $(nproc) 核"
echo "conda: $(which conda 2>/dev/null || echo 无)"
echo "Node: $(node --version 2>/dev/null || echo 无)"

# 定位 Python（conda 优先——系统 python 常无 pip）
PY=""
for c in /root/miniconda3/bin/python /root/anaconda3/bin/python /opt/miniconda3/bin/python \
         /opt/conda/bin/python /opt/anaconda3/bin/python /usr/local/miniconda3/bin/python \
         /usr/bin/python3 /usr/local/bin/python3; do
    if [ -x "$c" ]; then PY="$c"; break; fi
done
[ -z "$PY" ] && PY="$(command -v python3 || echo python3)"
if ! "$PY" -m pip --version >/dev/null 2>&1; then
    echo "· Python 无 pip，尝试 ensurepip / apt..."
    "$PY" -m ensurepip --upgrade >/dev/null 2>&1 || apt-get install -y python3-pip >/dev/null 2>&1 || true
fi
echo "使用 Python: $PY ($("$PY" --version 2>&1))"

# Node 检查（前端必需）
if ! command -v node >/dev/null 2>&1; then
    echo "· 安装 Node.js 22..."
    curl -fsSL https://deb.nodesource.com/setup_22.x | bash - >/dev/null 2>&1
    apt-get install -y nodejs >/dev/null 2>&1 || echo "✗ Node 安装失败（手动安装后重跑）"
fi

# npm 国内镜像
npm config set registry "$NPM_REGISTRY" 2>/dev/null
echo "npm registry: $(npm config get registry 2>/dev/null)"

# ---------- 2. 克隆/更新仓库 ----------
echo ""
echo "── 2. 克隆仓库 ──"
if [ ! -d "$APP_DIR/.git" ]; then
    git clone --depth 1 "$REPO_URL" "$APP_DIR" 2>&1 | tail -2
else
    cd "$APP_DIR" && git pull --ff-only 2>&1 | tail -1
fi
cd "$APP_DIR"
echo "✓ 仓库就绪: $(git log --oneline -1 2>/dev/null)"

# ---------- 3. 后端依赖 ----------
echo ""
echo "── 3. 后端依赖 ──"
"$PY" -m pip install -q -r backend/requirements.txt 2>&1 | tail -2
echo "✓ 后端依赖安装完成"

# ---------- 4. 数据库初始化 ----------
echo ""
echo "── 4. 数据库初始化 ──"
cd backend
"$PY" -m app.db.init_db 2>&1 | tail -3
echo "✓ 数据库就绪"

# ---------- 5. 前端构建（AutoDL 数据盘优先，绕 overlayfs SIGBUS） ----------
echo ""
echo "── 5. 前端构建 ──"

# 定位 AutoDL 数据盘（ext4 独立卷，非 overlayfs）
DATA_DISK=""
for d in /root/autodl-tmp /root/autodl-data /data; do
    if [ -d "$d" ] && ! mountpoint -q "$d" 2>/dev/null || df -T "$d" 2>/dev/null | grep -qE "ext4|xfs|btrfs"; then
        DATA_DISK="$d"; break
    fi
done

# 前端构建目录：数据盘副本（若可用），否则仓库内
SRC_FRONTEND="$APP_DIR/frontend"
if [ -n "$DATA_DISK" ]; then
    BUILD_DIR="$DATA_DISK/rehabflow-frontend"
    echo "· 检测到数据盘 $DATA_DISK（ext4，非 overlayfs）→ 前端在数据盘构建（绕 Bus error）"
    if [ ! -d "$BUILD_DIR/node_modules" ]; then
        mkdir -p "$BUILD_DIR"
        cp -r "$SRC_FRONTEND/." "$BUILD_DIR/"
    else
        cp -r "$SRC_FRONTEND/." "$BUILD_DIR/" 2>/dev/null || true   # 同步源码（保留 node_modules）
    fi
    cd "$BUILD_DIR"
else
    BUILD_DIR="$SRC_FRONTEND"
    cd "$BUILD_DIR"
    echo "· 未检测到数据盘，直接在仓库目录构建（若遇 Bus error，请将仓库移到 ext4 盘重试）"
fi

if [ ! -d node_modules ]; then
    echo "· npm install（$NPM_REGISTRY）..."
    npm install --silent 2>&1 | tail -1
fi
echo "· next build（BACKEND_URL=http://127.0.0.1:$BACKEND_PORT）..."
BACKEND_URL="http://127.0.0.1:$BACKEND_PORT" npm run build 2>&1 | tail -4
echo "✓ 前端构建完成（目录: $BUILD_DIR）"

# ---------- 6. 启动服务（后台） ----------
echo ""
echo "── 6. 启动服务 ──"
mkdir -p "$APP_DIR/logs"

cd "$APP_DIR/backend"
nohup "$PY" -m uvicorn app.main:app --host 0.0.0.0 --port "$BACKEND_PORT" --workers 2 \
    > "$APP_DIR/logs/backend.log" 2>&1 &
echo "✓ 后端 PID $! （端口 $BACKEND_PORT）"

cd "$BUILD_DIR"
nohup node node_modules/next/dist/bin/next start -H 0.0.0.0 -p "$FRONTEND_PORT" \
    > "$APP_DIR/logs/frontend.log" 2>&1 &
echo "✓ 前端 PID $! （端口 $FRONTEND_PORT）"

# ---------- 7. 验证 ----------
echo ""
echo "── 7. 验证 ──"
sleep 6
curl -s "http://127.0.0.1:$BACKEND_PORT/healthz" && echo " <- 后端健康"
curl -s -o /dev/null -w "前端 HTTP %{http_code}\n" "http://127.0.0.1:$FRONTEND_PORT/login"
echo "--- 关键：前端同源代理 → 后端 ---"
curl -s -X POST "http://127.0.0.1:$FRONTEND_PORT/api/v1/auth/login" \
     -H "Content-Type: application/json" \
     -d '{"username":"admin","password":"admin123"}' | head -c 80
echo " <- 登录 API（经前端代理）"

echo ""
echo "═══ 部署完成 ═══"
echo "后端(内网): http://127.0.0.1:$BACKEND_PORT"
echo "前端(内网): http://127.0.0.1:$FRONTEND_PORT"
echo ""
echo "AutoDL 公网访问（控制台「自定义服务」端口映射）："
echo "  前端页面:  https://u<uid>-<实例>.westc.seetacloud.com:8443  (映射自 6008)"
echo "  后端 API:  https://u<uid>-<实例>.westc.seetacloud.com:8443  (映射自 6006, /docs 为接口文档)"
echo ""
echo "日志: tail -f $APP_DIR/logs/backend.log / $APP_DIR/logs/frontend.log"
