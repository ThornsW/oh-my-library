"""Right-pane todo list (no toolbar — toolbar lives in the main window)."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QListWidget, QListWidgetItem, QVBoxLayout, QWidget

from memo.core import db
from memo.ui.todo_item import TodoRow


class TodoList(QWidget):
    todoSelected = Signal(object)        # int | None
    todoCompletedToggled = Signal(int, bool)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._list = QListWidget()
        self._list.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        self._list.itemSelectionChanged.connect(self._on_selection_changed)
        layout.addWidget(self._list)

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
        for todo in db.list_todos(filter_=self._filter, tag_id=self._tag_id, search=self._search):
            item = QListWidgetItem()
            item.setData(Qt.ItemDataRole.UserRole, todo.id)
            row = TodoRow(todo)
            row.completedToggled.connect(self.todoCompletedToggled.emit)
            item.setSizeHint(row.sizeHint())
            self._list.addItem(item)
            self._list.setItemWidget(item, row)
        self._list.blockSignals(False)

        if previously_selected is not None:
            self.select_todo(previously_selected)
        # selection may not have actually changed; emit current state so detail
        # panel stays consistent
        self.todoSelected.emit(self.selected_todo_id())

    def _on_selection_changed(self) -> None:
        self.todoSelected.emit(self.selected_todo_id())
