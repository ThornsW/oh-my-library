"""Left-hand tag sidebar.

Lists ``全部 / <each tag with active count>`` and lets the user add, rename,
and delete tags. Selection is communicated upstream via the ``tagSelected``
signal — ``None`` means "show everything".
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QInputDialog,
    QListWidget,
    QListWidgetItem,
    QMenu,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from memo.core import db


class TagSidebar(QWidget):
    tagSelected = Signal(object)  # int | None

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        self._list = QListWidget()
        self._list.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        self._list.itemSelectionChanged.connect(self._on_selection_changed)
        self._list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._list.customContextMenuRequested.connect(self._on_context_menu)

        self._add_btn = QPushButton("+ 新建标签")
        self._add_btn.clicked.connect(self._on_add_tag)

        layout.addWidget(self._list, 1)
        layout.addWidget(self._add_btn)

        self.refresh()

    def refresh(self, *, preserve_selection: bool = True) -> None:
        prev = self.selected_tag_id() if preserve_selection else None
        self._list.blockSignals(True)
        self._list.clear()

        all_item = QListWidgetItem(f"全部 ({db.count_active_todos()})")
        all_item.setData(Qt.ItemDataRole.UserRole, None)
        self._list.addItem(all_item)

        for tag in db.list_tags_with_counts():
            item = QListWidgetItem(f"{tag.name} ({tag.count})")
            item.setData(Qt.ItemDataRole.UserRole, tag.id)
            self._list.addItem(item)

        self._list.blockSignals(False)
        self._select_tag(prev)

    def select_tag(self, tag_id: int | None) -> None:
        self._select_tag(tag_id)

    def _select_tag(self, tag_id: int | None) -> None:
        for i in range(self._list.count()):
            it = self._list.item(i)
            if it.data(Qt.ItemDataRole.UserRole) == tag_id:
                self._list.setCurrentRow(i)
                return
        if self._list.count() > 0:
            self._list.setCurrentRow(0)

    def selected_tag_id(self) -> int | None:
        items = self._list.selectedItems()
        if not items:
            return None
        return items[0].data(Qt.ItemDataRole.UserRole)

    # ---- slots ----
    def _on_selection_changed(self) -> None:
        self.tagSelected.emit(self.selected_tag_id())

    def _on_add_tag(self) -> None:
        name, ok = QInputDialog.getText(self, "新建标签", "标签名:")
        if not ok:
            return
        name = name.strip()
        if not name:
            return
        try:
            db.create_tag(name)
        except Exception as e:
            QMessageBox.warning(self, "创建失败", str(e))
            return
        self.refresh()

    def _on_context_menu(self, pos) -> None:
        item = self._list.itemAt(pos)
        if item is None:
            return
        tag_id = item.data(Qt.ItemDataRole.UserRole)
        if tag_id is None:  # 全部 不可改
            return
        menu = QMenu(self)
        rename = QAction("重命名…", menu)
        delete = QAction("删除", menu)
        rename.triggered.connect(lambda: self._rename_tag(tag_id))
        delete.triggered.connect(lambda: self._delete_tag(tag_id))
        menu.addAction(rename)
        menu.addAction(delete)
        menu.exec(self._list.viewport().mapToGlobal(pos))

    def _rename_tag(self, tag_id: int) -> None:
        current = next((t for t in db.list_tags_with_counts() if t.id == tag_id), None)
        if current is None:
            return
        new_name, ok = QInputDialog.getText(self, "重命名标签", "新名称:", text=current.name)
        if not ok or not new_name.strip():
            return
        try:
            db.rename_tag(tag_id, new_name.strip())
        except Exception as e:
            QMessageBox.warning(self, "重命名失败", str(e))
            return
        self.refresh()

    def _delete_tag(self, tag_id: int) -> None:
        reply = QMessageBox.question(
            self,
            "删除标签",
            "确定要删除这个标签吗?(关联的待办不会被删除)",
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        db.delete_tag(tag_id)
        self.refresh()
