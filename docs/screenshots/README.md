# Screenshot provenance

These PNGs are captures of the real WatchMouse 2.4 interface. They use a recording-only test receiver or the desktop `--demo` mode, documentation-only IP addresses, and a demo key that cannot control a real computer.

- Phone screenshots: shared HTML/CSS/JS in a mobile-size browser viewport.
- Mac screenshot: native Cocoa window content rendered with `--demo --language en --screenshot`.
- Windows screenshot: native Tk window captured on the Windows CI runner with `--demo --language en --screenshot`.

Demo desktop modes do not load/write the user's settings, listen for phone connections, inject input, or change firewall/permission settings.

The `phone-*-v26.jpg` images show the red/black 2.6 UI served only on loopback by `tests/ui_server.py`; the controller mocks all desktop input. The visible test pairing data does not grant access to a real receiver.
