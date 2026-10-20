from __future__ import annotations

import sys

import pytest

linux_only = pytest.mark.skipif(sys.platform.startswith("win"), reason="Linux-only path")


@linux_only
def test_linux_autostart_writes_and_removes_desktop_file(isolated_data_dir):
    from memo.core import autostart

    assert autostart.is_enabled() is False

    autostart.enable()
    desktop = autostart._linux_desktop_path()  # noqa: SLF001
    assert desktop.exists()
    text = desktop.read_text(encoding="utf-8")
    assert "[Desktop Entry]" in text
    assert "Name=Memo" in text
    assert "Exec=" in text
    assert autostart.is_enabled() is True

    autostart.disable()
    assert not desktop.exists()
    assert autostart.is_enabled() is False


@linux_only
def test_linux_disable_when_not_enabled_is_noop(isolated_data_dir):
    from memo.core import autostart

    autostart.disable()
    assert autostart.is_enabled() is False


@linux_only
def test_linux_set_enabled_round_trip(isolated_data_dir):
    from memo.core import autostart

    autostart.set_enabled(True)
    assert autostart.is_enabled() is True
    autostart.set_enabled(False)
    assert autostart.is_enabled() is False
