"""Check four authenticated controller sessions without pressing any buttons.

Default target is the recording-only browser test server. Real XInput checks
require --native-neutral and an explicit --settings file; they only create,
refresh, and release neutral gamepads belonging to this test.
"""
from __future__ import annotations

import argparse
import ctypes
import http.client
import json
from pathlib import Path
import sys
import time
import uuid


def xinput_states():
    class Gamepad(ctypes.Structure):
        _fields_ = [("buttons", ctypes.c_ushort), ("lt", ctypes.c_ubyte),
                    ("rt", ctypes.c_ubyte), ("lx", ctypes.c_short),
                    ("ly", ctypes.c_short), ("rx", ctypes.c_short),
                    ("ry", ctypes.c_short)]

    class State(ctypes.Structure):
        _fields_ = [("packet", ctypes.c_uint32), ("pad", Gamepad)]

    library = ctypes.WinDLL("XInput1_4.dll")
    get_state = library.XInputGetState
    get_state.argtypes = [ctypes.c_uint32, ctypes.POINTER(State)]
    get_state.restype = ctypes.c_uint32
    result = {}
    for index in range(4):
        state = State()
        error = get_state(index, ctypes.byref(state))
        if error == 1167:
            continue
        if error:
            raise RuntimeError(f"XInputGetState({index}) failed: {error}")
        result[index] = {name: getattr(state.pad, name) for name, _ in Gamepad._fields_}
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=53515)
    parser.add_argument("--settings", type=Path)
    parser.add_argument("--native-neutral", action="store_true")
    parser.add_argument("--hold-seconds", type=float, default=0)
    args = parser.parse_args()
    if args.native_neutral and (sys.platform != "win32" or args.settings is None):
        parser.error("Native neutral checks require Windows and --settings")
    if not 0 <= args.hold_seconds <= 60:
        parser.error("hold-seconds must be between 0 and 60")
    token = json.loads(args.settings.read_text(encoding="utf-8-sig"))["token"] if args.settings else "browser-test-token"
    connection = http.client.HTTPConnection("127.0.0.1", args.port, timeout=5)
    leases = []
    requests = []

    def request(path, payload=None, expected=200):
        headers = {"X-WatchMouse-Token": token}
        body = None
        if payload is not None:
            headers["Content-Type"] = "application/json"
            body = json.dumps(payload).encode("utf-8")
        connection.request("POST" if payload is not None else "GET", path, body, headers)
        response = connection.getresponse()
        data = json.loads(response.read())
        if response.status != expected:
            raise AssertionError(f"{path}: HTTP {response.status}, expected {expected}; {data.get('errorCode', '')}; {data.get('error', '')}")
        return data

    def join():
        request_id = "neutral-check-" + uuid.uuid4().hex
        requests.append(request_id)
        lease = request("/api/pad/join", {"requestId": request_id})
        assert isinstance(lease.get("session"), str) and 1 <= lease.get("player", 0) <= 4
        lease["seq"] = 0
        leases.append(lease)
        if args.native_neutral:
            print(f"Joined independent WatchMouse session P{lease['player']}", flush=True)
        return lease

    def neutral(lease):
        lease["seq"] += 1
        request("/api/pad", {"session": lease["session"], "seq": lease["seq"], "pad": {}})

    try:
        status = request("/api/status")
        assert status.get("paired") and status.get("nativeGamepad")
        assert status.get("maxGamepads") == 4 and status.get("activeGamepads") == 0, "Other phone sessions are active; do not disturb them"
        if args.native_neutral:
            before = xinput_states()
            assert len(before) <= 1, "Other XInput controllers are connected; leave them untouched"
        for _ in range(4):
            neutral(join())
        assert len({lease["session"] for lease in leases}) == 4
        assert {lease["player"] for lease in leases} == {1, 2, 3, 4}
        full_id = "neutral-check-" + uuid.uuid4().hex
        requests.append(full_id)
        assert request("/api/pad/join", {"requestId": full_id}, 409)["errorCode"] == "gamepad_full"
        assert request("/api/status")["activeGamepads"] == 4
        if args.native_neutral:
            # ViGEm's get_user_index API can report zero for every target
            # (upstream issue #31). Verify Windows' actual connected slots.
            deadline = time.monotonic() + 5
            while time.monotonic() < deadline:
                states = xinput_states()
                if len(states) == 4:
                    break
                for lease in leases:
                    neutral(lease)
                time.sleep(0.2)
            assert len(states) == 4, "Four independent XInput devices did not appear"
            for state in states.values():
                assert state["buttons"] == state["lt"] == state["rt"] == 0, "Unexpected pressed button or trigger"
                # Readback can include Windows/Steam calibration offsets even
                # when the report we sent is exactly zero. Use the standard
                # XInput circular deadzones; never send corrective movement.
                assert state["lx"] ** 2 + state["ly"] ** 2 <= 7849 ** 2, "Left stick outside its neutral deadzone"
                assert state["rx"] ** 2 + state["ry"] ** 2 <= 8689 ** 2, "Right stick outside its neutral deadzone"
            print("PASS: four Xbox/XInput controllers connected; no buttons/triggers pressed, sticks within standard neutral deadzones.", flush=True)
        print("PASS: four distinct session/player assignments; fifth join rejected without disturbing them.", flush=True)
        deadline = time.monotonic() + args.hold_seconds
        while time.monotonic() < deadline:
            for lease in leases:
                neutral(lease)
            time.sleep(min(1, max(0, deadline - time.monotonic())))
    finally:
        for lease in leases:
            try:
                request("/api/pad/leave", {"session": lease["session"]})
            except Exception:
                print("Cleanup warning: session will expire through the receiver lease timeout", file=sys.stderr)
        for request_id in requests:
            try:
                request("/api/pad/leave", {"requestId": request_id})
            except Exception:
                pass
        connection.close()
    print("PASS: verification sessions released.", flush=True)


if __name__ == "__main__":
    main()
