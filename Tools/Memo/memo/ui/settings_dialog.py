"""Preferences dialog: always-on-top, autostart, global hotkey."""

from __future__ import annotations

from dataclasses import replace

from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QVBoxLayout,
    QWidget,
)

from pynput import keyboard

from memo.core.settings import Settings


HOTKEY_HELP = (
    "格式示例: <ctrl>+<shift>+m,<ctrl>+<alt>+j。\n"
    "支持的修饰键:<ctrl> / <alt> / <shift> / <cmd>。"
)


class SettingsDialog(QDialog):
    def __init__(self, settings: Settings, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("设置")
        self._original = settings

        outer = QVBoxLayout(self)
        form = QFormLayout()

        self.on_top = QCheckBox("窗口始终置顶")
        self.on_top.setChecked(settings.always_on_top)
        form.addRow(self.on_top)

        self.autostart_box = QCheckBox("开机自启")
        self.autostart_box.setChecked(settings.autostart)
        form.addRow(self.autostart_box)

        self.hotkey_edit = QLineEdit(settings.global_hotkey)
        form.addRow("全局快捷键:", self.hotkey_edit)
        help_label = QLabel(HOTKEY_HELP)
        help_label.setWordWrap(True)
        help_label.setStyleSheet("color: #888;")
        form.addRow(help_label)

        outer.addLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)
        outer.addWidget(buttons)

    def result_settings(self) -> Settings:
        return replace(
            self._original,
            always_on_top=self.on_top.isChecked(),
            autostart=self.autostart_box.isChecked(),
            global_hotkey=self.hotkey_edit.text().strip() or self._original.global_hotkey,
        )

    def _accept(self) -> None:
        combo = self.hotkey_edit.text().strip()
        try:
            keyboard.HotKey.parse(combo)
        except ValueError as e:
            QMessageBox.warning(self, "快捷键格式错误", f"{e}\n\n{HOTKEY_HELP}")
            return
        self.accept()
