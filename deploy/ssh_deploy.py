"""
RehabFlow 远程部署驱动器（paramiko）
用法: python deploy/ssh_deploy.py
前置: pip install paramiko；环境变量 RF_SSH_PASSWORD 或硬编码（测试后删除）
"""
import os
import sys
import time
import paramiko

HOST = "connect.westc.seetacloud.com"
PORT = 23887
USER = "root"
PASSWORD = os.environ.get("RF_SSH_PASSWORD", "RCQ20HzaGIyg")  # TODO: 部署后改为环境变量

REMOTE_SCRIPT = r"""
cat > /root/rf_remote_install.sh << 'REHABFLOW_EOF'
#!/usr/bin/env bash
set -uo pipefail
echo "═══ RehabFlow 部署到 seetacloud ═══"
echo "时间: $(date)"
echo "系统: $(uname -a)"

echo ""
echo "── 1. 环境探测 ──"
echo "OS: $(cat /etc/os-release 2>/dev/null | grep PRETTY_NAME | cut -d= -f2 | tr -d '\"')"
echo "内存: $(free -h 2>/dev/null | awk '/Mem:/{print $2}')"
echo "磁盘: $(df -h / | awk 'NR==2{print $4" 可用"}')"
echo "CPU: $(nproc) 核"
echo "Python: $(python3 --version 2>/dev/null || echo 无)"
echo "Node: $(node --version 2>/dev/null || echo 无)"
echo "conda: $(which conda 2>/dev/null || echo 无)"

PY=""
for c in /opt/miniconda3/bin/python /opt/conda/bin/python /usr/bin/python3 /usr/local/bin/python3; do
    if [ -x "$c" ]; then PY="$c"; break; fi
done
[ -z "$PY" ] && PY="$(command -v python3 || echo python3)"
echo "使用 Python: $PY"

if ! command -v node >/dev/null 2>&1; then
    echo "· 安装 Node.js..."
    curl -fsSL https://deb.nodesource.com/setup_22.x | bash - >/dev/null 2>&1
    apt-get install -y nodejs >/dev/null 2>&1 || echo "✗ Node 安装失败"
fi

echo ""
echo "── 2. 克隆仓库 ──"
APP_DIR="${APP_DIR:-/root/RehabFlow}"
if [ ! -d "$APP_DIR/.git" ]; then
    git clone --depth 1 https://github.com/flichote/RehabFlow.git "$APP_DIR" 2>&1 | tail -2
else
    cd "$APP_DIR" && git pull --ff-only 2>&1 | tail -1
fi
cd "$APP_DIR"
echo "✓ 仓库: $(git log --oneline -1 2>/dev/null)"

echo ""
echo "── 3. 后端依赖 ──"
"$PY" -m pip install -q -r backend/requirements.txt 2>&1 | tail -2
echo "✓ 依赖完成"

echo ""
echo "── 4. 数据库初始化 ──"
cd backend
"$PY" -m app.db.init_db 2>&1 | tail -3
echo "✓ 数据库就绪"

echo ""
echo "── 5. 前端构建 ──"
cd ../frontend
[ ! -d node_modules ] && npm install --silent 2>&1 | tail -1
npm run build 2>&1 | tail -3
echo "✓ 前端构建完成"

echo ""
echo "── 6. 启动服务 ──"
cd ../backend
mkdir -p ../logs
nohup "$PY" -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 2 > ../logs/backend.log 2>&1 &
echo "✓ 后端 PID $!"
cd ../frontend
nohup npx next start -H 0.0.0.0 -p 3000 > ../logs/frontend.log 2>&1 &
echo "✓ 前端 PID $!"

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
REHABFLOW_EOF
chmod +x /root/rf_remote_install.sh
bash /root/rf_remote_install.sh
"""

def main():
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    print(f"连接 {HOST}:{PORT} ...")
    client.connect(
        hostname=HOST, port=PORT, username=USER, password=PASSWORD,
        timeout=20, banner_timeout=20, auth_timeout=20,
        look_for_keys=False, allow_agent=False,
    )
    print("✓ 已连接\n")
    channel = client.get_transport().open_session()
    channel.get_pty()
    channel.exec_command("bash -s")
    for line in REMOTE_SCRIPT.splitlines():
        channel.send(line + "\n")
        time.sleep(0.02)
    channel.send("exit\n")
    time.sleep(0.5)
    channel.shutdown_write()

    # 流式读取输出
    output = ""
    while True:
        if channel.recv_ready():
            output += channel.recv(4096).decode(errors="replace")
        if channel.exit_status_ready() and not channel.recv_ready():
            break
        time.sleep(0.3)
    print(output)
    code = channel.recv_exit_status()
    client.close()
    print(f"\nexit={code}")
    return code

if __name__ == "__main__":
    sys.exit(main())
