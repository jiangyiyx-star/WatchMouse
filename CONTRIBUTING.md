# Contributing to WatchMouse

Bug reports and pull requests are welcome. Include your OS, phone/browser version, app version, and steps to reproduce. Remove pairing keys, QR codes, private addresses, and unrelated screen content from reports.

## Development

- Windows: see [Windows development guide](Windows/Windows/README.md).
- macOS: see [Mac development guide](Mac/README.md).
- Shared phone UI and HTTP protocol: `Windows/Windows/remote.*` and `receiver.py`.

Keep Windows PowerShell 5.1, Chinese Windows usernames/paths, and UTF-8 output working. Do not change saved pairing keys when upgrading. English is the default interface language; update English and Simplified Chinese strings together.

Run the shared Python tests, frontend interaction test, and relevant platform tests before submitting. UI changes should include screenshots made with demo data. Native input tests must mock final event posting rather than operate a developer's desktop.

## Pull requests

Explain the problem, final behavior, and validation. Keep each PR focused. Do not include generated executables, app bundles, runtime configuration, or logs in Git.

Contributions are provided under the project's [MIT license](LICENSE).
