#!/usr/bin/env bash
# RehabFlow 远程部署到 seetacloud 实例
# 用法：在实例上执行：bash <(curl -sL <此脚本URL>) 或直接上传执行
# 功能：环境探测 → 依赖安装 → 克隆仓库 → 数据库初始化 → 前端构建 → 启动服务
set -uo pipefail

echo "═══ RehabFlow 部署到 seetacloud ═══"
echo "时间: $(date)"
echo "系统: $(uname -a)"

# ---------- 1. 环境探测 ----------
echo ""
echo "── 1. 环境探测 ──"
echo "OS: $(cat /etc/os-release 2>/dev/null | grep PRETTY_NAME | cut -d= -f2 | tr -d '\"')"
echo "内存: $(free -h 2>/dev/null | awk '/Mem:/{print $2}')"
echo "磁盘: $(df -h / | awk 'NR==2{print $4" 可用"}')"
echo "CPU: $(nproc) 核"
echo "Python: $(python3 --version 2>/dev/null || echo 无)"
echo "Node: $(node --version 2>/dev/null || echo 无)"
echo "conda: $(which conda 2>/dev/null || echo 无)"
echo "docker: $(docker --version 2>/dev/null || echo 无)"

# 定位 Python
PY=""
for c in /opt/miniconda3/bin/python /opt/conda/bin/python /usr/bin/python3 /usr/local/bin/python3; do
    if [ -x "$c" ]; then PY="$c"; break; fi
done
[ -z "$PY" ] && PY="$(command -v python3 || echo python3)"
echo "使用 Python: $PY"

# Node 检查（前端必需）
if ! command -v node >/dev/null 2>&1; then
    echo "✗ 未安装 Node.js，尝试安装..."
    curl -fsSL https://deb.nodesource.com/setup_22.x | bash - 2>/dev/null
    apt-get install -y nodejs 2>/dev/null || echo "✗ Node 安装失败（后续手动处理）"
fi

# ---------- 2. 克隆仓库 ----------
echo ""
echo "── 2. 克隆仓库 ──"
APP_DIR="${APP_DIR:-/root/RehabFlow}"
if [ ! -d "$APP_DIR/.git" ]; then
    git clone --depth 1 https://github.com/flichote/RehabFlow.git "$APP_DIR" 2>&1 | tail -2
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

# ---------- 5. 前端构建 ----------
echo ""
echo "── 5. 前端构建 ──"
cd ../frontend
if [ ! -d node_modules ]; then
    npm install --silent 2>&1 | tail -1
fi
npm run build 2>&1 | tail -3
echo "✓ 前端构建完成"

# ---------- 6. 启动服务（后台） ----------
echo ""
echo "── 6. 启动服务 ──"
cd ../backend
mkdir -p ../logs
nohup "$PY" -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 2 > ../logs/backend.log 2>&1 &
echo "✓ 后端 PID $!"

cd ../frontend
nohup npx next start -H 0.0.0.0 -p 3000 > ../logs/frontend.log 2>&1 &
echo "✓ 前端 PID $!"

# ---------- 7. 验证 ----------
echo ""
echo "── 7. 验证 ──"
sleep 5
curl -s http://127.0.0.1:8000/healthz && echo " <- 后端健康"
curl -s -o /dev/null -w "前端 HTTP %{http_code}\n" http://127.0.0.1:3000/login
curl -s -X POST http://127.0.0.1:8000/api/v1/auth/login -H "Content-Type: application/json" \
     -d '{"username":"admin","password":"admin123"}' | head -c 60
echo " <- 登录 API"

echo ""
echo "═══ 部署完成 ═══"
echo "后端: http://<实例IP>:8000  前端: http://<实例IP>:3000"
echo "（seetacloud 实例外部访问需平台端口映射，见控制台「自定义服务」）"
