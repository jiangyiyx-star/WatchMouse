# Changelog

## Unreleased

- Phone gamepad mode with switchable Xbox and PlayStation layouts: dual sticks, d-pad, ABXY/△○□✕, shoulders, and View/Menu.
- Held buttons and sticks keep the mapped key down while pressed, release on lift, and free everything when you leave the mode, hide the page, or the phone stops sending.
- The gamepad is laid out like a real controller: shoulders in the top corners, left stick above the d-pad (Xbox) or below it (PlayStation), face buttons above the right stick, View/Menu out of thumb reach in the middle, and the centre of the screen left empty so the phone can be gripped. Control sizes scale with the viewport instead of being fixed.
- Landscape phones get a fullscreen button that hides the browser and tab chrome and locks the orientation where the platform allows it; portrait keeps a bottom safe-area margin and shows a rotate hint.
- Optional native controller output on Windows: with the ViGEmBus driver and `pip install vgamepad`, games see a real Xbox 360 pad (`POST /api/pad`, 20 Hz snapshots, analog sticks and triggers). Without it the panel keeps the dependency-free key mapping.
- The receiver reports `nativeGamepad` and `padBackend` in `/api/status`; the phone switches modes by itself and refreshes a held snapshot once a second so the five-second idle watchdog does not fire mid-hold.
- Tests cover pad snapshot validation, the authenticated `/api/pad` endpoint, fallback to key mapping, neutral release on mode change, and native mode in the frontend smoke suite.

## 2.6 — 2026-10-13

- Red/black phone controls and a responsive Windows QR pairing window.
- Persistent HTTP connections and bounded receiver connection lifetime.
- Lower motion scheduling delay, final pointer-coordinate delivery, and ordered input under slow responses.
- Less idle work on phone and desktop; asynchronous Windows address discovery and QR caching.
- Preserve 2.4 language, pairing, Mac compatibility, and bundled license notices.

## 2.4 — 2026-10-09

- Open-source Windows and macOS receivers under the MIT license.
- English by default; saved Simplified Chinese interface selection on phone and desktop.
- Pairing keys survive receiver restart, updates, and language changes.
- Phone reconnects automatically, retains drafts, and drops stale mouse input after disconnect.
- Corrected pairing keys update the bookmarked/current URL so a stale link does not force re-pairing after reload.
- Localized permission guidance, including the experimental watch page.
- Real demo screenshots, bilingual overview, build workflows, contribution and security guides.
- Windows packaged startup/resource checks and a build under a Chinese source path.

The Mac download targets Apple silicon. Physical Apple Watch compatibility is unverified. LAN HTTP is intended for trusted networks; it is not encrypted. Code signing/notarization is not configured for commercial distribution.

## 2.3.1 (Mac) — 2026-10-09

Show Accessibility permission guidance before phone commands. Real phone connection and Mac control confirmed by a user after permission setup.

## 2.3 — 2026-10-09

Windows desktop receiver and shared phone UI, including mouse, keyboard, scroll strip, and video modes. First Mac receiver adaptation.
