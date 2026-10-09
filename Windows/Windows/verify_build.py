"""Verify that a PyInstaller build contains this checkout's current code/assets."""
from __future__ import annotations

import argparse
import marshal
from pathlib import Path
import types

from PyInstaller.archive.readers import CArchiveReader

ROOT = Path(__file__).resolve().parent
ASSET_PATTERNS = (
    "remote.html", "remote.js", "remote.css", "app.ico", "manifest*.json",
    "*.webmanifest", "icon*.svg", "icon*.png", "sw.js", "service-worker.js",
    "watch.html", "watch.js", "watch.css",
)


def compare_code(bundled: types.CodeType, current: types.CodeType, location: str):
    # PyInstaller normalizes co_filename; compare executable content recursively.
    for name in (
        "co_code", "co_names", "co_varnames", "co_freevars", "co_cellvars",
        "co_flags", "co_argcount", "co_kwonlyargcount", "co_posonlyargcount",
        "co_linetable", "co_exceptiontable",
    ):
        if getattr(bundled, name, None) != getattr(current, name, None):
            raise RuntimeError(f"Stale compiled source: {location} ({name})")
    if len(bundled.co_consts) != len(current.co_consts):
        raise RuntimeError(f"Stale compiled source: {location} (constants)")
    for bundled_value, current_value in zip(bundled.co_consts, current.co_consts):
        if isinstance(bundled_value, types.CodeType):
            if not isinstance(current_value, types.CodeType):
                raise RuntimeError(f"Stale compiled source: {location} (nested code)")
            compare_code(bundled_value, current_value, f"{location}.{bundled_value.co_name}")
        elif bundled_value != current_value:
            raise RuntimeError(f"Stale compiled source: {location} (constant)")


def verify(executable: Path):
    archive = CArchiveReader(str(executable))
    modules = archive.open_embedded_archive("PYZ.pyz")
    for name in ("receiver", "input_control", "app"):
        bundled = marshal.loads(archive.extract("app")) if name == "app" else modules.extract(name)
        source = (ROOT / f"{name}.py").read_text(encoding="utf-8-sig")
        current = compile(source, bundled.co_filename, "exec", dont_inherit=True)
        compare_code(bundled, current, name)
    assets = {path for pattern in ASSET_PATTERNS for path in ROOT.glob(pattern) if path.is_file()}
    for path in sorted(assets):
        if path.name not in archive.toc:
            raise RuntimeError(f"Missing bundled asset: {path.name}")
        if archive.extract(path.name) != path.read_bytes():
            raise RuntimeError(f"Stale bundled asset: {path.name}")
    print(f"Verified current source (3 modules) and {len(assets)} bundled assets.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--exe", type=Path, default=ROOT / "dist" / "WatchMouse.exe")
    args = parser.parse_args()
    verify(args.exe)


if __name__ == "__main__":
    main()
