"""Cross-platform "launch on login" toggle.

- Windows: ``HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Run`` registry value.
- Linux:  ``$XDG_CONFIG_HOME/autostart/memo.desktop`` (defaults to
  ``~/.config/autostart/memo.desktop``).

The UI calls ``is_enabled()``, ``enable()``, ``disable()`` without caring about
the OS. The current Python executable + module path is used as the command, so
this works for ``python -m memo`` runs *and* for a future PyInstaller build
where ``sys.executable`` is the bundled binary.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

APP_NAME = "Memo"
LINUX_DESKTOP_FILENAME = "memo.desktop"
WIN_REG_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
WIN_REG_VALUE = "Memo"


def _is_windows() -> bool:
    return sys.platform.startswith("win")


def _autostart_command() -> str:
    """Command the OS should run at login."""
    exe = sys.executable
    # If we're being run as a frozen exe, no module argument is needed.
    if getattr(sys, "frozen", False):
        return f'"{exe}"' if _is_windows() else exe
    return f'"{exe}" -m memo' if _is_windows() else f"{exe} -m memo"


# ---------- Linux ----------

def _linux_autostart_dir() -> Path:
    base = os.environ.get("XDG_CONFIG_HOME") or os.path.expanduser("~/.config")
    return Path(base) / "autostart"


def _linux_desktop_path() -> Path:
    return _linux_autostart_dir() / LINUX_DESKTOP_FILENAME


def _linux_enable() -> None:
    d = _linux_autostart_dir()
    d.mkdir(parents=True, exist_ok=True)
    content = (
        "[Desktop Entry]\n"
        "Type=Application\n"
        f"Name={APP_NAME}\n"
        f"Exec={_autostart_command()}\n"
        "Terminal=false\n"
        "X-GNOME-Autostart-enabled=true\n"
    )
    _linux_desktop_path().write_text(content, encoding="utf-8")


def _linux_disable() -> None:
    p = _linux_desktop_path()
    if p.exists():
        p.unlink()


def _linux_is_enabled() -> bool:
    return _linux_desktop_path().exists()


# ---------- Windows ----------

def _win_open_run_key(write: bool):
    import winreg  # type: ignore[import-not-found]
    access = winreg.KEY_SET_VALUE | winreg.KEY_READ if write else winreg.KEY_READ
    return winreg.OpenKey(winreg.HKEY_CURRENT_USER, WIN_REG_KEY, 0, access)


def _win_enable() -> None:
    import winreg  # type: ignore[import-not-found]
    with _win_open_run_key(write=True) as key:
        winreg.SetValueEx(key, WIN_REG_VALUE, 0, winreg.REG_SZ, _autostart_command())


def _win_disable() -> None:
    import winreg  # type: ignore[import-not-found]
    try:
        with _win_open_run_key(write=True) as key:
            winreg.DeleteValue(key, WIN_REG_VALUE)
    except FileNotFoundError:
        pass


def _win_is_enabled() -> bool:
    import winreg  # type: ignore[import-not-found]
    try:
        with _win_open_run_key(write=False) as key:
            winreg.QueryValueEx(key, WIN_REG_VALUE)
            return True
    except FileNotFoundError:
        return False


# ---------- Public API ----------

def is_enabled() -> bool:
    return _win_is_enabled() if _is_windows() else _linux_is_enabled()


def enable() -> None:
    _win_enable() if _is_windows() else _linux_enable()


def disable() -> None:
    _win_disable() if _is_windows() else _linux_disable()


def set_enabled(value: bool) -> None:
    enable() if value else disable()
