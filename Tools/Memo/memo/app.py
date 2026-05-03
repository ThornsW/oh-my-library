"""Application bootstrap: QApplication, DB, settings, hotkey, lifecycle."""

from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import QObject, Qt, Signal
from PySide6.QtWidgets import QApplication, QMessageBox, QSystemTrayIcon

from memo.core import db
from memo.core.hotkey import HotkeyError, HotkeyManager
from memo.core.settings import Settings
from memo.core.singleton import acquire_or_signal_running
from memo.ui.main_window import MainWindow


def _load_stylesheet() -> str:
    """Load Memo's global QSS. Resolves to the bundled path under PyInstaller."""
    qss = Path(__file__).parent / "resources" / "style.qss"
    try:
        return qss.read_text(encoding="utf-8")
    except OSError:
        return ""


class _ThreadBridge(QObject):
    """Cross-thread trampoline: any background-thread callback → Qt signal
    delivered on the GUI thread via QueuedConnection."""

    triggered = Signal()

    def fire(self) -> None:
        self.triggered.emit()


def main() -> int:
    # Single-instance: a second launch wakes the running tray (raising the
    # main window) and exits, instead of spawning a duplicate icon.
    singleton = acquire_or_signal_running()
    if singleton is None:
        return 0

    app = QApplication.instance() or QApplication(sys.argv)
    # closing the main window must NOT quit — we live in the tray.
    app.setQuitOnLastWindowClosed(False)
    app.setApplicationName("Memo")
    app.setOrganizationName("Memo")

    # Force the Fusion base style so our QSS renders consistently across
    # KDE / GNOME / Win11 (native themes paint over child bg, breaking the
    # custom palette). Don't override the system font — fontconfig already
    # picks a CJK-capable family at the right size; touching it usually
    # makes Chinese text render thinner / smaller than the OS expects.
    app.setStyle("Fusion")
    qss = _load_stylesheet()
    if qss:
        app.setStyleSheet(qss)

    if not QSystemTrayIcon.isSystemTrayAvailable():
        QMessageBox.critical(
            None,
            "Memo",
            "当前桌面环境未提供系统托盘,无法运行 Memo。",
        )
        return 1

    db.connect()
    settings = Settings.load()

    window = MainWindow(settings)
    window.show()

    hotkey_bridge = _ThreadBridge()
    hotkey_bridge.triggered.connect(
        window.toggle_visible, type=Qt.ConnectionType.QueuedConnection
    )

    hotkey = HotkeyManager(hotkey_bridge.fire)
    try:
        hotkey.set_hotkey(settings.global_hotkey)
    except HotkeyError as e:
        # Don't kill the app — just inform the user; they can fix it in settings.
        QMessageBox.warning(window, "全局快捷键启动失败", str(e))

    # Wake-from-second-launch: the IPC accept thread posts onto this bridge,
    # which dispatches a queued slot on the GUI thread to surface the window.
    show_bridge = _ThreadBridge()

    def _show_window() -> None:
        if not window.isVisible() or window.isMinimized():
            window.showNormal()
        window.raise_()
        window.activateWindow()

    show_bridge.triggered.connect(_show_window, type=Qt.ConnectionType.QueuedConnection)
    singleton.serve(show_bridge.fire)

    def _on_settings_changed(new: Settings) -> None:
        if new.global_hotkey != hotkey.current:
            try:
                hotkey.set_hotkey(new.global_hotkey)
            except HotkeyError as e:
                QMessageBox.warning(window, "全局快捷键设置失败", str(e))

    window.settingsChanged.connect(_on_settings_changed)

    def _quit() -> None:
        hotkey.stop()
        singleton.stop()
        window.shutdown()
        db.close()
        app.quit()

    window.quitRequested.connect(_quit)
    app.aboutToQuit.connect(lambda: (hotkey.stop(), singleton.stop(), db.close()))

    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
