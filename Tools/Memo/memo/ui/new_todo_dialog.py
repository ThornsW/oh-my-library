"""New todo creation dialog and persistence helper."""

from __future__ import annotations

from dataclasses import dataclass, field

from PySide6.QtCore import QDate, Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDateEdit,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGroupBox,
    QLabel,
    QLineEdit,
    QMessageBox,
    QVBoxLayout,
    QWidget,
)

from memo.core import db
from memo.core.models import (
    PRIORITY_HIGH,
    PRIORITY_LABELS,
    PRIORITY_LOW,
    PRIORITY_NORMAL,
)
from memo.ui.subtask_list import SubtaskList


@dataclass
class NewTodoData:
    title: str
    priority: int = PRIORITY_NORMAL
    due_date: str | None = None
    tag_ids: list[int] = field(default_factory=list)
    subtasks: list[tuple[str, bool]] = field(default_factory=list)


class NewTodoDialog(QDialog):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("新建待办")
        self.setModal(True)
        self.resize(420, 480)

        self._tag_checks: dict[int, QCheckBox] = {}

        outer = QVBoxLayout(self)
        outer.setContentsMargins(18, 18, 18, 18)
        outer.setSpacing(14)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        form.setFormAlignment(Qt.AlignmentFlag.AlignTop)
        form.setHorizontalSpacing(10)
        form.setVerticalSpacing(10)

        self.title_edit = QLineEdit()
        self.title_edit.setPlaceholderText("标题…")
        form.addRow("标题", self.title_edit)

        self.priority_box = QComboBox()
        self.priority_box.addItem(PRIORITY_LABELS[PRIORITY_LOW], PRIORITY_LOW)
        self.priority_box.addItem(PRIORITY_LABELS[PRIORITY_NORMAL], PRIORITY_NORMAL)
        self.priority_box.addItem(PRIORITY_LABELS[PRIORITY_HIGH], PRIORITY_HIGH)
        self.priority_box.setCurrentIndex(self.priority_box.findData(PRIORITY_NORMAL))
        form.addRow("优先级", self.priority_box)

        due_row = QWidget()
        due_layout = QVBoxLayout(due_row)
        due_layout.setContentsMargins(0, 0, 0, 0)
        due_layout.setSpacing(6)

        self.due_check = QCheckBox("设置截止日期")
        due_layout.addWidget(self.due_check)

        self.due_edit = QDateEdit(QDate.currentDate())
        self.due_edit.setDisplayFormat("yyyy-MM-dd")
        self.due_edit.setCalendarPopup(True)
        self.due_edit.setEnabled(False)
        due_layout.addWidget(self.due_edit)

        self.due_check.toggled.connect(self.due_edit.setEnabled)
        form.addRow("截止", due_row)

        outer.addLayout(form)

        tag_group = QGroupBox("标签")
        tag_layout = QVBoxLayout(tag_group)
        tag_layout.setContentsMargins(10, 10, 10, 10)
        tag_layout.setSpacing(6)
        tags = db.list_tags_with_counts()
        if tags:
            for tag in tags:
                check = QCheckBox(tag.name)
                self._tag_checks[tag.id] = check
                tag_layout.addWidget(check)
        else:
            empty_label = QLabel("暂无标签")
            empty_label.setEnabled(False)
            tag_layout.addWidget(empty_label)
        outer.addWidget(tag_group)

        subtask_group = QGroupBox("子任务")
        subtask_layout = QVBoxLayout(subtask_group)
        subtask_layout.setContentsMargins(10, 10, 10, 10)
        self.subtasks = SubtaskList()
        subtask_layout.addWidget(self.subtasks)
        outer.addWidget(subtask_group, 1)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("创建")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("取消")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        outer.addWidget(buttons)

    def todo_data(self) -> NewTodoData:
        due_date = (
            self.due_edit.date().toString("yyyy-MM-dd")
            if self.due_check.isChecked()
            else None
        )
        return NewTodoData(
            title=self.title_edit.text().strip(),
            priority=self.priority_box.currentData(),
            due_date=due_date,
            tag_ids=[
                tag_id
                for tag_id, check in self._tag_checks.items()
                if check.isChecked()
            ],
            subtasks=self.subtasks.items(),
        )

    def accept(self) -> None:
        if not self.title_edit.text().strip():
            QMessageBox.warning(self, "创建失败", "标题不能为空。")
            self.title_edit.setFocus()
            return
        super().accept()


def create_todo_from_data(data: NewTodoData) -> int:
    title = data.title.strip()
    if not title:
        raise ValueError("title is required")

    todo_id = db.create_todo(title)
    try:
        db.update_todo(
            todo_id,
            title=title,
            note_md="",
            priority=data.priority,
            due_date=data.due_date,
        )
        db.set_todo_tags(todo_id, data.tag_ids)
        db.set_subtasks(todo_id, data.subtasks)
    except Exception:
        db.delete_todo(todo_id)
        raise
    return todo_id
