"""Editable subtask checklist."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class _SubtaskRow(QWidget):
    changed = Signal()
    deleted = Signal(object)  # emits self

    def __init__(self, text: str = "", completed: bool = False, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.checkbox = QCheckBox()
        self.checkbox.setChecked(completed)
        self.checkbox.toggled.connect(self.changed.emit)

        self.edit = QLineEdit(text)
        self.edit.setPlaceholderText("子任务…")
        self.edit.editingFinished.connect(self.changed.emit)

        self.del_btn = QPushButton("✕")
        self.del_btn.setFixedWidth(28)
        self.del_btn.clicked.connect(lambda: self.deleted.emit(self))

        layout.addWidget(self.checkbox)
        layout.addWidget(self.edit, 1)
        layout.addWidget(self.del_btn)


class SubtaskList(QWidget):
    changed = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(2)

        self._rows_box = QVBoxLayout()
        self._rows_box.setSpacing(2)
        outer.addLayout(self._rows_box)

        self._add_btn = QPushButton("+ 添加子任务")
        self._add_btn.clicked.connect(self._on_add)
        outer.addWidget(self._add_btn)

        self._rows: list[_SubtaskRow] = []

    def set_items(self, items: list[tuple[str, bool]]) -> None:
        for row in list(self._rows):
            self._rows_box.removeWidget(row)
            row.deleteLater()
        self._rows.clear()
        for text, completed in items:
            self._append_row(text, completed)

    def items(self) -> list[tuple[str, bool]]:
        return [
            (r.edit.text().strip(), r.checkbox.isChecked())
            for r in self._rows
            if r.edit.text().strip()
        ]

    def _append_row(self, text: str = "", completed: bool = False) -> None:
        row = _SubtaskRow(text, completed)
        row.changed.connect(self.changed.emit)
        row.deleted.connect(self._remove_row)
        self._rows_box.addWidget(row)
        self._rows.append(row)

    def _on_add(self) -> None:
        self._append_row()
        self._rows[-1].edit.setFocus()

    def _remove_row(self, row: _SubtaskRow) -> None:
        if row in self._rows:
            self._rows.remove(row)
            self._rows_box.removeWidget(row)
            row.deleteLater()
            self.changed.emit()
