from __future__ import annotations

import pytest

pytest.importorskip("PySide6")

from memo.core.models import PRIORITY_HIGH, PRIORITY_LOW  # noqa: E402
from memo.ui.new_todo_dialog import (  # noqa: E402
    NewTodoData,
    NewTodoDialog,
    create_todo_from_data,
)
from memo.ui.tag_sidebar import TagSidebar  # noqa: E402


def test_create_todo_from_data_persists_all_creation_fields(db):
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
    with pytest.raises(Exception):
        create_todo_from_data(
            NewTodoData(
                title="should not remain",
                tag_ids=[999999],
            )
        )

    assert db.list_todos(filter_="all") == []


def test_new_todo_dialog_exposes_entered_form_data(db, qapp):
    from PySide6.QtCore import QDate

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


def test_new_todo_dialog_preselects_requested_tags(db, qapp):
    work = db.create_tag("工作")
    personal = db.create_tag("个人")

    dialog = NewTodoDialog(preselected_tag_ids=[work.id])

    assert dialog._tag_checks[work.id].isChecked() is True  # noqa: SLF001
    assert dialog._tag_checks[personal.id].isChecked() is False  # noqa: SLF001

    dialog.title_edit.setText("写周报")
    assert dialog.todo_data().tag_ids == [work.id]


def test_tag_sidebar_context_menu_requests_new_todo_under_that_tag(db, qapp):
    tag = db.create_tag("科研")
    sidebar = TagSidebar()

    requested = []
    sidebar.newTodoRequested.connect(requested.append)

    menu = sidebar._build_tag_menu(tag.id)  # noqa: SLF001
    labels = [a.text() for a in menu.actions() if not a.isSeparator()]
    assert labels == ["在此标签下新建待办…", "重命名…", "删除"]

    menu.actions()[0].trigger()

    assert requested == [tag.id]


def test_main_window_new_action_uses_full_new_todo_dialog():
    from pathlib import Path

    source = Path("memo/ui/main_window.py").read_text(encoding="utf-8")

    assert "QInputDialog" not in source
    assert "NewTodoDialog" in source
    assert "create_todo_from_data" in source


# ---- MainWindow creation flow ----
# MainWindow is instantiated with ``__new__`` and hand-fed fakes so the flow can
# be driven without a real Qt window, tray or database.


class _FakeSettings:
    def __init__(self):
        self.filter = "done"
        self.selected_tag_id = 99

    def save(self):
        pass


class _FakeFilterBox:
    values = ["active", "all", "done"]

    def __init__(self):
        self.current_index = self.values.index("done")
        self.set_indexes = []

    def currentData(self):
        return self.values[self.current_index]

    def findData(self, value):
        return self.values.index(value)

    def setCurrentIndex(self, index):
        self.current_index = index
        self.set_indexes.append(index)


class _FakeSearchEdit:
    def __init__(self):
        self.value = "will hide item"
        self.cleared = False

    def text(self):
        return self.value

    def clear(self):
        self.value = ""
        self.cleared = True


class _FakeSidebar:
    def __init__(self):
        self.selected = 99
        self.refresh_count = 0

    def selected_tag_id(self):
        return self.selected

    def select_tag(self, tag_id):
        self.selected = tag_id

    def refresh(self):
        self.refresh_count += 1


class _FakeTodoList:
    def __init__(self):
        self.filter = "done"
        self.tag = 99
        self.search = "will hide item"
        self.refresh_count = 0
        self.selected_todo = None

    def set_filter(self, value):
        self.filter = value

    def set_tag(self, tag_id):
        self.tag = tag_id

    def set_search(self, text):
        self.search = text

    def refresh(self):
        self.refresh_count += 1

    def select_todo(self, todo_id):
        self.selected_todo = todo_id


def _install_fake_dialog(monkeypatch, *, tag_ids=None):
    """Patch the dialog + persistence used by MainWindow.

    ``tag_ids=None`` means "the user kept whatever was preselected"; pass a list
    to simulate the user editing the tag ticks before pressing 创建.
    """
    from memo.ui import main_window

    dialogs = []
    created = []

    class FakeDialog:
        class DialogCode:
            Accepted = 1

        def __init__(self, parent, *, preselected_tag_ids=()):
            self.parent = parent
            self.preselected_tag_ids = list(preselected_tag_ids)
            dialogs.append(self)

        def exec(self):
            return self.DialogCode.Accepted

        def todo_data(self):
            chosen = self.preselected_tag_ids if tag_ids is None else list(tag_ids)
            return NewTodoData(title="任务", tag_ids=chosen)

    def fake_create_todo_from_data(data):
        created.append(data)
        return 42

    monkeypatch.setattr(main_window, "NewTodoDialog", FakeDialog)
    monkeypatch.setattr(main_window, "create_todo_from_data", fake_create_todo_from_data)
    return dialogs, created


def _make_window():
    from memo.ui.main_window import MainWindow

    window = MainWindow.__new__(MainWindow)
    window._settings = _FakeSettings()
    window.filter_box = _FakeFilterBox()
    window.search_edit = _FakeSearchEdit()
    window.sidebar = _FakeSidebar()
    window.todo_list = _FakeTodoList()
    return window


def test_main_window_new_todo_switches_to_visible_filters(monkeypatch):
    _dialogs, created = _install_fake_dialog(monkeypatch, tag_ids=[])
    window = _make_window()

    window._on_new_todo()

    assert len(created) == 1
    assert window._settings.filter == "active"
    assert window.filter_box.set_indexes == [0]
    assert window._settings.selected_tag_id is None
    assert window.sidebar.selected is None
    assert window.search_edit.cleared is True
    assert window.todo_list.filter == "active"
    assert window.todo_list.tag is None
    assert window.todo_list.search == ""
    assert window.sidebar.refresh_count == 1
    assert window.todo_list.refresh_count >= 1
    assert window.todo_list.selected_todo == 42


def test_main_window_new_todo_for_tag_preselects_and_stays_on_that_tag(monkeypatch):
    dialogs, created = _install_fake_dialog(monkeypatch)
    window = _make_window()

    window._on_new_todo_for_tag(7)

    assert [d.preselected_tag_ids for d in dialogs] == [[7]]
    assert created[0].tag_ids == [7]
    # the new todo is filed under tag 7, so the list stays there instead of
    # jumping back to 全部待办
    assert window._settings.selected_tag_id == 7
    assert window.sidebar.selected == 7
    assert window.todo_list.tag == 7
    # the other filters still relax so the row is actually on screen
    assert window.todo_list.filter == "active"
    assert window.todo_list.search == ""
    assert window.todo_list.selected_todo == 42


def test_main_window_new_todo_for_tag_falls_back_when_user_unticks_the_tag(monkeypatch):
    _dialogs, created = _install_fake_dialog(monkeypatch, tag_ids=[])
    window = _make_window()

    window._on_new_todo_for_tag(7)

    assert created[0].tag_ids == []
    assert window._settings.selected_tag_id is None
    assert window.sidebar.selected is None
    assert window.todo_list.tag is None
    assert window.todo_list.selected_todo == 42
