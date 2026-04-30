# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for Memo.

Build:
    pyinstaller --clean Memo.spec

Output:
    dist/Memo            (Linux ELF)
    dist/Memo.exe        (Windows GUI exe — must be built on Windows)
"""

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
