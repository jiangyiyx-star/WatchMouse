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
import ctypes
import math
import secrets
import threading
import time
import traceback

AXES = ("lx", "ly", "rx", "ry")
TRIGGERS = ("lt", "rt")
BUTTONS = ("a", "b", "x", "y", "lb", "rb", "select", "start",
           "ls", "rs", "dup", "ddown", "dleft", "dright")
# Keys of the phone gamepad panel that are analog triggers instead of buttons.
TRIGGER_BUTTONS = {"lt": "lt", "rt": "rt"}

IDLE_RESET_SECONDS = 5.0
MAX_PLAYERS = 4
LEASE_SECONDS = 15
MAX_SEQUENCE = 9007199254740991
TOMBSTONE_SECONDS = 60
MAX_TOMBSTONES = 256
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
    try:
        number = float(value)
    except OverflowError:
        raise ValueError(f"手柄参数 {name} 必须是有限数字") from None
    if not math.isfinite(number):
        raise ValueError(f"手柄参数 {name} 必须是有限数字")
    return max(low, min(high, number))


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


def _xinput_user_index(pad):
    """Read ViGEm's reported slot as an unverified diagnostic hint.

    Test/factory pads without native handles do not use this Windows-only API.
    Older vgamepad bindings can use the same export directly from their DLL.
    Upstream issue #31 reports every target returning zero, even after long
    waits. This result must never decide capacity or identify a phone's pad.
    https://github.com/nefarius/ViGEmClient/issues/31
    """
    if not hasattr(pad, "_busp") or not hasattr(pad, "_devicep"):
        return None
    try:
        from vgamepad.win import vigem_client
        query = getattr(vigem_client, "vigem_target_x360_get_user_index", None)
        if query is None:
            query = vigem_client.vigemClient.vigem_target_x360_get_user_index
            query.argtypes = (ctypes.c_void_p, ctypes.c_void_p, ctypes.POINTER(ctypes.c_ulong))
            query.restype = ctypes.c_uint
    except (ImportError, AttributeError):
        raise OSError("无法确认 XInput 手柄席位，请更新 vgamepad") from None
    for attempt in range(4):
        index = ctypes.c_ulong(0xFFFFFFFF)
        result = query(pad._busp, pad._devicep, ctypes.byref(index))
        if result == 0x20000000:  # VIGEM_ERROR_NONE
            if index.value < MAX_PLAYERS:
                return int(index.value)
            break
        if result == 0xE0000014:  # VIGEM_ERROR_XUSB_USERINDEX_OUT_OF_RANGE
            break
        if attempt < 3:
            time.sleep(0.05)
    raise OSError("无法确认 XInput 手柄索引")


class VirtualPad:
    """One native pad, with a deadman that releases abandoned input."""

    def __init__(self, opener=connect):
        self.lock = threading.Lock()
        self.engine = None
        self.pad = None
        # No confirmed target-to-XInput mapping is currently available. The
        # unreliable getter below is retained only for local diagnostics.
        self.xinput_index = None
        self.reported_xinput_index = None
        self.index_error = ""
        self.native_capable = False
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
            self.native_capable = True
        except Exception as error:
            message = str(error) if isinstance(error, OSError) else "原生手柄初始化失败"
            traceback.clear_frames(error.__traceback__)
            self.engine = self.pad = None
            self.xinput_index = None
            self.error = message
            return
        try:
            self.reported_xinput_index = _xinput_user_index(self.pad)
        except Exception as error:
            self.index_error = str(error)
            traceback.clear_frames(error.__traceback__)
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
                try:
                    self._write(neutral())
                except Exception:
                    self._disable_locked("原生手柄重置失败")
                else:
                    self._state = neutral()
                    self.last_update = 0.0

    def _disable_locked(self, message):
        """Retire a broken target; a failed watchdog must not silently die."""
        pad = self.pad
        self.error = message
        self.pad = self.engine = None
        self.xinput_index = None
        self.reported_xinput_index = None
        self._state = neutral()
        self.last_update = 0.0
        self._stop.set()
        if pad is not None:
            try:
                pad.reset()
                pad.update()
            except Exception:
                pass

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
                failed = False
                try:
                    self._write(state)
                except Exception as error:
                    self._disable_locked("原生手柄写入失败")
                    # Driver tracebacks can retain the removed native target
                    # through _write() locals. Do not keep it in a protocol error.
                    traceback.clear_frames(error.__traceback__)
                    failed = True
                if failed:
                    raise OSError(self.error)
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
                self._disable_locked("原生手柄重置失败")
            self._state = neutral()
            self.last_update = 0.0

    def close(self):
        self._stop.set()
        try:
            self.reset()
        finally:
            with self.lock:
                self._state = neutral()
                self.last_update = 0.0
                self.pad = self.engine = None
                self.xinput_index = None
                self.reported_xinput_index = None


class PadRequestError(ValueError):
    def __init__(self, message, code="invalid_request"):
        super().__init__(message)
        self.code = code


class PadSessionError(OSError):
    def __init__(self, message, code):
        super().__init__(message)
        self.code = code


class PadPool:
    """Four independent native pads, owned by expiring opaque page leases.

    The lock also covers native writes and target removal: a delayed request
    cannot write to, or release, a seat that has been given to another phone.
    The seat limit belongs to this app. Other physical/virtual controllers can
    also consume Windows' four XInput slots; this pool does not assign them.
    """

    def __init__(self, seed=None, factory=None, lock=None, clock=None):
        self.lock = lock if lock is not None else threading.RLock()
        self._factory = factory if factory is not None else VirtualPad
        self._clock = clock if clock is not None else time.monotonic
        self._sessions = {}
        self._requests = {}
        self._tombstones = {}
        self._closed = False
        self._stop = threading.Event()
        self._watchdog = None
        try:
            self._seed = seed if seed is not None else self._new_pad()
        except PadSessionError:
            self._seed = None
        self.available = bool(getattr(self._seed, "available", False)) or getattr(self._seed, "native_capable", False) is True
        self.error = str(getattr(self._seed, "error", "")) or ("" if self.available else "原生手柄创建失败")
        if self.available:
            self._watchdog = threading.Thread(target=self._watch, name="watchmouse-pad-sessions", daemon=True)
            self._watchdog.start()

    def _new_pad(self):
        try:
            return self._factory()
        except Exception as error:
            raise PadSessionError("原生手柄创建失败", "gamepad_unavailable") from error

    @staticmethod
    def _request_id(value):
        if not isinstance(value, str) or not 1 <= len(value) <= 128:
            raise PadRequestError("requestId 必须是 1–128 字符的字符串")
        return value

    def _prune_tombstones_locked(self, now):
        for request_id, expiry in tuple(self._tombstones.items()):
            if expiry <= now:
                self._tombstones.pop(request_id, None)

    def _cancel_request_locked(self, request_id, now):
        self._prune_tombstones_locked(now)
        self._tombstones.pop(request_id, None)
        while len(self._tombstones) >= MAX_TOMBSTONES:
            self._tombstones.pop(next(iter(self._tombstones)))
        self._tombstones[request_id] = now + TOMBSTONE_SECONDS

    def _close_pad_locked(self, pad):
        if pad is None:
            return
        try:
            pad.close()
        except Exception:
            # Still close every other target, even if a driver call fails.
            self.error = "原生手柄关闭失败"

    def _retire_locked(self, session, now):
        entry = self._sessions.pop(session, None)
        if entry is None:
            return
        self._requests.pop(entry["request_id"], None)
        self._cancel_request_locked(entry["request_id"], now)
        # The lease is invalidated before the first native reset/remove call.
        self._close_pad_locked(entry["pad"])

    def _expire_locked(self, now):
        self._prune_tombstones_locked(now)
        expired = []
        for session, entry in self._sessions.items():
            if now - entry["last_seen"] >= LEASE_SECONDS or not entry["pad"].available:
                expired.append(session)
        for session in expired:
            self._retire_locked(session, now)
        return len(expired)

    def expire(self):
        with self.lock:
            return self._expire_locked(self._clock())

    def _watch(self):
        while not self._stop.wait(0.5):
            self.expire()

    def info(self):
        with self.lock:
            self._expire_locked(self._clock())
            return {"nativeGamepad": self.available and not self._closed,
                    "padBackend": "vigem" if self.available and not self._closed else "keyboard",
                    "padError": self.error,
                    "maxGamepads": MAX_PLAYERS,
                    "activeGamepads": len(self._sessions)}

    def join(self, request_id):
        with self.lock:
            request_id = self._request_id(request_id)
            now = self._clock()
            self._expire_locked(now)
            if self._closed or request_id in self._tombstones:
                raise PadSessionError("手柄连接已结束，请重新连接", "gamepad_session_expired")
            if not self.available:
                raise PadSessionError("原生手柄不可用：" + (self.error or "未安装驱动"), "gamepad_unavailable")
            session = self._requests.get(request_id)
            if session is not None:
                return self._joined(session)
            if len(self._sessions) >= MAX_PLAYERS:
                raise PadSessionError("手柄席位已满（最多 4 个），请等待其他手机退出", "gamepad_full")
            pad = self._seed
            self._seed = None
            if pad is None:
                pad = self._new_pad()
            if not getattr(pad, "available", False):
                self.error = str(getattr(pad, "error", "")) or "原生手柄创建失败"
                self._close_pad_locked(pad)
                raise PadSessionError("原生手柄不可用：" + self.error, "gamepad_unavailable")
            if any(entry["pad"] is pad for entry in self._sessions.values()):
                raise PadSessionError("原生手柄未能创建独立设备", "gamepad_unavailable")
            occupied = {entry["player"] for entry in self._sessions.values()}
            player = next(number for number in range(1, MAX_PLAYERS + 1) if number not in occupied)
            session = secrets.token_urlsafe(24)
            self._sessions[session] = {"request_id": request_id, "player": player, "pad": pad,
                                       "last_seq": 0, "last_seen": now}
            self._requests[request_id] = session
            return self._joined(session)

    def _joined(self, session):
        entry = self._sessions[session]
        # player is our lease seat, not the Windows XInput user index. ViGEm's
        # getter can return zero for all four real devices; never expose it as
        # a confirmed mapping or synthesize indices from player/target serials.
        return {"session": session, "player": entry["player"],
                "maxPlayers": MAX_PLAYERS, "leaseSeconds": LEASE_SECONDS}

    def apply(self, session, seq, state):
        with self.lock:
            if not isinstance(session, str) or not session:
                raise PadRequestError("手柄连接信息缺失，请刷新网页", "gamepad_session_required")
            if isinstance(seq, bool) or not isinstance(seq, int) or not 1 <= seq <= MAX_SEQUENCE:
                raise PadRequestError("手柄序号必须是有效的正整数")
            now = self._clock()
            self._expire_locked(now)
            entry = self._sessions.get(session)
            if self._closed or entry is None:
                raise PadSessionError("手柄连接已过期，请重新连接", "gamepad_session_expired")
            if seq <= entry["last_seq"]:
                return {"result": "OK", "ignored": True, "stale": True}
            snapshot = normalize(state)
            failed = False
            try:
                result = entry["pad"].apply(snapshot)
            except Exception as error:
                self._retire_locked(session, now)
                traceback.clear_frames(error.__traceback__)
                failed = True
            if failed:
                raise PadSessionError("原生手柄写入失败，请重新连接", "gamepad_unavailable")
            entry["last_seq"] = seq
            entry["last_seen"] = now
            return {"result": result}

    def leave(self, session=None, request_id=None):
        with self.lock:
            if request_id is not None:
                request_id = self._request_id(request_id)
            if session is not None and (not isinstance(session, str) or not session):
                raise PadRequestError("手柄连接信息无效")
            now = self._clock()
            self._expire_locked(now)
            if session is not None:
                entry = self._sessions.get(session)
                if entry is not None:
                    if request_id is not None and request_id != entry["request_id"]:
                        raise PadRequestError("手柄连接信息不匹配")
                    self._retire_locked(session, now)
                # An old lease cannot cancel an active request with a new lease.
                if request_id is not None and request_id not in self._requests:
                    self._cancel_request_locked(request_id, now)
            elif request_id is not None:
                existing = self._requests.get(request_id)
                if existing is not None:
                    self._retire_locked(existing, now)
                else:
                    self._cancel_request_locked(request_id, now)
            return {"result": "OK"}

    def close(self):
        self._stop.set()
        with self.lock:
            if self._closed:
                return
            self._closed = True
            now = self._clock()
            for session in tuple(self._sessions):
                self._retire_locked(session, now)
            if self._seed is not None:
                self._close_pad_locked(self._seed)
                self._seed = None
