"""User data directory resolution for the app."""

from __future__ import annotations

import os
from pathlib import Path

from platformdirs import user_data_dir

APP_NAME = "Memo"


def data_dir() -> Path:
    """Return the per-user data directory, creating it if needed.

    Honors ``MEMO_DATA_DIR`` for tests.
    """
    override = os.environ.get("MEMO_DATA_DIR")
    base = Path(override) if override else Path(user_data_dir(APP_NAME, appauthor=False))
    base.mkdir(parents=True, exist_ok=True)
    return base


def db_path() -> Path:
    return data_dir() / "memo.db"


def settings_path() -> Path:
    return data_dir() / "settings.json"
