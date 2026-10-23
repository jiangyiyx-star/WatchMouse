"""Native gamepad output through ViGEmBus (optional, Windows only).

The receiver stays dependency-free: when the driver or the Python binding is
missing, ``VirtualPad.available`` is False and the phone keeps the keyboard
mapping that shipped with the gamepad panel.

Install once, on the Windows computer:
  1. ViGEmBus driver: https://github.com/nefarius/ViGEmBus/releases
  2. ``pip install vgamepad``
Then restart WatchMouse; the phone switches to native mode automatically.
"""
from __future__ import annotations

import sys
import threading
import time

AXES = ("lx", "ly", "rx", "ry")
TRIGGERS = ("lt", "rt")
BUTTONS = ("a", "b", "x", "y", "lb", "rb", "select", "start",
           "ls", "rs", "dup", "ddown", "dleft", "dright")
# Keys of the phone gamepad panel that are analog triggers instead of buttons.
TRIGGER_BUTTONS = {"lt": "lt", "rt": "rt"}

IDLE_RESET_SECONDS = 5.0
BUTTON_ATTRIBUTES = {
    "a": "XUSB_GAMEPAD_A", "b": "XUSB_GAMEPAD_B",
    "x": "XUSB_GAMEPAD_X", "y": "XUSB_GAMEPAD_Y",
    "lb": "XUSB_GAMEPAD_LEFT_SHOULDER", "rb": "XUSB_GAMEPAD_RIGHT_SHOULDER",
    "select": "XUSB_GAMEPAD_BACK", "start": "XUSB_GAMEPAD_START",
    "ls": "XUSB_GAMEPAD_LEFT_THUMB", "rs": "XUSB_GAMEPAD_RIGHT_THUMB",
    "dup": "XUSB_GAMEPAD_DPAD_UP", "ddown": "XUSB_GAMEPAD_DPAD_DOWN",
    "dleft": "XUSB_GAMEPAD_DPAD_LEFT", "dright": "XUSB_GAMEPAD_DPAD_RIGHT",
}


def neutral():
    state = {axis: 0.0 for axis in AXES}
    state.update({trigger: 0.0 for trigger in TRIGGERS})
    state["buttons"] = ()
    return state


def _number(value, name, low, high):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"手柄参数 {name} 必须是数字")
    return max(low, min(high, float(value)))


def normalize(state):
    """Validate one untrusted pad snapshot from the phone."""
    if not isinstance(state, dict):
        raise ValueError("手柄状态必须是 JSON 对象")
    result = neutral()
    for axis in AXES:
        result[axis] = _number(state.get(axis, 0.0), axis, -1.0, 1.0)
    for trigger in TRIGGERS:
        result[trigger] = _number(state.get(trigger, 0.0), trigger, 0.0, 1.0)
    buttons = state.get("buttons", [])
    if not isinstance(buttons, list) or len(buttons) > len(BUTTONS):
        raise ValueError("手柄按键列表无效")
    pressed = []
    allowed = BUTTONS + tuple(TRIGGER_BUTTONS)
    for name in buttons:
        if not isinstance(name, str) or name not in allowed:
            raise ValueError("不支持的手柄按键")
        if name not in pressed:
            pressed.append(name)
    # The panel sends triggers as buttons in keyboard mode; accept both forms.
    for name in pressed:
        trigger = TRIGGER_BUTTONS.get(name)
        if trigger:
            result[trigger] = 1.0
    result["buttons"] = tuple(name for name in pressed if name not in TRIGGER_BUTTONS)
    return result


def _external_site_packages():
    """Paths a frozen build must see so an extra pip package still imports."""
    try:
        import site
    except Exception:
        return []
    paths = []
    for getter in (getattr(site, "getsitepackages", None), getattr(site, "getusersitepackages", None)):
        if not getter:
            continue
        try:
            found = getter()
        except Exception:
            continue
        if isinstance(found, str):
            found = [found]
        paths.extend(path for path in found or [] if path not in paths)
    return paths


def connect():
    """Import vgamepad and create a virtual Xbox 360 pad, or explain why not."""
    if sys.platform != "win32":
        return None, "原生手柄仅在 Windows 上可用"
    # The packaged EXE ships its own interpreter, so a driver binding the user
    # installed afterwards lives outside the bundle and needs an explicit path.
    if getattr(sys, "frozen", False):
        for path in _external_site_packages():
            if path not in sys.path:
                sys.path.append(path)
    try:
        import vgamepad as vg
    except Exception:
        return None, "未安装 vgamepad（pip install vgamepad）"
    try:
        pad = vg.VX360Gamepad()
    except Exception:
        return None, "需要先安装 ViGEmBus 驱动"
    return (vg, pad), ""


class VirtualPad:
    """Best-effort native pad; every failure degrades to the keyboard mapping."""

    def __init__(self, opener=connect):
        self.lock = threading.Lock()
        self.engine = None
        self.pad = None
        self.error = ""
        self.last_update = 0.0
        self._state = neutral()
        self._stop = threading.Event()
        self._watchdog = None
        self._open(opener)

    def _open(self, opener):
        try:
            opened, error = opener()
        except Exception:
            opened, error = None, "原生手柄初始化失败"
        if not opened:
            self.error = error
            return
        self.engine, self.pad = opened
        try:
            self.pad.reset()
            self.pad.update()
        except Exception:
            self.engine = self.pad = None
            self.error = "原生手柄初始化失败"
            return
        self._watchdog = threading.Thread(target=self._watch, name="watchmouse-pad", daemon=True)
        self._watchdog.start()

    @property
    def available(self):
        return self.pad is not None

    def _watch(self):
        # Mirrors the keyboard hold watchdog: a dropped page must not leave a
        # button held on the computer.
        while not self._stop.wait(0.5):
            with self.lock:
                if not self.available or not self.last_update:
                    continue
                if time.monotonic() - self.last_update < IDLE_RESET_SECONDS:
                    continue
                if self._state == neutral():
                    self.last_update = 0.0
                    continue
                self._write(neutral())
                self._state = neutral()
                self.last_update = 0.0

    def _write(self, state):
        vg, pad = self.engine, self.pad
        pad.reset()
        for name in state["buttons"]:
            attribute = BUTTON_ATTRIBUTES.get(name)
            if attribute:
                pad.press_button(button=getattr(vg.XUSB_BUTTON, attribute))
        # Screen coordinates grow downwards; XUSB expects up to be positive.
        pad.left_joystick_float(x_value_float=state["lx"], y_value_float=-state["ly"])
        pad.right_joystick_float(x_value_float=state["rx"], y_value_float=-state["ry"])
        pad.left_trigger_float(value_float=state["lt"])
        pad.right_trigger_float(value_float=state["rt"])
        pad.update()

    def apply(self, state):
        with self.lock:
            if not self.available:
                raise OSError("原生手柄不可用：" + (self.error or "未安装驱动"))
            if state != self._state:
                self._write(state)
                self._state = state
            self.last_update = time.monotonic()
            return "OK"

    def reset(self):
        with self.lock:
            if not self.available:
                return
            try:
                self._write(neutral())
            except Exception:
                pass
            self._state = neutral()
            self.last_update = 0.0

    def close(self):
        self._stop.set()
        self.reset()
        with self.lock:
            self.pad = self.engine = None