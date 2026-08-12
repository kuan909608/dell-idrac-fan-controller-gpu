import json
import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from socketserver import TCPServer
from typing import Mapping


@dataclass(frozen=True)
class WebSettings:
    host: str = "127.0.0.1"
    port: int = 8080


def _is_stale(last_updated, now, stale_after_seconds):
    if not last_updated:
        return True
    try:
        updated = datetime.fromisoformat(last_updated)
        if updated.tzinfo is None:
            updated = updated.replace(tzinfo=timezone.utc)
        return (now - updated.astimezone(timezone.utc)).total_seconds() > stale_after_seconds
    except (TypeError, ValueError):
        return True


def _public_device(name, device, now, stale_after_seconds):
    status = device.get("sensor_status", "unknown")
    if status == "ok" and _is_stale(device.get("last_updated"), now, stale_after_seconds):
        status = "stale"
    return {
        "name": name,
        "fan_control_mode": device.get("fan_control_mode"),
        "fan_speed": device.get("fan_speed"),
        "cpu_temps": list(device.get("cpu_temps") or []),
        "gpu_temps": list(device.get("gpu_temps") or []),
        "control_temperature": device.get("control_temperature"),
        "sensor_status": status,
        "last_error": device.get("last_error"),
        "last_updated": device.get("last_updated"),
        "vms": [
            _public_device(vm_name, vm_state, now, stale_after_seconds)
            for vm_name, vm_state in sorted((device.get("vms") or {}).items())
        ],
    }


def build_status_snapshot(runtime_state: Mapping, stale_after_seconds=180) -> dict:
    now = datetime.now(timezone.utc)
    return {
        "generated_at": now.isoformat(),
        "hosts": [
            _public_device(host_name, host_state, now, stale_after_seconds)
            for host_name, host_state in sorted(runtime_state.items())
        ],
    }


DASHBOARD_HTML = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>iDRAC Thermal Console</title>
  <style>
    :root { color-scheme: dark; --bg:#07100c; --panel:#0b1812; --line:#24563a; --fg:#b7f7cf; --dim:#6f9c80; --ok:#62e993; --warn:#ffd166; --bad:#ff6b6b; }
    * { box-sizing:border-box; }
    body { margin:0; background:var(--bg); color:var(--fg); font:14px/1.45 ui-monospace,SFMono-Regular,Menlo,Consolas,monospace; }
    main { width:min(1100px,calc(100% - 24px)); margin:24px auto; }
    header { display:flex; justify-content:space-between; gap:16px; align-items:end; border-bottom:1px solid var(--line); padding-bottom:12px; }
    h1 { margin:0; font-size:clamp(18px,4vw,28px); letter-spacing:.08em; }
    .dim { color:var(--dim); } .status-ok { color:var(--ok); } .status-error { color:var(--bad); } .status-stale { color:var(--warn); }
    #hosts { display:grid; gap:12px; margin-top:16px; }
    .host { border:1px solid var(--line); background:var(--panel); padding:14px; box-shadow:4px 4px 0 #020604; }
    .host-head { display:flex; justify-content:space-between; gap:12px; margin-bottom:12px; }
    .grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(150px,1fr)); gap:8px; }
    .metric { border-left:2px solid var(--line); padding-left:8px; } .metric b { display:block; font-size:18px; }
    .vms { margin-top:12px; padding-top:10px; border-top:1px dashed var(--line); }
    footer { margin-top:18px; color:var(--dim); }
  </style>
</head>
<body><main>
  <header><div><div class="dim">DELL POWEREDGE // HOMELAB AI THERMAL MONITOR</div><h1>iDRAC THERMAL CONSOLE</h1></div><div id="connection">CONNECTING...</div></header>
  <section id="hosts" aria-live="polite"></section>
  <footer>READ-ONLY // LOCAL BINDING BY DEFAULT // AUTO REFRESH 3s</footer>
</main>
<script>
const hosts = document.querySelector('#hosts');
const connection = document.querySelector('#connection');
const el = (tag, text, cls) => { const node=document.createElement(tag); if(text!==undefined) node.textContent=text; if(cls) node.className=cls; return node; };
const metric = (label, value) => { const box=el('div',undefined,'metric'); box.append(el('span',label,'dim'),el('b',value)); return box; };
const temperatures = values => values && values.length ? values.map(v => `${Number(v).toFixed(1)}°C`).join('  ') : '--';
const timestamp = value => value ? value.slice(0,19).replace('T',' ') : '--';
function hostCard(host) {
  const card=el('article',undefined,'host'); const head=el('div',undefined,'host-head');
  head.append(el('strong',`[${host.name}]`),el('span',String(host.sensor_status||'unknown').toUpperCase(),`status-${host.sensor_status||'stale'}`));
  const grid=el('div',undefined,'grid');
  grid.append(metric('CPU',temperatures(host.cpu_temps)),metric('GPU',temperatures(host.gpu_temps)),metric('CONTROL',host.control_temperature==null?'--':`${Number(host.control_temperature).toFixed(1)}°C`),metric('FAN',`${host.fan_speed??'--'}% / ${host.fan_control_mode??'--'}`),metric('UPDATED',timestamp(host.last_updated)));
  card.append(head,grid);
  if(host.last_error) card.append(el('div',`! ${host.last_error}`,'status-error'));
  if(host.vms && host.vms.length) { const vms=el('div',undefined,'vms'); vms.append(el('div','VM GPU SOURCES','dim')); host.vms.forEach(vm=>vms.append(el('div',`${vm.name}: ${temperatures(vm.gpu_temps)}`))); card.append(vms); }
  return card;
}
async function refresh() {
  try { const response=await fetch('/api/status',{cache:'no-store'}); if(!response.ok) throw new Error(`HTTP ${response.status}`); const data=await response.json(); hosts.replaceChildren(...data.hosts.map(hostCard)); if(!data.hosts.length) hosts.append(el('div','NO HOST DATA','dim')); connection.textContent='ONLINE'; connection.className='status-ok'; }
  catch(error) { connection.textContent=`OFFLINE // ${error.message}`; connection.className='status-error'; }
}
refresh(); setInterval(refresh,3000);
</script></body></html>"""


class _Handler(BaseHTTPRequestHandler):
    runtime_state = None

    def _headers(self, status, content_type, length=None):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; connect-src 'self'")
        if length is not None:
            self.send_header("Content-Length", str(length))
        self.end_headers()

    def do_GET(self):
        if self.path == "/api/status":
            payload = json.dumps(build_status_snapshot(self.runtime_state)).encode("utf-8")
            self._headers(200, "application/json; charset=utf-8", len(payload))
            self.wfile.write(payload)
        elif self.path == "/":
            payload = DASHBOARD_HTML.encode("utf-8")
            self._headers(200, "text/html; charset=utf-8", len(payload))
            self.wfile.write(payload)
        elif self.path == "/favicon.ico":
            self._headers(204, "image/x-icon", 0)
        else:
            self._headers(404, "text/plain; charset=utf-8", 0)

    def _method_not_allowed(self):
        self.send_response(405)
        self.send_header("Allow", "GET")
        self.send_header("Content-Length", "0")
        self.end_headers()

    do_POST = _method_not_allowed
    do_PUT = _method_not_allowed
    do_PATCH = _method_not_allowed
    do_DELETE = _method_not_allowed

    def log_message(self, _format, *_args):
        return


class _MonitoringHTTPServer(ThreadingHTTPServer):
    def server_bind(self):
        # HTTPServer performs a reverse-DNS lookup here, which is unnecessary
        # for a local status endpoint and can block startup on isolated hosts.
        TCPServer.server_bind(self)
        self.server_name = self.server_address[0]
        self.server_port = self.server_address[1]


class MonitoringServer:
    def __init__(self, runtime_state, settings=WebSettings()):
        handler = type("RuntimeStatusHandler", (_Handler,), {"runtime_state": runtime_state})
        self._server = _MonitoringHTTPServer((settings.host, settings.port), handler)
        self._thread = threading.Thread(target=self._server.serve_forever, name="monitoring-web", daemon=True)

    @property
    def address(self):
        return self._server.server_address

    def start(self):
        self._thread.start()

    def stop(self):
        self._server.shutdown()
        self._server.server_close()
        if self._thread.is_alive():
            self._thread.join(timeout=2)
