#!/usr/bin/env python3
"""Web monitor + controller for PWM Fan."""
import json
import os
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse

STATUS_FILE = "/tmp/pwm-fan-status.json"
CTRL_FILE   = "/tmp/pwm-fan-ctrl.json"   # manual override: {"mode":"auto"|"manual", "duty":0-100}
PORT = 8081

HTML = """<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>PWM Fan Control</title>
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: -apple-system, 'Segoe UI', sans-serif; background: #0f172a; color: #e2e8f0;
       display: flex; justify-content: center; align-items: center; min-height: 100vh; }
.card { background: #1e293b; border-radius: 16px; padding: 32px; max-width: 440px; width: 90%;
        box-shadow: 0 4px 24px rgba(0,0,0,0.3); }
h1 { font-size: 1.3rem; text-align: center; margin-bottom: 20px; color: #94a3b8; }
.row { display: flex; justify-content: space-between; align-items: center;
       padding: 12px 0; border-bottom: 1px solid #334155; }
.row:last-child { border-bottom: none; }
.label { font-size: 0.85rem; color: #64748b; }
.value { font-size: 1.4rem; font-weight: 700; }
.temp .value { color: #fb923c; }
.duty .value { color: #60a5fa; }
.rpm .value { color: #4ade80; }
.bar-wrap { background: #334155; border-radius: 6px; height: 10px; margin-top: 6px; overflow: hidden; }
.temp .bar-fill { background: linear-gradient(90deg, #4ade80, #facc15, #ef4444); height:100%; border-radius:6px; transition: width 0.5s; }
.duty .bar-fill { background: linear-gradient(90deg, #2563eb, #60a5fa); height:100%; border-radius:6px; transition: width 0.5s; }
.rpm .bar-fill { background: #4ade80; height:100%; border-radius:6px; transition: width 0.5s; }
/* Controls */
.ctrl { margin-top: 20px; padding-top: 16px; border-top: 1px solid #334155; }
.mode-row { display: flex; gap: 8px; margin-bottom: 16px; }
.mode-btn { flex: 1; padding: 10px; border: 2px solid #334155; border-radius: 8px;
            background: transparent; color: #94a3b8; font-size: 0.9rem; cursor: pointer; transition: all 0.2s; }
.mode-btn.active { border-color: #60a5fa; color: #60a5fa; background: rgba(96,165,250,0.1); }
.mode-btn:hover { border-color: #60a5fa; }
.slider-wrap { display: flex; align-items: center; gap: 12px; }
.slider-wrap input[type=range] { flex: 1; -webkit-appearance: none; height: 8px;
  background: #334155; border-radius: 4px; outline: none; }
.slider-wrap input[type=range]::-webkit-slider-thumb { -webkit-appearance: none;
  width: 28px; height: 28px; background: #60a5fa; border-radius: 50%; cursor: pointer; }
.duty-display { font-size: 2rem; font-weight: 700; color: #60a5fa; min-width: 70px; text-align: right; }
.btns { display: flex; gap: 8px; margin-top: 8px; }
.preset-btn { flex: 1; padding: 8px; border: 1px solid #334155; border-radius: 6px;
              background: transparent; color: #94a3b8; font-size: 0.8rem; cursor: pointer; }
.preset-btn:hover { border-color: #60a5fa; color: #60a5fa; }
.hdd-refresh { background: #1e293b; border: 1px solid #475569; border-radius: 6px;
  cursor: pointer; font-size: 0.85rem; padding: 4px 10px; margin-left: 8px; color: #a78bfa; }
.hdd-refresh:hover { border-color: #a78bfa; color: #a78bfa; }
.info { text-align: center; margin-top: 12px; font-size: 0.7rem; color: #475569; }
</style>
<script>
let mode = 'auto';
let dirty = 0;  // timestamp of last manual change, prevent refresh flicker

async function refresh() {
  try {
    const r = await fetch('/api/status');
    const d = await r.json();
    document.getElementById('temp').textContent = d.temp_c + ' °C';
    document.getElementById('temp-bar').style.width = Math.min(100, (d.temp_c / 80) * 100) + '%';
    if (d.hdd_c != null) {
      document.getElementById('hdd').textContent = d.hdd_c + ' °C';
      document.getElementById('hdd-bar').style.width = Math.min(100, (d.hdd_c / 60) * 100) + '%';
    } else { document.getElementById('hdd').textContent = '—'; }
    document.getElementById('duty').textContent = d.duty + '%';
    document.getElementById('duty-bar').style.width = d.duty + '%';
    document.getElementById('rpm').textContent = d.rpm > 0 ? d.rpm + ' RPM' : '—';
    document.getElementById('rpm-bar').style.width = d.rpm > 0 ? Math.min(100, (d.rpm / 3000) * 100) + '%' : '0%';
    document.getElementById('gpio').textContent = 'PWM @ ' + d.freq + 'Hz';
    document.getElementById('time').textContent = new Date().toLocaleTimeString('zh-CN');
    // sync slider only if we haven't just manually changed it (2s debounce)
    let sl = document.getElementById('slider');
    if (mode === 'manual' && document.activeElement !== sl && Date.now() - dirty > 2000) {
      sl.value = d.duty;
      document.getElementById('dutyVal').textContent = d.duty + '%';
    }
  } catch(e) {}
}

async function setMode(m) {
  mode = m;
  document.getElementById('btn-auto').classList.toggle('active', m === 'auto');
  document.getElementById('btn-manual').classList.toggle('active', m === 'manual');
  if (m === 'auto') {
    await fetch('/api/ctrl', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({mode:'auto'}) });
  } else {
    let d = parseInt(document.getElementById('slider').value);
    await setDuty(d);
  }
}

async function refreshHdd() {
  let btn = document.querySelector('.hdd-refresh');
  btn.textContent = '⏳';
  btn.disabled = true;
  await fetch('/api/hdd_refresh', { method:'POST' });
  // wait 2s for driver to pick up, then refresh display
  setTimeout(() => {
    refresh();
    btn.textContent = 'Refresh';
    btn.disabled = false;
  }, 2000);
}

async function setDuty(v) {
  dirty = Date.now();
  document.getElementById('dutyVal').textContent = v + '%';
  document.getElementById('slider').value = v;
  document.getElementById('btn-auto').classList.remove('active');
  document.getElementById('btn-manual').classList.add('active');
  mode = 'manual';
  await fetch('/api/ctrl', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({mode:'manual', duty: v}) });
}

document.addEventListener('DOMContentLoaded', () => {
  document.getElementById('slider').addEventListener('input', function() {
    setDuty(parseInt(this.value));
  });
  setInterval(refresh, 2000);
  refresh();
});
</script>
</head>
<body>
<div class="card">
  <h1>PWM Fan Control</h1>

  <div class="row temp">
    <div><div class="label">CPU Temperature</div><div class="value" id="temp">—</div></div>
  </div>
  <div class="bar-wrap"><div class="bar-fill" id="temp-bar" style="width:0%"></div></div>

  <div class="row hdd" style="margin-top:8px">
    <div>
      <div class="label">HDD Temperature <button class="hdd-refresh" onclick="refreshHdd()">Refresh</button></div>
      <div class="value" id="hdd">—</div>
    </div>
  </div>
  <div class="bar-wrap"><div class="bar-fill" id="hdd-bar" style="width:0%; background:#a78bfa;"></div></div>

  <div class="row duty" style="margin-top:8px">
    <div><div class="label">Fan Duty Cycle</div><div class="value" id="duty">—</div></div>
  </div>
  <div class="bar-wrap"><div class="bar-fill" id="duty-bar" style="width:0%"></div></div>

  <div class="row rpm">
    <div><div class="label">Fan Speed</div><div class="value" id="rpm">—</div></div>
  </div>
  <div class="bar-wrap"><div class="bar-fill" id="rpm-bar" style="width:0%"></div></div>

  <div class="ctrl">
    <div class="mode-row">
      <button class="mode-btn active" id="btn-auto" onclick="setMode('auto')">Auto</button>
      <button class="mode-btn" id="btn-manual" onclick="setMode('manual')">Manual</button>
    </div>
    <div class="slider-wrap">
      <input type="range" id="slider" min="0" max="100" value="50" oninput="setDuty(parseInt(this.value))">
      <span class="duty-display" id="dutyVal">50%</span>
    </div>
    <div class="btns">
      <button class="preset-btn" onclick="document.getElementById('slider').value=0;setDuty(0)">OFF</button>
      <button class="preset-btn" onclick="document.getElementById('slider').value=25;setDuty(25)">25%</button>
      <button class="preset-btn" onclick="document.getElementById('slider').value=50;setDuty(50)">50%</button>
      <button class="preset-btn" onclick="document.getElementById('slider').value=75;setDuty(75)">75%</button>
      <button class="preset-btn" onclick="document.getElementById('slider').value=100;setDuty(100)">100%</button>
    </div>
  </div>

  <div class="info"><span id="gpio">—</span> | <span id="time">—</span></div>
  <div class="info" style="margin-top:8px"><a href="https://github.com/arounyf/PWM-fan" target="_blank" style="color:#a78bfa;text-decoration:none;">github.com/arounyf/PWM-fan</a></div>
</div>
</body>
</html>"""

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/api/status":
            try:
                with open(STATUS_FILE) as f:
                    data = f.read()
                self._json(200, data)
            except FileNotFoundError:
                self._json(503, '{"error":"driver not running"}')
        else:
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(HTML.encode())

    def do_POST(self):
        if self.path == "/api/ctrl":
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length).decode()
            ctrl = json.loads(body)
            with open(CTRL_FILE, "w") as f:
                json.dump(ctrl, f)
            self._json(200, '{"ok":true}')
        elif self.path == "/api/hdd_refresh":
            with open("/tmp/pwm-fan-hdd-refresh", "w") as f:
                f.write("1")
            self._json(200, '{"ok":true}')
        else:
            self._json(404, '{"error":"not found"}')

    def _json(self, code, data):
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(data.encode() if isinstance(data, str) else json.dumps(data).encode())

    def log_message(self, format, *args):
        pass

def main():
    print(f"Fan Control Web: http://0.0.0.0:{PORT}")
    server = HTTPServer(("0.0.0.0", PORT), Handler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    server.server_close()

if __name__ == "__main__":
    main()
