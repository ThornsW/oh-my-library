"""The talk button: hold to talk, or tap once to start and tap again to stop.

Remote-desktop apps sometimes turn a long touch into a quick right-click, so a
short press of any mouse button falls back to tap-to-toggle instead of failing.
"""

from __future__ import annotations

import time

from gi.repository import Gdk, Gtk

from ..pipeline import Pipeline

HOLD_SECONDS = 0.4


class TalkButton(Gtk.Button):
    def __init__(self, pipeline: Pipeline, compact: bool = False):
        super().__init__()
        self.pipeline = pipeline
        self.compact = compact
        self._t0 = 0.0
        self._holding = False
        self._swallow_release = False
        self.label = Gtk.Label()
        self.label.set_justify(Gtk.Justification.CENTER)
        self.add(self.label)
        self.set_can_focus(False)
        self.get_style_context().add_class("talk")
        self.connect("button-press-event", self._on_press)
        self.connect("button-release-event", self._on_release)
        pipeline.recording_changed.connect(lambda _on: self.refresh())
        self.refresh()

    def refresh(self) -> None:
        p = self.pipeline
        if not p.recording:
            text = "按住说话" if self.compact else "按住说话\n（或点一下开始，再点一下结束）"
        elif p.toggle_mode:
            text = "再点一下\n结束" if self.compact else "录音中…\n再点一下结束"
        else:
            text = "松开结束" if self.compact else "录音中…\n松开结束"
        self.label.set_text(text)
        ctx = self.get_style_context()
        ctx.remove_class("talk-idle")
        ctx.remove_class("talk-rec")
        ctx.add_class("talk-rec" if p.recording else "talk-idle")

    def _on_press(self, _w, event) -> bool:
        # GTK also sends 2BUTTON/3BUTTON events after a fast second click; the
        # plain BUTTON_PRESS for that click has already arrived, so skip them.
        if event.type != Gdk.EventType.BUTTON_PRESS:
            return True
        p = self.pipeline
        if p.recording:
            if p.toggle_mode:
                self._swallow_release = True
                p.stop_recording()
            return True
        self._t0 = time.monotonic()
        self._holding = True
        p.start_recording()
        return True

    def _on_release(self, _w, _event) -> bool:
        p = self.pipeline
        if self._swallow_release:
            self._swallow_release = False
            return True
        if not self._holding:
            return True
        self._holding = False
        if not p.recording:
            return True
        if time.monotonic() - self._t0 >= HOLD_SECONDS:
            p.stop_recording()
        else:
            p.toggle_mode = True
            p.recording_changed.emit(True)  # let every talk button show "tap to stop"
        return True
