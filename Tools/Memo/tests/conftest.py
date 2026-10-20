from __future__ import annotations

import os
from pathlib import Path

import pytest

# Must be set before any test module imports PySide6. conftest is imported
# first, so this covers every Qt test in one place.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.fixture(scope="session")
def qapp():
    """The one QApplication for the whole run, set up the way memo.app does.

    Qt allows a single instance per process, so this has to be shared. Applying
    the real style and stylesheet keeps layout assertions honest.
    """
    pytest.importorskip("PySide6")
    from PySide6.QtWidgets import QApplication

    from memo.app import _load_stylesheet

    app = QApplication.instance() or QApplication([])
    app.setStyle("Fusion")
    app.setStyleSheet(_load_stylesheet())
    return app


@pytest.fixture
def isolated_data_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Redirect both MEMO_DATA_DIR and XDG_CONFIG_HOME under a tmp dir."""
    data_dir = tmp_path / "memo_data"
    config_dir = tmp_path / "config"
    data_dir.mkdir()
    config_dir.mkdir()
    monkeypatch.setenv("MEMO_DATA_DIR", str(data_dir))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(config_dir))
    return data_dir


@pytest.fixture
def db(isolated_data_dir):
    """Open a fresh DB in the isolated dir; close after the test."""
    from memo.core import db as db_mod

    db_mod.close()
    db_mod.connect()
    yield db_mod
    db_mod.close()
