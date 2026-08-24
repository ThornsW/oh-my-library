from __future__ import annotations

import pytest

pytest.importorskip("PySide6")


def test_native_icons_are_available_without_qtawesome(qapp) -> None:
    from memo.ui.icons import app_icon, icon

    names = ["plus", "search", "pin", "settings"]

    assert not app_icon().isNull()
    for name in names:
        assert not icon(name).isNull()
