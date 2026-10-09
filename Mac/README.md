# macOS development

[Project overview](../README.md) · [简体中文介绍](../README.zh-CN.md)

The Mac receiver uses a native Cocoa window and Quartz input events. It shares the HTTP service and phone assets in `Windows/Windows`.

## Download and start

Download [WatchMouse-Mac-2.4-arm64.zip](https://github.com/jiangyiyx-star/WatchMouse/releases/download/v2.4/WatchMouse-Mac-2.4-arm64.zip), unzip, and move `WatchMouse.app` to Applications. The download targets Apple silicon and macOS 11 or later. Intel builds can be made on an Intel Mac but have not been validated.

The app is ad-hoc signed, not Apple-notarized. If first launch is blocked, confirm the download's source and use **Open Anyway** in System Settings → Privacy & Security. Enable WatchMouse in Accessibility (some newer systems show the permission under Device Control and Data Access). When updating an ad-hoc build, a stale enabled permission record may need to be removed and the current `/Applications/WatchMouse.app` added again.

Keep the receiver open; closing the window or Command+Q stops it. Select the target desktop window before using the phone.

## Language and pairing

English is the default. Choose **简体中文** in the top-right language selector to save Chinese and update labels/buttons/status/menu immediately. Phone language is chosen separately in its connection settings.

Configuration and the persistent pairing key are saved in `~/Library/Application Support/WatchMouse/config.json`; logs are in `desktop.log` alongside it. Updates and language changes preserve the key. The phone remembers it in the same browser and automatically reconnects after the receiver returns or Accessibility permission is granted. Bookmark the paired URL. An IP address change requires scanning the new URL; the key itself stays unchanged. Clearing browser storage or resetting desktop config requires pairing again.

## Input behavior

Mouse movement, clicks, drag, scroll, key controls, and Unicode text use Quartz. Phone Ctrl/Win shortcut modifiers map to Command; Alt maps to Option, Shift maps to Shift, and the protocol's `control` modifier sends literal Control.

Keycodes use ANSI positions; Unicode text avoids changing the clipboard. Some games/apps handle their own keycodes and may ignore Unicode or synthetic input. See [Apple's Unicode event documentation](https://developer.apple.com/documentation/coregraphics/cgevent/keyboardsetunicodestring%28stringlength%3Aunicodestring%3A%29?language=objc).

When connecting fails, check trusted same-Wi-Fi access, client isolation, selected address, and application firewall access to TCP 53514. Mac does not call Windows/PowerShell firewall setup.

## Source and build

Use Python 3.12 or later from the repository root:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r Mac/requirements.txt
.venv/bin/python Mac/app.py
bash Mac/build.sh
```

Build output: `Mac/dist/WatchMouse.app` and `Mac/dist/WatchMouse-Mac-2.4-<architecture>.zip`. Set `WATCHMOUSE_PYTHON=/path/to/python3` if needed. Paths containing spaces and Chinese characters are supported. The spec includes the shared web resources and license notices.

Source runs may require permission for Python or its launching terminal; release builds require permission for WatchMouse. Formal signing/notarization requires an Apple Developer identity and is not configured here.

## Tests and screenshots

```bash
.venv/bin/python -m unittest discover -s Windows/Windows/tests
.venv/bin/python -m unittest discover -s Mac/tests
node Windows/Windows/tests/frontend-smoke.cjs
.venv/bin/python Mac/app.py --demo --language en --screenshot demo.png
```

Demo mode is explicitly offline. It uses documentation-only IP/key values, never reads/writes real settings, starts no server, and creates no native input controller. Screenshot mode captures the actual rendered Cocoa content view and requires demo mode.

Tests create real Quartz event objects but intercept final event posting. Native app launch, QR rendering, service, permission refusal, and UI language were checked. A user confirmed real phone-to-Mac connection/control; complete target-app coverage and physical Apple Watch behavior remain unverified.
