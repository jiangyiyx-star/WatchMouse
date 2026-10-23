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

# Real keyboards report scancodes; games that read DirectInput or Raw Input
# ignore synthetic events that only carry a virtual key. Send scancodes first
# and fall back to the virtual key when the layout has no mapping for it.
KEYEVENTF_EXTENDEDKEY, KEYEVENTF_KEYUP = 0x0001, 0x0002
KEYEVENTF_SCANCODE = 0x0008
SCAN = {
    "escape": 0x01, "esc": 0x01, "1": 0x02, "2": 0x03, "3": 0x04, "4": 0x05,
    "5": 0x06, "6": 0x07, "7": 0x08, "8": 0x09, "9": 0x0A, "0": 0x0B,
    "backspace": 0x0E, "tab": 0x0F, "q": 0x10, "w": 0x11, "e": 0x12, "r": 0x13,
    "t": 0x14, "y": 0x15, "u": 0x16, "i": 0x17, "o": 0x18, "p": 0x19,
    "enter": 0x1C, "ctrl": 0x1D, "a": 0x1E, "s": 0x1F, "d": 0x20, "f": 0x21,
    "g": 0x22, "h": 0x23, "j": 0x24, "k": 0x25, "l": 0x26, "shift": 0x2A,
    "z": 0x2C, "x": 0x2D, "c": 0x2E, "v": 0x2F, "b": 0x30, "n": 0x31,
    "m": 0x32, "alt": 0x38, "space": 0x39, "f1": 0x3B, "f2": 0x3C,
    "f3": 0x3D, "f4": 0x3E, "f5": 0x3F, "f6": 0x40, "f7": 0x41, "f8": 0x42,
    "f9": 0x43, "f10": 0x44, "home": 0x47, "up": 0x48, "pageup": 0x49,
    "left": 0x4B, "right": 0x4D, "end": 0x4F, "down": 0x50, "pagedown": 0x51,
    "insert": 0x52, "delete": 0x53, "f11": 0x57, "f12": 0x58, "win": 0x5B,
}


def elevated():
    """True when this process can drive elevated windows (games launched by Steam)."""
    if sys.platform != "win32":
        return False
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False

def mouse(dx=0, dy=0, data=0, flags=0):
    item = INPUT(type=0)
    item.mi = MOUSEINPUT(dx, dy, data & 0xFFFFFFFF, flags, 0, 0)
    return item

def key(vk=0, scan=0, flags=0):
    item = INPUT(type=1)
    item.ki = KEYBDINPUT(vk, scan, flags, 0, 0)
    return item

class InputController:
    # How this platform hands keys to the desktop; reported to the phone so the
    # settings panel can explain game compatibility.
    KEYBOARD_MODE = "scancode"

    def __init__(self, sender=None):
        self.user32 = None
        self._scans = {}
        if sender is None:
            if sys.platform != "win32":
                raise OSError("接收器只能在 Windows 运行")
            self.user32 = ctypes.WinDLL("user32", use_last_error=True)
            self.user32.SendInput.argtypes = (ctypes.c_uint, ctypes.POINTER(INPUT), ctypes.c_int)
            self.user32.SendInput.restype = ctypes.c_uint
            sender = self._native_send
        self.sender, self.lock = sender, threading.RLock()
        self.dragging, self.drag_timer = False, None
        self.held_keys = set()
        self.hold_timer = None
        self.last_activity = time.monotonic()

    def _native_send(self, items):
        array = (INPUT * len(items))(*items)
        sent = self.user32.SendInput(len(items), array, ctypes.sizeof(INPUT))
        if sent != len(items):
            raise OSError("Windows 未接受输入。请确认目标窗口没有以管理员身份运行。")

    def send(self, *items):
        if items:
            self.sender(list(items))

    def _cancel_hold_timer(self):
        if self.hold_timer:
            self.hold_timer.cancel()
            self.hold_timer = None

    def _schedule_hold_watchdog(self):
        self._cancel_hold_timer()
        if not self.held_keys and not self.dragging:
            return
        self.hold_timer = threading.Timer(5, self._hold_expired)
        self.hold_timer.daemon = True
        self.hold_timer.start()

    def release_all(self):
        with self.lock:
            if self.drag_timer:
                self.drag_timer.cancel()
                self.drag_timer = None
            self._cancel_hold_timer()
            if self.dragging:
                try:
                    self.send(mouse(flags=0x0004))
                finally:
                    self.dragging = False
            held = sorted(self.held_keys)
            self.held_keys.clear()
            for name in held:
                try:
                    self.send(self._key_event(name, up=True))
                except OSError:
                    pass

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

    def _hold_expired(self):
        with self.lock:
            if not self.held_keys:
                return
            remaining = 5 - (time.monotonic() - self.last_activity)
            if remaining <= 0:
                self.release_all()
            else:
                self.hold_timer = threading.Timer(remaining, self._hold_expired)
                self.hold_timer.daemon = True
                self.hold_timer.start()

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

    def _scan_code(self, name):
        """Hardware scancode for a key name, or 0 when the layout has none."""
        if name in self._scans:
            return self._scans[name]
        code = 0
        if self.user32 is not None:
            try:
                code = int(self.user32.MapVirtualKeyW(VK[name], 0))
            except Exception:
                code = 0
        if not code:
            code = SCAN.get(name, 0)
        self._scans[name] = code
        return code

    def _key_event(self, name, up=False):
        """Keyboard event that games accept: scancode first, virtual key as fallback."""
        flags = KEYEVENTF_EXTENDEDKEY if name in EXTENDED else 0
        scan = self._scan_code(name)
        if scan:
            flags |= KEYEVENTF_SCANCODE
            if up:
                flags |= KEYEVENTF_KEYUP
            return key(scan=scan, flags=flags)
        return key(VK[name], flags=flags | (KEYEVENTF_KEYUP if up else 0))

    def press_key(self, name, modifiers, state="tap"):
        if not isinstance(name, str) or name.lower() not in VK:
            raise ValueError("不支持的按键")
        if state not in ("tap", "down", "up"):
            raise ValueError("无效按键状态")
        if not isinstance(modifiers, list) or len(modifiers) > 4 or any(not isinstance(mod, str) or mod not in MODIFIERS for mod in modifiers):
            raise ValueError("无效组合键")
        if state != "tap" and modifiers:
            raise ValueError("按住/松开不支持组合键")
        name, held = name.lower(), list(dict.fromkeys(modifiers))
        if state == "down":
            if name in self.held_keys:
                return
            self.send(self._key_event(name))
            self.held_keys.add(name)
            self._schedule_hold_watchdog()
            return
        if state == "up":
            if name not in self.held_keys:
                return
            self.send(self._key_event(name, up=True))
            self.held_keys.discard(name)
            self._schedule_hold_watchdog()
            return
        items = [self._key_event(mod) for mod in held]
        items.extend([self._key_event(name), self._key_event(name, up=True)])
        items.extend(self._key_event(mod, up=True) for mod in reversed(held))
        try:
            self.send(*items)
        except OSError:
            self.send(self._key_event(name, up=True), *(self._key_event(mod, up=True) for mod in reversed(held)))
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
                name = "enter" if scan == 10 else "tab"
                items.extend([self._key_event(name), self._key_event(name, up=True)])
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
                self.press_key(payload["key"], payload.get("modifiers", []), payload.get("state", "tap"))
            if self.held_keys or self.dragging:
                self._schedule_hold_watchdog()
            return "OK"
