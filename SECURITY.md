# Security

WatchMouse grants a paired device mouse and keyboard control of a computer. Use it on a trusted local network and only share its pairing link with your own devices.

- A random persistent key authenticates input commands. The phone remembers the key locally; desktop updates preserve the existing key.
- LAN HTTP traffic is not encrypted. A device that can observe traffic on the network may obtain the pairing key. Do not expose the receiver to the public Internet or forward TCP port 53514.
- Input requests are restricted to the receiver's origin, validated, serialized, and bounded. Held mouse buttons have an inactivity watchdog.
- macOS requires Accessibility permission. Windows normally runs without administrator privileges; firewall setup is a separate administrator-approved action.
- The app does not collect analytics or send input through a hosted WatchMouse service. Browser or keyboard dictation may use the platform provider's services.

## Reset pairing

Stop the app. Back up and then remove `config.json` from `%LOCALAPPDATA%\WatchMouse` (Windows) or `~/Library/Application Support/WatchMouse` (Mac), then restart. A new key will be generated and old links will stop working. Pair your devices again. This also resets saved desktop preferences.

## Reporting a vulnerability

Use GitHub's private vulnerability reporting under the repository's **Security** tab. Do not post usable pairing keys or exploit details in a public issue before a fix is available.

The latest release is the supported version. Experimental Apple Watch compatibility is not guaranteed.
