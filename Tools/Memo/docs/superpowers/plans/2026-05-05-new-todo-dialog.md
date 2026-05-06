# New Todo Dialog Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a full "新建待办" dialog that collects title, tags, subtasks, due date, and priority before creating a todo.

**Architecture:** Add a focused `NewTodoDialog` UI module with a small `NewTodoData` dataclass and a testable `create_todo_from_data()` persistence helper. Keep `MainWindow._on_new_todo()` thin: show the dialog, save accepted data, refresh the existing panes, and select the new todo.

**Tech Stack:** Python 3.11, PySide6 6.4 widgets, pytest, SQLite helpers in `memo.core.db`.

---

### Task 1: Add Testable New-Todo Data And Persistence Helper

**Files:**
- Create: `memo/ui/new_todo_dialog.py`
- Create: `tests/test_new_todo_dialog.py`

- [ ] **Step 1: Write the failing persistence-helper test**

Create `tests/test_new_todo_dialog.py` with:

```python
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
```

- [ ] **Step 2: Run the new test and verify it fails**

Run:

```bash
mamba run -n memo pytest tests/test_new_todo_dialog.py::test_create_todo_from_data_persists_all_creation_fields -q
```

Expected: FAIL with `ModuleNotFoundError: No module named 'memo.ui.new_todo_dialog'`.

- [ ] **Step 3: Add minimal data/helper implementation**

Create `memo/ui/new_todo_dialog.py` with:

```python
"""New todo creation dialog and persistence helper."""

from __future__ import annotations

from dataclasses import dataclass, field

from memo.core import db
from memo.core.models import PRIORITY_NORMAL


@dataclass
class NewTodoData:
    title: str
    priority: int = PRIORITY_NORMAL
    due_date: str | None = None
    tag_ids: list[int] = field(default_factory=list)
    subtasks: list[tuple[str, bool]] = field(default_factory=list)


def create_todo_from_data(data: NewTodoData) -> int:
    title = data.title.strip()
    if not title:
        raise ValueError("title is required")

    todo_id = db.create_todo(title)
    db.update_todo(
        todo_id,
        title=title,
        note_md="",
        priority=data.priority,
        due_date=data.due_date,
    )
    db.set_todo_tags(todo_id, data.tag_ids)
    db.set_subtasks(todo_id, data.subtasks)
    return todo_id
```

- [ ] **Step 4: Run the persistence-helper test and verify it passes**

Run:

```bash
mamba run -n memo pytest tests/test_new_todo_dialog.py::test_create_todo_from_data_persists_all_creation_fields -q
```

Expected: PASS.

- [ ] **Step 5: Commit Task 1**

Run:

```bash
git add memo/ui/new_todo_dialog.py tests/test_new_todo_dialog.py
git commit -m "feat: add new todo creation data helper"
```

---

### Task 2: Build The New Todo Dialog UI

**Files:**
- Modify: `memo/ui/new_todo_dialog.py`
- Modify: `tests/test_new_todo_dialog.py`

- [ ] **Step 1: Add failing dialog state tests**

Append these tests to `tests/test_new_todo_dialog.py`:

```python
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
```

- [ ] **Step 2: Run dialog tests and verify they fail**

Run:

```bash
mamba run -n memo pytest tests/test_new_todo_dialog.py -q
```

Expected: one PASS from Task 1 and FAILs mentioning `cannot import name 'NewTodoDialog'` or missing dialog attributes.

- [ ] **Step 3: Implement the dialog**

Replace `memo/ui/new_todo_dialog.py` with:

```python
"""New todo creation dialog and persistence helper."""

from __future__ import annotations

from dataclasses import dataclass, field

from PySide6.QtCore import QDate
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDateEdit,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QVBoxLayout,
    QWidget,
)

from memo.core import db
from memo.core.models import (
    PRIORITY_LABELS,
    PRIORITY_LOW,
    PRIORITY_NORMAL,
    PRIORITY_HIGH,
)
from memo.ui.subtask_list import SubtaskList


@dataclass
class NewTodoData:
    title: str
    priority: int = PRIORITY_NORMAL
    due_date: str | None = None
    tag_ids: list[int] = field(default_factory=list)
    subtasks: list[tuple[str, bool]] = field(default_factory=list)


def create_todo_from_data(data: NewTodoData) -> int:
    title = data.title.strip()
    if not title:
        raise ValueError("title is required")

    todo_id = db.create_todo(title)
    db.update_todo(
        todo_id,
        title=title,
        note_md="",
        priority=data.priority,
        due_date=data.due_date,
    )
    db.set_todo_tags(todo_id, data.tag_ids)
    db.set_subtasks(todo_id, data.subtasks)
    return todo_id


class NewTodoDialog(QDialog):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("新建待办")
        self.setModal(True)
        self.resize(420, 480)

        self._tag_checks: dict[int, QCheckBox] = {}

        root = QVBoxLayout(self)
        root.setContentsMargins(18, 18, 18, 14)
        root.setSpacing(14)

        form = QFormLayout()
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)

        self.title_edit = QLineEdit()
        self.title_edit.setPlaceholderText("标题…")
        form.addRow("标题", self.title_edit)

        self.priority_box = QComboBox()
        for value in (PRIORITY_LOW, PRIORITY_NORMAL, PRIORITY_HIGH):
            self.priority_box.addItem(PRIORITY_LABELS[value], value)
        self.priority_box.setCurrentIndex(self.priority_box.findData(PRIORITY_NORMAL))
        form.addRow("优先级", self.priority_box)

        due_row = QHBoxLayout()
        self.due_check = QCheckBox("截止")
        self.due_check.toggled.connect(self._on_due_toggled)
        due_row.addWidget(self.due_check)
        self.due_edit = QDateEdit(QDate.currentDate())
        self.due_edit.setCalendarPopup(True)
        self.due_edit.setDisplayFormat("yyyy-MM-dd")
        self.due_edit.setEnabled(False)
        due_row.addWidget(self.due_edit, 1)
        form.addRow("截止时间", due_row)

        root.addLayout(form)
        root.addWidget(self._build_tags_group())

        subtasks_group = QGroupBox("子任务")
        subtasks_layout = QVBoxLayout(subtasks_group)
        subtasks_layout.setContentsMargins(10, 10, 10, 10)
        self.subtasks = SubtaskList()
        subtasks_layout.addWidget(self.subtasks)
        root.addWidget(subtasks_group, 1)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("创建")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("取消")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

        self.title_edit.setFocus()

    def todo_data(self) -> NewTodoData:
        return NewTodoData(
            title=self.title_edit.text().strip(),
            priority=self.priority_box.currentData(),
            due_date=(
                self.due_edit.date().toString("yyyy-MM-dd")
                if self.due_check.isChecked()
                else None
            ),
            tag_ids=[
                tag_id
                for tag_id, checkbox in self._tag_checks.items()
                if checkbox.isChecked()
            ],
            subtasks=self.subtasks.items(),
        )

    def accept(self) -> None:
        if not self.title_edit.text().strip():
            QMessageBox.warning(self, "创建失败", "标题不能为空。")
            self.title_edit.setFocus()
            return
        super().accept()

    def _on_due_toggled(self, checked: bool) -> None:
        self.due_edit.setEnabled(checked)

    def _build_tags_group(self) -> QGroupBox:
        group = QGroupBox("标签")
        layout = QVBoxLayout(group)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(6)

        tags = db.list_tags_with_counts()
        if not tags:
            empty = QLabel("暂无标签")
            empty.setEnabled(False)
            layout.addWidget(empty)
            return group

        for tag in tags:
            checkbox = QCheckBox(tag.name)
            self._tag_checks[tag.id] = checkbox
            layout.addWidget(checkbox)
        return group
```

- [ ] **Step 4: Run dialog tests and verify they pass**

Run:

```bash
mamba run -n memo pytest tests/test_new_todo_dialog.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit Task 2**

Run:

```bash
git add memo/ui/new_todo_dialog.py tests/test_new_todo_dialog.py
git commit -m "feat: add new todo dialog"
```

---

### Task 3: Wire The Dialog Into MainWindow

**Files:**
- Modify: `memo/ui/main_window.py`
- Modify: `tests/test_new_todo_dialog.py`

- [ ] **Step 1: Add a failing source-level guard test for the new action path**

Append this test to `tests/test_new_todo_dialog.py`:

```python
def test_main_window_new_action_uses_full_new_todo_dialog():
    from pathlib import Path

    source = Path("memo/ui/main_window.py").read_text(encoding="utf-8")

    assert "QInputDialog" not in source
    assert "NewTodoDialog" in source
    assert "create_todo_from_data" in source
```

- [ ] **Step 2: Run the guard test and verify it fails**

Run:

```bash
mamba run -n memo pytest tests/test_new_todo_dialog.py::test_main_window_new_action_uses_full_new_todo_dialog -q
```

Expected: FAIL because `QInputDialog` is still imported and used.

- [ ] **Step 3: Update MainWindow imports and `_on_new_todo()`**

In `memo/ui/main_window.py`, remove `QInputDialog` from the `PySide6.QtWidgets` import list.

Add this import near the other UI imports:

```python
from memo.ui.new_todo_dialog import NewTodoDialog, create_todo_from_data
```

Replace `_on_new_todo()` with:

```python
    def _on_new_todo(self) -> None:
        dlg = NewTodoDialog(self)
        if dlg.exec() != dlg.DialogCode.Accepted:
            return

        todo_id = create_todo_from_data(dlg.todo_data())
        self.sidebar.refresh()
        self.todo_list.refresh()
        self.todo_list.select_todo(todo_id)
```

- [ ] **Step 4: Run the guard test and dialog tests**

Run:

```bash
mamba run -n memo pytest tests/test_new_todo_dialog.py -q
```

Expected: PASS.

- [ ] **Step 5: Run the full test suite**

Run:

```bash
mamba run -n memo pytest -q
```

Expected: PASS.

- [ ] **Step 6: Commit Task 3**

Run:

```bash
git add memo/ui/main_window.py tests/test_new_todo_dialog.py
git commit -m "feat: use full dialog for new todos"
```

---

### Task 4: Final Verification

**Files:**
- Read: `docs/superpowers/specs/2026-05-05-new-todo-dialog-design.md`
- Read: `memo/ui/new_todo_dialog.py`
- Read: `memo/ui/main_window.py`
- Read: `tests/test_new_todo_dialog.py`

- [ ] **Step 1: Verify the implementation matches the approved spec**

Check these requirements manually:

- "新建" and `Ctrl+N` open `NewTodoDialog`
- dialog fields include title, tags, subtasks, due date, and priority
- empty title is rejected before database writes
- accepted dialog creates todo and persists selected fields
- sidebar/list refresh and new todo is selected
- no database schema change was introduced

- [ ] **Step 2: Run full verification**

Run:

```bash
mamba run -n memo pytest -q
```

Expected: PASS.

- [ ] **Step 3: Check git state**

Run:

```bash
git status --short
```

Expected: clean working tree.
