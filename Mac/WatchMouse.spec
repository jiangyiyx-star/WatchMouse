# Build using: python -m PyInstaller Mac/WatchMouse.spec (or Mac/build.sh).
from pathlib import Path
import sys
root = Path(SPECPATH).resolve()
shared = root.parent / 'Windows' / 'Windows'
sys.path.insert(0, str(shared))
from receiver import VERSION
bundle_version = VERSION if VERSION.count('.') == 2 else VERSION + '.0'
assets = [(str(shared / name), '.') for name in
          ('remote.html','remote.js','remote.css','manifest.webmanifest','icon.svg')]
assets += [(str(root.parent / name), '.') for name in ('LICENSE', 'THIRD_PARTY_LICENSES.txt')]
a = Analysis([str(root / 'app.py')], pathex=[str(root),str(shared)], datas=assets,
             hiddenimports=['Quartz','AppKit','Foundation','ApplicationServices','PIL.PngImagePlugin'],
             hookspath=[], hooksconfig={}, runtime_hooks=[], excludes=['tkinter'])
pyz = PYZ(a.pure)
exe = EXE(pyz,a.scripts,[],exclude_binaries=True,name='WatchMouse',debug=False,
          bootloader_ignore_signals=False,strip=False,upx=False,console=False)
coll = COLLECT(exe,a.binaries,a.datas,strip=False,upx=False,name='WatchMouse')
app = BUNDLE(coll,name='WatchMouse.app',bundle_identifier='com.jiangyiyx.watchmouse',
             info_plist={'CFBundleShortVersionString':bundle_version,'CFBundleVersion':bundle_version,
                         'NSHighResolutionCapable':True,
                         'NSLocalNetworkUsageDescription':'Allow your phone on the same Wi-Fi to connect to and control this Mac.'})
