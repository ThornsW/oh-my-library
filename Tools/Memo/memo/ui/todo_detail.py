"""Detail / edit panel for a single todo."""

from __future__ import annotations

from PySide6.QtCore import QDate, Qt, Signal
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDateEdit,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMenu,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QStackedWidget,
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
from memo.ui._color import darken, hex_to_rgba


class TodoDetail(QWidget):
    saved = Signal(int)         # todo_id after save
    deleted = Signal(int)       # todo_id after delete
    completedToggled = Signal(int, bool)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("detailPane")
        self._todo: Todo | None = None
        self._selected_tag_ids: set[int] = set()

        # use a stack so when no todo is selected we show a friendly placeholder
        # rather than a half-disabled blank form.
        self._stack = QStackedWidget(self)

        # ---- empty placeholder ----
        empty = QLabel("← 在左侧选择一条待办,或按 Ctrl+N 新建。")
        empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty.setStyleSheet("color: #94A3B8; font-size: 13px;")
        self._stack.addWidget(empty)

        # ---- editor pane ----
        editor = QWidget()
        outer = QVBoxLayout(editor)
        outer.setContentsMargins(32, 28, 32, 22)
        outer.setSpacing(15)

        # header: completed checkbox + big title input
        head = QHBoxLayout()
        head.setSpacing(12)
        self.completed_box = QCheckBox()
        self.completed_box.toggled.connect(self._on_completed_toggled)
        head.addWidget(self.completed_box, 0, Qt.AlignmentFlag.AlignVCenter)

        self.title_edit = QLineEdit()
        self.title_edit.setPlaceholderText("标题…")
        self.title_edit.setStyleSheet(
            "QLineEdit{font-size:21px; font-weight:600; color:#0F172A;"
            "background:transparent; border:none; padding:5px 0;}"
            "QLineEdit:focus{border-bottom:1px solid #2563EB;}"
        )
        head.addWidget(self.title_edit, 1)
        outer.addLayout(head)

        # meta row: due / priority / tags — all on one line, label-free
        meta = QHBoxLayout()
        meta.setSpacing(8)

        # due date controls
        self.due_check = QCheckBox("截止")
        self.due_check.toggled.connect(self._on_due_check_toggled)
        meta.addWidget(self.due_check)

        self.due_edit = QDateEdit(QDate.currentDate())
        self.due_edit.setCalendarPopup(True)
        self.due_edit.setDisplayFormat("yyyy-MM-dd")
        self.due_edit.setEnabled(False)
        self.due_edit.setMaximumWidth(140)
        meta.addWidget(self.due_edit)

        meta.addSpacing(12)

        prio_lbl = QLabel("优先级")
        prio_lbl.setProperty("class", "muted")
        meta.addWidget(prio_lbl)
        self.priority_box = QComboBox()
        self.priority_box.addItem(PRIORITY_LABELS[PRIORITY_LOW], PRIORITY_LOW)
        self.priority_box.addItem(PRIORITY_LABELS[PRIORITY_NORMAL], PRIORITY_NORMAL)
        self.priority_box.addItem(PRIORITY_LABELS[PRIORITY_HIGH], PRIORITY_HIGH)
        self.priority_box.setCurrentIndex(1)
        self.priority_box.setMaximumWidth(90)
        meta.addWidget(self.priority_box)

        meta.addStretch(1)
        outer.addLayout(meta)

        # tags row: chips + "+" button
        tags_row = QHBoxLayout()
        tags_row.setSpacing(6)
        tags_lbl = QLabel("标签")
        tags_lbl.setProperty("class", "muted")
        tags_row.addWidget(tags_lbl)
        self._chip_box = QHBoxLayout()
        self._chip_box.setSpacing(6)
        tags_row.addLayout(self._chip_box)
        self._tag_btn = QToolButton()
        self._tag_btn.setText("+")
        self._tag_btn.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self._tag_menu = QMenu(self._tag_btn)
        self._tag_btn.setMenu(self._tag_menu)
        tags_row.addWidget(self._tag_btn)
        tags_row.addStretch(1)
        outer.addLayout(tags_row)

        outer.addSpacing(4)

        # subtasks section
        sub_lbl = QLabel("子任务")
        sub_lbl.setProperty("class", "muted")
        outer.addWidget(sub_lbl)

        from memo.ui.subtask_list import SubtaskList  # avoid circular import
        self.subtasks = SubtaskList()
        outer.addWidget(self.subtasks)

        outer.addSpacing(4)

        # markdown editor / preview
        notes_lbl = QLabel("笔记")
        notes_lbl.setProperty("class", "muted")
        outer.addWidget(notes_lbl)

        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        self.note_edit = QPlainTextEdit()
        self.note_edit.setPlaceholderText("用 Markdown 写笔记…")
        self.note_preview = QTextBrowser()
        self.note_preview.setOpenExternalLinks(True)
        self.tabs.addTab(self.note_edit, "编辑")
        self.tabs.addTab(self.note_preview, "预览")
        self.tabs.currentChanged.connect(self._on_tab_changed)
        outer.addWidget(self.tabs, 1)

        # buttons
        btns = QHBoxLayout()
        btns.addStretch(1)
        self.delete_btn = QPushButton("删除")
        self.delete_btn.setProperty("class", "danger")
        self.delete_btn.clicked.connect(self._on_delete)
        self.save_btn = QPushButton("保存")
        self.save_btn.setProperty("class", "primary")
        self.save_btn.setDefault(True)
        self.save_btn.clicked.connect(self._on_save)
        btns.addWidget(self.delete_btn)
        btns.addWidget(self.save_btn)
        outer.addLayout(btns)

        self._stack.addWidget(editor)

        # outer widget root
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.addWidget(self._stack)

        self.set_todo(None)

    # ---- public API ----
    def set_todo(self, todo: Todo | None) -> None:
        self._todo = todo
        if todo is None:
            self._stack.setCurrentIndex(0)  # placeholder
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

        self._stack.setCurrentIndex(1)  # editor
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

    # ---- helpers ----
    def _rebuild_chips(self, tags: list[Tag]) -> None:
        while self._chip_box.count():
            item = self._chip_box.takeAt(0)
            w = item.widget()
            if w is not None:
                w.setParent(None)
                w.deleteLater()
        for tag in tags:
            chip = QPushButton(f"{tag.name}  ✕")
            chip.setCursor(Qt.CursorShape.PointingHandCursor)
            text_col = darken(tag.color, 0.45)
            bg_col = hex_to_rgba(tag.color, 0.20)
            hover_bg = hex_to_rgba(tag.color, 0.32)
            chip.setStyleSheet(
                f"QPushButton{{color:{text_col}; background:{bg_col};"
                "border-radius:10px; border:none;"
                "padding:4px 12px; font-size:12px; font-weight:600;"
                "min-height:18px;}"
                f"QPushButton:hover{{background:{hover_bg};}}"
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
