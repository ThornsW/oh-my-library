from __future__ import annotations

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

pytest.importorskip("PySide6")

from PySide6.QtWidgets import QApplication  # noqa: E402


@pytest.fixture(scope="module")
def qapp():
    return QApplication.instance() or QApplication([])


def test_native_icons_are_available_without_qtawesome(qapp) -> None:
    from memo.ui.icons import app_icon, icon

    names = ["plus", "search", "pin", "settings"]

    assert not app_icon().isNull()
    for name in names:
        assert not icon(name).isNull()
