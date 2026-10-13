# Performance checks — WatchMouse 2.6

Measured on the local Windows machine on 2026-10-13, using Python 3.14.3. All input was intercepted by a mock controller. These are transport and regression checks, not phone-to-screen Wi-Fi latency measurements.

## HTTP transport

```powershell
cd Windows\Windows
.\.build-venv\Scripts\python.exe tests\benchmark_receiver.py --requests 1000 --rounds 3
```

The same current handler is run with two configurations: HTTP/1.0, unbuffered responses and Nagle enabled (the previous transport behavior), versus HTTP/1.1, buffered responses and TCP_NODELAY. Each run warms up with 20 requests, then measures 1,000 authenticated, sequential mouse commands over loopback. It counts accepted connections, each of which starts one handler thread.

| Round | Transport | Connections / handler threads | Total time | p50 response | p95 response |
| --- | --- | ---: | ---: | ---: | ---: |
| 1 | Previous transport | 1,000 | 3.858 s | 0.731 ms | 15.941 ms |
| 1 | Current transport | 1 | 0.331 s | 0.320 ms | 0.528 ms |
| 2 | Previous transport | 1,000 | 3.194 s | 0.761 ms | 16.251 ms |
| 2 | Current transport | 1 | 0.285 s | 0.271 ms | 0.417 ms |
| 3 | Previous transport | 1,000 | 3.864 s | 0.874 ms | 16.400 ms |
| 3 | Current transport | 1 | 0.327 s | 0.313 ms | 0.490 ms |

Median run duration: **3.858 → 0.327 seconds**. Connections/handler threads: **1,000 → 1** per measured run. This isolates transport settings, rather than comparing complete application versions. Browser scheduling, Wi-Fi, Windows pointer acceleration, target application processing, and physical display latency are outside this measurement.

## Changes and limits

- Persistent HTTP reuses an active connection for continuous input. Headers and small responses are written together. No new runtime dependency or protocol migration is required.
- Receiver connections are capped at 64 and idle/body reads time out after 5 seconds. Ambiguous/truncated requests cannot become a second command. Shutdown stops new input, interrupts sockets, and releases held buttons after current input completes. On Windows, a blocked reader can remain until the socket timeout; it cannot inject additional input after shutdown.
- The phone's first motion flush is scheduled after 16 ms instead of 28 ms. Under a slow response, further motion accumulates and is emitted when the response completes. Discrete actions retain ordering, and click/text requests are never automatically replayed after failure. The timer setting alone is not an end-to-end latency guarantee.
- Pointer-up coordinates are consumed so the last segment of a gesture is retained. Pointer indicator drawing is limited to animation frames, avoiding a layout read for every touch event.
- The drag heartbeat runs only during an active drag and skips redundant heartbeats while input is flowing. Background pages stop connection polling; automatic reconnect preserves pairing and drafts.
- Windows LAN address discovery runs off the Tk thread, with duplicate refreshes coalesced. The window and service startup no longer wait for the PowerShell address scan. An unchanged link/DPI size reuses its QR image. Idle event polling runs every 250 ms, versus 100 ms while operations are active.

## Verification

```powershell
.\Windows\Windows\.build-venv\Scripts\python.exe -m unittest discover -s Windows/Windows/tests
node Windows/Windows/tests/frontend-smoke.cjs
```

The local release check passed 80 Python tests and the frontend suite. A deterministic frontend scenario holds one response while 24 alternating move/scroll samples arrive: four total packets carry all 160 pixels and 25 wheel steps, with one layout read; acknowledgements are released manually instead of relying on timer precision.

Tests cover input/authentication, persistent HTTP framing and shutdown, saved languages and pairing, nonblocking address discovery, QR cache invalidation, and stale health replies. Frontend checks cover slow responses, input ordering, final coordinates, IME/Unicode, draft preservation, reconnect, and drag release.

The browser was also checked at 320×568, 390×844, 915×412, and 360×240: no document overflow and visible main controls at least 44×44 px, with English/Chinese switching and mock draft send/delete working. Actual Samsung phone Wi-Fi latency and physical Apple Watch compatibility still require device testing.
