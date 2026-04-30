# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for Memo.

Build:
    pyinstaller --clean Memo.spec

Output:
    dist/Memo            (Linux ELF)
    dist/Memo.exe        (Windows GUI exe — must be built on Windows)
"""

import os
import sys

from PyInstaller.utils.hooks import collect_all

block_cipher = None

datas = []
binaries = []
hiddenimports = []

# PySide6 ships Qt plugins, qtawesome ships its bundled fonts, pynput needs
# its platform-specific submodules — let collect_all pull all of that in.
for pkg in ("PySide6", "shiboken6", "qtawesome", "pynput"):
    d, b, h = collect_all(pkg)
    datas += d
    binaries += b
    hiddenimports += h

# On Linux, also bundle the fcitx5 Qt6 input-method plugin so end users with
# fcitx5 (the common Chinese IM on Ubuntu/Debian) can type CJK in the app
# without installing anything extra. The plugin from the build host is
# linked against system Qt 6.4 and is ABI-compatible with the bundled Qt 6.4.
if sys.platform.startswith("linux"):
    _fcitx_plugin = "/usr/lib/x86_64-linux-gnu/qt6/plugins/platforminputcontexts/libfcitx5platforminputcontextplugin.so"
    if os.path.exists(_fcitx_plugin):
        binaries.append((_fcitx_plugin, "PySide6/Qt/plugins/platforminputcontexts"))

a = Analysis(
    ["memo/__main__.py"],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="Memo",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
