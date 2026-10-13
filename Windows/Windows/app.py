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
BG, CARD, TEXT, MUTED, ACCENT = "#0d0e12", "#191b22", "#eef0f5", "#9295a3", "#d92746"
BORDER, INSET = "#303441", "#111218"
ACCENT_TEXT, WHITE = "#ff657c", "#ffffff"
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
    '同一 Wi-Fi，扫码连接手机。': 'Same Wi-Fi. Scan to connect.',
    '用手机相机扫一扫': 'Scan with your phone camera',
    '连接电脑': 'Connect to your computer',
    '电脑地址': 'Computer address',
    '刷新': 'Refresh',
    '复制连接链接': 'Copy connection link',
    '在电脑打开': 'Open on computer',
    '接收器': 'Receiver',
    '端口 {port}': 'Port {port}',
    '打开应用后自动启动。': 'Starts automatically with this app.',
    '连接设置': 'Connection settings',
    '允许局域网': 'Allow LAN access',
    '网络设置': 'Network settings',
    '手机未连接时，检查同一 Wi-Fi 与专用网络设置。': 'Check the same Wi-Fi and private network settings if your phone cannot connect.',
    '请复制连接链接': 'Copy the connection link',
    '正在查找局域网地址…': 'Finding local network addresses…',
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


def shutdown_server(server):
    """Always release the listening socket, even when shutdown fails."""
    try:
        server.shutdown()
    finally:
        server.server_close()


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
        self.addresses_pending = False
        self.address_thread = None
        self.service_generation = 0
        self.qr_cache_key = None
        self.update_title()
        icon_path = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent)) / "app.ico"
        if icon_path.exists():
            try:
                self.root.iconbitmap(str(icon_path))
            except tk.TclError:
                logging.info("Window icon unavailable", exc_info=True)
        # Tk point fonts follow Windows DPI; scale pixel dimensions to match.
        self.ui_scale = max(1.0, float(self.root.tk.call("tk", "scaling")) / (96 / 72))
        self.qr_size = round(252 * self.ui_scale)
        screen_width = max(520, self.root.winfo_screenwidth() - 64)
        screen_height = max(440, self.root.winfo_screenheight() - 100)
        width, height = min(round(900 * self.ui_scale), screen_width), min(round(820 * self.ui_scale), screen_height)
        self.root.geometry(f"{width}x{height}" + ("+0+0" if demo else ""))
        self.root.minsize(min(round(780 * self.ui_scale), screen_width), min(round(600 * self.ui_scale), screen_height))
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
        px = lambda value: round(value * self.ui_scale)
        style.configure("TFrame", background=BG)
        style.configure("Card.TFrame", background=CARD)
        style.configure("TLabel", background=BG, foreground=TEXT, font=("Microsoft YaHei UI", 10))
        style.configure("Card.TLabel", background=CARD, foreground=TEXT)
        style.configure("Muted.TLabel", background=CARD, foreground=MUTED, font=("Microsoft YaHei UI", 9))
        style.configure("TButton", background="#2a2d38", foreground=TEXT, borderwidth=1,
                        bordercolor=BORDER, lightcolor=BORDER, darkcolor=BORDER,
                        padding=(px(14), px(10)), font=("Microsoft YaHei UI", 10))
        style.map("TButton", background=[("active", "#343846"), ("disabled", "#21242d")],
                  foreground=[("disabled", "#626676")], bordercolor=[("focus", ACCENT_TEXT)])
        style.configure("Accent.TButton", background=ACCENT, foreground=WHITE,
                        bordercolor=ACCENT, lightcolor=ACCENT, darkcolor=ACCENT,
                        font=("Microsoft YaHei UI", 10, "bold"))
        style.map("Accent.TButton", background=[("active", "#e12e4c"), ("disabled", "#2a2d38")],
                  foreground=[("disabled", "#626676")], bordercolor=[("active", "#e12e4c")])
        style.configure("Quiet.TButton", background=BG, foreground=MUTED, borderwidth=0,
                        padding=(px(10), px(8)), font=("Microsoft YaHei UI", 9))
        style.map("Quiet.TButton", background=[("active", CARD), ("disabled", BG)],
                  foreground=[("active", TEXT), ("disabled", "#626676")])
        style.configure("CardQuiet.TButton", background=CARD, foreground=MUTED, borderwidth=1,
                        bordercolor=BORDER, lightcolor=BORDER, darkcolor=BORDER,
                        padding=(px(12), px(8)), font=("Microsoft YaHei UI", 9))
        style.map("CardQuiet.TButton", background=[("active", "#2a2d38"), ("disabled", CARD)],
                  foreground=[("active", TEXT), ("disabled", "#626676")])
        style.configure("TCombobox", fieldbackground=INSET, background=INSET, foreground=TEXT,
                        arrowcolor=MUTED, bordercolor=BORDER, lightcolor=BORDER, darkcolor=BORDER,
                        padding=px(7), selectbackground=ACCENT, selectforeground=WHITE)
        style.map("TCombobox", fieldbackground=[("readonly", INSET)], foreground=[("readonly", TEXT)],
                  bordercolor=[("focus", ACCENT_TEXT)], arrowcolor=[("active", ACCENT_TEXT)])
        style.configure("Vertical.TScrollbar", background="#343846", troughcolor=BG,
                        bordercolor=BG, lightcolor=BG, darkcolor=BG, arrowcolor=MUTED,
                        gripcount=0, width=px(9))
        self.root.option_add("*TCombobox*Listbox.background", INSET)
        self.root.option_add("*TCombobox*Listbox.foreground", TEXT)
        self.root.option_add("*TCombobox*Listbox.selectBackground", ACCENT)
        self.root.option_add("*TCombobox*Listbox.selectForeground", WHITE)

    def build_ui(self):
        px = lambda value: round(value * self.ui_scale)
        viewport = ttk.Frame(self.root)
        viewport.pack(fill="both", expand=True)
        canvas = tk.Canvas(viewport, bg=BG, highlightthickness=0, bd=0, yscrollincrement=px(24))
        scrollbar = ttk.Scrollbar(viewport, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        outer = ttk.Frame(canvas, padding=px(28))
        content = canvas.create_window((0, 0), window=outer, anchor="nw")
        self._visual_scroll_needed = False
        self._visual_compact = None
        responsive_labels = []
        responsive_connection = []

        def update_scroll(_event=None):
            canvas.configure(scrollregion=canvas.bbox("all"))
            needed = outer.winfo_reqheight() > canvas.winfo_height() + 2
            if needed != self._visual_scroll_needed:
                self._visual_scroll_needed = needed
                if needed:
                    scrollbar.pack(side="right", fill="y")
                else:
                    scrollbar.pack_forget()
                    canvas.yview_moveto(0)

        def resize_content(event):
            canvas.itemconfigure(content, width=event.width)
            usable = max(px(300), event.width - px(104))
            for label in responsive_labels:
                label.configure(wraplength=usable)
            if responsive_connection:
                card, qr_area, address_area = responsive_connection
                compact = event.width < px(780)
                if compact != self._visual_compact:
                    self._visual_compact = compact
                    card.columnconfigure(0, weight=1 if compact else 0)
                    card.columnconfigure(1, weight=0 if compact else 1)
                    qr_area.grid_configure(row=0, column=0, columnspan=2 if compact else 1,
                                           padx=0 if compact else (0, px(28)))
                    address_area.grid_configure(row=1 if compact else 0, column=0 if compact else 1,
                                                columnspan=2 if compact else 1,
                                                pady=(px(20) if compact else px(4), 0))
            update_scroll()

        def scroll_content(event):
            if not self._visual_scroll_needed or not event.delta or event.widget.winfo_class() in ("TCombobox", "Listbox"):
                return None
            steps = max(1, round(abs(event.delta) / 120))
            canvas.yview_scroll(-steps if event.delta > 0 else steps, "units")
            return "break"

        outer.bind("<Configure>", update_scroll)
        canvas.bind("<Configure>", resize_content)
        self.root.bind("<MouseWheel>", scroll_content, add="+")
        header = ttk.Frame(outer)
        header.pack(fill="x")
        mark = tk.Canvas(header, width=px(31), height=px(34), bg=BG, highlightthickness=0, bd=0)
        mark.pack(side="left", padx=(0, px(11)))
        # A native line icon keeps the wordmark crisp at every Windows DPI.
        mark.create_line(*[px(n) for n in (15, 2, 5, 4, 4, 15, 5, 30, 15, 32, 25, 30, 26, 15, 25, 4, 15, 2)],
                         fill=ACCENT, width=1.8 * self.ui_scale, smooth=True)
        mark.create_line(px(15), px(3), px(15), px(13), fill=ACCENT, width=1.8 * self.ui_scale)
        mark.create_line(px(5), px(14), px(25), px(14), fill=ACCENT, width=1.8 * self.ui_scale)
        self.localized_widget(ttk.Label, header, text="WatchMouse", font=("Segoe UI", 23, "bold")).pack(side="left")
        self.status = LocalizedStringVar(self, value="正在启动…")
        self.status_label = tk.Label(header, textvariable=self.status, bg=BG, fg=ACCENT_TEXT,
                                     font=("Microsoft YaHei UI", 9), padx=px(10), pady=px(5))
        self.status_label.pack(side="right")
        self.language_var = tk.StringVar(value=next(label for label, code in LANGUAGES.items() if code == self.language))
        language_select = ttk.Combobox(header, textvariable=self.language_var, values=list(LANGUAGES), state="readonly", width=8)
        language_select.pack(side="right", padx=(px(10), 0))
        language_select.bind("<<ComboboxSelected>>", self.change_language)
        self.localized_widget(ttk.Label, outer, text="同一 Wi-Fi，扫码连接手机。", foreground=MUTED,
                  font=("Microsoft YaHei UI", 11)).pack(anchor="w", pady=(px(12), px(22)))

        connection_border = tk.Frame(outer, bg=BORDER, bd=0)
        connection_border.pack(fill="x")
        connection = ttk.Frame(connection_border, style="Card.TFrame", padding=px(22))
        connection.pack(fill="both", expand=True, padx=1, pady=1)
        connection.columnconfigure(1, weight=1)
        qr_column = ttk.Frame(connection, style="Card.TFrame")
        qr_column.grid(row=0, column=0, sticky="n", padx=(0, px(28)))
        qr_plate = tk.Frame(qr_column, bg="white", padx=px(8), pady=px(8))
        qr_plate.pack()
        self.qr_text = LocalizedStringVar(self, value="二维码加载中")
        self.qr_label = tk.Label(qr_plate, textvariable=self.qr_text, width=27, height=12, bg="white", fg=BG,
                                 font=("Microsoft YaHei UI", 10), bd=0)
        self.qr_label.pack()
        self.localized_widget(ttk.Label, qr_column, text="用手机相机扫一扫", style="Muted.TLabel").pack(pady=(px(12), 0))

        right = ttk.Frame(connection, style="Card.TFrame")
        right.grid(row=0, column=1, sticky="nsew", pady=(px(4), 0))
        responsive_connection.extend((connection, qr_column, right))
        self.localized_widget(ttk.Label, right, text="连接电脑", style="Card.TLabel", font=("Microsoft YaHei UI", 17, "bold")).pack(anchor="w")
        self.localized_widget(ttk.Label, right, text="电脑地址", style="Muted.TLabel").pack(anchor="w", pady=(px(20), px(8)))
        address_row = ttk.Frame(right, style="Card.TFrame")
        address_row.pack(fill="x")
        self.ip_var = tk.StringVar()
        self.ip_select = ttk.Combobox(address_row, textvariable=self.ip_var, state="readonly", width=17)
        self.ip_select.bind("<<ComboboxSelected>>", lambda _: self.update_link())
        self.refresh_button = self.localized_widget(ttk.Button, address_row, text="刷新", command=self.refresh_addresses, style="CardQuiet.TButton")
        self.refresh_button.pack(side="right", padx=(px(8), 0))
        self.ip_select.pack(side="left", fill="x", expand=True)
        self.link_var = tk.StringVar()
        self.link_entry = tk.Entry(right, textvariable=self.link_var, readonlybackground=INSET, fg=MUTED,
                                   relief="flat", font=("Segoe UI", 9), state="readonly", bd=0,
                                   highlightthickness=1, highlightbackground=BORDER,
                                   highlightcolor=ACCENT_TEXT, selectbackground=ACCENT, selectforeground=WHITE)
        self.link_entry.pack(fill="x", ipady=px(8), pady=(px(10), px(18)))
        self.copy_button = self.localized_widget(ttk.Button, right, text="复制连接链接", command=self.copy_link, style="Accent.TButton")
        self.copy_button.pack(fill="x")
        self.preview_button = self.localized_widget(ttk.Button, right, text="在电脑打开", command=self.open_browser, style="CardQuiet.TButton")
        self.preview_button.pack(fill="x", pady=(px(8), 0))

        service_border = tk.Frame(outer, bg=BORDER, bd=0)
        service_border.pack(fill="x", pady=(px(16), 0))
        details = ttk.Frame(service_border, style="Card.TFrame", padding=px(18))
        details.pack(fill="both", expand=True, padx=1, pady=1)
        service_heading = ttk.Frame(details, style="Card.TFrame")
        service_heading.pack(fill="x")
        self.localized_widget(ttk.Label, service_heading, text="接收器", style="Card.TLabel", font=("Microsoft YaHei UI", 10, "bold")).pack(side="left")
        self.localized_widget(ttk.Label, service_heading, text=LocalizedText("端口 {port}", {"port": self.port}), style="Muted.TLabel").pack(side="right")
        self.detail_var = LocalizedStringVar(self, value="打开应用后自动启动。")
        detail_label = ttk.Label(details, textvariable=self.detail_var, style="Muted.TLabel", wraplength=px(700))
        detail_label.pack(anchor="w", pady=(px(8), px(12)))
        responsive_labels.append(detail_label)
        service_actions = ttk.Frame(details, style="Card.TFrame")
        service_actions.pack(fill="x")
        self.start_button = self.localized_widget(ttk.Button, service_actions, text="启动服务", command=self.start, style="CardQuiet.TButton")
        self.start_button.pack(side="left")
        self.stop_button = self.localized_widget(ttk.Button, service_actions, text="停止服务", command=self.stop, style="CardQuiet.TButton")
        self.stop_button.pack(side="left", padx=px(8))
        self.restart_button = self.localized_widget(ttk.Button, service_actions, text="重新启动", command=self.restart, style="CardQuiet.TButton")
        self.restart_button.pack(side="left")

        network = ttk.Frame(outer)
        network.pack(fill="x", pady=(px(14), 0))
        network_actions = ttk.Frame(network)
        network_actions.pack(fill="x")
        self.localized_widget(ttk.Label, network_actions, text="连接设置", foreground=MUTED, font=("Microsoft YaHei UI", 9)).pack(side="left", padx=(0, px(14)))
        self.localized_widget(ttk.Button, network_actions, text="允许局域网", command=self.allow_firewall, style="Quiet.TButton").pack(side="left")
        self.localized_widget(ttk.Button, network_actions, text="网络设置", command=self.open_network_settings, style="Quiet.TButton").pack(side="left", padx=px(4))
        self.network_var = LocalizedStringVar(self, value="手机未连接时，检查同一 Wi-Fi 与专用网络设置。")
        network_label = ttk.Label(network, textvariable=self.network_var, foreground=MUTED,
                                  font=("Microsoft YaHei UI", 9), wraplength=px(730))
        network_label.pack(anchor="w", pady=(px(6), 0))
        responsive_labels.append(network_label)
        self.notice = LocalizedStringVar(self, value="")
        notice_label = ttk.Label(outer, textvariable=self.notice, foreground=ACCENT_TEXT,
                                 font=("Microsoft YaHei UI", 9), wraplength=px(730))
        notice_label.pack(anchor="w", pady=(px(10), 0))
        responsive_labels.append(notice_label)
        self.update_buttons()

    def refresh_addresses(self):
        if self.demo:
            self.apply_addresses(["192.0.2.10"])
            return
        if self.closing or self.addresses_pending:
            return
        self.addresses_pending = True
        if not self.addresses:
            self.network_var.set("正在查找局域网地址…")
        self.update_buttons()

        def worker():
            try:
                addresses = receiver.lan_addresses()
            except Exception:
                logging.exception("LAN address lookup failed")
                addresses = []
            self.events.put(("addresses", addresses))

        self.address_thread = threading.Thread(target=worker, daemon=True)
        self.address_thread.start()

    def apply_addresses(self, addresses):
        """Apply background discovery only from the Tk event loop."""
        self.addresses_pending = False
        self.addresses = addresses
        current = self.ip_var.get()
        values = self.addresses or ["127.0.0.1"]
        self.ip_select["values"] = values
        self.ip_var.set(current if current in values else values[0])
        self.update_link()
        if not self.addresses:
            self.network_var.set("未检测到局域网 IPv4 地址。连接 Wi-Fi 后点击“刷新网络地址”。")
        else:
            self.network_var.set(self.network_warning)
        self.update_buttons()

    def update_link(self):
        address = self.ip_var.get()
        if not address:
            return
        link = f"http://{address}:{self.port}/?token={urllib.parse.quote(self.token, safe='')}"
        if self.link_var.get() != link:
            self.link_var.set(link)
        cache_key = (link, self.qr_size)
        if cache_key == self.qr_cache_key:
            return
        try:
            import qrcode
            from PIL import ImageTk
            qr = qrcode.QRCode(border=3, box_size=6, error_correction=qrcode.constants.ERROR_CORRECT_M)
            qr.add_data(link)
            qr.make(fit=True)
            picture = qr.make_image(fill_color=BG, back_color="white").convert("RGB")
            # Integral module sizes keep the QR code crisp and easy to scan.
            size = len(qr.get_matrix())
            box = max(1, self.qr_size // size)
            picture = picture.resize((size * box, size * box), resample=0)
            self.qr_image = ImageTk.PhotoImage(picture)
            self.qr_text.set("")
            self.qr_label.configure(image=self.qr_image, width=self.qr_size, height=self.qr_size)
            self.qr_cache_key = cache_key
        except ImportError:
            self.qr_image = None
            self.qr_cache_key = None
            self.qr_text.set("二维码组件未安装\n\n请使用复制链接\n或安装 requirements-build.txt")
            self.qr_label.configure(image="", width=27, height=12)
        except Exception:
            logging.exception("QR generation failed")
            self.qr_image = None
            self.qr_cache_key = None
            self.qr_text.set("请复制连接链接")
            self.qr_label.configure(image="", width=27, height=12)

    def copy_link(self):
        if self.demo or not self.link_var.get():
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
            for button in (self.start_button, self.stop_button, self.restart_button,
                           self.refresh_button, self.copy_button, self.preview_button):
                button["state"] = "disabled"
            return
        self.refresh_button["state"] = "disabled" if self.addresses_pending else "normal"
        self.copy_button["state"] = "normal" if self.link_var.get() else "disabled"
        self.start_button["state"] = "disabled" if self.busy or running else "normal"
        self.stop_button["state"] = "normal" if running and not self.borrowed and not self.busy else "disabled"
        self.restart_button["state"] = "normal" if running and not self.borrowed and not self.busy else "disabled"

    def start(self):
        if self.closing or self.demo or self.busy or self.server or self.borrowed:
            return
        self.busy = True
        self.service_generation += 1
        self.status.set("正在启动…")
        self.update_buttons()
        self.operation_thread = threading.Thread(target=self.start_worker, daemon=True)
        self.operation_thread.start()

    def start_worker(self):
        server = None
        serving = False
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
                    server = None
                    return
                threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.2}, daemon=True).start()
                serving = True
                self.server = server
                self.port = int(server.server_address[1])
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
                failed_server = self.server if self.server is server else None
                if failed_server is not None:
                    self.server = None
            if failed_server:
                try:
                    shutdown_server(failed_server)
                except Exception:
                    logging.exception("Failed receiver cleanup")
            elif server is not None and not serving:
                try:
                    server.server_close()
                except Exception:
                    logging.exception("Unstarted receiver cleanup failed")
            if isinstance(exc, OSError) and getattr(exc, "winerror", None) == 10048:
                message = LocalizedText("端口 {port} 已被占用。请关闭原接收器或占用该端口的软件，再点“启动服务”。", {"port": self.port})
            else:
                message = getattr(exc, "localized_text", str(exc))
            self.events.put(("error", message))

    def stop(self, restart=False):
        if self.busy or not self.server:
            return
        self.busy = True
        self.service_generation += 1
        self.status.set("正在停止…")
        self.update_buttons()
        with self.server_lock:
            server = self.server
            self.server = None
        def worker():
            try:
                shutdown_server(server)
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
            generation, port, token = self.service_generation, self.port, self.token
            def worker():
                try:
                    data = request_json(port, token)
                    healthy = data.get("app") == "WatchMouse" and bool(data.get("paired"))
                except Exception:
                    healthy = False
                self.events.put(("health", (generation, healthy)))
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
                    self.status_label.configure(fg=ACCENT_TEXT)
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
                    generation, value = value
                    if generation != self.service_generation or self.busy or not (self.server or self.borrowed):
                        continue
                    if value:
                        self.status.set("服务运行中")
                        self.status_label.configure(fg=ACCENT_TEXT)
                    else:
                        self.status.set("服务无响应")
                        self.status_label.configure(fg="#ffac91")
                        if self.borrowed:
                            self.borrowed = False
                elif kind == "network":
                    self.network_warning = value
                    if value:
                        self.network_var.set(value)
                elif kind == "addresses":
                    self.apply_addresses(value)
                elif kind == "firewall":
                    self.firewall_pending = False
                    if value.get("ok"):
                        self.notice.set(value["message"])
                    else:
                        self.notice.set("防火墙设置未完成，服务仍在运行。")
                        self.network_var.set(value.get("message", "请检查 Windows 防火墙设置"))
        except queue.Empty:
            pass
        self.update_buttons()
        self.poll_firewall_result()
        active = self.busy or self.addresses_pending or self.firewall_pending
        self.root.after(100 if active else 250, self.poll_events)

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
            self.service_generation += 1
            server = self.server
            self.server = None
        self.status.set("正在关闭…")
        operation_thread = self.operation_thread
        def worker():
            if server:
                try:
                    shutdown_server(server)
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
