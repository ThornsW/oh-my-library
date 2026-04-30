"""Application bootstrap: QApplication, DB, settings, hotkey, lifecycle."""

from __future__ import annotations

import sys

from PySide6.QtCore import QObject, Qt, Signal
from PySide6.QtWidgets import QApplication, QMessageBox, QSystemTrayIcon

from memo.core import db
from memo.core.hotkey import HotkeyError, HotkeyManager
from memo.core.settings import Settings
from memo.ui.main_window import MainWindow


class _HotkeyBridge(QObject):
    """Cross-thread trampoline: pynput callback → Qt signal on the GUI thread."""

    triggered = Signal()

    def fire(self) -> None:  # called from pynput's listener thread
        self.triggered.emit()


def main() -> int:
    app = QApplication.instance() or QApplication(sys.argv)
    # closing the main window must NOT quit — we live in the tray.
    app.setQuitOnLastWindowClosed(False)
    app.setApplicationName("Memo")
    app.setOrganizationName("Memo")

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

    bridge = _HotkeyBridge()
    bridge.triggered.connect(window.toggle_visible, type=Qt.ConnectionType.QueuedConnection)

    hotkey = HotkeyManager(bridge.fire)
    try:
        hotkey.set_hotkey(settings.global_hotkey)
    except HotkeyError as e:
        # Don't kill the app — just inform the user; they can fix it in settings.
        QMessageBox.warning(window, "全局快捷键启动失败", str(e))

    def _on_settings_changed(new: Settings) -> None:
        if new.global_hotkey != hotkey.current:
            try:
                hotkey.set_hotkey(new.global_hotkey)
            except HotkeyError as e:
                QMessageBox.warning(window, "全局快捷键设置失败", str(e))

    window.settingsChanged.connect(_on_settings_changed)

    def _quit() -> None:
        hotkey.stop()
        window.shutdown()
        db.close()
        app.quit()

    window.quitRequested.connect(_quit)
    app.aboutToQuit.connect(lambda: (hotkey.stop(), db.close()))

    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
