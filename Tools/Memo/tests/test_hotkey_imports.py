from __future__ import annotations

import os
import subprocess
import sys

import pytest

from memo.core import hotkey


def test_validate_rejects_an_unparsable_combo() -> None:
    with pytest.raises(hotkey.HotkeyError):
        hotkey.validate("not a combo!!")


def test_validate_accepts_the_default_combo() -> None:
    from memo.core.settings import DEFAULT_HOTKEY

    hotkey.validate(DEFAULT_HOTKEY)  # must not raise


def test_settings_dialog_reuses_the_shared_validator() -> None:
    """The dialog used to re-implement parsing and its own ImportError /
    ValueError handling; keep it on the one code path."""
    from pathlib import Path

    source = Path("memo/ui/settings_dialog.py").read_text(encoding="utf-8")

    assert "hotkey.validate" in source
    assert "from pynput" not in source


def test_app_modules_import_without_display() -> None:
    env = os.environ.copy()
    env.pop("DISPLAY", None)
    env.pop("WAYLAND_DISPLAY", None)

    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "import memo.app; import memo.ui.settings_dialog",
        ],
        cwd=os.getcwd(),
        env=env,
        text=True,
        capture_output=True,
        timeout=10,
    )

    assert result.returncode == 0, result.stderr
