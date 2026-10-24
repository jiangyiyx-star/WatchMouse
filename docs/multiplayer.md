# Multiplayer verification — 2.8

Verified on Windows on 2026-10-25. Each phone page owns an opaque lease and an independent native Xbox controller; P1–P4 are WatchMouse seats, not guaranteed game player numbers.

## Automated checks

- 146 Python tests passed, covering session isolation, ordered snapshots, idempotent joins, pending-join cancellation, expiry, capacity, native failures and existing receiver behavior. Unit tests mock native devices and desktop input.
- The Node frontend smoke suite passed, including four phone contexts, a fifth waiting page, lost/late replies, reconnects, backgrounding, rotation and keyboard fallback.
- Five browser tabs against the recording-only test server received four distinct seats; the fifth waited and acquired a released seat. Portrait and landscape viewports retained the seat without document overflow.
- The final Windows EXE was checked against all four application modules and eight bundled assets, including license notices.

## Native neutral check

The packaged 2.8 receiver on the ROG PC accepted four independent HTTP sessions. Windows `XInputGetState` reported four connected Xbox/XInput devices. A fifth join was rejected without disturbing them, and all test leases were released afterward. Only neutral snapshots were sent: buttons and triggers read zero; sticks were inside the standard XInput neutral deadzones.

This confirms four Windows devices and session allocation. It does not constitute a four-physical-phone match or a complete test of any particular game's local multiplayer. Physical and other virtual Xbox controllers share the four XInput slots.

ViGEm's `vigem_target_x360_get_user_index` can report zero for every distinct target ([upstream issue #31](https://github.com/nefarius/ViGEmClient/issues/31)). The receiver treats this value as a diagnostic only. A regression test covers four separate targets reporting the same hint; it must not reject them or invent game player indices.

## Reproduce

From `Windows/Windows`, use the project's Python environment:

```powershell
.\.build-venv\Scripts\python.exe -m unittest discover -s tests
node tests/frontend-smoke.cjs
.\.build-venv\Scripts\python.exe verify_build.py --exe ..\..\WatchMouse-2.8.exe
```

For recording-only HTTP verification, run `tests/ui_server.py` in one terminal, then `tests/check_multiplayer.py` in another. The server mocks all desktop input and listens on loopback port 53515.

For the optional native check, first stop other phone sessions and disconnect other controllers. Keep the configured Windows receiver running, then run:

```powershell
.\.build-venv\Scripts\python.exe tests/check_multiplayer.py --native-neutral --port 53514 --settings "$env:LOCALAPPDATA\WatchMouse\config.json"
```

The native check creates and releases only its own neutral sessions, does not print the pairing key, and refuses to proceed when phone sessions are already active. Native support requires an existing compatible ViGEmBus/vgamepad setup. The EXE and these checks do not install a driver.
