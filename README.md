# PWM Fan Driver + Web Monitor

> 专为 **OEC-Turbo (RK3566)** 适配的 GPIO PWM 风扇驱动，支持温度自控和 Web 手动调速。

## 硬件接线

| 风扇线 | 颜色 | 接法 |
|--------|------|------|
| GND | 黑 | 外部 12V 电源 GND |
| 12V | 黄/红 | 外部 12V 电源正极 |
| TACH | 绿/黄 | GPIO TX (转速读取) |
| PWM | 蓝 | GPIO RX (控制信号) |

## 部署步骤

```bash
# 1. 安装依赖
sudo apt-get update
sudo apt-get install -y python3-libgpiod

# 2. 复制文件
sudo mkdir -p /opt/pwm-fan
sudo cp fan_driver.py web_server.py /opt/pwm-fan/
sudo chmod +x /opt/pwm-fan/*.py

# 3. 安装服务
sudo cp pwm-fan.service pwm-fan-web.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now pwm-fan pwm-fan-web

# 4. 验证
cat /tmp/pwm-fan-status.json
curl http://127.0.0.1:8081
```

## Web 访问

`http://<机器IP>:8081`

- **Auto 模式**：≤35°C 风扇停转，35~65°C 线性调速，≥65°C 全速
- **Manual 模式**：滑块 0%~100%，支持 OFF/25/50/75/100% 快捷按钮

## 配置

编辑 `fan_driver.py` 顶部常量：

| 参数 | 说明 |
|------|------|
| PWM_CHIP | PWM 控制 gpiochip |
| PWM_PIN | PWM 控制引脚 |
| TACH_CHIP | 转速反馈 gpiochip |
| TACH_PIN | 转速反馈引脚 |
| PWM_FREQ | PWM 频率 (Hz) |
| TEMP_MIN | 风扇起转温度 (毫度) |
| TEMP_MAX | 风扇全速温度 (毫度) |
| DUTY_MIN | 最低占空比 (%) |

## 文件说明

| 文件 | 作用 |
|------|------|
| fan_driver.py | 主驱动，PWM 输出 + 温度读取 + 转速反馈 |
| web_server.py | Web 监控控制页面 |
| pwm-fan.service | 驱动 systemd 服务 |
| pwm-fan-web.service | Web systemd 服务 |
| test_gpio.py | GPIO 测试工具 |
| install.sh | 一键安装脚本 (需 root) |
