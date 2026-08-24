"""Pick a Qt input-method plugin that a bundled Qt can actually load.

Qt requires an *exact* ``QT_VERSION`` match for QPA plugins — not just the
same major version. A PyInstaller bundle ships its own Qt, so the distro's
``libfcitx5platforminputcontextplugin.so`` (built against the system Qt) can
never be loaded from it. With Qt 6.11 bundled and Ubuntu 24.04's Qt 6.4
plugin on disk, Qt says:

    Ignoring QPA plugin due to mismatching Qt versions 396032 394240
    ... undefined symbol: QWindowSystemInterface::handleExtendedKeyEvent(...)

Qt's own ibus input-context plugin lives *inside* the bundle, so it is always
version-matched. fcitx5 serves the IBus protocol through its ``ibusfrontend``
addon: it takes the ``org.freedesktop.IBus`` bus name and writes the same
address file ``ibus-daemon`` does. Asking Qt for ``ibus`` therefore still
reaches fcitx5 — and Memo stops depending on the build machine's Qt version
matching the user's desktop.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

_FCITX_MODULES = {"fcitx", "fcitx5"}


def _ibus_bus_dir() -> Path:
    config_home = os.environ.get("XDG_CONFIG_HOME")
    base = Path(config_home) if config_home else Path.home() / ".config"
    return base / "ibus" / "bus"


def ibus_frontend_is_live() -> bool:
    """True when a process is serving the IBus protocol right now.

    Covers ibus-daemon and fcitx5's ibusfrontend alike — both write the same
    address file. A file left behind by a previous session is ignored by
    checking that the PID it records still exists.
    """
    try:
        entries = sorted(_ibus_bus_dir().iterdir())
    except OSError:
        return False

    for entry in entries:
        try:
            content = entry.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for line in content.splitlines():
            key, sep, value = line.partition("=")
            if sep and key.strip() == "IBUS_DAEMON_PID":
                pid = value.strip()
                if pid.isdigit() and Path("/proc", pid).exists():
                    return True
    return False


def configure() -> str | None:
    """Route fcitx input through ibus when that is the only plugin we can load.

    Returns the value written to ``QT_IM_MODULE``, or ``None`` when the
    environment was left alone. Must run before ``QApplication`` is created —
    Qt reads ``QT_IM_MODULE`` while building the platform integration.

    Falls through untouched when nothing serves IBus, so a desktop whose
    fcitx5 has ibusfrontend disabled keeps whatever it had configured.
    """
    if not sys.platform.startswith("linux"):
        return None
    if os.environ.get("QT_IM_MODULE", "").strip().lower() not in _FCITX_MODULES:
        return None
    if not ibus_frontend_is_live():
        return None

    os.environ["QT_IM_MODULE"] = "ibus"
    return "ibus"
