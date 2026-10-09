# Build using: python -m PyInstaller Mac/WatchMouse.spec (or Mac/build.sh).
from pathlib import Path
root = Path(SPECPATH).resolve()
shared = root.parent / 'Windows' / 'Windows'
assets = [(str(shared / name), '.') for name in
          ('remote.html','remote.js','remote.css','manifest.webmanifest','icon.svg')]
a = Analysis([str(root / 'app.py')], pathex=[str(root),str(shared)], datas=assets,
             hiddenimports=['Quartz','AppKit','Foundation','ApplicationServices','PIL.PngImagePlugin'],
             hookspath=[], hooksconfig={}, runtime_hooks=[], excludes=['tkinter'])
pyz = PYZ(a.pure)
exe = EXE(pyz,a.scripts,[],exclude_binaries=True,name='WatchMouse',debug=False,
          bootloader_ignore_signals=False,strip=False,upx=False,console=False)
coll = COLLECT(exe,a.binaries,a.datas,strip=False,upx=False,name='WatchMouse')
app = BUNDLE(coll,name='WatchMouse.app',bundle_identifier='com.jiangyiyx.watchmouse',
             info_plist={'CFBundleShortVersionString':'2.3.0','CFBundleVersion':'230',
                         'NSHighResolutionCapable':True,
                         'NSLocalNetworkUsageDescription':'让同一 Wi-Fi 的手机连接并控制这台 Mac。'})
