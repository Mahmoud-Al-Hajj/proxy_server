# Admin.py - Password-protected web admin panel (runs on a separate port)

import threading
import json
import base64
import secrets
from http.server import BaseHTTPRequestHandler, HTTPServer
from config import ADMIN_PORT, ADMIN_PASSWORD, LOG_FILE
import cache
import Stats
import metrics
from filter import get_blocked_hosts, add_blocked_host

# In-memory session store: { token: True }
# When the user logs in, we give them a cookie with a random token.
# Every subsequent request checks for that cookie instead of re-asking for a password.
sessions = set()
sessions_lock = threading.Lock()


def create_session():
    token = secrets.token_hex(32)
    with sessions_lock:
        sessions.add(token)
    return token


def valid_session(token):
    with sessions_lock:
        return token in sessions


def get_cookie(headers, name):
    """Extract a cookie value from the Cookie header."""
    raw = headers.get('Cookie', '')
    for part in raw.split(';'):
        part = part.strip()
        if part.startswith(name + '='):
            return part[len(name) + 1:]
    return None


def read_logs(lines=50):
    try:
        with open(LOG_FILE, 'r', encoding='utf-8') as f:
            all_lines = f.readlines()
            return ''.join(all_lines[-lines:])
    except FileNotFoundError:
        return 'No log file yet.'


class AdminHandler(BaseHTTPRequestHandler):

    def is_authenticated(self):
        """Check if the request has a valid session cookie."""
        token = get_cookie(self.headers, 'admin_session')
        return token is not None and valid_session(token)

    def check_basic_auth(self):
        """Check HTTP Basic Auth header (only used on the login POST)."""
        auth = self.headers.get('Authorization', '')
        if not auth.startswith('Basic '):
            return False
        decoded = base64.b64decode(auth[6:]).decode('utf-8')
        password = decoded.split(':', 1)[1]
        return password == ADMIN_PASSWORD

    def send_login_page(self, error=False):
        """Serve a simple HTML login form."""
        msg = '<p style="color:#a32d2d;font-size:13px">Wrong password.</p>' if error else ''
        html = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <title>Proxy Admin – Login</title>
  <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{ font-family: system-ui, sans-serif; background: #f5f5f3;
            display: flex; align-items: center; justify-content: center; height: 100vh; }}
    .card {{ background: #fff; border: 0.5px solid #ddd; border-radius: 12px;
             padding: 32px 36px; width: 340px; }}
    h1 {{ font-size: 16px; font-weight: 500; margin-bottom: 20px; color: #1a1a18; }}
    input {{ width: 100%; padding: 8px 10px; border-radius: 6px;
             border: 0.5px solid #ccc; font-size: 13px; margin-bottom: 12px; }}
    button {{ width: 100%; padding: 8px; border-radius: 6px; border: none;
              background: #1a1a18; color: #fff; font-size: 13px; cursor: pointer; }}
  </style>
</head>
<body>
  <div class="card">
    <h1>Proxy admin panel</h1>
    {msg}
    <form method="POST" action="/login">
      <input type="password" name="password" placeholder="Password" autofocus />
      <button type="submit">Sign in</button>
    </form>
  </div>
</body>
</html>"""
        body = html.encode()
        self.send_response(200)
        self.send_header('Content-Type', 'text/html')
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        pass

    def do_GET(self):
        # Login page — always accessible
        if self.path == '/login':
            self.send_login_page()
            return

        # Everything else requires a valid session cookie
        if not self.is_authenticated():
            self.send_response(302)
            self.send_header('Location', '/login')
            self.end_headers()
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
        length = int(self.headers.get('Content-Length', 0))
        body   = self.rfile.read(length).decode('utf-8')

        # Login form submission — no session required
        if self.path == '/login':
            # Parse form body: "password=admin123"
            password = ''
            for part in body.split('&'):
                if part.startswith('password='):
                    password = part[len('password='):]

            if password == ADMIN_PASSWORD:
                token = create_session()
                self.send_response(302)
                self.send_header('Set-Cookie', f'admin_session={token}; Path=/; HttpOnly')
                self.send_header('Location', '/')
                self.end_headers()
            else:
                self.send_login_page(error=True)
            return

        # All other POST routes require authentication
        if not self.is_authenticated():
            self.send_response(302)
            self.send_header('Location', '/login')
            self.end_headers()
            return

        data = json.loads(body) if body.strip().startswith('{') else {}

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
        s['blacklist']  = get_blocked_hosts()
        self.json_response(s)

    def serve_metrics(self):
        self.json_response(metrics.get_summary())

    def serve_logs(self):
        body = read_logs().encode('utf-8')
        self.send_response(200)
        self.send_header('Content-Type', 'text/plain')
        self.end_headers()
        self.wfile.write(body)

    def serve_dashboard(self):
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
    .grid-5 { display: grid; grid-template-columns: repeat(5, 1fr); gap: 10px; margin-bottom: 16px; }
    .grid-4 { display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; }
    .grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-bottom: 24px; }
    .metric { background: #ebebea; border-radius: 8px; padding: 12px 16px; }
    .metric-label { font-size: 12px; color: #888; margin-bottom: 4px; }
    .metric-val { font-size: 24px; font-weight: 500; }
    .card { background: #fff; border: 0.5px solid #ddd; border-radius: 12px; padding: 16px 20px; margin-bottom: 24px; }
    .card-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }
    .card-title { font-size: 13px; font-weight: 500; }
    button { padding: 5px 14px; border-radius: 6px; border: 0.5px solid #ccc; background: #f0f0ee; font-size: 12px; cursor: pointer; }
    button.danger  { border-color: #f09595; background: #fce; color: #791f1f; }
    button.primary { border-color: #85b7eb; background: #e6f1fb; color: #0c447c; }
    input[type=text] { padding: 6px 10px; border-radius: 6px; border: 0.5px solid #ccc; background: #f5f5f3; font-size: 13px; width: 100%; }
    .row { display: flex; gap: 8px; margin-top: 10px; }
    .row input { flex: 1; }
    .log-box { font-family: monospace; font-size: 11px; color: #555; line-height: 1.9; white-space: pre-wrap; word-break: break-all; max-height: 280px; overflow-y: auto; }
    .host-list  { font-family: monospace; font-size: 12px; color: #a32d2d; line-height: 2; }
    .cache-list { font-family: monospace; font-size: 12px; color: #444;    line-height: 2; }
    .badge { display: inline-block; font-size: 10px; padding: 1px 7px; border-radius: 99px; }
    .online { background: #eaf3de; color: #27500a; }
    .status-bar { display: flex; align-items: center; justify-content: space-between; margin-bottom: 20px; }
    .hint { font-size: 11px; color: #aaa; margin-top: 6px; }
    .feedback { font-size: 12px; color: #0c447c; min-height: 16px; margin-top: 6px; }
    .bar-wrap { background: #f0f0f0; border-radius: 3px; height: 12px; margin-bottom: 8px; }
    .bar { height: 100%; border-radius: 3px; }
    .perf-row { display: flex; justify-content: space-between; font-size: 12px; color: #555; margin-bottom: 2px; }
  </style>
</head>
<body>

<div class="status-bar">
  <div>
    <h1>Proxy admin panel</h1>
    <div class="subtitle">Live stats - refreshes every 5 seconds</div>
  </div>
  <span class="badge online">Online</span>
</div>

<!-- General stats -->
<div class="grid-5">
  <div class="metric"><div class="metric-label">Total requests</div><div class="metric-val" id="m-total">—</div></div>
  <div class="metric"><div class="metric-label">Cache hits</div><div class="metric-val" id="m-hits">—</div></div>
  <div class="metric"><div class="metric-label">Cache misses</div><div class="metric-val" id="m-misses">—</div></div>
  <div class="metric"><div class="metric-label">Cache size</div><div class="metric-val" id="m-cache">—</div></div>
  <div class="metric"><div class="metric-label">Blocked</div><div class="metric-val" style="color:#a32d2d" id="m-blocked">—</div></div>
</div>

<!-- Performance -->
<div class="card">
  <div class="card-title" style="margin-bottom:12px">Performance</div>
  <div class="grid-4" style="margin-bottom:14px">
    <div class="metric"><div class="metric-label">Avg hit (cache)</div><div class="metric-val" style="font-size:18px;color:#3b6d11" id="p-hit">—</div></div>
    <div class="metric"><div class="metric-label">Avg miss (network)</div><div class="metric-val" style="font-size:18px" id="p-miss">—</div></div>
    <div class="metric"><div class="metric-label">Speed improvement</div><div class="metric-val" style="font-size:18px;color:#185fa5" id="p-speedup">—</div></div>
    <div class="metric"><div class="metric-label">Time saved</div><div class="metric-val" style="font-size:18px;color:#0c447c" id="p-saved">—</div></div>
  </div>
  <div id="p-bars"><div style="font-size:12px;color:#aaa">Make a few requests to see the chart.</div></div>
  <div class="hint" id="p-hint"></div>
</div>

<!-- Cache and blacklist -->
<div class="grid-2">
  <div class="card">
    <div class="card-header">
      <div class="card-title">Cache contents</div>
      <button class="danger" onclick="clearCache()">Clear cache</button>
    </div>
    <div class="cache-list" id="cache-list">—</div>
    <div class="hint" id="cache-hint"></div>
    <div class="feedback" id="msg-cache"></div>
  </div>

  <div class="card">
    <div class="card-title" style="margin-bottom:10px">Blacklist</div>
    <div class="host-list" id="host-list">—</div>
    <div class="row">
      <input type="text" id="new-host" placeholder="Add host to block..." />
      <button class="primary" onclick="addHost()">Add</button>
    </div>
    <div class="feedback" id="msg-host"></div>
  </div>
</div>

<!-- Logs -->
<div class="card">
  <div class="card-header">
    <div class="card-title">Recent logs</div>
    <button onclick="loadLogs()">Refresh</button>
  </div>
  <div class="log-box" id="log-box">—</div>
</div>

<script>
  // All fetch() calls go to the same origin — the session cookie is sent
  // automatically by the browser on every request, so no auth header needed.

  async function loadStats() {
    try {
      const r = await fetch('/api/stats');
      if (!r.ok) { window.location = '/login'; return; }
      const d = await r.json();

      document.getElementById('m-total').textContent   = d.total;
      document.getElementById('m-hits').textContent    = d.hits;
      document.getElementById('m-cache').textContent   = d.cache_size;
      document.getElementById('m-blocked').textContent = d.blocked;

      const keys = d.cache_keys || [];
      document.getElementById('cache-list').textContent = keys.length ? keys.join('\\n') : 'Cache is empty';
      document.getElementById('cache-hint').textContent = keys.length ? keys.length + ' entries · TTL ' + 300 + 's' : '';

      const bl = d.blacklist || [];
      document.getElementById('host-list').textContent = bl.length ? bl.join('\\n') : 'No hosts blocked';
    } catch(e) { console.error('loadStats:', e); }
  }

  async function loadMetrics() {
    try {
      const r = await fetch('/api/metrics');
      if (!r.ok) { window.location = '/login'; return; }
      const d = await r.json();

      document.getElementById('p-hit').textContent     = d.avg_hit_ms  != null ? d.avg_hit_ms  + ' ms' : '—';
      document.getElementById('p-miss').textContent    = d.avg_miss_ms != null ? d.avg_miss_ms + ' ms' : '—';
      document.getElementById('p-speedup').textContent = d.speedup     != null ? d.speedup + 'x'       : '—';
      document.getElementById('p-saved').textContent   = d.total_saved_ms > 0  ? (d.total_saved_ms / 1000).toFixed(2) + ' s' : '—';
      document.getElementById('m-misses').textContent  = d.miss_count != null ? d.miss_count : '—';

      const bars = document.getElementById('p-bars');
      if (d.avg_miss_ms != null && d.avg_hit_ms != null) {
        const hitPct = Math.max(0.5, (d.avg_hit_ms / d.avg_miss_ms) * 100).toFixed(1);
        bars.innerHTML =
          '<div class="perf-row"><span>Network fetch (miss)</span><span style="font-family:monospace">' + d.avg_miss_ms + ' ms</span></div>' +
          '<div class="bar-wrap"><div class="bar" style="width:100%;background:#185fa5;opacity:0.7"></div></div>' +
          '<div class="perf-row"><span>Memory serve (hit)</span><span style="font-family:monospace;color:#3b6d11">' + d.avg_hit_ms + ' ms</span></div>' +
          '<div class="bar-wrap"><div class="bar" style="width:' + hitPct + '%;background:#3b6d11"></div></div>';
        document.getElementById('p-hint').textContent =
          'Based on ' + (d.hit_count + d.miss_count) + ' requests  ' + d.hit_count + ' hits, ' + d.miss_count + ' misses';
      } else {
        bars.innerHTML = '<div style="font-size:12px;color:#aaa">Make a few requests to see the comparison chart.</div>';
      }
    } catch(e) { console.error('loadMetrics:', e); }
  }

  async function loadLogs() {
    try {
      const r = await fetch('/api/logs');
      if (!r.ok) { window.location = '/login'; return; }
      const text = await r.text();
      const box  = document.getElementById('log-box');
      box.textContent  = text || 'No logs yet.';
      box.scrollTop = box.scrollHeight;
    } catch(e) { console.error('loadLogs:', e); }
  }

  async function clearCache() {
    await fetch('/api/cache/clear', { method: 'POST' });
    document.getElementById('msg-cache').textContent = 'Cache cleared.';
    setTimeout(() => document.getElementById('msg-cache').textContent = '', 2000);
    loadStats(); loadMetrics();
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
    document.getElementById('msg-host').textContent = d.message;
    document.getElementById('new-host').value = '';
    setTimeout(() => document.getElementById('msg-host').textContent = '', 2000);
    loadStats();
  }

  loadStats();
  loadLogs();
  loadMetrics();
  setInterval(loadStats,   5000);
  setInterval(loadLogs,   10000);
  setInterval(loadMetrics, 5000);
</script>
</body>
</html>"""
        body = html.encode('utf-8')
        self.send_response(200)
        self.send_header('Content-Type', 'text/html')
        self.end_headers()
        self.wfile.write(body)


def start_admin():
    server = HTTPServer(('0.0.0.0', ADMIN_PORT), AdminHandler)
    thread = threading.Thread(target=server.serve_forever)
    thread.daemon = True
    thread.start()
    print(f"[Admin] Panel running on http://127.0.0.1:{ADMIN_PORT}")