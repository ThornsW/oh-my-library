from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

from memo.core import input_method

linux_only = pytest.mark.skipif(
    not sys.platform.startswith("linux"), reason="input-method routing is Linux-only"
)

DEAD_PID = 4194304  # above /proc/sys/kernel/pid_max on any normal Linux box


def _write_bus_file(config_home: Path, pid: int) -> Path:
    bus_dir = config_home / "ibus" / "bus"
    bus_dir.mkdir(parents=True, exist_ok=True)
    target = bus_dir / "abc123-unix-0"
    target.write_text(
        f"IBUS_ADDRESS=unix:path=/run/user/1000/bus,fcitx_random_string=deadbeef\n"
        f"IBUS_DAEMON_PID={pid}\n",
        encoding="utf-8",
    )
    return target


@linux_only
def test_configure_routes_fcitx_to_ibus_when_frontend_is_live(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    monkeypatch.setenv("QT_IM_MODULE", "fcitx")
    _write_bus_file(tmp_path, os.getpid())

    assert input_method.configure() == "ibus"
    assert os.environ["QT_IM_MODULE"] == "ibus"


@linux_only
def test_configure_leaves_fcitx_alone_when_nothing_serves_ibus(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    monkeypatch.setenv("QT_IM_MODULE", "fcitx")
    # no bus directory at all

    assert input_method.configure() is None
    assert os.environ["QT_IM_MODULE"] == "fcitx"


@linux_only
def test_configure_ignores_a_bus_file_left_by_a_dead_session(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    monkeypatch.setenv("QT_IM_MODULE", "fcitx5")
    _write_bus_file(tmp_path, DEAD_PID)

    assert input_method.configure() is None
    assert os.environ["QT_IM_MODULE"] == "fcitx5"


@linux_only
@pytest.mark.parametrize("configured", ["ibus", "xim", ""])
def test_configure_only_touches_fcitx(tmp_path, monkeypatch, configured):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    monkeypatch.setenv("QT_IM_MODULE", configured)
    _write_bus_file(tmp_path, os.getpid())

    assert input_method.configure() is None
    assert os.environ["QT_IM_MODULE"] == configured


@linux_only
def test_configure_is_a_no_op_when_qt_im_module_is_unset(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    monkeypatch.delenv("QT_IM_MODULE", raising=False)
    _write_bus_file(tmp_path, os.getpid())

    assert input_method.configure() is None
    assert "QT_IM_MODULE" not in os.environ


@linux_only
def test_ibus_frontend_detection_tolerates_an_unreadable_bus_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "does-not-exist"))

    assert input_method.ibus_frontend_is_live() is False


def test_app_configures_input_method_before_creating_qapplication() -> None:
    """Qt reads QT_IM_MODULE while building the platform integration, so the
    call has to come first — a later call would silently do nothing."""
    source = (Path(__file__).resolve().parents[1] / "memo" / "app.py").read_text(
        encoding="utf-8"
    )

    configure_at = source.index("input_method.configure()")
    qapp_at = source.index("QApplication(")

    assert configure_at < qapp_at
