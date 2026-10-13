# Third-party notices

The MIT license applies to WatchMouse's source. It does not replace licenses of bundled runtimes and libraries.

| Component | Purpose | Upstream license |
| --- | --- | --- |
| [Python](https://www.python.org/psf/license/) | Runtime | Python Software Foundation license |
| [PyInstaller](https://pyinstaller.org/en/stable/license.html) | Packaging | GPL 2.0 with a distribution exception for bundled applications |
| [PyObjC](https://pyobjc.readthedocs.io/en/latest/license.html) | macOS Cocoa/Quartz bindings | MIT |
| [qrcode](https://github.com/lincolnloop/python-qrcode/blob/main/LICENSE) | QR code generation | BSD |
| [Pillow](https://github.com/python-pillow/Pillow/blob/main/LICENSE) | Images and QR rendering | HPND and included notices |
| [Tcl/Tk](https://www.tcl-lang.org/software/tcltk/license.html) | Windows desktop UI | Tcl/Tk license |
| [OpenSSL 3](https://github.com/openssl/openssl/blob/openssl-3.0.16/LICENSE.txt) | Bundled Python runtime cryptography libraries | Apache 2.0 |
| [libffi](https://github.com/libffi/libffi/blob/v3.4.4/LICENSE) | Windows Python foreign-function interface | MIT |
| [mpdecimal](https://github.com/python/cpython-source-deps/blob/mpdecimal-4.0.0/COPYRIGHT.txt) | Python decimal arithmetic | BSD 2-Clause |
| [Expat](https://github.com/libexpat/libexpat/blob/R_2_8_2/expat/COPYING) | Python XML parser | MIT |
| [LibTomMath](https://github.com/libtom/libtommath/blob/master/LICENSE) | Tcl arithmetic library | Public domain / Unlicense |
| [Microsoft C/C++ runtime](https://learn.microsoft.com/en-us/cpp/windows/redistributing-visual-cpp-files) | Windows Python runtime dependencies | Microsoft redistribution terms; excluded from WatchMouse's MIT license |

Development/CI uses Node.js for frontend tests and browser tools for screenshots. They are not part of the phone UI, which has no third-party JavaScript dependencies.

Full license texts are included in [THIRD_PARTY_LICENSES.txt](THIRD_PARTY_LICENSES.txt) and packaged with the desktop apps.

Review the upstream license and the notices shipped with the installed dependency version when redistributing a custom build.
