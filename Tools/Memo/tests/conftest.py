from __future__ import annotations

import os
from pathlib import Path

import pytest


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
