# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for Memo.

Build:
    pyinstaller --clean Memo.spec

Output:
    dist/Memo            (Linux ELF)
    dist/Memo.exe        (Windows GUI exe — must be built on Windows)

Memo is a pure QWidget app — no QML / QtQuick / networking / multimedia.
``collect_all`` would otherwise drag in QtWebEngine, all of Qt3D,
QtMultimedia, QtSensors, QtPositioning … bloating the bundle to 100MB+
for no reason. We aggressively filter both the PySide6 Python binding
modules and the underlying Qt6 shared libraries / Qt plugins down to
what the app actually needs at runtime.
"""

import os
import sys

from PyInstaller.utils.hooks import collect_all

# --- which PySide6 modules / Qt libs / Qt plugins to keep -----------------

KEEP_PYSIDE_MODULES = {
    "QtCore",
    "QtGui",
    "QtWidgets",
    "QtDBus",         # required for the tray icon on Linux desktops
}

# Qt6 shared libraries we keep (matched against the file's basename prefix,
# i.e. "libQt6Core" matches "libQt6Core.so.6.4.2").
KEEP_QT_LIB_BASENAMES = {
    "libQt6Core",
    "libQt6Gui",
    "libQt6Widgets",
    "libQt6DBus",
    "libQt6XcbQpa",          # backing lib for the xcb platform plugin
    "libQt6OpenGL",          # libQt6Gui transitively dlopens it
    "libQt6WaylandClient",   # so the bundle also runs on Wayland sessions
}

KEEP_QT_PLUGIN_DIRS = {
    "platforms",
    "platforminputcontexts",
    "platformthemes",
    "imageformats",
    "xcbglintegrations",
    "wayland-decoration-client",
    "wayland-graphics-integration-client",
    "wayland-shell-integration",
}

KEEP_QT_PLUGIN_BASENAMES = {
    "platforms": {
        "libqxcb",
        "libqminimal",
    },
    "platforminputcontexts": {
        "libcomposeplatforminputcontextplugin",
        "libfcitx5platforminputcontextplugin",
        "libibusplatforminputcontextplugin",
    },
    "platformthemes": {
        "libqxdgdesktopportal",
    },
    "imageformats": {
        "libqgif",
        "libqico",
        "libqjpeg",
    },
    "xcbglintegrations": {
        "libqxcb-glx-integration",
    },
}

# Specific full filenames to drop. Use this set when only one version of a
# multi-versioned library family should be dropped — DROP_BINARY_BASENAMES
# below matches by prefix and would kill every version.
#
# The bundled fcitx5 plugin (Ubuntu 24.04) drags in system ICU 74 alongside
# Qt6Core's hard-linked conda ICU 70 — ~22 MB of duplicate Unicode data
# (compressed). We keep ICU 70 (Qt6Core can't run without it) and drop the
# ICU 74 copy. At runtime on Ubuntu 24.04, libicu*.so.74 are still found via
# the system loader, so the fcitx5 plugin works. Older distros without ICU
# 74 (e.g. Ubuntu 22.04) lose the bundled fcitx5 fallback and must rely on
# their system input-method stack (ibus / system Compose).
DROP_FULL_BASENAMES = {
    "libicudata.so.74",
    "libicui18n.so.74",
    "libicuuc.so.74",
}


DROP_BINARY_BASENAMES = {
    # Only needed by filtered SVG/WebP/TIFF Qt plugins or excluded Qt modules.
    "libQt6Svg",
    "libQt6SvgWidgets",
    "libQt6Network",
    "libLerc",
    "libdeflate",
    "libsharpyuv",
    "libtiff",
    "libwebp",
    "libwebpdemux",
    "libwebpmux",
    # Transitive deps of the bundled fcitx5 input-method plugin (Ubuntu 24.04
    # system libs). These are universally present on supported Linux desktops,
    # so the bundle's copies just bloat the binary — drop them and let the
    # runtime loader fall back to the system copy.
    "libcrypto",
    "libssl",
    "libsystemd",
    "libgcrypt",
    "libgpg-error",
    "libzstd",
    "liblz4",
    "libcap",
}


def _basename_prefix(p: str) -> str:
    name = os.path.basename(p)
    return name.split(".", 1)[0]


def _is_pyside_module_so(src: str) -> bool:
    norm = src.replace("\\", "/")
    name = os.path.basename(src)
    return "/PySide6/" in norm and name.endswith(".abi3.so")


def _pyside_module_name(src: str) -> str:
    return os.path.basename(src).rsplit(".", 2)[0]


def _is_qt_lib(src: str) -> bool:
    name = os.path.basename(src)
    return name.startswith("libQt6") or name.startswith("Qt6")


def _qt_plugin_dir(src: str) -> str:
    norm = src.replace("\\", "/")
    if "/qt6/plugins/" in norm:
        return norm.split("/qt6/plugins/", 1)[1].split("/", 1)[0]
    if "/PySide6/Qt/plugins/" in norm:
        return norm.split("/PySide6/Qt/plugins/", 1)[1].split("/", 1)[0]
    return ""


def _qt_plugin_name(src: str) -> str:
    return _basename_prefix(src)


def _is_qt_plugin(src: str) -> bool:
    return bool(_qt_plugin_dir(src))


def _keep_binary(src: str) -> bool:
    if os.path.basename(src) in DROP_FULL_BASENAMES:
        return False
    if _basename_prefix(src) in DROP_BINARY_BASENAMES:
        return False
    if _is_pyside_module_so(src):
        return _pyside_module_name(src) in KEEP_PYSIDE_MODULES
    if _is_qt_lib(src):
        return _basename_prefix(src) in KEEP_QT_LIB_BASENAMES
    if _is_qt_plugin(src):
        plugin_dir = _qt_plugin_dir(src)
        if plugin_dir not in KEEP_QT_PLUGIN_DIRS:
            return False
        keep_names = KEEP_QT_PLUGIN_BASENAMES.get(plugin_dir)
        return keep_names is None or _qt_plugin_name(src) in keep_names
    return True


def _filter_toc(entries, predicate):
    return [entry for entry in entries if predicate(entry[1])]


def _keep_data(src: str) -> bool:
    norm = src.replace("\\", "/")
    name = os.path.basename(src)
    if name.endswith((".py", ".pyc", ".c", ".h")):
        return False
    if name.endswith(".pyi") or name == "py.typed" or ".dist-info/" in norm:
        return False
    if "/tests/" in norm or "/test_" in norm:
        return False
    if "/translations/" in norm and norm.endswith(".qm"):
        return False
    if any(b in norm for b in ("/qml/", "/Qt/qml/", "/QtQuick/", "/Qt3D/", "/QtCharts/")):
        return False
    return True


# --- collect everything, then filter --------------------------------------

datas = []
binaries = []
hiddenimports = []

for pkg in ("PySide6", "shiboken6", "pynput", "Xlib", "evdev"):
    d, b, h = collect_all(pkg)
    datas += d
    binaries += b
    hiddenimports += h

binaries = [(s, d) for s, d in binaries if _keep_binary(s)]
datas = [(s, d) for s, d in datas if _keep_data(s) and _keep_binary(s)]

# bundle Memo's own data resources (QSS stylesheet, etc.)
datas += [("memo/resources/style.qss", "memo/resources")]

hiddenimports = [
    h for h in hiddenimports
    if not h.startswith("PySide6.")
    or h.split(".")[1] in KEEP_PYSIDE_MODULES
    or h.split(".")[1] == "support"
]

# pynput chooses its Linux backend with importlib at runtime. In sandboxed
# builds, its PyInstaller hook can fail to import pynput because no X
# connection is available, so the backend modules must be explicit.
hiddenimports += [
    "pynput._util.xorg",
    "pynput._util.xorg_keysyms",
    "pynput.keyboard._base",
    "pynput.keyboard._xorg",
    "pynput.mouse._base",
    "pynput.mouse._xorg",
]

EXCLUDED_PYSIDE = [
    "PySide6.Qt3DAnimation", "PySide6.Qt3DCore", "PySide6.Qt3DExtras",
    "PySide6.Qt3DInput", "PySide6.Qt3DLogic", "PySide6.Qt3DRender",
    "PySide6.QtCharts", "PySide6.QtConcurrent", "PySide6.QtDataVisualization",
    "PySide6.QtHelp", "PySide6.QtMultimedia", "PySide6.QtMultimediaWidgets",
    "PySide6.QtNetwork", "PySide6.QtNetworkAuth", "PySide6.QtOpenGL",
    "PySide6.QtOpenGLWidgets", "PySide6.QtPdf", "PySide6.QtPdfWidgets",
    "PySide6.QtPositioning", "PySide6.QtPrintSupport", "PySide6.QtQml",
    "PySide6.QtQuick", "PySide6.QtQuick3D", "PySide6.QtQuickControls2",
    "PySide6.QtQuickWidgets", "PySide6.QtRemoteObjects", "PySide6.QtScxml",
    "PySide6.QtSensors", "PySide6.QtSerialBus", "PySide6.QtSerialPort",
    "PySide6.QtSpatialAudio", "PySide6.QtSql", "PySide6.QtStateMachine",
    "PySide6.QtTest", "PySide6.QtTextToSpeech", "PySide6.QtUiTools",
    "PySide6.QtWebChannel", "PySide6.QtWebEngineCore", "PySide6.QtWebEngineQuick",
    "PySide6.QtWebEngineWidgets", "PySide6.QtWebSockets", "PySide6.QtXml",
]

# --- Linux: bundle the system fcitx5 Qt6 IM plugin so Chinese input works
#     out of the box for users running fcitx5. The plugin from Ubuntu 24.04
#     is ABI-compatible with our bundled Qt 6.4.2.
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
    excludes=EXCLUDED_PYSIDE + [
        "numpy", "pandas", "scipy", "matplotlib", "PIL", "tkinter",
        # Memo never does decimal arithmetic; _decimal alone is ~1.5 MB.
        "_decimal", "decimal",
    ],
    noarchive=False,
)

a.binaries = _filter_toc(a.binaries, _keep_binary)
a.datas = _filter_toc(a.datas, _keep_data)

# PyInstaller 6 dropped bytecode encryption (``cipher``) along with
# ``Analysis.zipped_data`` / ``Analysis.zipfiles``; both were unused here.
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="Memo",
    debug=False,
    bootloader_ignore_signals=False,
    strip=True,    # strip ELF debug symbols
    upx=False,     # PyInstaller disables UPX on non-Windows by default
                   # because UPX-compressing modern Linux shared libs
                   # (libpython, Qt6 cores, libstdc++, libpyside6/shiboken6,
                   # …) is known to cause SIGSEGV at dlopen time. Empirical
                   # tests with PYINSTALLER_FORCE_UPX=1 confirmed the binary
                   # still core-dumps even after excluding the obvious risk
                   # libs — leave UPX off until a stable exclude set is
                   # narrowed down.
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
