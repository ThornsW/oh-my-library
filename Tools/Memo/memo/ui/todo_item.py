"""Row widget shown inside the todo list."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QCheckBox,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QWidget,
)

from memo.core.models import (
    PRIORITY_HIGH,
    PRIORITY_LABELS,
    PRIORITY_LOW,
    PRIORITY_NORMAL,
    Todo,
)

_PRIORITY_COLOR = {
    PRIORITY_HIGH: "#E5484D",
    PRIORITY_NORMAL: "#F5A623",
    PRIORITY_LOW: "#8E8E93",
}


class TodoRow(QWidget):
    completedToggled = Signal(int, bool)

    def __init__(self, todo: Todo, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._todo_id = todo.id

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(8)

        self.checkbox = QCheckBox()
        self.checkbox.setChecked(todo.completed)
        self.checkbox.toggled.connect(self._on_toggle)

        self.title = QLabel(todo.title)
        self.title.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        if todo.completed:
            self.title.setStyleSheet("color: #888; text-decoration: line-through;")

        self.due = QLabel(todo.due_date or "")
        self.due.setStyleSheet("color: #888;")
        self.due.setMinimumWidth(80)
        self.due.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        self.dot = QLabel("●")
        color = QColor(_PRIORITY_COLOR.get(todo.priority, "#8E8E93")).name()
        label = PRIORITY_LABELS.get(todo.priority, "")
        self.dot.setStyleSheet(f"color: {color};")
        self.dot.setToolTip(f"优先级:{label}")
        self.dot.setMinimumWidth(16)

        layout.addWidget(self.checkbox)
        layout.addWidget(self.title, 1)
        layout.addWidget(self.due)
        layout.addWidget(self.dot)

    def _on_toggle(self, checked: bool) -> None:
        self.completedToggled.emit(self._todo_id, checked)
