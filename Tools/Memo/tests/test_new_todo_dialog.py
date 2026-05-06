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


def test_create_todo_from_data_removes_todo_when_post_create_persistence_fails(db):
    from memo.ui.new_todo_dialog import NewTodoData, create_todo_from_data

    with pytest.raises(Exception):
        create_todo_from_data(
            NewTodoData(
                title="should not remain",
                tag_ids=[999999],
            )
        )

    assert db.count_all_todos() == 0


def test_new_todo_dialog_exposes_entered_form_data(db, qapp):
    from PySide6.QtCore import QDate

    from memo.core.models import PRIORITY_LOW
    from memo.ui.new_todo_dialog import NewTodoDialog

    work = db.create_tag("工作")
    personal = db.create_tag("个人")

    dialog = NewTodoDialog()
    dialog.title_edit.setText("准备会议")
    dialog.priority_box.setCurrentIndex(dialog.priority_box.findData(PRIORITY_LOW))
    dialog.due_check.setChecked(True)
    dialog.due_edit.setDate(QDate(2026, 6, 1))
    dialog._tag_checks[work.id].setChecked(True)  # noqa: SLF001
    dialog._tag_checks[personal.id].setChecked(False)  # noqa: SLF001
    dialog.subtasks.set_items([("约会议室", False), ("发议程", True)])

    data = dialog.todo_data()

    assert data.title == "准备会议"
    assert data.priority == PRIORITY_LOW
    assert data.due_date == "2026-06-01"
    assert data.tag_ids == [work.id]
    assert data.subtasks == [("约会议室", False), ("发议程", True)]


def test_new_todo_dialog_rejects_empty_title(db, qapp, monkeypatch):
    from memo.ui import new_todo_dialog as dialog_mod

    warnings: list[str] = []
    monkeypatch.setattr(
        dialog_mod.QMessageBox,
        "warning",
        lambda _parent, _title, message: warnings.append(message),
    )

    dialog = dialog_mod.NewTodoDialog()
    dialog.title_edit.setText("   ")
    dialog.accept()

    assert dialog.result() == dialog.DialogCode.Rejected
    assert warnings == ["标题不能为空。"]


def test_main_window_new_action_uses_full_new_todo_dialog():
    from pathlib import Path

    source = Path("memo/ui/main_window.py").read_text(encoding="utf-8")

    assert "QInputDialog" not in source
    assert "NewTodoDialog" in source
    assert "create_todo_from_data" in source
