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
# 直接拉取并执行仓库内的 AutoDL 适配部署脚本（单一事实源）
curl -sL https://raw.githubusercontent.com/flichote/RehabFlow/main/deploy/remote_install.sh -o /root/rf_install.sh
chmod +x /root/rf_install.sh
bash /root/rf_install.sh
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
