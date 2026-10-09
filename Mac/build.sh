#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
PYTHON="${WATCHMOUSE_PYTHON:-python3}"
if [[ "$(uname -s)" != Darwin ]]; then
  echo 'Build on macOS.' >&2
  exit 1
fi
"$PYTHON" -m venv .build-venv
.build-venv/bin/python -m pip install -r requirements.txt
.build-venv/bin/python -m PyInstaller --noconfirm --clean WatchMouse.spec
/usr/bin/codesign --force --deep --sign - dist/WatchMouse.app
/usr/bin/ditto -c -k --sequesterRsrc --keepParent dist/WatchMouse.app "dist/WatchMouse-Mac-2.3.1-$(uname -m).zip"
echo "Created: $(pwd)/dist/WatchMouse.app"
