"""Detail / edit panel for a single todo."""

from __future__ import annotations

from PySide6.QtCore import QDate, Qt, Signal
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDateEdit,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMenu,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QTabWidget,
    QTextBrowser,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from memo.core import db
from memo.core.models import (
    PRIORITY_HIGH,
    PRIORITY_LABELS,
    PRIORITY_LOW,
    PRIORITY_NORMAL,
    Tag,
    Todo,
)


class TodoDetail(QWidget):
    saved = Signal(int)         # todo_id after save
    deleted = Signal(int)       # todo_id after delete
    completedToggled = Signal(int, bool)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._todo: Todo | None = None
        self._selected_tag_ids: set[int] = set()

        outer = QVBoxLayout(self)
        outer.setContentsMargins(8, 8, 8, 8)

        # ---- header: completed + title
        head = QHBoxLayout()
        self.completed_box = QCheckBox()
        self.completed_box.toggled.connect(self._on_completed_toggled)
        self.title_edit = QLineEdit()
        self.title_edit.setPlaceholderText("标题")
        head.addWidget(self.completed_box)
        head.addWidget(self.title_edit, 1)
        outer.addLayout(head)

        # ---- meta row
        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        # due date: enable checkbox + QDateEdit
        due_row = QHBoxLayout()
        self.due_check = QCheckBox("设定")
        self.due_check.toggled.connect(self._on_due_check_toggled)
        self.due_edit = QDateEdit(QDate.currentDate())
        self.due_edit.setCalendarPopup(True)
        self.due_edit.setDisplayFormat("yyyy-MM-dd")
        self.due_edit.setEnabled(False)
        due_row.addWidget(self.due_check)
        due_row.addWidget(self.due_edit, 1)
        due_widget = QWidget()
        due_widget.setLayout(due_row)
        form.addRow("截止:", due_widget)

        self.priority_box = QComboBox()
        self.priority_box.addItem(PRIORITY_LABELS[PRIORITY_LOW], PRIORITY_LOW)
        self.priority_box.addItem(PRIORITY_LABELS[PRIORITY_NORMAL], PRIORITY_NORMAL)
        self.priority_box.addItem(PRIORITY_LABELS[PRIORITY_HIGH], PRIORITY_HIGH)
        self.priority_box.setCurrentIndex(1)
        form.addRow("优先级:", self.priority_box)

        # tags chip area
        tags_widget = QWidget()
        tags_layout = QHBoxLayout(tags_widget)
        tags_layout.setContentsMargins(0, 0, 0, 0)
        tags_layout.setSpacing(4)
        self._chip_box = QHBoxLayout()
        self._chip_box.setSpacing(4)
        self._tag_btn = QToolButton()
        self._tag_btn.setText("+ 标签")
        self._tag_btn.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self._tag_menu = QMenu(self._tag_btn)
        self._tag_btn.setMenu(self._tag_menu)
        tags_layout.addLayout(self._chip_box)
        tags_layout.addWidget(self._tag_btn)
        tags_layout.addStretch(1)
        form.addRow("标签:", tags_widget)
        outer.addLayout(form)

        # ---- subtasks
        outer.addWidget(QLabel("子任务:"))
        from memo.ui.subtask_list import SubtaskList  # local import: UI tree
        self.subtasks = SubtaskList()
        outer.addWidget(self.subtasks)

        # ---- markdown editor / preview
        self.tabs = QTabWidget()
        self.note_edit = QPlainTextEdit()
        self.note_edit.setPlaceholderText("用 Markdown 写笔记…")
        self.note_preview = QTextBrowser()
        self.note_preview.setOpenExternalLinks(True)
        self.tabs.addTab(self.note_edit, "编辑")
        self.tabs.addTab(self.note_preview, "预览")
        self.tabs.currentChanged.connect(self._on_tab_changed)
        outer.addWidget(self.tabs, 1)

        # ---- buttons
        btns = QHBoxLayout()
        btns.addStretch(1)
        self.delete_btn = QPushButton("删除")
        self.delete_btn.clicked.connect(self._on_delete)
        self.save_btn = QPushButton("保存")
        self.save_btn.setDefault(True)
        self.save_btn.clicked.connect(self._on_save)
        btns.addWidget(self.delete_btn)
        btns.addWidget(self.save_btn)
        outer.addLayout(btns)

        self.set_todo(None)

    # ---- public API ----
    def set_todo(self, todo: Todo | None) -> None:
        self._todo = todo
        if todo is None:
            self._set_enabled(False)
            self.title_edit.clear()
            self.note_edit.clear()
            self.note_preview.clear()
            self.completed_box.setChecked(False)
            self.due_check.setChecked(False)
            self.due_edit.setEnabled(False)
            self.priority_box.setCurrentIndex(1)
            self._selected_tag_ids = set()
            self._rebuild_chips([])
            self._rebuild_tag_menu()
            self.subtasks.set_items([])
            return

        self._set_enabled(True)
        self.title_edit.setText(todo.title)
        self.note_edit.setPlainText(todo.note_md)
        self.completed_box.blockSignals(True)
        self.completed_box.setChecked(todo.completed)
        self.completed_box.blockSignals(False)

        self.due_check.blockSignals(True)
        if todo.due_date:
            self.due_check.setChecked(True)
            self.due_edit.setEnabled(True)
            self.due_edit.setDate(QDate.fromString(todo.due_date, "yyyy-MM-dd"))
        else:
            self.due_check.setChecked(False)
            self.due_edit.setEnabled(False)
        self.due_check.blockSignals(False)

        idx = self.priority_box.findData(todo.priority)
        self.priority_box.setCurrentIndex(idx if idx >= 0 else 1)

        self._selected_tag_ids = {t.id for t in todo.tags}
        self._rebuild_tag_menu()
        self._rebuild_chips(todo.tags)

        self.subtasks.set_items([(s.text, s.completed) for s in todo.subtasks])

        self.tabs.setCurrentIndex(0)

    def refresh_tags_from_db(self) -> None:
        """Pick up newly-created or renamed tags without re-loading the todo."""
        self._rebuild_tag_menu()

    # ---- helpers ----
    def _set_enabled(self, on: bool) -> None:
        for w in (
            self.title_edit, self.completed_box, self.due_check, self.due_edit,
            self.priority_box, self._tag_btn, self.subtasks, self.note_edit,
            self.note_preview, self.save_btn, self.delete_btn, self.tabs,
        ):
            w.setEnabled(on)

    def _rebuild_chips(self, tags: list[Tag]) -> None:
        # clear
        while self._chip_box.count():
            item = self._chip_box.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()
        for tag in tags:
            chip = QPushButton(f"#{tag.name} ✕")
            chip.setFlat(True)
            chip.setStyleSheet(
                "QPushButton{"
                f"background:{tag.color}; color:white; border-radius:8px;"
                "padding:2px 8px;}"
            )
            chip.clicked.connect(lambda _checked=False, tid=tag.id: self._toggle_tag(tid, False))
            self._chip_box.addWidget(chip)

    def _rebuild_tag_menu(self) -> None:
        self._tag_menu.clear()
        all_tags = db.list_tags_with_counts()
        if not all_tags:
            empty = QAction("(暂无标签,先到左侧创建)", self._tag_menu)
            empty.setEnabled(False)
            self._tag_menu.addAction(empty)
            return
        for tag in all_tags:
            act = QAction(tag.name, self._tag_menu)
            act.setCheckable(True)
            act.setChecked(tag.id in self._selected_tag_ids)
            act.toggled.connect(lambda checked, tid=tag.id: self._toggle_tag(tid, checked))
            self._tag_menu.addAction(act)

    def _toggle_tag(self, tag_id: int, on: bool) -> None:
        if on:
            self._selected_tag_ids.add(tag_id)
        else:
            self._selected_tag_ids.discard(tag_id)
        # rebuild chips from cached list of all tags filtered by ids
        all_tags = {t.id: t for t in db.list_tags_with_counts()}
        chips = [all_tags[i] for i in self._selected_tag_ids if i in all_tags]
        self._rebuild_chips(chips)
        self._rebuild_tag_menu()

    def _on_due_check_toggled(self, on: bool) -> None:
        self.due_edit.setEnabled(on)

    def _on_tab_changed(self, idx: int) -> None:
        if idx == 1:  # preview
            self.note_preview.setMarkdown(self.note_edit.toPlainText())

    def _on_completed_toggled(self, checked: bool) -> None:
        if self._todo is None:
            return
        self.completedToggled.emit(self._todo.id, checked)

    def _on_save(self) -> None:
        if self._todo is None:
            return
        title = self.title_edit.text().strip()
        if not title:
            QMessageBox.warning(self, "保存失败", "标题不能为空。")
            return
        due = (
            self.due_edit.date().toString("yyyy-MM-dd")
            if self.due_check.isChecked()
            else None
        )
        priority = self.priority_box.currentData()
        db.update_todo(
            self._todo.id,
            title=title,
            note_md=self.note_edit.toPlainText(),
            priority=priority,
            due_date=due,
        )
        db.set_todo_tags(self._todo.id, list(self._selected_tag_ids))
        db.set_subtasks(self._todo.id, self.subtasks.items())
        self.saved.emit(self._todo.id)

    def _on_delete(self) -> None:
        if self._todo is None:
            return
        reply = QMessageBox.question(self, "删除待办", "确定删除这条待办吗?")
        if reply != QMessageBox.StandardButton.Yes:
            return
        todo_id = self._todo.id
        db.delete_todo(todo_id)
        self.deleted.emit(todo_id)
