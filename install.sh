#!/bin/bash
# PWM Fan Driver 一键部署
set -e
DIR="$(cd "$(dirname "$0")" && pwd)"

echo "=== 安装依赖 ==="
apt-get update -qq
apt-get install -y python3-libgpiod 2>&1 | tail -1

echo "=== 复制文件 ==="
mkdir -p /opt/pwm-fan
cp "$DIR/fan_driver.py" "$DIR/web_server.py" /opt/pwm-fan/
chmod +x /opt/pwm-fan/*.py

echo "=== 安装服务 ==="
cp "$DIR/pwm-fan.service" "$DIR/pwm-fan-web.service" /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now pwm-fan pwm-fan-web

sleep 2
echo ""
echo "=== 状态 ==="
cat /tmp/pwm-fan-status.json 2>/dev/null || echo "(等待驱动启动...)"
echo ""
IP=$(hostname -I 2>/dev/null | awk '{print $1}')
echo "部署完成!  Web: http://${IP:-<IP>}:8081"
