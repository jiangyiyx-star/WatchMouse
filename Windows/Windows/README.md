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

The build creates `.build-venv`, packages `dist\WatchMouse.exe`, verifies compiled modules/assets/license notices against the checkout, and creates the versioned `dist\WatchMouse-2.4.exe` release copy. After dependencies are installed you may use `build.ps1 -SkipInstall`.

`run.bat` opens the built app when present and otherwise falls back to the development Python. Windows PowerShell 5.1 scripts use UTF-8 with BOM and CRLF; subprocess output and Python use UTF-8 explicitly. Paths and usernames containing Chinese characters are supported.

## Connection and one-time pairing

Use the same trusted Wi-Fi on the phone and computer. Start the receiver and scan its QR code. On a trusted home network, select the Windows **Private** network profile and allow the app when prompted by Windows Firewall. The **Allow LAN connection** button asks for administrator approval to add only this executable/port's private-profile, local-subnet inbound rule. Everyday control does not require administrator privileges.

The pairing key is stored in `%LOCALAPPDATA%\WatchMouse\config.json`; updates preserve it. The same phone browser remembers it and reconnects automatically after receiver restart. Bookmark the paired URL. If the IP address changes, scan the new address; if browser storage or desktop config is reset, pair again. Logs are in the same directory as `desktop.log`.

The interface starts in English. Select **中文** in the desktop language selector or the phone's connection settings to save a Chinese preference. Desktop and phone preferences are independent. Closing the desktop window stops its receiver. Repeated launches bring the running window forward.

If only `127.0.0.1` appears, connect to the network and refresh addresses. If the port is occupied, close the previous receiver before retrying. The app does not stop unrelated software. Windows may reject input directed at an elevated target app; use a normal target window.

## Phone and watch

The phone UI provides trackpad, scrolling, drag, video-key controls, and a draft composer using the phone's own input method. Dictation uses the phone keyboard; LAN HTTP does not normally expose browser microphone APIs. No virtual microphone driver or audio streaming is installed.

The `/watch?token=...&lang=en` page uses ordinary links/forms without JavaScript. Each action link is single-use and expires after five minutes. Actual Apple Watch compatibility is unverified.

## Tests and safe screenshots

```powershell
py -3 -m unittest discover -s tests
node tests/frontend-smoke.cjs
py -3 app.py --demo --language en --screenshot demo.png
```

Demo mode displays documentation-only pairing data and does not read/write real configuration, start a receiver, inject desktop input, or change firewall settings. Screenshot mode is only available with demo mode.

Protocol/input tests mock final injection. The GitHub Windows workflow builds and checks the EXE and captures the real rendered demo window. Published binaries are not commercially signed.
