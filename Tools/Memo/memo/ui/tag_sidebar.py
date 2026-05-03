"""Left-hand tag sidebar.

Layout:
    ┌────────────────────────┐
    │  全部待办  · N         │   <- "system" view, NOT a tag
    │                        │
    │  标签                  │   <- header
    │  ●  工作  ·  3         │
    │  ●  个人  ·  2         │
    │                        │
    │  + 新建标签            │
    └────────────────────────┘

Selection is mutually exclusive between the "全部待办" navigation button at
the top and the tag list below. The ``tagSelected`` signal carries:
    - ``None`` when 全部待办 is active (show all)
    - ``int`` when a specific tag is selected
"""

from __future__ import annotations

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QAction, QColor, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import (
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMenu,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from memo.core import db


def _color_swatch(color_hex: str | None) -> QIcon:
    """Tiny filled circle used as the row icon."""
    pm = QPixmap(10, 10)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor(color_hex or "#9CA3AF"))
    p.drawEllipse(0, 0, 10, 10)
    p.end()
    return QIcon(pm)


class TagSidebar(QWidget):
    tagSelected = Signal(object)  # int | None

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("sidebarPane")
        self.setMinimumWidth(210)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(4)

        # ---- "全部待办" nav button (NOT in the tag list) ----
        self._all_btn = QPushButton("全部待办")
        self._all_btn.setProperty("class", "navrow")
        self._all_btn.setCheckable(True)
        self._all_btn.setChecked(True)
        self._all_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._all_btn.clicked.connect(self._on_all_clicked)
        layout.addWidget(self._all_btn)

        layout.addSpacing(12)

        header = QLabel("标签")
        header.setObjectName("sidebarHeader")
        layout.addWidget(header)

        self._list = QListWidget()
        self._list.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        self._list.setFrameShape(QListWidget.Shape.NoFrame)
        self._list.setIconSize(QSize(10, 10))
        self._list.itemSelectionChanged.connect(self._on_tag_selection_changed)
        self._list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._list.customContextMenuRequested.connect(self._on_context_menu)
        layout.addWidget(self._list, 1)

        self._add_btn = QPushButton("+ 新建标签")
        self._add_btn.setProperty("class", "ghost")
        self._add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._add_btn.clicked.connect(self._on_add_tag)
        layout.addWidget(self._add_btn)

        self._selected_tag_id: int | None = None
        self.refresh()

    # ---- public API ----
    def select_tag(self, tag_id: int | None) -> None:
        self._selected_tag_id = tag_id
        self._sync_selection()

    def selected_tag_id(self) -> int | None:
        return self._selected_tag_id

    def refresh(self, *, preserve_selection: bool = True) -> None:
        prev = self._selected_tag_id if preserve_selection else None
        self._all_btn.setText(f"全部待办  ·  {db.count_active_todos()}")

        self._list.blockSignals(True)
        self._list.clear()
        for tag in db.list_tags_with_counts():
            item = QListWidgetItem(_color_swatch(tag.color), f"{tag.name}  ·  {tag.count}")
            item.setData(Qt.ItemDataRole.UserRole, tag.id)
            self._list.addItem(item)
        self._list.blockSignals(False)

        # restore visual state
        self._selected_tag_id = prev
        self._sync_selection()

    # ---- internal ----
    def _sync_selection(self) -> None:
        """Reflect ``self._selected_tag_id`` in the widgets without firing
        the selection signal twice."""
        self._all_btn.blockSignals(True)
        self._list.blockSignals(True)
        self._all_btn.setChecked(self._selected_tag_id is None)
        if self._selected_tag_id is None:
            self._list.clearSelection()
        else:
            for i in range(self._list.count()):
                it = self._list.item(i)
                if it.data(Qt.ItemDataRole.UserRole) == self._selected_tag_id:
                    self._list.setCurrentRow(i)
                    break
            else:
                # selected tag was removed; fall back to "全部"
                self._selected_tag_id = None
                self._all_btn.setChecked(True)
        self._all_btn.blockSignals(False)
        self._list.blockSignals(False)

    # ---- slots ----
    def _on_all_clicked(self) -> None:
        # checkable button with no group: clicking when already checked would
        # toggle it off. Force back on so we always have a clear active view.
        self._all_btn.blockSignals(True)
        self._all_btn.setChecked(True)
        self._all_btn.blockSignals(False)
        if self._selected_tag_id is None:
            return
        self._selected_tag_id = None
        self._list.clearSelection()
        self.tagSelected.emit(None)

    def _on_tag_selection_changed(self) -> None:
        items = self._list.selectedItems()
        if not items:
            return
        tag_id = items[0].data(Qt.ItemDataRole.UserRole)
        if tag_id == self._selected_tag_id:
            return
        self._selected_tag_id = tag_id
        self._all_btn.blockSignals(True)
        self._all_btn.setChecked(False)
        self._all_btn.blockSignals(False)
        self.tagSelected.emit(tag_id)

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
        if self._selected_tag_id == tag_id:
            self._selected_tag_id = None
            self.tagSelected.emit(None)
        self.refresh()
