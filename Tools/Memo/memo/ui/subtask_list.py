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
    deleted = Signal(object)  # emits self

    def __init__(self, text: str = "", completed: bool = False, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(2, 1, 2, 1)
        layout.setSpacing(8)

        self.checkbox = QCheckBox()
        self.checkbox.setChecked(completed)
        layout.addWidget(self.checkbox)

        self.edit = QLineEdit(text)
        self.edit.setPlaceholderText("子任务…")
        # blends into the surface; only shows a border on focus.
        self.edit.setStyleSheet(
            "QLineEdit{background:transparent; border:1px solid transparent;"
            "border-radius:4px; padding:4px 6px;}"
            "QLineEdit:hover{background:#F1F5F9;}"
            "QLineEdit:focus{background:#FFFFFF; border-color:#2563EB;}"
        )
        layout.addWidget(self.edit, 1)

        self.del_btn = QPushButton("×")
        self.del_btn.setFixedSize(22, 22)
        self.del_btn.setProperty("class", "ghost")
        self.del_btn.setStyleSheet(
            "QPushButton{color:#94A3B8; border:none; border-radius:11px;"
            "background:transparent; font-size:15px; font-weight:600;"
            "padding:0; min-width:22px; min-height:22px;}"
            "QPushButton:hover{color:#DC2626; background:#FEF2F2;}"
        )
        self.del_btn.clicked.connect(lambda: self.deleted.emit(self))
        layout.addWidget(self.del_btn)


class SubtaskList(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        self._rows_box = QVBoxLayout()
        self._rows_box.setContentsMargins(0, 0, 0, 0)
        self._rows_box.setSpacing(2)
        outer.addLayout(self._rows_box)

        self._add_btn = QPushButton("+ 添加子任务")
        self._add_btn.setProperty("class", "ghost")
        self._add_btn.setStyleSheet(
            "QPushButton{color:#64748B; text-align:left; padding:6px 4px;"
            "border:none; background:transparent;}"
            "QPushButton:hover{color:#2563EB;}"
        )
        self._add_btn.clicked.connect(self._on_add)
        outer.addWidget(self._add_btn)

        self._rows: list[_SubtaskRow] = []

    def set_items(self, items: list[tuple[str, bool]]) -> None:
        while self._rows:
            row = self._rows.pop()
            self._rows_box.removeWidget(row)
            # setParent(None) detaches the widget *immediately*, so it stops
            # painting before the next event-loop tick. Without this, the old
            # rows linger as ghost children of self until deleteLater fires
            # and the user sees stale subtasks bleed across todos.
            row.setParent(None)
            row.deleteLater()
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
            row.setParent(None)
            row.deleteLater()
