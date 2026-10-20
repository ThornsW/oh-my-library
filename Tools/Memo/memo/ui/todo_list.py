"""Right-pane todo list (no toolbar — toolbar lives in the main window)."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QLabel,
    QListWidget,
    QListWidgetItem,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from memo.core import db
from memo.ui.todo_item import TodoRow


class TodoList(QWidget):
    todoSelected = Signal(object)        # int | None
    todoCompletedToggled = Signal(int, bool)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("listPane")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._header = QLabel("待办")
        self._header.setObjectName("listHeader")
        layout.addWidget(self._header)

        # stacked: real list vs. empty-state placeholder
        self._stack = QStackedWidget()
        self._list = QListWidget()
        self._list.setObjectName("todoRows")
        self._list.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        self._list.setSpacing(2)
        self._list.setUniformItemSizes(False)
        self._list.itemSelectionChanged.connect(self._on_selection_changed)

        self._empty = QLabel("没有待办。\n按 Ctrl+N 新建一个。")
        self._empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty.setStyleSheet("color: #94A3B8; font-size: 13px; padding: 40px;")

        self._stack.addWidget(self._list)
        self._stack.addWidget(self._empty)
        layout.addWidget(self._stack, 1)

        self._filter = "active"
        self._tag_id: int | None = None
        self._search = ""

    # ---- public API ----
    def set_filter(self, value: str) -> None:
        self._filter = value
        self.refresh()

    def set_tag(self, tag_id: int | None) -> None:
        self._tag_id = tag_id
        self.refresh()

    def set_search(self, text: str) -> None:
        self._search = text
        self.refresh()

    def selected_todo_id(self) -> int | None:
        items = self._list.selectedItems()
        if not items:
            return None
        return items[0].data(Qt.ItemDataRole.UserRole)

    def select_todo(self, todo_id: int | None) -> None:
        for i in range(self._list.count()):
            it = self._list.item(i)
            if it.data(Qt.ItemDataRole.UserRole) == todo_id:
                self._list.setCurrentRow(i)
                return

    def refresh(self) -> None:
        previously_selected = self.selected_todo_id()
        self._list.blockSignals(True)
        self._list.clear()
        todos = db.list_todos(filter_=self._filter, tag_id=self._tag_id, search=self._search)
        for todo in todos:
            item = QListWidgetItem()
            item.setData(Qt.ItemDataRole.UserRole, todo.id)
            row = TodoRow(todo)
            row.completedToggled.connect(self.todoCompletedToggled.emit)
            item.setSizeHint(row.sizeHint())
            self._list.addItem(item)
            self._list.setItemWidget(item, row)
        self._list.blockSignals(False)

        self._stack.setCurrentIndex(1 if not todos else 0)

        if previously_selected is not None:
            self.select_todo(previously_selected)
        # selection may not have actually changed; emit current state so detail
        # panel stays consistent
        self.todoSelected.emit(self.selected_todo_id())

    def _on_selection_changed(self) -> None:
        self.todoSelected.emit(self.selected_todo_id())
