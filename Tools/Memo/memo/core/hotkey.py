"""Global hotkey support, wrapping ``pynput.keyboard.GlobalHotKeys``.

The pynput listener runs on a background thread; the registered callback
therefore fires off the Qt main thread. Callers should marshal back to the GUI
thread (see ``memo.app`` for the Qt-signal trampoline).
"""

from __future__ import annotations

from typing import Callable


class HotkeyError(RuntimeError):
    """Raised when a hotkey string cannot be parsed or the listener fails."""


def _load_keyboard():
    try:
        from pynput import keyboard
    except ImportError as e:  # pragma: no cover - depends on display backend
        raise HotkeyError(f"全局快捷键后端不可用: {e}") from e
    return keyboard


class HotkeyManager:
    """Owns a single ``GlobalHotKeys`` listener and lets us swap the binding."""

    def __init__(self, callback: Callable[[], None]) -> None:
        self._callback = callback
        self._listener: object | None = None
        self._combo: str | None = None

    @property
    def current(self) -> str | None:
        return self._combo

    def set_hotkey(self, combo: str) -> None:
        """Parse and start listening on ``combo``. Replaces any previous binding."""
        keyboard = _load_keyboard()
        try:
            keyboard.HotKey.parse(combo)
        except ValueError as e:
            raise HotkeyError(f"无法解析的快捷键: {combo!r} ({e})") from e

        self.stop()
        listener = keyboard.GlobalHotKeys({combo: self._callback})
        try:
            listener.start()
        except Exception as e:  # pragma: no cover - platform/permissions
            raise HotkeyError(f"启动全局快捷键监听失败: {e}") from e
        self._listener = listener
        self._combo = combo

    def stop(self) -> None:
        if self._listener is not None:
            try:
                self._listener.stop()
            except Exception:
                pass
            self._listener = None
            self._combo = None
