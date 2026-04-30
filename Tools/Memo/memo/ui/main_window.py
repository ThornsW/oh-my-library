"""Main window: assembles sidebar / list / detail and owns the toolbar + tray."""

from __future__ import annotations

from PySide6.QtCore import QByteArray, Qt, Signal, Slot
from PySide6.QtGui import QAction, QCloseEvent, QIcon, QKeySequence
from PySide6.QtWidgets import (
    QComboBox,
    QInputDialog,
    QLineEdit,
    QMainWindow,
    QMenu,
    QSizePolicy,
    QSplitter,
    QSystemTrayIcon,
    QToolBar,
    QWidget,
)

import qtawesome as qta

from memo.core import autostart, db
from memo.core.settings import Settings
from memo.ui.settings_dialog import SettingsDialog
from memo.ui.tag_sidebar import TagSidebar
from memo.ui.todo_detail import TodoDetail
from memo.ui.todo_list import TodoList


_FILTER_DATA = [("active", "未完成"), ("all", "全部"), ("done", "已完成")]


class MainWindow(QMainWindow):
    quitRequested = Signal()
    settingsChanged = Signal(Settings)  # emitted when user accepts settings dialog

    def __init__(self, settings: Settings) -> None:
        super().__init__()
        self.setWindowTitle("Memo")
        self.resize(900, 600)
        self.setWindowIcon(self._app_icon())

        self._settings = settings

        # ---- toolbar ----
        toolbar = QToolBar()
        toolbar.setMovable(False)
        self.addToolBar(toolbar)

        self.on_top_action = QAction(qta.icon("fa5s.thumbtack"), "置顶", self)
        self.on_top_action.setCheckable(True)
        self.on_top_action.setChecked(settings.always_on_top)
        self.on_top_action.toggled.connect(self._on_top_toggled)
        toolbar.addAction(self.on_top_action)

        toolbar.addSeparator()

        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("搜索…")
        self.search_edit.setClearButtonEnabled(True)
        self.search_edit.setMaximumWidth(220)
        self.search_edit.textChanged.connect(self._on_search)
        toolbar.addWidget(self.search_edit)

        self.filter_box = QComboBox()
        for value, label in _FILTER_DATA:
            self.filter_box.addItem(label, value)
        idx = self.filter_box.findData(settings.filter)
        self.filter_box.setCurrentIndex(idx if idx >= 0 else 0)
        self.filter_box.currentIndexChanged.connect(self._on_filter)
        toolbar.addWidget(self.filter_box)

        new_action = QAction(qta.icon("fa5s.plus"), "新建待办", self)
        new_action.setShortcut(QKeySequence("Ctrl+N"))
        new_action.triggered.connect(self._on_new_todo)
        toolbar.addAction(new_action)

        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        toolbar.addWidget(spacer)

        settings_action = QAction(qta.icon("fa5s.cog"), "设置", self)
        settings_action.triggered.connect(self._open_settings)
        toolbar.addAction(settings_action)

        # ---- central splitter layout ----
        self.sidebar = TagSidebar()
        self.todo_list = TodoList()
        self.todo_detail = TodoDetail()

        right = QSplitter(Qt.Orientation.Vertical)
        right.addWidget(self.todo_list)
        right.addWidget(self.todo_detail)
        right.setStretchFactor(0, 1)
        right.setStretchFactor(1, 1)
        self._right_splitter = right

        root = QSplitter(Qt.Orientation.Horizontal)
        root.addWidget(self.sidebar)
        root.addWidget(right)
        root.setStretchFactor(0, 0)
        root.setStretchFactor(1, 1)
        root.setSizes([200, 700])
        self._root_splitter = root

        self.setCentralWidget(root)

        # ---- wire signals ----
        self.sidebar.tagSelected.connect(self._on_tag_selected)
        self.todo_list.todoSelected.connect(self._on_todo_selected)
        self.todo_list.todoCompletedToggled.connect(self._on_completed_toggled_in_list)
        self.todo_detail.saved.connect(self._on_detail_saved)
        self.todo_detail.deleted.connect(self._on_detail_deleted)
        self.todo_detail.completedToggled.connect(self._on_completed_toggled_in_detail)

        # ---- tray ----
        self._tray = self._build_tray()
        self._tray.show()

        # ---- restore persisted state ----
        self._restore_geometry()
        self._apply_always_on_top(settings.always_on_top, initial=True)

        # initial selection / refresh
        self.sidebar.select_tag(settings.selected_tag_id)
        self.todo_list.set_filter(settings.filter)
        self.todo_list.set_tag(settings.selected_tag_id)
        self.todo_list.refresh()

    # ---- icon ----
    def _app_icon(self) -> QIcon:
        return qta.icon("fa5s.sticky-note", color="#F5A623")

    # ---- tray ----
    def _build_tray(self) -> QSystemTrayIcon:
        tray = QSystemTrayIcon(self._app_icon(), self)
        menu = QMenu()
        toggle = QAction("显示 / 隐藏", menu)
        toggle.triggered.connect(self.toggle_visible)
        menu.addAction(toggle)
        self._tray_top_action = QAction("置顶", menu)
        self._tray_top_action.setCheckable(True)
        self._tray_top_action.setChecked(self._settings.always_on_top)
        self._tray_top_action.toggled.connect(self.on_top_action.setChecked)
        menu.addAction(self._tray_top_action)
        menu.addSeparator()
        prefs = QAction("设置…", menu)
        prefs.triggered.connect(self._open_settings)
        menu.addAction(prefs)
        menu.addSeparator()
        quit_act = QAction("退出 Memo", menu)
        quit_act.triggered.connect(self.quitRequested.emit)
        menu.addAction(quit_act)
        tray.setContextMenu(menu)
        tray.activated.connect(self._on_tray_activated)
        return tray

    def _on_tray_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self.toggle_visible()

    @Slot()
    def toggle_visible(self) -> None:
        if self.isVisible() and not self.isMinimized():
            self.hide()
        else:
            self.showNormal()
            self.raise_()
            self.activateWindow()

    # ---- always on top ----
    def _on_top_toggled(self, on: bool) -> None:
        self._settings.always_on_top = on
        if hasattr(self, "_tray_top_action"):
            self._tray_top_action.blockSignals(True)
            self._tray_top_action.setChecked(on)
            self._tray_top_action.blockSignals(False)
        self._apply_always_on_top(on)
        self._save_settings()

    def _apply_always_on_top(self, on: bool, *, initial: bool = False) -> None:
        flags = self.windowFlags()
        new_flags = (
            flags | Qt.WindowType.WindowStaysOnTopHint
            if on
            else flags & ~Qt.WindowType.WindowStaysOnTopHint
        )
        if new_flags == flags and not initial:
            return
        self.setWindowFlags(new_flags)
        if not initial:
            self.show()

    # ---- toolbar slots ----
    def _on_search(self, text: str) -> None:
        self.todo_list.set_search(text)

    def _on_filter(self, _idx: int) -> None:
        value = self.filter_box.currentData()
        self._settings.filter = value
        self.todo_list.set_filter(value)
        self._save_settings()

    def _on_new_todo(self) -> None:
        title, ok = QInputDialog.getText(self, "新建待办", "标题:")
        if not ok or not title.strip():
            return
        todo_id = db.create_todo(title.strip())
        self.sidebar.refresh()
        self.todo_list.refresh()
        self.todo_list.select_todo(todo_id)

    def _open_settings(self) -> None:
        dlg = SettingsDialog(self._settings, self)
        if dlg.exec() != dlg.DialogCode.Accepted:
            return
        new_settings = dlg.result_settings()
        # apply autostart at the OS level if it changed
        if new_settings.autostart != self._settings.autostart:
            try:
                autostart.set_enabled(new_settings.autostart)
            except Exception as e:
                from PySide6.QtWidgets import QMessageBox
                QMessageBox.warning(self, "开机自启设置失败", str(e))
                new_settings.autostart = autostart.is_enabled()
        # always-on-top
        if new_settings.always_on_top != self._settings.always_on_top:
            self.on_top_action.setChecked(new_settings.always_on_top)
        self._settings = new_settings
        self._save_settings()
        self.settingsChanged.emit(new_settings)

    # ---- selection / data slots ----
    def _on_tag_selected(self, tag_id: object) -> None:
        self._settings.selected_tag_id = tag_id  # type: ignore[assignment]
        self.todo_list.set_tag(tag_id)  # type: ignore[arg-type]
        self._save_settings()

    def _on_todo_selected(self, todo_id: object) -> None:
        if todo_id is None:
            self.todo_detail.set_todo(None)
            return
        todo = db.get_todo(int(todo_id))
        self.todo_detail.set_todo(todo)

    def _on_completed_toggled_in_list(self, todo_id: int, completed: bool) -> None:
        db.set_completed(todo_id, completed)
        self.sidebar.refresh()
        self.todo_list.refresh()
        # re-load detail if showing this item
        current = self.todo_detail._todo  # type: ignore[attr-defined]
        if current is not None and current.id == todo_id:
            self.todo_detail.set_todo(db.get_todo(todo_id))

    def _on_completed_toggled_in_detail(self, todo_id: int, completed: bool) -> None:
        db.set_completed(todo_id, completed)
        self.sidebar.refresh()
        self.todo_list.refresh()

    def _on_detail_saved(self, todo_id: int) -> None:
        self.sidebar.refresh()
        self.todo_list.refresh()
        # re-select
        self.todo_list.select_todo(todo_id)

    def _on_detail_deleted(self, _todo_id: int) -> None:
        self.todo_detail.set_todo(None)
        self.sidebar.refresh()
        self.todo_list.refresh()

    # ---- geometry persistence ----
    def _restore_geometry(self) -> None:
        geo = self._settings.window_geometry
        if geo:
            self.restoreGeometry(QByteArray.fromBase64(geo.encode("ascii")))
        h_state = self._settings.splitter_horizontal
        v_state = self._settings.splitter_vertical
        if h_state:
            self._root_splitter.restoreState(QByteArray.fromBase64(h_state.encode("ascii")))
        if v_state:
            self._right_splitter.restoreState(QByteArray.fromBase64(v_state.encode("ascii")))

    def _store_geometry(self) -> None:
        self._settings.window_geometry = bytes(self.saveGeometry().toBase64()).decode("ascii")
        self._settings.splitter_horizontal = bytes(
            self._root_splitter.saveState().toBase64()
        ).decode("ascii")
        self._settings.splitter_vertical = bytes(
            self._right_splitter.saveState().toBase64()
        ).decode("ascii")

    def _save_settings(self) -> None:
        try:
            self._store_geometry()
            self._settings.save()
        except Exception:
            pass  # don't kill the app over settings persistence

    # ---- close = hide to tray ----
    def closeEvent(self, event: QCloseEvent) -> None:  # noqa: N802 - Qt API
        self._save_settings()
        event.ignore()
        self.hide()

    def shutdown(self) -> None:
        """Persist state and close tray. Called by app on real quit."""
        self._save_settings()
        self._tray.hide()
