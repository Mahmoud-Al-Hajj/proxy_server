# admin.py - Password-protected web admin panel (runs on a separate port)

import threading
import json
import base64
from http.server import BaseHTTPRequestHandler, HTTPServer
from config import ADMIN_PORT, ADMIN_PASSWORD, LOG_FILE
import cache
import Stats
import metrics
from filter import get_blocked_hosts, add_blocked_host


def read_logs(lines=50):
    try:
        with open(LOG_FILE, 'r') as f:
            all_lines = f.readlines()
            return ''.join(all_lines[-lines:])
    except FileNotFoundError:
        return 'No log file yet.'


class AdminHandler(BaseHTTPRequestHandler):
    """Handles all HTTP requests to the admin panel."""

    def check_auth(self):
        """
        Check HTTP Basic Auth header.
        Returns True if the password matches, False otherwise.
        """
        auth_header = self.headers.get('Authorization', '')
        if not auth_header.startswith('Basic '):
            return False

        encoded = auth_header[6:]
        decoded = base64.b64decode(encoded).decode('utf-8')
        password = decoded.split(':', 1)[1]
        return password == ADMIN_PASSWORD

    def require_auth(self):
        """Send a 401 response that prompts the browser for a password."""
        self.send_response(401)
        self.send_header('WWW-Authenticate', 'Basic realm="Proxy Admin"')
        self.send_header('Content-Type', 'text/plain')
        self.end_headers()
        self.wfile.write(b'Unauthorized')

    def log_message(self, format, *args):
        """Stops the repetitive HTTP access logs"""
        pass

    def do_GET(self):
        if not self.check_auth():
            self.require_auth()
            return

        if self.path == '/':
            self.serve_dashboard()
        elif self.path == '/api/stats':
            self.serve_stats()
        elif self.path == '/api/metrics':
            self.serve_metrics()
        elif self.path == '/api/logs':
            self.serve_logs()
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        if not self.check_auth():
            self.require_auth()
            return

        length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(length).decode('utf-8')
        data = json.loads(body) if body else {}

        if self.path == '/api/cache/clear':
            cache.clear()
            self.json_response({'ok': True, 'message': 'Cache cleared'})

        elif self.path == '/api/blacklist/add':
            host = data.get('host', '').strip()
            if host:
                add_blocked_host(host)
                self.json_response({'ok': True, 'message': f'{host} blocked'})
            else:
                self.json_response({'ok': False, 'message': 'No host provided'})
        else:
            self.send_response(404)
            self.end_headers()

    def json_response(self, data):
        body = json.dumps(data).encode()
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(body)

    def serve_stats(self):
        s = Stats.get()
        s['cache_size'] = cache.size()
        s['cache_keys'] = cache.keys()
        s['blacklist'] = get_blocked_hosts()
        self.json_response(s)

    def serve_metrics(self):
        m = metrics.get_summary()
        self.json_response(m)

    def serve_logs(self):
        body = read_logs().encode()
        self.send_response(200)
        self.send_header('Content-Type', 'text/plain')
        self.end_headers()
        self.wfile.write(body)

    def serve_dashboard(self):
        """Serve the full admin HTML page."""
        html = """<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <title>Proxy Admin</title>
  <style>
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body { font-family: system-ui, sans-serif; background: #f5f5f3; color: #1a1a18; padding: 24px; }
    h1 { font-size: 18px; font-weight: 500; margin-bottom: 4px; }
    .subtitle { font-size: 13px; color: #888; margin-bottom: 20px; }
    .grid-4 { display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; margin-bottom: 16px; }
    .grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-bottom: 12px; }
    .metric { background: #ebebea; border-radius: 8px; padding: 12px 16px; }
    .metric-label { font-size: 12px; color: #888; margin-bottom: 4px; }
    .metric-val { font-size: 24px; font-weight: 500; }
    .card { background: #fff; border: 0.5px solid #ddd; border-radius: 12px; padding: 16px 20px; }
    .card-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }
    .card-title { font-size: 13px; font-weight: 500; }
    button { padding: 5px 14px; border-radius: 6px; border: 0.5px solid #ccc; background: #f0f0ee; font-size: 12px; cursor: pointer; }
    button.danger { border-color: #f09595; background: #fce; color: #791f1f; }
    button.primary { border-color: #85b7eb; background: #e6f1fb; color: #0c447c; }
    input[type=text] { padding: 6px 10px; border-radius: 6px; border: 0.5px solid #ccc; background: #f5f5f3; font-size: 13px; width: 100%; }
    .row { display: flex; gap: 8px; margin-top: 10px; }
    .row input { flex: 1; }
    .log-box { font-family: monospace; font-size: 11px; color: #555; line-height: 1.9; white-space: pre-wrap; word-break: break-all; max-height: 280px; overflow-y: auto; }
    .host-list { font-family: monospace; font-size: 12px; color: #a32d2d; line-height: 2; }
    .cache-list { font-family: monospace; font-size: 12px; color: #444; line-height: 2; }
    .badge { display: inline-block; font-size: 10px; padding: 1px 7px; border-radius: 99px; margin-right: 4px; }
    .online { background: #eaf3de; color: #27500a; }
    .status-bar { display: flex; align-items: center; justify-content: space-between; margin-bottom: 20px; }
    .hint { font-size: 11px; color: #aaa; margin-top: 6px; }
    #msg { font-size: 12px; color: #0c447c; min-height: 16px; margin-top: 6px; }
    .grid-4 { display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; }
  </style>
</head>
<body>

<div class="status-bar">
  <div>
    <h1>Proxy admin panel</h1>
    <div class="subtitle" id="port-info">Loading...</div>
  </div>
  <span class="badge online">Online</span>
</div>

<div class="grid-4" id="metrics">
  <div class="metric"><div class="metric-label">Total requests</div><div class="metric-val" id="m-total">—</div></div>
  <div class="metric"><div class="metric-label">Cache hits</div><div class="metric-val" id="m-hits">—</div></div>
  <div class="metric"><div class="metric-label">Cache entries</div><div class="metric-val" id="m-cache">—</div></div>
  <div class="metric"><div class="metric-label">Blocked</div><div class="metric-val" style="color:#a32d2d" id="m-blocked">—</div></div>
</div>

<div class="card">
  <div class="card-title" style="margin-bottom:10px">Performance metrics</div>
  <div class="grid-4" style="margin-bottom: 12px;">
    <div class="metric"><div class="metric-label">Avg hit</div><div class="metric-val" style="font-size:18px" id="p-hit">—</div></div>
    <div class="metric"><div class="metric-label">Avg miss</div><div class="metric-val" style="font-size:18px" id="p-miss">—</div></div>
    <div class="metric"><div class="metric-label">Speedup</div><div class="metric-val" style="font-size:18px;color:#3b6d11" id="p-speedup">—</div></div>
    <div class="metric"><div class="metric-label">Time saved</div><div class="metric-val" style="font-size:18px;color:#0c447c" id="p-saved">—</div></div>
  </div>
  <div id="p-bars"></div>
  <div class="hint" id="p-hint"></div>
  <style>
    .perf-row { display: flex; justify-content: space-between; font-size: 12px; margin-bottom: 4px; }
    .bar-wrap { background: #f0f0f0; border-radius: 3px; height: 12px; margin-bottom: 8px; }
    .bar { height: 100%; border-radius: 3px; }
  </style>
</div>

<div class="grid-2">
  <div class="card">
    <div class="card-header">
      <div class="card-title">Cache contents</div>
      <button class="danger" onclick="clearCache()">Clear cache</button>
    </div>
    <div class="cache-list" id="cache-list">Loading...</div>
    <div class="hint" id="cache-hint"></div>
    <div id="msg"></div>
  </div>

  <div class="card">
    <div class="card-title" style="margin-bottom:10px">Blacklist</div>
    <div class="host-list" id="host-list">Loading...</div>
    <div class="row">
      <input type="text" id="new-host" placeholder="Add host to block..." />
      <button class="primary" onclick="addHost()">Add</button>
    </div>
    <div id="msg2" style="font-size:12px; color:#0c447c; min-height:16px; margin-top:6px;"></div>
  </div>
</div>

<div class="card">
  <div class="card-header">
    <div class="card-title">Recent logs</div>
    <button onclick="loadLogs()">Refresh</button>
  </div>
  <div class="log-box" id="log-box">Loading...</div>
</div>

<script>
  async function loadStats() {
    const r = await fetch('/api/stats');
    const d = await r.json();
    document.getElementById('m-total').textContent   = d.total;
    document.getElementById('m-hits').textContent    = d.hits;
    document.getElementById('m-cache').textContent   = d.cache_size;
    document.getElementById('m-blocked').textContent = d.blocked;
    document.getElementById('port-info').textContent = 'Proxy admin · live stats';

    const cacheEl = document.getElementById('cache-list');
    const cacheKeys = d.cache_keys || [];
    cacheEl.textContent = cacheKeys.length ? cacheKeys.join('\\n') : 'Cache is empty';
    document.getElementById('cache-hint').textContent =
      cacheKeys.length ? cacheKeys.length + ' entries · TTL 60s' : '';

    const hostEl = document.getElementById('host-list');
    hostEl.textContent = (d.blacklist || []).length ? d.blacklist.join('\\n') : 'No hosts blocked';
  }

  async function loadLogs() {
    const r = await fetch('/api/logs');
    const text = await r.text();
    const box = document.getElementById('log-box');
    box.textContent = text;
    box.scrollTop = box.scrollHeight;
  }

  async function clearCache() {
    await fetch('/api/cache/clear', { method: 'POST' });
    document.getElementById('msg').textContent = 'Cache cleared.';
    setTimeout(() => document.getElementById('msg').textContent = '', 2000);
    loadStats();
  }

  async function addHost() {
    const host = document.getElementById('new-host').value.trim();
    if (!host) return;
    const r = await fetch('/api/blacklist/add', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ host })
    });
    const d = await r.json();
    document.getElementById('msg2').textContent = d.message;
    document.getElementById('new-host').value = '';
    setTimeout(() => document.getElementById('msg2').textContent = '', 2000);
    loadStats();
  }


  async function loadMetrics() {
    const r = await fetch('/api/metrics');
    const d = await r.json();
    document.getElementById('p-miss').textContent    = d.avg_miss_ms !== null ? d.avg_miss_ms + ' ms' : '—';
    document.getElementById('p-hit').textContent     = d.avg_hit_ms  !== null ? d.avg_hit_ms  + ' ms' : '—';
    document.getElementById('p-speedup').textContent = d.speedup     !== null ? d.speedup + '×'       : '—';
    document.getElementById('p-saved').textContent   = d.total_saved_ms > 0   ? (d.total_saved_ms / 1000).toFixed(2) + ' s' : '—';

    const bars = document.getElementById('p-bars');
    if (d.avg_miss_ms && d.avg_hit_ms) {
      const hitPct = Math.max(0.5, (d.avg_hit_ms / d.avg_miss_ms) * 100).toFixed(1);
      bars.innerHTML = `
        <div class="perf-row"><span>Network fetch (miss)</span><span style="font-family:monospace">${d.avg_miss_ms} ms</span></div>
        <div class="bar-wrap"><div class="bar" style="width:100%;background:#185fa5;opacity:0.7"></div></div>
        <div class="perf-row"><span>Memory serve (hit)</span><span style="font-family:monospace;color:#3b6d11">${d.avg_hit_ms} ms</span></div>
        <div class="bar-wrap"><div class="bar" style="width:${hitPct}%;background:#3b6d11"></div></div>`;
      document.getElementById('p-hint').textContent =
        'Based on ' + (d.hit_count + d.miss_count) + ' requests — ' + d.hit_count + ' hits, ' + d.miss_count + ' misses';
    }
  }

  loadStats();
  loadLogs();
  loadMetrics();
  setInterval(loadStats, 5000);
  setInterval(loadLogs, 10000);
  setInterval(loadMetrics, 5000);
</script>
</body>
</html>"""
        body = html.encode()
        self.send_response(200)
        self.send_header('Content-Type', 'text/html')
        self.end_headers()
        self.wfile.write(body)


def start_admin():
    """Start the admin HTTP server in a background daemon thread."""
    server = HTTPServer(('0.0.0.0', ADMIN_PORT), AdminHandler)
    thread = threading.Thread(target=server.serve_forever)
    thread.daemon = True #dont wait for it to finish when exiting the main program
    thread.start()
    print(f"[Admin] Panel running on http://127.0.0.1:{ADMIN_PORT}")