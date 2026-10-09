"""WatchMouse desktop launcher: start, pair and stop the local receiver."""
from __future__ import annotations

import argparse
import ctypes
from dataclasses import dataclass, field
import hashlib
import json
import logging
from logging.handlers import RotatingFileHandler
import os
from pathlib import Path
import queue
import subprocess
import sys
import threading
import tkinter as tk
from tkinter import messagebox, ttk
import urllib.error
import urllib.parse
import urllib.request

import receiver

APP_TITLE = "WatchMouse · Phone keyboard and mouse"
APP_DIR = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "WatchMouse"
BG, CARD, TEXT, MUTED, ACCENT = "#0b1120", "#152036", "#eef4ff", "#9babc5", "#58dfcd"
LANGUAGES = {"English": "en", "中文": "zh-CN"}
ENGLISH = {
    "WatchMouse · 手机键盘和鼠标": APP_TITLE,
    "界面语言": "Language",
    "语言已保存，下次启动会自动使用。": "Language saved for your next launch.",
    "无法保存语言设置：{error}": "Could not save the language setting: {error}",
    "端口必须在 1–65535 之间": "Port must be between 1 and 65535.",
    "Windows 防火墙设置需要管理员授权": "Administrator approval is required to configure Windows Firewall.",
    "Windows 未能添加防火墙规则": "Windows could not add the firewall rule.",
    "已允许此应用通过专用网络的局域网连接": "This app is now allowed on your private local network.",
    "正在启动…": "Starting…",
    "手机就是键盘和鼠标": "Your phone is your keyboard and mouse",
    "手机与电脑连接同一个 Wi-Fi，扫描二维码即可使用。": "Connect your phone and computer to the same Wi-Fi, then scan the QR code.",
    "二维码加载中": "Loading QR code",
    "手机扫码打开": "Scan with your phone",
    "链接包含配对密钥，只分享给自己的设备。": "The link includes your pairing key. Share it only with your own devices.",
    "复制手机链接": "Copy phone link",
    "电脑预览": "Preview",
    "刷新网络地址": "Refresh addresses",
    "服务会随应用自动启动，关闭此窗口会停止本应用的服务。": "The receiver starts automatically. Closing this window stops this app's receiver.",
    "启动服务": "Start",
    "停止服务": "Stop",
    "重新启动": "Restart",
    "无法连接时：检查同一 Wi-Fi、Windows 网络类型与防火墙。": "Can't connect? Check your Wi-Fi, Windows network profile and firewall.",
    "允许局域网连接": "Allow LAN access",
    "打开网络设置": "Network settings",
    "端口 {port} · 本机运行": "Port {port} · Runs locally",
    "未检测到局域网 IPv4 地址。连接 Wi-Fi 后点击“刷新网络地址”。": "No local IPv4 address found. Connect to Wi-Fi, then select Refresh addresses.",
    "二维码组件未安装\n\n请使用复制链接\n或安装 requirements-build.txt": "QR component unavailable\n\nUse Copy phone link\nor install requirements-build.txt",
    "请使用左侧链接连接": "Use the link on the left",
    "手机连接链接已复制。": "Phone connection link copied.",
    "发现正在运行的 WatchMouse {version}。当前应用为 {current}，请关闭旧接收器后点击“启动服务”。": "WatchMouse {version} is already running. This app is {current}. Close the old receiver, then select Start.",
    "旧版本": "an older version",
    "端口 {port} 已被其他服务使用。请关闭原接收器后重试。": "Port {port} is in use by another service. Close the previous receiver and retry.",
    "接收器健康检查失败": "Receiver health check failed.",
    "端口 {port} 已被占用。请关闭原接收器或占用该端口的软件，再点“启动服务”。": "Port {port} is in use. Close the previous receiver or the app using this port, then select Start.",
    "正在停止…": "Stopping…",
    "服务运行中": "Receiver running",
    "已连接另一进程中的 WatchMouse 接收器。关闭此窗口会保留该服务。": "Connected to a WatchMouse receiver in another process. Closing this window leaves that receiver running.",
    "服务已启动，端口 {port}。手机扫码后，在电脑上点选要操作的窗口。": "Receiver running on port {port}. Scan the code, then select the window you want to control on your computer.",
    "服务已停止": "Receiver stopped",
    "手机控制已停止。点击“启动服务”继续使用。": "Phone control stopped. Select Start to continue.",
    "启动失败": "Start failed",
    "服务无响应": "Receiver not responding",
    "防火墙设置未完成，服务仍在运行。": "Firewall setup did not finish. The receiver is still running.",
    "请检查 Windows 防火墙设置": "Check your Windows Firewall settings.",
    "当前网络是“公用网络”。在自己的家庭 Wi-Fi 中，请打开网络设置改为“专用网络”，再允许局域网连接。": "Your network is Public. On your own home Wi-Fi, open Network settings, select Private, then allow LAN access.",
    "等待 Windows 管理员授权或防火墙设置结果…": "Waiting for Windows administrator approval or the firewall result…",
    "Windows 将请求管理员授权，用于开放本应用在家庭局域网的端口。": "Windows will request administrator approval to allow this app's port on your home network.",
    "管理员授权未完成，可稍后再次允许局域网连接。": "Administrator approval did not finish. You can select Allow LAN access again later.",
    "防火墙设置尚未返回结果，请检查 Windows 授权窗口。": "Firewall setup has not returned a result. Check the Windows approval dialog.",
    "正在关闭…": "Closing…",
    "启动未完成：{error}\n\n日志：{log}": "Startup did not finish: {error}\n\nLog: {log}",
    "演示": "Demo",
    "演示模式：示例地址与二维码，不会连接或控制电脑。": "Demo: sample address and QR code. No connection or computer control.",
}


def normalize_language(value):
    return "zh-CN" if value == "zh-CN" else "en"


@dataclass(frozen=True)
class LocalizedText:
    source: str
    values: dict = field(default_factory=dict)


def translate(value, language="en"):
    message = value if isinstance(value, LocalizedText) else LocalizedText(str(value))
    text = message.source if normalize_language(language) == "zh-CN" else ENGLISH.get(message.source, message.source)
    values = {key: translate(item, language) if isinstance(item, LocalizedText) else item for key, item in message.values.items()}
    return text.format(**values) if values else text


class LocalizedError(RuntimeError):
    def __init__(self, source, **values):
        self.localized_text = LocalizedText(source, values)
        super().__init__(translate(self.localized_text))


class LocalizedStringVar(tk.StringVar):
    """Keep message templates so an active status also changes language."""
    def __init__(self, app, value=""):
        self.app = app
        self.source = value
        super().__init__(master=app.root, value=app.tr(value))
        app.localized_variables.append(self)

    def set(self, value):
        self.source = value
        super().set(self.app.tr(value))

    def refresh(self):
        super().set(self.app.tr(self.source))


POWERSHELL_UTF8 = "[Console]::OutputEncoding = New-Object System.Text.UTF8Encoding($false); $OutputEncoding = [Console]::OutputEncoding; "


def capture_windows_client(window_id, expected_size):
    """Ask the native window to paint its full client, including off-screen rows."""
    from ctypes import wintypes
    from PIL import Image

    class BitmapInfoHeader(ctypes.Structure):
        _fields_ = [
            ("size", wintypes.DWORD), ("width", wintypes.LONG),
            ("height", wintypes.LONG), ("planes", wintypes.WORD),
            ("bit_count", wintypes.WORD), ("compression", wintypes.DWORD),
            ("image_size", wintypes.DWORD), ("x_pels", wintypes.LONG),
            ("y_pels", wintypes.LONG), ("colors_used", wintypes.DWORD),
            ("colors_important", wintypes.DWORD),
        ]

    user32 = ctypes.WinDLL("user32", use_last_error=True)
    gdi32 = ctypes.WinDLL("gdi32", use_last_error=True)
    signatures = (
        (user32.GetAncestor, (wintypes.HWND, wintypes.UINT), wintypes.HWND),
        (user32.GetClientRect, (wintypes.HWND, ctypes.POINTER(wintypes.RECT)), wintypes.BOOL),
        (user32.GetDC, (wintypes.HWND,), wintypes.HDC),
        (user32.ReleaseDC, (wintypes.HWND, wintypes.HDC), ctypes.c_int),
        (user32.PrintWindow, (wintypes.HWND, wintypes.HDC, wintypes.UINT), wintypes.BOOL),
        (gdi32.CreateCompatibleDC, (wintypes.HDC,), wintypes.HDC),
        (gdi32.CreateDIBSection, (wintypes.HDC, ctypes.c_void_p, wintypes.UINT, ctypes.POINTER(ctypes.c_void_p), wintypes.HANDLE, wintypes.DWORD), wintypes.HBITMAP),
        (gdi32.SelectObject, (wintypes.HDC, wintypes.HGDIOBJ), wintypes.HGDIOBJ),
        (gdi32.DeleteObject, (wintypes.HGDIOBJ,), wintypes.BOOL),
        (gdi32.DeleteDC, (wintypes.HDC,), wintypes.BOOL),
        (gdi32.GdiFlush, (), wintypes.BOOL),
    )
    for function, arguments, result in signatures:
        function.argtypes, function.restype = arguments, result
    window = user32.GetAncestor(window_id, 2)  # GA_ROOT: the Tk wrapper window.
    rect = wintypes.RECT()
    if not window or not user32.GetClientRect(window, ctypes.byref(rect)):
        raise OSError("Cannot inspect the native demo window.")
    size = (rect.right - rect.left, rect.bottom - rect.top)
    if size != expected_size or min(size) <= 0:
        raise OSError(f"Native demo client is {size}; expected {expected_size}.")
    width, height = size
    header = BitmapInfoHeader()
    header.size, header.width, header.height = ctypes.sizeof(header), width, -height
    header.planes, header.bit_count = 1, 32
    bits = ctypes.c_void_p()
    source_dc = memory_dc = bitmap = original = None
    try:
        source_dc = user32.GetDC(window)
        memory_dc = gdi32.CreateCompatibleDC(source_dc) if source_dc else None
        if not memory_dc:
            raise OSError("Cannot allocate the native demo capture context.")
        bitmap = gdi32.CreateDIBSection(source_dc, ctypes.byref(header), 0, ctypes.byref(bits), None, 0)
        if not bitmap or not bits.value:
            raise OSError("Cannot allocate the native demo capture bitmap.")
        original = gdi32.SelectObject(memory_dc, bitmap)
        if not original or original == ctypes.c_void_p(-1).value:
            raise OSError("Cannot select the native demo capture bitmap.")
        # PW_CLIENTONLY | PW_RENDERFULLCONTENT captures only this native client.
        # Tk requires its children to be on-screen to paint; CI sets a large
        # display before launch so every control has been rendered normally.
        if not user32.PrintWindow(window, memory_dc, 1 | 2):
            raise OSError("PrintWindow did not render the native demo window.")
        gdi32.GdiFlush()
        image = Image.frombytes("RGB", size, ctypes.string_at(bits, width * height * 4), "raw", "BGRX", 0, 1)
        black_bottom_row = any(image.crop((0, row, width, row + 1)).getbbox() is None for row in range(max(0, height - 8), height))
        if all(low == high for low, high in image.getextrema()) or black_bottom_row:
            raise OSError("Native demo capture is blank or missing its lower section.")
        return image
    finally:
        if original and original != ctypes.c_void_p(-1).value:
            gdi32.SelectObject(memory_dc, original)
        if bitmap:
            gdi32.DeleteObject(bitmap)
        if memory_dc:
            gdi32.DeleteDC(memory_dc)
        if source_dc:
            user32.ReleaseDC(window, source_dc)


def setup_logging():
    APP_DIR.mkdir(parents=True, exist_ok=True)
    handler = RotatingFileHandler(APP_DIR / "desktop.log", maxBytes=500_000, backupCount=2, encoding="utf-8")
    logging.basicConfig(level=logging.INFO, handlers=[handler], format="%(asctime)s %(levelname)s %(message)s")


def is_admin():
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except (AttributeError, OSError):
        return False


def firewall_rule_name(port):
    suffix = hashlib.sha256(str(Path(sys.executable).resolve()).encode("utf-8")).hexdigest()[:10]
    return f"WatchMouse-LAN-{int(port)}-{suffix}"


def configure_firewall(port):
    """Install only this executable/port's private, local-subnet inbound rule."""
    port = int(port)
    if not 1 <= port <= 65535:
        raise ValueError("端口必须在 1–65535 之间")
    if not is_admin():
        raise PermissionError("Windows 防火墙设置需要管理员授权")
    executable = str(Path(sys.executable).resolve()).replace("'", "''")
    name = firewall_rule_name(port)
    script = (
        POWERSHELL_UTF8 + "$ErrorActionPreference='Stop'; "
        f"$rule = Get-NetFirewallRule -Name '{name}' -ErrorAction SilentlyContinue; "
        "if ($rule) { $rule | Remove-NetFirewallRule }; "
        f"New-NetFirewallRule -Name '{name}' -DisplayName 'WatchMouse LAN ({port})' "
        f"-Direction Inbound -Action Allow -Protocol TCP -LocalPort {port} "
        f"-Program '{executable}' -Profile Private -RemoteAddress LocalSubnet | Out-Null"
    )
    result = subprocess.run(
        ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", script],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0), timeout=30,
    )
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or "Windows 未能添加防火墙规则")
    return "已允许此应用通过专用网络的局域网连接"


def firewall_helper(port):
    try:
        result = {"ok": True, "message": configure_firewall(port)}
    except Exception as exc:
        logging.exception("Firewall setup failed")
        result = {"ok": False, "message": str(exc)}
    (APP_DIR / "firewall-result.json").write_text(json.dumps(result, ensure_ascii=False), encoding="utf-8")
    return 0 if result["ok"] else 1


def request_json(port, token, timeout=1.5):
    request = urllib.request.Request(
        f"http://127.0.0.1:{int(port)}/api/status",
        headers={"X-WatchMouse-Token": token},
    )
    # Ignore system HTTP proxies for the local receiver.
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with opener.open(request, timeout=timeout) as response:
        return json.load(response)


def single_instance():
    """Retain the mutex handle for the process lifetime."""
    if sys.platform != "win32":
        return None, False
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.CreateMutexW.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_wchar_p]
    kernel32.CreateMutexW.restype = ctypes.c_void_p
    ctypes.set_last_error(0)
    handle = kernel32.CreateMutexW(None, False, "Local\\WatchMouse-Desktop-v2")
    duplicate = ctypes.get_last_error() == 183
    if duplicate:
        user32 = ctypes.windll.user32
        user32.FindWindowW.argtypes = [ctypes.c_wchar_p, ctypes.c_wchar_p]
        user32.FindWindowW.restype = ctypes.c_void_p
        for title in (APP_TITLE, "WatchMouse · 手机键盘和鼠标"):
            window = user32.FindWindowW(None, title)
            if window:
                user32.ShowWindow(window, 9)
                user32.SetForegroundWindow(window)
                break
    return handle, duplicate


class WatchMouseApp:
    def __init__(self, root, *, demo=False, language=None, screenshot=None):
        self.root = root
        self.demo = demo
        self.settings = {"token": "PUBLIC-DEMO-NOT-A-PAIRING-KEY", "port": 53514} if demo else receiver.load_settings()
        self.language = normalize_language(language or self.settings.get("language"))
        self.localized_variables = []
        self.localized_widgets = []
        self.port = int(self.settings.get("port", 53514))
        self.token = str(self.settings["token"])
        self.server = None
        self.server_lock = threading.Lock()
        self.operation_thread = None
        self.borrowed = False
        self.busy = False
        self.closing = False
        self.events = queue.Queue()
        self.addresses = []
        self.health_pending = False
        self.network_warning = ""
        self.firewall_pending = False
        self.qr_image = None
        self.screenshot_error = None
        self.update_title()
        icon_path = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent)) / "app.ico"
        if icon_path.exists():
            try:
                self.root.iconbitmap(str(icon_path))
            except tk.TclError:
                logging.info("Window icon unavailable", exc_info=True)
        self.root.geometry("820x790+0+0" if demo else "820x790")
        self.root.minsize(760, 790)
        self.root.configure(bg=BG)
        self.root.protocol("WM_DELETE_WINDOW", self.close)
        self.root.option_add("*Font", ("Microsoft YaHei UI", 10))
        self.style()
        self.build_ui()
        self.refresh_addresses()
        if demo:
            self.status.set("演示")
            self.detail_var.set("演示模式：示例地址与二维码，不会连接或控制电脑。")
            self.network_var.set("")
            if screenshot:
                self.root.after(1500, lambda: self.capture_demo(screenshot))
        else:
            self.root.after(100, self.poll_events)
            self.root.after(150, self.start)
            self.root.after(3000, self.health_check)
            self.check_network_profile()

    def tr(self, value):
        return translate(value, self.language)

    def update_title(self):
        title = self.tr("WatchMouse · 手机键盘和鼠标")
        self.root.title(f"{title} · {self.tr('演示')}" if self.demo else title)

    def localized_widget(self, factory, parent, **options):
        source = options.pop("text")
        widget = factory(parent, text=self.tr(source), **options)
        self.localized_widgets.append((widget, source))
        if self.demo and factory is ttk.Button:
            widget.configure(state="disabled")
        return widget

    def change_language(self, _event=None):
        language = LANGUAGES.get(self.language_var.get(), "en")
        if language == self.language:
            return
        if not self.demo:
            try:
                # Reload to preserve receiver updates and the existing pairing key.
                settings = receiver.load_settings()
                settings["language"] = language
                receiver.save_settings(settings)
            except OSError as exc:
                self.notice.set(LocalizedText("无法保存语言设置：{error}", {"error": str(exc)}))
                self.language_var.set(next(label for label, code in LANGUAGES.items() if code == self.language))
                return
            self.settings = settings
        self.language = language
        self.update_title()
        for widget, source in self.localized_widgets:
            widget.configure(text=self.tr(source))
        for variable in self.localized_variables:
            variable.refresh()
        if not self.demo:
            self.notice.set("语言已保存，下次启动会自动使用。")

    def capture_demo(self, output):
        """Capture this real demo window; never include live pairing settings."""
        try:
            self.root.update_idletasks()
            image = capture_windows_client(self.root.winfo_id(), (self.root.winfo_width(), self.root.winfo_height()))
            path = Path(output)
            path.parent.mkdir(parents=True, exist_ok=True)
            image.save(path)
        except Exception as exc:
            self.screenshot_error = exc
            logging.exception("Demo screenshot failed")
        finally:
            self.root.destroy()

    def style(self):
        style = ttk.Style(self.root)
        style.theme_use("clam")
        style.configure("TFrame", background=BG)
        style.configure("Card.TFrame", background=CARD)
        style.configure("TLabel", background=BG, foreground=TEXT)
        style.configure("Card.TLabel", background=CARD, foreground=TEXT)
        style.configure("Muted.TLabel", background=CARD, foreground=MUTED)
        style.configure("TButton", background="#253651", foreground=TEXT, borderwidth=0, padding=(14, 10))
        style.map("TButton", background=[("active", "#354b6b"), ("disabled", "#1b2940")], foreground=[("disabled", "#62728c")])
        style.configure("Accent.TButton", background=ACCENT, foreground=BG)
        style.map("Accent.TButton", background=[("active", "#8eecdf")])
        style.configure("TCombobox", fieldbackground="#253651", background="#253651", foreground=TEXT, padding=6)
        style.map("TCombobox", fieldbackground=[("readonly", "#253651")], foreground=[("readonly", TEXT)])

    def build_ui(self):
        outer = ttk.Frame(self.root, padding=24)
        outer.pack(fill="both", expand=True)
        header = ttk.Frame(outer)
        header.pack(fill="x")
        ttk.Label(header, text="WatchMouse", font=("Segoe UI", 25, "bold")).pack(side="left")
        self.status = LocalizedStringVar(self, value="正在启动…")
        self.status_label = tk.Label(header, textvariable=self.status, bg="#253651", fg=ACCENT, padx=14, pady=8)
        self.status_label.pack(side="right")
        self.localized_widget(ttk.Label, outer, text="手机就是键盘和鼠标", font=("Microsoft YaHei UI", 16, "bold")).pack(anchor="w", pady=(12, 3))
        self.localized_widget(ttk.Label, outer, text="手机与电脑连接同一个 Wi-Fi，扫描二维码即可使用。", foreground=MUTED).pack(anchor="w", pady=(0, 18))
        language_row = ttk.Frame(outer)
        language_row.pack(fill="x", pady=(0, 12))
        self.localized_widget(ttk.Label, language_row, text="界面语言", foreground=MUTED).pack(side="left", padx=(0, 10))
        self.language_var = tk.StringVar(value=next(label for label, code in LANGUAGES.items() if code == self.language))
        self.language_select = ttk.Combobox(language_row, textvariable=self.language_var, values=list(LANGUAGES), state="readonly", width=12)
        self.language_select.pack(side="left")
        self.language_select.bind("<<ComboboxSelected>>", self.change_language)
        connection = ttk.Frame(outer, style="Card.TFrame", padding=18)
        connection.pack(fill="x")
        self.qr_text = LocalizedStringVar(self, value="二维码加载中")
        self.qr_label = tk.Label(connection, textvariable=self.qr_text, width=205, height=205, bg="white", fg=BG)
        self.qr_label.pack(side="right", padx=(18, 0))
        left = ttk.Frame(connection, style="Card.TFrame")
        left.pack(side="left", fill="both", expand=True)
        self.localized_widget(ttk.Label, left, text="手机扫码打开", style="Card.TLabel", font=("Microsoft YaHei UI", 15, "bold")).pack(anchor="w", pady=(0, 12))
        self.ip_var = tk.StringVar()
        self.ip_select = ttk.Combobox(left, textvariable=self.ip_var, state="readonly")
        self.ip_select.pack(fill="x")
        self.ip_select.bind("<<ComboboxSelected>>", lambda _: self.update_link())
        self.link_var = tk.StringVar()
        self.link_entry = tk.Entry(left, textvariable=self.link_var, readonlybackground="#253651", fg=TEXT, relief="flat", font=("Segoe UI", 10), state="readonly")
        self.link_entry.pack(fill="x", ipady=8, pady=(10, 5))
        self.localized_widget(ttk.Label, left, text="链接包含配对密钥，只分享给自己的设备。", style="Muted.TLabel", wraplength=410).pack(anchor="w", pady=(0, 12))
        actions = ttk.Frame(left, style="Card.TFrame")
        actions.pack(fill="x")
        self.localized_widget(ttk.Button, actions, text="复制手机链接", command=self.copy_link, style="Accent.TButton").pack(side="left")
        self.localized_widget(ttk.Button, actions, text="电脑预览", command=self.open_browser).pack(side="left", padx=(8, 0))
        self.localized_widget(ttk.Button, left, text="刷新网络地址", command=self.refresh_addresses).pack(anchor="w", pady=(10, 0))
        details = ttk.Frame(outer, style="Card.TFrame", padding=16)
        details.pack(fill="x", pady=(14, 0))
        self.detail_var = LocalizedStringVar(self, value="服务会随应用自动启动，关闭此窗口会停止本应用的服务。")
        ttk.Label(details, textvariable=self.detail_var, style="Card.TLabel", wraplength=720).pack(anchor="w")
        service_actions = ttk.Frame(details, style="Card.TFrame")
        service_actions.pack(fill="x", pady=(12, 0))
        self.start_button = self.localized_widget(ttk.Button, service_actions, text="启动服务", command=self.start)
        self.start_button.pack(side="left")
        self.stop_button = self.localized_widget(ttk.Button, service_actions, text="停止服务", command=self.stop)
        self.stop_button.pack(side="left", padx=8)
        self.restart_button = self.localized_widget(ttk.Button, service_actions, text="重新启动", command=self.restart)
        self.restart_button.pack(side="left")
        network = ttk.Frame(outer)
        network.pack(fill="x", pady=(16, 0))
        self.network_var = LocalizedStringVar(self, value="无法连接时：检查同一 Wi-Fi、Windows 网络类型与防火墙。")
        ttk.Label(network, textvariable=self.network_var, foreground=MUTED, wraplength=740).pack(anchor="w")
        network_actions = ttk.Frame(network)
        network_actions.pack(fill="x", pady=(10, 0))
        self.localized_widget(ttk.Button, network_actions, text="允许局域网连接", command=self.allow_firewall).pack(side="left")
        self.localized_widget(ttk.Button, network_actions, text="打开网络设置", command=self.open_network_settings).pack(side="left", padx=8)
        self.localized_widget(ttk.Label, network_actions, text=LocalizedText("端口 {port} · 本机运行", {"port": self.port}), foreground=MUTED).pack(side="right")
        self.notice = LocalizedStringVar(self, value="")
        ttk.Label(outer, textvariable=self.notice, foreground=ACCENT).pack(anchor="w", pady=(12, 0))
        self.update_buttons()

    def refresh_addresses(self):
        try:
            self.addresses = ["192.0.2.10"] if self.demo else receiver.lan_addresses()
        except Exception:
            logging.exception("LAN address lookup failed")
            self.addresses = []
        current = self.ip_var.get()
        values = self.addresses or ["127.0.0.1"]
        self.ip_select["values"] = values
        self.ip_var.set(current if current in values else values[0])
        self.update_link()
        if not self.addresses:
            self.network_var.set("未检测到局域网 IPv4 地址。连接 Wi-Fi 后点击“刷新网络地址”。")

    def update_link(self):
        address = self.ip_var.get()
        link = f"http://{address}:{self.port}/?token={urllib.parse.quote(self.token, safe='')}"
        self.link_var.set(link)
        try:
            import qrcode
            from PIL import ImageTk
            qr = qrcode.QRCode(border=3, box_size=6, error_correction=qrcode.constants.ERROR_CORRECT_M)
            qr.add_data(link)
            qr.make(fit=True)
            picture = qr.make_image(fill_color=BG, back_color="white").convert("RGB")
            # Integral module sizes keep the QR code crisp and easy to scan.
            size = len(qr.get_matrix())
            box = max(1, 210 // size)
            picture = picture.resize((size * box, size * box), resample=0)
            self.qr_image = ImageTk.PhotoImage(picture)
            self.qr_text.set("")
            self.qr_label.configure(image=self.qr_image, width=210, height=210)
        except ImportError:
            self.qr_text.set("二维码组件未安装\n\n请使用复制链接\n或安装 requirements-build.txt")
            self.qr_label.configure(width=27, height=12)
        except Exception:
            logging.exception("QR generation failed")
            self.qr_text.set("请使用左侧链接连接")
            self.qr_label.configure(width=27, height=12)

    def copy_link(self):
        if self.demo:
            return
        self.root.clipboard_clear()
        self.root.clipboard_append(self.link_var.get())
        self.notice.set("手机连接链接已复制。")

    def open_browser(self):
        if self.demo:
            return
        url = f"http://127.0.0.1:{self.port}/?token={urllib.parse.quote(self.token, safe='')}"
        os.startfile(url)

    def update_buttons(self):
        running = self.server is not None or self.borrowed
        if self.demo:
            for button in (self.start_button, self.stop_button, self.restart_button):
                button["state"] = "disabled"
            return
        self.start_button["state"] = "disabled" if self.busy or running else "normal"
        self.stop_button["state"] = "normal" if running and not self.borrowed and not self.busy else "disabled"
        self.restart_button["state"] = "normal" if running and not self.borrowed and not self.busy else "disabled"

    def start(self):
        if self.demo or self.busy or self.server or self.borrowed:
            return
        self.busy = True
        self.status.set("正在启动…")
        self.update_buttons()
        self.operation_thread = threading.Thread(target=self.start_worker, daemon=True)
        self.operation_thread.start()

    def start_worker(self):
        try:
            existing = None
            try:
                existing = request_json(self.port, self.token)
            except Exception:
                pass
            if existing:
                if existing.get("app") == "WatchMouse" and existing.get("paired"):
                    if existing.get("version") != receiver.VERSION:
                        raise LocalizedError(
                            "发现正在运行的 WatchMouse {version}。当前应用为 {current}，请关闭旧接收器后点击“启动服务”。",
                            version=existing.get("version") or LocalizedText("旧版本"), current=receiver.VERSION,
                        )
                    self.events.put(("borrowed", existing))
                    return
                raise LocalizedError("端口 {port} 已被其他服务使用。请关闭原接收器后重试。", port=self.port)
            if self.closing:
                return
            server = receiver.create_server(host="0.0.0.0", port=self.port, token=self.token)
            with self.server_lock:
                if self.closing:
                    server.server_close()
                    return
                self.server = server
                self.port = int(server.server_address[1])
                threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.2}, daemon=True).start()
            result = request_json(self.port, self.token)
            if result.get("app") != "WatchMouse" or not result.get("paired"):
                raise LocalizedError("接收器健康检查失败")
            self.events.put(("started", result))
            if is_admin():
                try:
                    self.events.put(("firewall", {"ok": True, "message": configure_firewall(self.port)}))
                except Exception as exc:
                    self.events.put(("firewall", {"ok": False, "message": str(exc)}))
        except Exception as exc:
            logging.exception("Receiver startup failed")
            with self.server_lock:
                failed_server = self.server
                self.server = None
            if failed_server:
                failed_server.shutdown()
                failed_server.server_close()
            if isinstance(exc, OSError) and getattr(exc, "winerror", None) == 10048:
                message = LocalizedText("端口 {port} 已被占用。请关闭原接收器或占用该端口的软件，再点“启动服务”。", {"port": self.port})
            else:
                message = getattr(exc, "localized_text", str(exc))
            self.events.put(("error", message))

    def stop(self, restart=False):
        if self.busy or not self.server:
            return
        self.busy = True
        self.status.set("正在停止…")
        self.update_buttons()
        with self.server_lock:
            server = self.server
            self.server = None
        def worker():
            try:
                server.shutdown()
                server.server_close()
                self.events.put(("stopped", restart))
            except Exception as exc:
                self.events.put(("error", str(exc)))
        self.operation_thread = threading.Thread(target=worker, daemon=True)
        self.operation_thread.start()

    def restart(self):
        self.stop(restart=True)

    def health_check(self):
        if self.closing:
            return
        if (self.server or self.borrowed) and not self.busy and not self.health_pending:
            self.health_pending = True
            def worker():
                try:
                    data = request_json(self.port, self.token)
                    healthy = data.get("app") == "WatchMouse" and bool(data.get("paired"))
                    self.events.put(("health", healthy))
                except Exception:
                    self.events.put(("health", False))
            threading.Thread(target=worker, daemon=True).start()
        self.root.after(3000, self.health_check)

    def poll_events(self):
        if self.closing:
            return
        try:
            while True:
                kind, value = self.events.get_nowait()
                if kind in ("started", "borrowed"):
                    self.busy = False
                    self.borrowed = kind == "borrowed"
                    self.status.set("服务运行中")
                    self.status_label.configure(fg=ACCENT)
                    self.detail_var.set(
                        "已连接另一进程中的 WatchMouse 接收器。关闭此窗口会保留该服务。" if self.borrowed else
                        LocalizedText("服务已启动，端口 {port}。手机扫码后，在电脑上点选要操作的窗口。", {"port": self.port})
                    )
                    self.update_link()
                elif kind == "stopped":
                    self.busy = False
                    self.status.set("服务已停止")
                    self.detail_var.set("手机控制已停止。点击“启动服务”继续使用。")
                    if value:
                        self.start()
                elif kind == "error":
                    self.busy = False
                    self.status.set("启动失败")
                    self.status_label.configure(fg="#ffac91")
                    self.detail_var.set(value)
                elif kind == "health":
                    self.health_pending = False
                    if value:
                        self.status.set("服务运行中")
                        self.status_label.configure(fg=ACCENT)
                    else:
                        self.status.set("服务无响应")
                        self.status_label.configure(fg="#ffac91")
                        if self.borrowed:
                            self.borrowed = False
                elif kind == "network":
                    self.network_warning = value
                    if value:
                        self.network_var.set(value)
                elif kind == "firewall":
                    self.firewall_pending = False
                    if value.get("ok"):
                        self.notice.set(value["message"])
                    else:
                        self.notice.set("防火墙设置未完成，服务仍在运行。")
                        self.network_var.set(value.get("message", "请检查 Windows 防火墙设置"))
                self.update_buttons()
        except queue.Empty:
            pass
        self.poll_firewall_result()
        self.root.after(100, self.poll_events)

    def check_network_profile(self):
        def worker():
            try:
                result = subprocess.run(
                    ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command",
                     POWERSHELL_UTF8 + "Get-NetConnectionProfile | Select-Object -ExpandProperty NetworkCategory"],
                    capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=15,
                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                )
                categories = result.stdout.splitlines()
                if "Private" not in categories and "Public" in categories:
                    self.events.put(("network", "当前网络是“公用网络”。在自己的家庭 Wi-Fi 中，请打开网络设置改为“专用网络”，再允许局域网连接。"))
            except Exception:
                logging.info("Network profile lookup unavailable", exc_info=True)
        threading.Thread(target=worker, daemon=True).start()

    def open_network_settings(self):
        if self.demo:
            return
        os.startfile("ms-settings:network-wifi")

    def allow_firewall(self):
        if self.demo:
            return
        if self.firewall_pending:
            self.notice.set("等待 Windows 管理员授权或防火墙设置结果…")
            return
        self.firewall_pending = True
        result_path = APP_DIR / "firewall-result.json"
        result_path.unlink(missing_ok=True)
        self.notice.set("Windows 将请求管理员授权，用于开放本应用在家庭局域网的端口。")
        if is_admin():
            def worker():
                try:
                    self.events.put(("firewall", {"ok": True, "message": configure_firewall(self.port)}))
                except Exception as exc:
                    self.events.put(("firewall", {"ok": False, "message": str(exc)}))
            threading.Thread(target=worker, daemon=True).start()
            return
        args = ["--configure-firewall", str(self.port)]
        if not getattr(sys, "frozen", False):
            args.insert(0, str(Path(__file__).resolve()))
        shell32 = ctypes.windll.shell32
        shell32.ShellExecuteW.argtypes = [ctypes.c_void_p, ctypes.c_wchar_p, ctypes.c_wchar_p, ctypes.c_wchar_p, ctypes.c_wchar_p, ctypes.c_int]
        shell32.ShellExecuteW.restype = ctypes.c_void_p
        result = shell32.ShellExecuteW(None, "runas", sys.executable, subprocess.list2cmdline(args), str(Path(__file__).resolve().parent), 0)
        if not result or int(result) <= 32:
            self.firewall_pending = False
            self.notice.set("管理员授权未完成，可稍后再次允许局域网连接。")
        else:
            self.root.after(45000, self.firewall_timeout)

    def firewall_timeout(self):
        if self.firewall_pending:
            self.firewall_pending = False
            self.notice.set("防火墙设置尚未返回结果，请检查 Windows 授权窗口。")

    def poll_firewall_result(self):
        result_path = APP_DIR / "firewall-result.json"
        if not self.firewall_pending or not result_path.exists():
            return
        try:
            value = json.loads(result_path.read_text(encoding="utf-8"))
            result_path.unlink(missing_ok=True)
            self.events.put(("firewall", value))
        except (OSError, ValueError):
            pass

    def close(self):
        if self.closing:
            return
        with self.server_lock:
            self.closing = True
            server = self.server
            self.server = None
        self.status.set("正在关闭…")
        operation_thread = self.operation_thread
        def worker():
            if server:
                try:
                    server.shutdown()
                    server.server_close()
                except Exception:
                    logging.exception("Receiver shutdown failed")
            if operation_thread and operation_thread.is_alive():
                operation_thread.join(timeout=5)
        closing_thread = threading.Thread(target=worker, daemon=True)
        closing_thread.start()
        def finish():
            if closing_thread.is_alive():
                self.root.after(50, finish)
            else:
                self.root.destroy()
        finish()


def main():
    parser = argparse.ArgumentParser(description="WatchMouse desktop application")
    parser.add_argument("--configure-firewall", type=int, metavar="PORT")
    parser.add_argument("--demo", action="store_true", help="Show a safe demo without settings, network or input control")
    parser.add_argument("--language", choices=("en", "zh-CN"), help="Override the display language for this launch")
    parser.add_argument("--screenshot", type=Path, help="Save the demo window as a PNG and exit (requires --demo)")
    args = parser.parse_args()
    if args.screenshot and not args.demo:
        parser.error("--screenshot requires --demo")
    if args.demo and args.configure_firewall is not None:
        parser.error("--demo cannot configure the firewall")
    if not args.demo:
        setup_logging()
    if args.configure_firewall is not None:
        return firewall_helper(args.configure_firewall)
    mutex, duplicate = (None, False) if args.demo else single_instance()
    if duplicate:
        return 0
    root = tk.Tk()
    try:
        app = WatchMouseApp(root, demo=args.demo, language=args.language, screenshot=args.screenshot)
        root.mainloop()
        if app.screenshot_error is not None:
            return 1
    except Exception as exc:
        logging.exception("Desktop app failed")
        language = args.language or ("en" if args.demo else receiver.load_settings().get("language", "en"))
        messagebox.showerror("WatchMouse", translate(LocalizedText("启动未完成：{error}\n\n日志：{log}", {"error": str(exc), "log": APP_DIR / "desktop.log"}), language))
        return 1
    finally:
        if mutex:
            ctypes.windll.kernel32.CloseHandle.argtypes = [ctypes.c_void_p]
            ctypes.windll.kernel32.CloseHandle(mutex)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
