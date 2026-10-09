"""Temporarily size the isolated Windows GitHub runner display for native screenshots.

Uses the WinAPI's enumerated display modes, without writing the display registry.
This helper deliberately refuses to change a user's ordinary desktop.
"""
from __future__ import annotations

import argparse
import ctypes
import os
import sys
import time


class DevModeW(ctypes.Structure):
    # Fixed-width Win32 types also make the layout inspectable on other hosts.
    _fields_ = [
        ("dmDeviceName", ctypes.c_uint16 * 32),
        ("dmSpecVersion", ctypes.c_uint16), ("dmDriverVersion", ctypes.c_uint16),
        ("dmSize", ctypes.c_uint16), ("dmDriverExtra", ctypes.c_uint16),
        ("dmFields", ctypes.c_uint32), ("display_union", ctypes.c_ubyte * 16),
        ("dmColor", ctypes.c_int16), ("dmDuplex", ctypes.c_int16),
        ("dmYResolution", ctypes.c_int16), ("dmTTOption", ctypes.c_int16),
        ("dmCollate", ctypes.c_int16), ("dmFormName", ctypes.c_uint16 * 32),
        ("dmLogPixels", ctypes.c_uint16), ("dmBitsPerPel", ctypes.c_uint32),
        ("dmPelsWidth", ctypes.c_uint32), ("dmPelsHeight", ctypes.c_uint32),
        ("dmDisplayFlags", ctypes.c_uint32), ("dmDisplayFrequency", ctypes.c_uint32),
        ("dmICMMethod", ctypes.c_uint32), ("dmICMIntent", ctypes.c_uint32),
        ("dmMediaType", ctypes.c_uint32), ("dmDitherType", ctypes.c_uint32),
        ("dmReserved1", ctypes.c_uint32), ("dmReserved2", ctypes.c_uint32),
        ("dmPanningWidth", ctypes.c_uint32), ("dmPanningHeight", ctypes.c_uint32),
    ]


def get_api():
    if sys.platform != "win32" or os.environ.get("GITHUB_ACTIONS") != "true":
        raise RuntimeError("Display changes are allowed only on the isolated Windows GitHub Actions runner.")
    if ctypes.sizeof(DevModeW) != 220:
        raise RuntimeError("Incorrect Win32 DEVMODEW structure layout.")
    api = ctypes.WinDLL("user32", use_last_error=True)
    api.EnumDisplaySettingsW.argtypes = [ctypes.c_wchar_p, ctypes.c_uint32, ctypes.POINTER(DevModeW)]
    api.EnumDisplaySettingsW.restype = ctypes.c_int
    api.ChangeDisplaySettingsW.argtypes = [ctypes.POINTER(DevModeW), ctypes.c_uint32]
    api.ChangeDisplaySettingsW.restype = ctypes.c_int32
    api.GetSystemMetrics.argtypes, api.GetSystemMetrics.restype = [ctypes.c_int], ctypes.c_int
    api.SetProcessDPIAware.argtypes, api.SetProcessDPIAware.restype = [], ctypes.c_int
    api.SetProcessDPIAware()
    return api


def screen_size(api):
    return api.GetSystemMetrics(0), api.GetSystemMetrics(1)


def set_display(api, minimum=(1280, 1024)):
    width, height = screen_size(api)
    print(f"CI primary display before capture: {width}x{height}")
    if width >= minimum[0] and height >= minimum[1]:
        return
    candidates = []
    index = 0
    while True:
        mode = DevModeW()
        mode.dmSize = ctypes.sizeof(mode)
        if not api.EnumDisplaySettingsW(None, index, ctypes.byref(mode)):
            break
        index += 1
        if mode.dmPelsWidth >= minimum[0] and mode.dmPelsHeight >= minimum[1] and mode.dmBitsPerPel >= 32:
            candidates.append(mode)
    candidates.sort(key=lambda mode: (mode.dmPelsWidth * mode.dmPelsHeight, abs(mode.dmDisplayFrequency - 60)))
    for mode in candidates:
        # Use a driver-enumerated mode; CDS_TEST validates before the temporary
        # dynamic change. Neither call includes CDS_UPDATEREGISTRY.
        if api.ChangeDisplaySettingsW(ctypes.byref(mode), 2) != 0:
            continue
        if api.ChangeDisplaySettingsW(ctypes.byref(mode), 0) != 0:
            continue
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            width, height = screen_size(api)
            if width >= minimum[0] and height >= minimum[1]:
                print(f"CI primary display ready: {width}x{height}")
                return
            time.sleep(0.2)
    raise RuntimeError(f"No supported display mode reached {minimum[0]}x{minimum[1]}; native screenshots would be clipped.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--restore", action="store_true", help="Restore the registry's original display mode after the CI screenshot")
    args = parser.parse_args()
    api = get_api()
    if args.restore:
        code = api.ChangeDisplaySettingsW(None, 0)
        if code != 0:
            raise RuntimeError(f"Could not restore the CI display mode (WinAPI result {code}).")
        print("CI display restored to the original registry mode.")
    else:
        set_display(api)


if __name__ == "__main__":
    main()
