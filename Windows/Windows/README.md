# Windows development

[Project overview](../../README.md) · [简体中文介绍](../../README.zh-CN.md)

The Windows receiver is a Tk desktop application, a local HTTP server, and a Windows `SendInput` adapter. Shared phone assets live in this directory and are also used by the Mac build.

## Run and build

Python 3.10 or later is required for development; published EXEs include their own runtime.

```powershell
py -3 -m pip install -r requirements-build.txt
py -3 app.py
powershell -NoProfile -ExecutionPolicy Bypass -File .\build.ps1
```

The build creates `.build-venv`, packages `dist\WatchMouse-2.8.exe`, verifies all four application modules (`app`, `receiver`, `input_control`, `pad_control`), assets and license notices against the checkout, and copies the result to `dist\WatchMouse.exe`. After dependencies are installed you may use `build.ps1 -SkipInstall`.

The native gamepad binding remains optional and external. This build does not install or bundle `vgamepad`, its client DLL, or the ViGEmBus driver. The frozen receiver can load an existing package from the current user's Python site-packages; its Python version and DLL architecture must match the EXE (Python 3.14, x64 in the current local build). Keep `vgamepad/win/vigem/client/x64/ViGEmClient.dll` beside the library's Python files in its original relative location. The upstream vgamepad 0.1.0 installer may launch a driver installer, so an already configured computer should reuse its existing files rather than reinstall them during a WatchMouse build.

`run.bat` opens the built app when present and otherwise falls back to the development Python. Windows PowerShell 5.1 scripts use UTF-8 with BOM and CRLF; subprocess output and Python use UTF-8 explicitly. Paths and usernames containing Chinese characters are supported.

## Connection and one-time pairing

Use the same trusted Wi-Fi on the phone and computer. Start the receiver and scan its QR code. On a trusted home network, select the Windows **Private** network profile and allow the app when prompted by Windows Firewall. The **Allow LAN connection** button asks for administrator approval to add only this executable/port's private-profile, local-subnet inbound rule. Everyday control does not require administrator privileges.

The pairing key is stored in `%LOCALAPPDATA%\WatchMouse\config.json`; updates preserve it. The same phone browser remembers it and reconnects automatically after receiver restart. Bookmark the paired URL. If the IP address changes, scan the new address; if browser storage or desktop config is reset, pair again. Logs are in the same directory as `desktop.log`.

The interface starts in English. Select **中文** in the desktop language selector or the phone's connection settings to save a Chinese preference. Desktop and phone preferences are independent. Closing the desktop window stops its receiver. Repeated launches bring the running window forward.

If only `127.0.0.1` appears, connect to the network and refresh addresses. If the port is occupied, close the previous receiver before retrying. The app does not stop unrelated software. Windows may reject input directed at an elevated target app; use a normal target window.

## Phone and watch

The phone UI provides trackpad, scrolling, drag, video-key controls, and a draft composer using the phone's own input method. Dictation uses the phone keyboard; LAN HTTP does not normally expose browser microphone APIs. No virtual microphone driver or audio streaming is installed.

The `/watch?token=...&lang=en` page uses ordinary links/forms without JavaScript. Each action link is single-use and expires after five minutes. Actual Apple Watch compatibility is unverified.

## Native multiplayer gamepads

On a computer with ViGEmBus and the matching vgamepad binding already configured, each phone browser in **Gamepad** mode receives its own native Xbox 360 controller and a WatchMouse P1–P4 seat. Put all phones and the computer on the same Wi-Fi, scan the QR code on each phone, and connect all players before starting a local multiplayer game. Press A on each phone to join when the game requests it; joining rules and supported player counts depend on the game.

WatchMouse seats do not guarantee the same player number inside a game. Physical Xbox controllers and virtual controllers from other apps share Windows' [four XInput slots](https://learn.microsoft.com/en-us/windows/win32/xinput/getting-started-with-xinput). Leaving the mode or hiding the page releases controls; a visible, active page sends a neutral heartbeat to retain its seat without holding buttons, and expired sessions release their seats. Keyboard fallback does not provide independent multiplayer controllers. macOS retains keyboard mapping, without native multiplayer controller support.

## Performance

See [performance checks](../../docs/performance.md) for the transport benchmark, queue regression checks, and desktop startup changes. Benchmarks use a mock input controller; they never move or type into the real desktop.

## Tests and safe screenshots

```powershell
py -3 -m unittest discover -s tests
node tests/frontend-smoke.cjs
py -3 app.py --demo --language en --screenshot demo.png
```

Demo mode displays documentation-only pairing data and does not read/write real configuration, start a receiver, inject desktop input, or change firewall settings. Screenshot mode is only available with demo mode.

Protocol/input tests mock final injection. The GitHub Windows workflow builds and checks the EXE and captures the real rendered demo window. Published binaries are not commercially signed.
