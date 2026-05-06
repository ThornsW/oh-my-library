from __future__ import annotations

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

PySide6 = pytest.importorskip("PySide6")

from PySide6.QtWidgets import QApplication  # noqa: E402

from memo.core.models import PRIORITY_HIGH  # noqa: E402


@pytest.fixture(scope="module")
def qapp():
    return QApplication.instance() or QApplication([])


def test_create_todo_from_data_persists_all_creation_fields(db):
    from memo.ui.new_todo_dialog import NewTodoData, create_todo_from_data

    tag = db.create_tag("实验")
    todo_id = create_todo_from_data(
        NewTodoData(
            title="写实验记录",
            priority=PRIORITY_HIGH,
            due_date="2026-05-20",
            tag_ids=[tag.id],
            subtasks=[("整理数据", False), ("提交报告", True)],
        )
    )

    todo = db.get_todo(todo_id)

    assert todo is not None
    assert todo.title == "写实验记录"
    assert todo.note_md == ""
    assert todo.priority == PRIORITY_HIGH
    assert todo.due_date == "2026-05-20"
    assert [tag.name for tag in todo.tags] == ["实验"]
    assert [(s.text, s.completed) for s in todo.subtasks] == [
        ("整理数据", False),
        ("提交报告", True),
    ]
