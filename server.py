import json
from asyncio import Event

from aiohttp import web

import errors
from lock import Lock

routes = web.RouteTableDef()

INDEX_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=no">
<title>Yeelock</title>
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    background: #0a0a0a; color: #fff;
    min-height: 100vh; display: flex; flex-direction: column;
    align-items: center; justify-content: center; padding: 20px;
  }
  .card {
    background: #161616; border: 1px solid #222; border-radius: 20px;
    padding: 32px 28px; width: 100%; max-width: 360px;
  }
  h1 { font-size: 18px; font-weight: 600; text-align: center; margin-bottom: 24px; color: #ccc; }
  .lock-icon {
    font-size: 64px; text-align: center; margin-bottom: 24px;
    transition: transform 0.3s;
  }
  .lock-icon.unlocked { transform: scale(1.1); }
  .status {
    text-align: center; font-size: 14px; color: #666;
    min-height: 20px; margin-bottom: 24px;
    transition: color 0.3s;
  }
  .status.success { color: #34c759; }
  .status.error { color: #ff453a; }
  .status.working { color: #ff9f0a; }
  .battery {
    text-align: center; font-size: 13px; color: #444;
    margin-bottom: 20px;
  }
  .battery span { color: #666; }
  .actions { display: flex; flex-direction: column; gap: 10px; }
  button {
    width: 100%; padding: 14px; border: none; border-radius: 12px;
    font-size: 16px; font-weight: 600; cursor: pointer;
    transition: all 0.2s; position: relative;
  }
  button:active { transform: scale(0.97); }
  button:disabled { opacity: 0.4; cursor: not-allowed; transform: none; }
  .btn-unlock { background: #34c759; color: #fff; }
  .btn-lock { background: #ff453a; color: #fff; }
  .btn-temp { background: #ff9f0a; color: #fff; }
  .btn-battery { background: #1c1c1e; color: #999; border: 1px solid #333; }
  .settings {
    margin-top: 20px; padding-top: 16px; border-top: 1px solid #222;
  }
  .field { margin-bottom: 12px; }
  .field label { display: block; font-size: 11px; color: #666; margin-bottom: 4px; text-transform: uppercase; letter-spacing: 0.5px; }
  .field input {
    width: 100%; padding: 10px 12px; background: #1c1c1e; border: 1px solid #333;
    border-radius: 8px; color: #fff; font-size: 14px; font-family: monospace;
  }
  .field input:focus { outline: none; border-color: #555; }
  .toggle-settings {
    background: none; border: none; color: #444; font-size: 12px;
    cursor: pointer; padding: 8px; width: 100%; text-align: center;
  }
  .toggle-settings:hover { color: #666; }
  .hidden { display: none; }
</style>
</head>
<body>
<div class="card">
  <h1>Yeelock</h1>
  <div class="lock-icon" id="lockIcon">🔒</div>
  <div class="battery" id="batteryInfo"></div>
  <div class="status" id="status">Ready</div>
  <div class="actions">
    <button class="btn-unlock" onclick="doAction('unlock')">Unlock</button>
    <button class="btn-lock" onclick="doAction('lock')">Lock</button>
    <button class="btn-temp" onclick="doAction('temp_unlock')">Temp Unlock</button>
    <button class="btn-battery" onclick="getBattery()">Check Battery</button>
  </div>
  <button class="toggle-settings" onclick="toggleSettings()">Settings</button>
  <div class="settings hidden" id="settings">
    <div class="field">
      <label>Serial Number</label>
      <input type="text" id="sn" placeholder="XXXXXXXX">
    </div>
    <div class="field">
      <label>Sign Key</label>
      <input type="text" id="signKey" placeholder="your_sign_key_hex">
    </div>
  </div>
</div>
<script>
const $ = id => document.getElementById(id);
const SN_KEY = 'yeelock_sn';
const SIGN_KEY = 'yeelock_sign_key';

window.onload = () => {
  $('sn').value = localStorage.getItem(SN_KEY) || '';
  $('signKey').value = localStorage.getItem(SIGN_KEY) || '';
};

function save() {
  localStorage.setItem(SN_KEY, $('sn').value);
  localStorage.setItem(SIGN_KEY, $('signKey').value);
}

function setStatus(msg, type) {
  const s = $('status');
  s.textContent = msg;
  s.className = 'status ' + (type || '');
}

function setButtons(disabled) {
  document.querySelectorAll('.actions button').forEach(b => b.disabled = disabled);
}

function toggleSettings() {
  $('settings').classList.toggle('hidden');
}

async function doAction(action) {
  const sn = $('sn').value.trim();
  const key = $('signKey').value.trim();
  if (!sn || !key) { toggleSettings(); setStatus('Enter S/N and key', 'error'); return; }
  save();
  setButtons(true);
  setStatus('Connecting...', 'working');
  $('lockIcon').className = 'lock-icon';
  try {
    const res = await fetch('/do', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({action, sn, sign_key: key})
    });
    const data = await res.json();
    if (data.success) {
      const label = action === 'lock' ? 'Locked' : action === 'unlock' ? 'Unlocked' : 'Temp Unlocked';
      const icon = action === 'lock' ? '🔒' : '🔓';
      $('lockIcon').textContent = icon;
      $('lockIcon').className = 'lock-icon' + (action !== 'lock' ? ' unlocked' : '');
      setStatus(label, 'success');
    } else {
      setStatus(data.error || 'Failed', 'error');
    }
  } catch (e) {
    setStatus('Connection error', 'error');
  }
  setButtons(false);
}

async function getBattery() {
  const sn = $('sn').value.trim();
  if (!sn) { toggleSettings(); setStatus('Enter S/N', 'error'); return; }
  save();
  setButtons(true);
  setStatus('Reading battery...', 'working');
  try {
    const res = await fetch('/info', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({sn})
    });
    const data = await res.json();
    if (data.battery !== undefined) {
      $('batteryInfo').innerHTML = '🔋 <span>' + data.battery + '%</span>';
      setStatus('Battery: ' + data.battery + '%', 'success');
    } else {
      setStatus(data.error || 'Failed', 'error');
    }
  } catch (e) {
    setStatus('Connection error', 'error');
  }
  setButtons(false);
}
</script>
</body>
</html>"""


class Server:
    def __init__(self, port: int):
        self.port: int = port

    async def start(self):
        app = web.Application()
        app.add_routes(routes)

        runner = web.AppRunner(app)
        await runner.setup()

        site = web.TCPSite(runner, port=self.port)
        await site.start()

        await Event().wait()

    @routes.get('/')
    async def index(request):
        return web.Response(text=INDEX_HTML, content_type='text/html')

    @routes.post('/info')
    async def info(request):
        try:
            data = await request.json()
            sn = data['sn']
            timeout = int(data.get('timeout', 10))
        except (json.decoder.JSONDecodeError, AttributeError, KeyError):
            return web.json_response({'error': 'Invalid input'}, status=400)

        try:
            lock = await Lock.create(sn, bytearray(), timeout)
            level = await lock.get_battery()
        except errors.DeviceNotFoundError:
            return web.json_response({'error': 'Device not found'}, status=400)

        return web.json_response({'battery': level})

    @routes.post('/do')
    async def do(request):
        try:
            data = await request.json()
            action = data['action']
            sn = data['sn']
            sign_key = data['sign_key']
            timeout = int(data.get('timeout', 10))
        except (json.decoder.JSONDecodeError, AttributeError, KeyError):
            return web.json_response({'error': 'Invalid input'}, status=400)

        try:
            lock = await Lock.create(sn, bytearray.fromhex(sign_key), timeout)
        except ValueError:
            return web.json_response({'error': 'Sign key is not a hexadecimal string'}, status=400)
        except errors.DeviceNotFoundError:
            return web.json_response({'error': 'Device not found'}, status=400)

        if action == 'lock':
            await lock.lock()
        elif action == 'unlock':
            await lock.unlock()
        elif action == 'temp_unlock':
            await lock.temp_unlock()
        else:
            return web.json_response({'error': 'Unknown action to do'}, status=400)

        return web.json_response({'success': True})

