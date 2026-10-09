"""WatchMouse 2: phone, watch and desktop share one local HTTP service."""
from __future__ import annotations
import argparse
import html
import ipaddress
import json
import os
from pathlib import Path
import secrets
import socket
import subprocess
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlencode, urlparse
from input_control import InputController

PORT, VERSION = 53514, "2.3"
ASSETS = {"/": ("remote.html", "text/html"), "/remote.html": ("remote.html", "text/html"),
          "/remote.js": ("remote.js", "text/javascript"), "/remote.css": ("remote.css", "text/css"),
          "/manifest.webmanifest": ("manifest.webmanifest", "application/manifest+json"),
          "/icon.svg": ("icon.svg", "image/svg+xml")}

def resource_path(name):
    return Path(getattr(sys, "_MEIPASS", Path(__file__).parent)) / name

def settings_path():
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "WatchMouse" / "config.json"
    return Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "WatchMouse" / "config.json"

def save_settings(settings):
    path = settings_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(settings, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)
    if sys.platform == "darwin":
        path.chmod(0o600)

def load_settings():
    try:
        settings = json.loads(settings_path().read_text(encoding="utf-8"))
        if not isinstance(settings, dict):
            settings = {}
    except (OSError, ValueError):
        settings = {}
    if not isinstance(settings.get("token"), str) or len(settings["token"]) < 16:
        settings["token"] = secrets.token_hex(16)
        save_settings(settings)
    return settings

def lan_addresses():
    """Prefer real private LAN adapters; ignore VPN and Hyper-V networks."""
    candidates = []
    if sys.platform == "win32":
        script = ("Get-NetIPAddress -AddressFamily IPv4 | Where-Object { $_.IPAddress -ne '127.0.0.1' "
                  "-and $_.IPAddress -notlike '169.254.*' } | Select-Object InterfaceAlias,IPAddress "
                  "| ConvertTo-Json -Compress")
        try:
            raw = subprocess.check_output(["powershell.exe", "-NoProfile", "-Command", script],
                                          timeout=8, creationflags=subprocess.CREATE_NO_WINDOW)
            entries = json.loads(raw.decode("utf-8", errors="replace"))
            if isinstance(entries, dict):
                entries = [entries]
            for entry in entries or []:
                address, alias = entry["IPAddress"], entry.get("InterfaceAlias", "").lower()
                if any(item in alias for item in ("vethernet", "wsl", "hyper-v", "vpn", "tun", "tailscale")):
                    continue
                ip = ipaddress.ip_address(address)
                if not any(ip in ipaddress.ip_network(net) for net in ("10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16")):
                    continue
                priority = 0 if any(item in alias for item in ("wlan", "wi-fi", "wifi", "无线")) else 1
                candidates.append((priority, address))
        except (OSError, ValueError, subprocess.SubprocessError):
            pass
    if sys.platform == "darwin":
        try:
            raw = subprocess.check_output(["/sbin/ifconfig"], timeout=5).decode("utf-8")
            interface = ""
            for line in raw.splitlines():
                if line and not line[0].isspace():
                    interface = line.split(":", 1)[0]
                parts = line.split()
                if interface.startswith("en") and len(parts) > 1 and parts[0] == "inet":
                    address = parts[1]
                    ip = ipaddress.ip_address(address)
                    if ip.is_private and not address.startswith(("127.", "169.254.")):
                        candidates.append((0, address))
        except (OSError, ValueError, subprocess.SubprocessError):
            pass
    if not candidates:
        try:
            for item in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
                address = item[4][0]
                if ipaddress.ip_address(address).is_private and not address.startswith(("127.", "169.254.")):
                    candidates.append((2, address))
        except OSError:
            pass
    return list(dict.fromkeys(address for _, address in sorted(candidates)))

def local_ip():
    return next(iter(lan_addresses()), "127.0.0.1")

class ReceiverServer(ThreadingHTTPServer):
    daemon_threads = True
    def __init__(self, address, token, controller):
        self.token, self.controller = token, controller
        self.started_at, self.last_command_at = time.time(), 0.0
        self.command_count, self.last_client = 0, ""
        self.command_lock = threading.Lock()
        self.watch_actions = {}
        self.watch_lock = threading.Lock()
        super().__init__(address, Handler)

    def register_watch_action(self, command):
        with self.watch_lock:
            now = time.monotonic()
            self.watch_actions = {nonce: item for nonce, item in self.watch_actions.items() if item[0] > now}
            while len(self.watch_actions) >= 2048:
                self.watch_actions.pop(next(iter(self.watch_actions)))
            nonce = secrets.token_urlsafe(12)
            self.watch_actions[nonce] = (now + 300, command)
            return nonce

    def consume_watch_action(self, nonce):
        with self.watch_lock:
            item = self.watch_actions.pop(nonce, None)
            return item[1] if item and item[0] > time.monotonic() else None

    def execute(self, payload, client):
        with self.command_lock:
            result = self.controller.execute(payload)
            self.last_command_at, self.last_client = time.time(), client
            self.command_count += 1
            return result

    def server_close(self):
        try:
            self.controller.release_all()
        finally:
            super().server_close()

class Handler(BaseHTTPRequestHandler):
    server_version = "WatchMouse/2.3"
    def log_message(self, *_):
        pass

    def reply(self, status, body, content_type="application/json", headers=None):
        if isinstance(body, dict):
            body = json.dumps(body, ensure_ascii=False)
        data = body.encode("utf-8") if isinstance(body, str) else body
        self.send_response(status)
        for key, value in {"Content-Type": content_type + "; charset=utf-8", "Content-Length": str(len(data)),
                           "Cache-Control": "no-store", "Referrer-Policy": "no-referrer", "X-Content-Type-Options": "nosniff",
                           "Content-Security-Policy": "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; form-action 'self'; frame-ancestors 'none'", **(headers or {})}.items():
            self.send_header(key, value)
        self.end_headers()
        try:
            self.wfile.write(data)
        except (ConnectionError, OSError):
            pass

    def authorized(self, token=""):
        token = self.headers.get("X-WatchMouse-Token", "") or token
        return isinstance(token, str) and secrets.compare_digest(token.encode("utf-8", errors="replace"), self.server.token.encode("utf-8"))

    def read_body(self):
        length = int(self.headers.get("Content-Length", "0"))
        if length <= 0 or length > 32768:
            raise ValueError("请求大小无效（上限 32 KB）")
        return self.rfile.read(length).decode("utf-8")

    def same_origin(self):
        origin = self.headers.get("Origin")
        return not origin or origin == "http://" + self.headers.get("Host", "")

    def do_GET(self):
        url = urlparse(self.path)
        query = parse_qs(url.query)
        token = query.get("token", [""])[0]
        if url.path == "/api/status":
            paired = self.authorized(token)
            self.reply(200, {"app": "WatchMouse", "version": VERSION, "paired": paired,
                             "port": self.server.server_port, "commandCount": self.server.command_count,
                             "lastClient": self.server.last_client if paired else "",
                             "lastCommandAt": self.server.last_command_at if paired else 0,
                             "features": ["mouse", "keyboard", "unicode", "watch"]})
        elif url.path == "/c":
            command = query.get("q", [""])[0]
            if command == "PING":
                self.reply(200, "PONG", "text/plain")
            elif not self.authorized(token):
                self.reply(401, "ERR: 请先配对", "text/plain")
            else:
                self.perform({"command": command}, plain=True)
        elif url.path in ("/watch", "/watch.html"):
            if "action" in query:
                if not self.authorized(token):
                    return self.reply(401, self.watch_page("", "配对码无效"), "text/html")
                command = self.server.consume_watch_action(query["action"][0])
                message = "操作已处理或链接已过期，请重新点击按钮"
                if command:
                    try:
                        result = self.server.execute({"command": command}, self.client_address[0])
                        message = "连接正常" if result == "PONG" else "已执行"
                    except (ValueError, OSError, TypeError, OverflowError) as error:
                        message = str(error)
                return self.reply(303, "", "text/plain", {"Location": "/watch?" + urlencode({"token": token, "message": message})})
            self.reply(200, self.watch_page(token, query.get("message", [""])[0][:200]), "text/html")
        elif url.path in ASSETS:
            filename, content_type = ASSETS[url.path]
            try:
                self.reply(200, resource_path(filename).read_bytes(), content_type)
            except OSError:
                self.reply(404, {"ok": False, "error": "页面文件缺失"})
        elif url.path == "/favicon.ico":
            self.reply(204, b"", "image/x-icon")
        else:
            self.reply(404, {"ok": False, "error": "页面不存在"})

    def perform(self, payload, plain=False):
        try:
            result = self.server.execute(payload, self.client_address[0])
            self.reply(200, result if plain else {"ok": True, "result": result}, "text/plain" if plain else "application/json")
        except (ValueError, TypeError, OverflowError) as error:
            self.reply(400, str(error) if plain else {"ok": False, "error": str(error)}, "text/plain" if plain else "application/json")
        except OSError as error:
            self.reply(409, str(error) if plain else {"ok": False, "error": str(error)}, "text/plain" if plain else "application/json")

    def do_POST(self):
        path = urlparse(self.path).path
        if path not in ("/api/command", "/watch"):
            return self.reply(404, {"ok": False, "error": "接口不存在"})
        if not self.same_origin():
            return self.reply(403, {"ok": False, "error": "请从电脑提供的遥控页面操作"})
        try:
            body = self.read_body()
            if path == "/watch":
                form = parse_qs(body, keep_blank_values=True)
                token = form.get("token", [""])[0]
                if not self.authorized(token):
                    return self.reply(401, self.watch_page("", "配对码无效，请重新打开电脑提供的链接"), "text/html")
                payload = {"command": form.get("command", ["PING"])[0]}
                if "text" in form:
                    payload = {"text": form["text"][0]}
                try:
                    result = self.server.execute(payload, self.client_address[0])
                    message = "连接正常" if result == "PONG" else "已执行"
                except (ValueError, OSError, TypeError, OverflowError) as error:
                    message = str(error)
                return self.reply(303, "", "text/plain", {"Location": "/watch?" + urlencode({"token": token, "message": message})})
            if not self.headers.get("Content-Type", "").startswith("application/json"):
                return self.reply(415, {"ok": False, "error": "请发送 JSON"})
            payload = json.loads(body)
            if not isinstance(payload, dict):
                raise ValueError("请求必须是 JSON 对象")
            if not self.authorized(payload.get("token", "")):
                return self.reply(401, {"ok": False, "error": "配对码无效，请扫描电脑上的二维码"})
            self.perform(payload)
        except (ValueError, UnicodeError) as error:
            self.reply(400, {"ok": False, "error": str(error)})

    def watch_page(self, token, message=""):
        escape = html.escape
        css = ("*{box-sizing:border-box}body{margin:0;padding:10px;background:#0b1220;color:#edf3ff;font:15px -apple-system,Arial,sans-serif}"
               "h1{font-size:19px;margin:4px 0 8px}p{font-size:12px;color:#9daec9;margin:8px 0}form{margin:0}"
               ".grid{display:grid;grid-template-columns:1fr 1fr;gap:7px}button,input,textarea{font:inherit;border-radius:10px;"
               "border:1px solid #33435d;padding:12px 5px;background:#17263e;color:white;min-width:0;width:100%}"
               "button{min-height:44px}.control{display:flex;align-items:center;justify-content:center;min-height:44px;text-align:center;text-decoration:none;color:white;background:#17263e;border:1px solid #33435d;border-radius:10px;padding:10px 5px}"
               "textarea{margin-top:8px}a{color:#8ec5ff}@media(max-width:160px){.grid{grid-template-columns:1fr}body{padding:5px}}")
        head = ("<!doctype html><html lang='zh-CN'><head><meta charset='utf-8'><meta name='disabled-adaptations' content='watch'>"
                "<meta name='viewport' content='width=device-width,initial-scale=1'><title>WatchMouse · 手表</title><style>" + css +
                "</style></head><body><h1>WatchMouse</h1><p>" + escape(message or "手表简洁遥控") + "</p>")
        if not self.authorized(token):
            return head + ("<form method='get' action='/watch'><label>电脑 App 配对码<input name='token' autocomplete='off' required>"
                           "</label><button>连接电脑</button></form><p>与电脑连接同一 Wi-Fi</p></body></html>")
        buttons = [("K up", "上一个 ↑"), ("K down", "下一个 ↓"), ("K space", "播放 / 暂停"), ("PING", "测试连接"),
                   ("C", "左键"), ("RC", "右键"), ("S 2", "滚轮 ↑"), ("S -2", "滚轮 ↓"),
                   ("M -40,0", "光标 ←"), ("M 40,0", "光标 →"), ("M 0,-40", "光标 ↑"), ("M 0,40", "光标 ↓"),
                   ("K enter", "回车"), ("K backspace", "退格")]
        hidden = "<input type='hidden' name='token' value='" + escape(token, quote=True) + "'>"
        controls = "<div class='grid'>"
        for command, label in buttons:
            action_url = "/watch?" + urlencode({"token": token, "action": self.server.register_watch_action(command)})
            controls += "<a class='control' href='" + escape(action_url, quote=True) + "'>" + escape(label) + "</a>"
        controls += "</div><form method='post' action='/watch'>" + hidden
        controls += "<textarea name='text' rows='2' maxlength='4000' placeholder='要输入到电脑的文字'></textarea><button>发送文字</button></form>"
        controls += "<p>每点一次执行一次。请先在电脑选中输入框。</p><p><a href='/?" + escape(urlencode({"token": token}), quote=True) + "'>手机触控板版</a></p></body></html>"
        return head + controls

def create_server(host="0.0.0.0", port=PORT, token=None, controller=None):
    return ReceiverServer((host, port), token or load_settings()["token"], controller or InputController())

def main():
    parser = argparse.ArgumentParser(description="WatchMouse 接收器（桌面 App 请运行 app.py）")
    parser.add_argument("--port", type=int, default=PORT)
    args = parser.parse_args()
    server = create_server(port=args.port)
    print("手机打开：http://" + local_ip() + ":" + str(server.server_port) + "/?token=" + server.token)
    print("手表使用上述地址的 /watch 页面。Ctrl+C 退出。")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()

if __name__ == "__main__":
    main()
