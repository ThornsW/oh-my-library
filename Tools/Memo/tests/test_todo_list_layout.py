from __future__ import annotations

import os
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

PySide6 = pytest.importorskip("PySide6")

from PySide6.QtWidgets import QApplication, QLabel  # noqa: E402

from memo.core.models import PRIORITY_NORMAL, Subtask, Tag, Todo  # noqa: E402
from memo.ui import todo_list as todo_list_mod  # noqa: E402


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication([])
    app.setStyle("Fusion")
    app.setStyleSheet(Path("memo/resources/style.qss").read_text(encoding="utf-8"))
    return app


def test_todo_row_widget_owns_its_height_without_list_item_padding(monkeypatch, qapp):
    todo = Todo(
        id=1,
        title="更新实验代码",
        priority=PRIORITY_NORMAL,
        tags=[Tag(id=1, name="论文", color="#7AA2F7")],
        subtasks=[Subtask(id=1, todo_id=1, text="整理数据", completed=False)],
    )
    monkeypatch.setattr(todo_list_mod.db, "list_todos", lambda **_: [todo])

    widget = todo_list_mod.TodoList()
    widget.resize(320, 140)
    widget.refresh()
    widget.show()
    qapp.processEvents()

    item = widget._list.item(0)
    row = widget._list.itemWidget(item)

    assert item.sizeHint().height() <= row.sizeHint().height() + 2
    assert row.geometry().y() <= 2
    for label in row.findChildren(QLabel):
        assert label.geometry().height() >= label.sizeHint().height()
