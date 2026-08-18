#!/usr/bin/env bash
# ============================================================
#  PWM Fan — 安装 + 升级 一键脚本 (自链网盘分发)
# ============================================================
#  同一个命令, 自动判断:
#    首次安装 (服务不存在)   -> 装依赖 + 部署 + 启动
#    升级 (服务已存在)       -> 删旧文件 + 下载新版 + 重启
#
#  用法:
#    root 机器 (Armbian):   curl -fL https://dl.runyf.cn/pwnfan/install.sh | bash
#    fnOS (admin 用户):     curl -fL https://dl.runyf.cn/pwnfan/install.sh | SUDO_PASS=admin bash
#
#  部署后 Web 面板:  http://<设备IP>:8081
# ============================================================
set -e

BASE="https://dl.runyf.cn/pwnfan"
FILES=("fan_driver.py" "web_server.py")
DEST="/opt/pwm-fan"
SERVICES="pwm-fan pwm-fan-web"
SYSDIR="/etc/systemd/system"

# --- 提权助手: root 直接执行, 否则走 sudo ---
run() {
    if [ "$(id -u)" = "0" ]; then
        "$@"
    elif command -v sudo >/dev/null 2>&1; then
        if [ -n "$SUDO_PASS" ]; then
            echo "$SUDO_PASS" | sudo -S "$@"
        else
            sudo "$@"
        fi
    else
        echo "错误: 非 root 且无 sudo, 无法提权" >&2
        exit 1
    fi
}

echo "==================== PWM Fan 安装/升级 ===================="

# ---- 0. 判断模式 (先判断, 因为后面会写入服务文件) ----
if run test -f "$SYSDIR/pwm-fan.service"; then
    MODE="升级"
else
    MODE="安装"
fi
echo "== 检测到: $MODE 模式 =="

# ---- 1. 下载驱动文件 (删旧 + 直接落到 /opt/pwm-fan) ----
echo "== 1. 下载驱动文件到 $DEST =="
run mkdir -p "$DEST"
for f in "${FILES[@]}"; do
    run rm -f "$DEST/$f"
    run curl -fL -o "$DEST/$f" "$BASE/$f"
    echo "   $f 已就位 ($(run stat -c%s "$DEST/$f") bytes)"
done
run chmod +x "$DEST"/*.py

# ---- 2. 缺少依赖时安装 (仅首次需要) ----
if ! run python3 -c "import gpiod" 2>/dev/null; then
    echo "== 2. 缺少 python3-libgpiod, 安装依赖 =="
    run apt-get update -qq
    run apt-get install -y python3-libgpiod 2>&1 | tail -1
else
    echo "== 2. 依赖已就绪 (python3-libgpiod) =="
fi

# ---- 3. 写入 systemd 服务 (升级时同样刷新, 保证与新版一致) ----
echo "== 3. 写入 systemd 服务 =="
cat > /tmp/pwm-fan.service <<'EOF'
[Unit]
Description=PWM Fan Driver
After=sysinit.target

[Service]
Type=simple
ExecStart=/usr/bin/python3 /opt/pwm-fan/fan_driver.py
Restart=always
RestartSec=10
StartLimitBurst=10
StartLimitIntervalSec=300

[Install]
WantedBy=multi-user.target
EOF
cat > /tmp/pwm-fan-web.service <<'EOF'
[Unit]
Description=PWM Fan Web Monitor
After=pwm-fan.service
Wants=pwm-fan.service

[Service]
Type=simple
ExecStart=/usr/bin/python3 /opt/pwm-fan/web_server.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF
run install -o root -g root -m 644 /tmp/pwm-fan.service "$SYSDIR/pwm-fan.service"
run install -o root -g root -m 644 /tmp/pwm-fan-web.service "$SYSDIR/pwm-fan-web.service"
run rm -f /tmp/pwm-fan.service /tmp/pwm-fan-web.service
run systemctl daemon-reload

# ---- 4. 安装 -> 启动; 升级 -> 重启 ----
if [ "$MODE" = "升级" ]; then
    echo "== 4. 升级模式: 重启服务 =="
    run systemctl restart $SERVICES
else
    echo "== 4. 首次安装: 启用并启动服务 =="
    run systemctl enable --now $SERVICES
fi
sleep 2

# ---- 5. 验证 ----
echo "== 5. 验证 =="
run systemctl is-active $SERVICES
curl -s -o /dev/null -w "   Web HTTP %{http_code}\n" http://127.0.0.1:8081 || true

IP=$(hostname -I 2>/dev/null | awk '{print $1}')
echo ""
echo "==================== 完成 ===================="
echo "  Web 面板: http://${IP:-<IP>}:8081"
echo "  github.com/arounyf/PWM-fan"
