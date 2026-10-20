"""Small always-on-top window that never takes keyboard focus from the terminal."""

from __future__ import annotations

from gi.repository import Gdk, GLib, Gtk

from ..pipeline import Pipeline
from .style import set_status_style
from .talk_button import TalkButton


class FloatingWindow(Gtk.Window):
    def __init__(self, pipeline: Pipeline, show_main, on_closed):
        super().__init__(title="语音输入 悬浮窗")
        self.cfg = pipeline.cfg
        self._on_closed = on_closed
        self.set_name("floating")
        self.set_decorated(False)
        self.set_resizable(False)
        self.set_keep_above(True)
        self.set_accept_focus(False)
        self.set_focus_on_map(False)
        self.set_type_hint(Gdk.WindowTypeHint.UTILITY)
        self.set_skip_taskbar_hint(True)
        self.set_skip_pager_hint(True)

        handle = Gtk.EventBox()
        handle_label = Gtk.Label(label="⠿ 拖动", xalign=0)
        handle_label.get_style_context().add_class("handle")
        handle.add(handle_label)
        handle.connect("button-press-event", self._start_drag)
        handle.connect("realize", lambda w: w.get_window().set_cursor(
            Gdk.Cursor.new_from_name(w.get_display(), "move")))

        main_btn = self._small("主窗口", show_main)
        close_btn = self._small("✕", self.close_floating)
        close_btn.set_tooltip_text("关闭悬浮窗（主窗口里可以重新打开）")

        self.talk = TalkButton(pipeline, compact=True)
        self.talk.set_size_request(200, 96)
        self.status = Gtk.Label(label="空闲")
        self.status.set_line_wrap(True)
        self.status.set_max_width_chars(22)
        self.status.set_justify(Gtk.Justification.CENTER)
        self.status.get_style_context().add_class("status-small")

        top = Gtk.Box(spacing=6)
        top.pack_start(handle, True, True, 0)
        top.pack_start(main_btn, False, False, 0)
        top.pack_start(close_btn, False, False, 0)
        lay = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        lay.set_border_width(8)
        lay.pack_start(top, False, False, 0)
        lay.pack_start(self.talk, False, False, 0)
        lay.pack_start(self.status, False, False, 0)
        self.add(lay)

        self._save_timer = 0
        pos = self.cfg["floating_pos"]
        if isinstance(pos, list) and len(pos) == 2:
            self.move(int(pos[0]), int(pos[1]))
        self.connect("configure-event", self._on_configure)

    @staticmethod
    def _small(text: str, action) -> Gtk.Button:
        b = Gtk.Button(label=text)
        b.set_can_focus(False)
        b.set_size_request(48, 40)
        b.get_style_context().add_class("small")
        b.connect("clicked", lambda _b: action())
        return b

    def _start_drag(self, _w, event) -> bool:
        self.begin_move_drag(event.button, int(event.x_root), int(event.y_root), event.time)
        return True

    def set_status(self, kind: str, text: str) -> None:
        self.status.set_text(text if len(text) <= 40 else text[:40] + "…")
        set_status_style(self.status, kind)

    def _on_configure(self, _w, _event) -> bool:
        if self._save_timer:
            GLib.source_remove(self._save_timer)
        self._save_timer = GLib.timeout_add(600, self._save_pos)
        return False

    def _save_pos(self) -> bool:
        self._save_timer = 0
        x, y = self.get_position()
        if self.cfg["floating_pos"] != [x, y]:
            self.cfg["floating_pos"] = [x, y]
            self.cfg.save()
        return False

    def close_floating(self) -> None:
        self.hide()
        self._on_closed()
