"""Windows SendInput: mouse, shortcuts and Unicode text."""
from __future__ import annotations
import ctypes
import sys
import threading
import time

ULONG_PTR = ctypes.c_size_t
class MOUSEINPUT(ctypes.Structure):
    _fields_ = [("dx", ctypes.c_long), ("dy", ctypes.c_long), ("mouseData", ctypes.c_ulong),
                ("dwFlags", ctypes.c_ulong), ("time", ctypes.c_ulong), ("dwExtraInfo", ULONG_PTR)]
class KEYBDINPUT(ctypes.Structure):
    _fields_ = [("wVk", ctypes.c_ushort), ("wScan", ctypes.c_ushort), ("dwFlags", ctypes.c_ulong),
                ("time", ctypes.c_ulong), ("dwExtraInfo", ULONG_PTR)]
class HARDWAREINPUT(ctypes.Structure):
    _fields_ = [("uMsg", ctypes.c_ulong), ("wParamL", ctypes.c_ushort), ("wParamH", ctypes.c_ushort)]
class _U(ctypes.Union):
    _fields_ = [("mi", MOUSEINPUT), ("ki", KEYBDINPUT), ("hi", HARDWAREINPUT)]
class INPUT(ctypes.Structure):
    _anonymous_ = ("u",)
    _fields_ = [("type", ctypes.c_ulong), ("u", _U)]

VK = {"backspace": 0x08, "tab": 0x09, "enter": 0x0D, "escape": 0x1B, "esc": 0x1B,
      "space": 0x20, "pageup": 0x21, "pagedown": 0x22, "end": 0x23, "home": 0x24,
      "left": 0x25, "up": 0x26, "right": 0x27, "down": 0x28, "insert": 0x2D, "delete": 0x2E}
VK.update({chr(code).lower(): code for code in range(65, 91)})
VK.update({str(num): 0x30 + num for num in range(10)})
VK.update({"f" + str(num): 0x6F + num for num in range(1, 13)})
MODIFIERS = {"ctrl": 0x11, "shift": 0x10, "alt": 0x12, "win": 0x5B}
EXTENDED = {"pageup", "pagedown", "end", "home", "left", "up", "right", "down", "insert", "delete", "win"}

def mouse(dx=0, dy=0, data=0, flags=0):
    item = INPUT(type=0)
    item.mi = MOUSEINPUT(dx, dy, data & 0xFFFFFFFF, flags, 0, 0)
    return item

def key(vk=0, scan=0, flags=0):
    item = INPUT(type=1)
    item.ki = KEYBDINPUT(vk, scan, flags, 0, 0)
    return item

class InputController:
    def __init__(self, sender=None):
        if sender is None:
            if sys.platform != "win32":
                raise OSError("接收器只能在 Windows 运行")
            self.user32 = ctypes.WinDLL("user32", use_last_error=True)
            self.user32.SendInput.argtypes = (ctypes.c_uint, ctypes.POINTER(INPUT), ctypes.c_int)
            self.user32.SendInput.restype = ctypes.c_uint
            sender = self._native_send
        self.sender, self.lock = sender, threading.RLock()
        self.dragging, self.drag_timer = False, None
        self.last_activity = time.monotonic()

    def _native_send(self, items):
        array = (INPUT * len(items))(*items)
        sent = self.user32.SendInput(len(items), array, ctypes.sizeof(INPUT))
        if sent != len(items):
            raise OSError("Windows 未接受输入。请确认目标窗口没有以管理员身份运行。")

    def send(self, *items):
        if items:
            self.sender(list(items))

    def release_all(self):
        with self.lock:
            if self.drag_timer:
                self.drag_timer.cancel()
                self.drag_timer = None
            if self.dragging:
                try:
                    self.send(mouse(flags=0x0004))
                finally:
                    self.dragging = False

    def _drag_expired(self):
        with self.lock:
            if not self.dragging:
                return
            remaining = 5 - (time.monotonic() - self.last_activity)
            if remaining <= 0:
                self.release_all()
            else:
                self.drag_timer = threading.Timer(remaining, self._drag_expired)
                self.drag_timer.daemon = True
                self.drag_timer.start()

    def command(self, command):
        if not isinstance(command, str):
            raise ValueError("鼠标指令必须是文本")
        if command == "PING":
            return "PONG"
        if command.startswith("M "):
            parts = command[2:].split(",")
            if len(parts) != 2:
                raise ValueError("移动需要 dx,dy")
            dx, dy = map(int, parts)
            if max(abs(dx), abs(dy)) > 4096:
                raise ValueError("单次移动过大")
            self.send(mouse(dx, dy, flags=0x0001))
        elif command.startswith("S "):
            amount = int(command[2:])
            if abs(amount) > 100:
                raise ValueError("单次滚动过大")
            self.send(mouse(data=amount * 120, flags=0x0800))
        elif command in ("C", "RC"):
            if self.dragging:
                self.release_all()
            down, up = (0x0002, 0x0004) if command == "C" else (0x0008, 0x0010)
            self.send(mouse(flags=down), mouse(flags=up))
        elif command == "MD":
            if not self.dragging:
                self.send(mouse(flags=0x0002))
                self.dragging = True
                self.drag_timer = threading.Timer(5, self._drag_expired)
                self.drag_timer.daemon = True
                self.drag_timer.start()
        elif command == "MU":
            self.release_all()
        elif command.startswith("K "):
            self.press_key(command[2:].strip(), [])
        else:
            raise ValueError("未知指令")
        return "OK"

    def press_key(self, name, modifiers):
        if not isinstance(name, str) or name.lower() not in VK:
            raise ValueError("不支持的按键")
        if not isinstance(modifiers, list) or len(modifiers) > 4 or any(not isinstance(mod, str) or mod not in MODIFIERS for mod in modifiers):
            raise ValueError("无效组合键")
        name, held = name.lower(), list(dict.fromkeys(modifiers))
        items = [key(MODIFIERS[mod], flags=1 if mod == "win" else 0) for mod in held]
        extended = 1 if name in EXTENDED else 0
        items.extend([key(VK[name], flags=extended), key(VK[name], flags=extended | 2)])
        items.extend(key(MODIFIERS[mod], flags=2 | (1 if mod == "win" else 0)) for mod in reversed(held))
        try:
            self.send(*items)
        except OSError:
            self.send(key(VK[name], flags=extended | 2), *(key(MODIFIERS[mod], flags=2 | (1 if mod == "win" else 0)) for mod in reversed(held)))
            raise

    def type_text(self, text):
        if not isinstance(text, str) or not text or len(text) > 4000:
            raise ValueError("请输入 1–4000 字的文字")
        text = text.replace("\r\n", "\n").replace("\r", "\n")
        if "\x00" in text:
            raise ValueError("文字包含无效字符")
        units = text.encode("utf-16-le", errors="strict")
        items = []
        for offset in range(0, len(units), 2):
            scan = int.from_bytes(units[offset:offset + 2], "little")
            if scan in (10, 9):
                code = VK["enter" if scan == 10 else "tab"]
                items.extend([key(code), key(code, flags=2)])
            else:
                items.extend([key(scan=scan, flags=4), key(scan=scan, flags=6)])
        for start in range(0, len(items), 128):
            self.send(*items[start:start + 128])

    def execute(self, payload):
        with self.lock:
            self.last_activity = time.monotonic()
            actions = [name for name in ("command", "text", "key") if name in payload]
            if len(actions) != 1:
                raise ValueError("一次请求只能有一个操作")
            if "command" in payload:
                return self.command(payload["command"])
            if "text" in payload:
                self.type_text(payload["text"])
            else:
                self.press_key(payload["key"], payload.get("modifiers", []))
            return "OK"
