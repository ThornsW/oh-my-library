from __future__ import annotations

import json

from memo.core import paths
from memo.core.settings import DEFAULT_HOTKEY, Settings


def test_defaults_when_file_missing(isolated_data_dir):
    s = Settings.load()
    assert s.always_on_top is False
    assert s.autostart is False
    assert s.global_hotkey == DEFAULT_HOTKEY
    assert s.filter == "active"
    assert s.selected_tag_id is None


def test_save_then_load_round_trip(isolated_data_dir):
    s = Settings(
        always_on_top=True,
        autostart=True,
        global_hotkey="<ctrl>+<alt>+j",
        selected_tag_id=7,
        filter="all",
    )
    s.save()
    loaded = Settings.load()
    assert loaded == s


def test_load_tolerates_unknown_keys(isolated_data_dir):
    paths.settings_path().write_text(
        json.dumps({"always_on_top": True, "deprecated_key": "ignore_me"}),
        encoding="utf-8",
    )
    loaded = Settings.load()
    assert loaded.always_on_top is True
    # unknown key didn't blow up; defaults still applied
    assert loaded.filter == "active"


def test_load_tolerates_corrupt_file(isolated_data_dir):
    paths.settings_path().write_text("{not valid json", encoding="utf-8")
    loaded = Settings.load()
    assert loaded == Settings()
