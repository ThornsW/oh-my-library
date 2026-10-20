"""Main window: big talk button, status, text editor and history. Sized for touch."""

from __future__ import annotations

import threading

from gi.repository import GLib, Gtk, Pango

from .. import __version__
from .. import deliver as dv
from ..errors import StageError
from ..log import log, redact
from ..pipeline import Pipeline, Signal, State, Utterance
from .style import button, hbox, set_status_style, text_of, text_view
from .talk_button import TalkButton

ITEM_COLOR = {
    State.SUBMITTED: "#188038", State.PASTED: "#188038", State.COPIED: "#188038",
    State.PENDING: "#b06000", State.FAILED: "#c5221f", State.EDITOR: "#5f6368",
}
COL_ID, COL_TEXT, COL_COLOR = 0, 1, 2


class MainWindow(Gtk.Window):
    def __init__(self, pipeline: Pipeline, open_settings, toggle_floating):
        super().__init__(title=f"语音输入 Voice-to-Text v{__version__}")
        self.p = pipeline
        self.cfg = pipeline.cfg
        self.status_changed = Signal()  # (kind, text), mirrored by the floating window
        self.set_default_size(560, 820)

        self.status = Gtk.Label(label="空闲")
        self.status.set_line_wrap(True)
        self.status.set_justify(Gtk.Justification.CENTER)
        self.status.get_style_context().add_class("status")
        self.target_label = Gtk.Label(xalign=0)
        self.target_label.set_line_wrap(True)
        self.bind_btn = button("绑定窗口", 44, self.bind_window)

        self.level = Gtk.ProgressBar()
        self.talk = TalkButton(pipeline)
        self.talk.set_size_request(-1, 120)

        self.auto_paste = Gtk.CheckButton(label="自动粘贴")
        self.auto_enter = Gtk.CheckButton(label="自动回车")
        self.on_top = Gtk.CheckButton(label="窗口置顶")
        self.auto_paste.set_active(bool(self.cfg["auto_paste"]))
        self.auto_enter.set_active(bool(self.cfg["auto_enter"]))
        self.on_top.set_active(bool(self.cfg["main_on_top"]))
        self.auto_paste.connect("toggled", lambda b: self._save("auto_paste", b.get_active()))
        self.auto_enter.connect("toggled", lambda b: self._save("auto_enter", b.get_active()))
        self.on_top.connect("toggled", lambda b: self._set_on_top(b.get_active()))

        editor_scroll, self.editor = text_view("", 100)
        editor_hint = Gtk.Label(label="识别结果预览 / 编辑区：关闭「自动粘贴」时识别结果放在这里，改好后点「发送」",
                                xalign=0)
        editor_hint.set_line_wrap(True)
        editor_hint.get_style_context().add_class("hint")

        self.store = Gtk.ListStore(int, str, str)
        self.history = Gtk.TreeView(model=self.store)
        self.history.set_headers_visible(False)
        self.history.get_selection().set_mode(Gtk.SelectionMode.MULTIPLE)
        self.history.get_selection().connect("changed", lambda _s: self._show_selected_detail())
        renderer = Gtk.CellRendererText()
        renderer.props.wrap_mode = Pango.WrapMode.WORD_CHAR
        renderer.props.wrap_width = 480
        self.history.append_column(Gtk.TreeViewColumn("", renderer, text=COL_TEXT, foreground=COL_COLOR))
        self.history.connect("size-allocate", lambda w, a: setattr(renderer.props, "wrap_width", max(200, a.width - 20)))
        history_scroll = Gtk.ScrolledWindow()
        history_scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        history_scroll.set_shadow_type(Gtk.ShadowType.IN)
        history_scroll.add(self.history)

        self.detail = Gtk.Label(xalign=0)
        self.detail.set_line_wrap(True)
        self.detail.set_selectable(True)
        self.detail.get_style_context().add_class("hint")

        lay = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        lay.set_border_width(10)
        lay.pack_start(self.status, False, False, 0)
        row = Gtk.Box(spacing=6)
        row.pack_start(self.target_label, True, True, 0)
        row.pack_start(self.bind_btn, False, False, 0)
        lay.pack_start(row, False, False, 0)
        lay.pack_start(self.level, False, False, 0)
        lay.pack_start(self.talk, False, False, 0)
        row = Gtk.Box(spacing=10)
        for w in (self.auto_paste, self.auto_enter, self.on_top):
            row.pack_start(w, False, False, 0)
        row.pack_end(button("设置", 44, open_settings), False, False, 0)
        row.pack_end(button("悬浮窗", 44, toggle_floating), False, False, 0)
        lay.pack_start(row, False, False, 0)
        lay.pack_start(editor_hint, False, False, 0)
        lay.pack_start(editor_scroll, False, False, 0)
        lay.pack_start(hbox(button("发送", 52, self.send_editor),
                            button("仅复制", 52, lambda: self._copy(text_of(self.editor))),
                            button("↵ 回车", 52, self.p.press_enter),
                            button("清空", 52, lambda: self.editor.get_buffer().set_text("")),
                            homogeneous=True), False, False, 0)
        lay.pack_start(Gtk.Label(label="历史（失败或被拦下的文字会保留在这里）", xalign=0), False, False, 0)
        lay.pack_start(history_scroll, True, True, 0)
        lay.pack_start(hbox(button("发送选中", 44, self.send_selected),
                            button("复制", 44, self.copy_selected),
                            button("放入编辑框", 44, self.edit_selected),
                            button("重新识别", 44, self.retry_selected),
                            button("删除", 44, self.delete_selected),
                            homogeneous=True), False, False, 0)
        lay.pack_start(self.detail, False, False, 0)
        self.add(lay)

        self._rows: dict[int, Gtk.TreeIter] = {}
        self._last_notice = ("info", "空闲")
        self._editor_timer = 0
        p = pipeline
        p.item_changed.connect(self._on_item)
        p.notice.connect(self._on_notice)
        p.level.connect(self._on_level)
        p.recording_changed.connect(self._on_recording)
        p.editor_append.connect(self._append_editor)
        self.editor.get_buffer().connect("changed", lambda _b: self._schedule_editor_save())

        GLib.timeout_add(200, self._on_tick)
        GLib.timeout_add(600, self._poll_active)
        self.set_keep_above(bool(self.cfg["main_on_top"]))
        self.refresh_target()
        self.set_status("info", "空闲")

    # ---------- status ----------

    def set_status(self, kind: str, text: str) -> None:
        self.status.set_text(text)
        set_status_style(self.status, kind)
        self.status_changed.emit(kind, text)

    def _on_notice(self, kind: str, text: str) -> None:
        self._last_notice = (kind, text)
        if not self.p.recording:
            self.set_status(kind, text)

    def _on_recording(self, on: bool) -> None:
        if not on:
            self.level.set_fraction(0)
            self.set_status(*self._last_notice)

    def _on_tick(self) -> bool:
        if self.p.recording and self.p.recorder:
            hint = "再点一下结束" if self.p.toggle_mode else "松开结束"
            self.set_status("rec", f"● 录音中 {self.p.recorder.elapsed:.1f}s · {hint}")
        return True

    def _on_level(self, db: float) -> None:
        self.level.set_fraction(max(0.0, min(1.0, (db + 60) / 60)))

    # ---------- target window ----------

    def refresh_target(self) -> None:
        ctx = self.target_label.get_style_context()
        ctx.remove_class("error-text")
        if self.cfg["target_mode"] == "follow":
            title = dv.window_title(self.p.last_external) if self.p.last_external else ""
            self.target_label.set_text(f"目标（跟随最后使用的窗口）：{title or '还没有'}")
            self.bind_btn.hide()
            return
        self.bind_btn.show()
        wid = self.cfg["target_window"]
        if wid and dv.window_exists(wid):
            self.target_label.set_text(f"目标窗口：{dv.window_title(wid) or wid}")
        else:
            self.target_label.set_text("目标窗口：未绑定（点右边「绑定窗口」，再点一下终端）")
            ctx.add_class("error-text")

    def _poll_active(self) -> bool:
        if self.cfg["target_mode"] == "follow":
            before = self.p.last_external
            self.p.poll_active_window()
            if self.p.last_external != before:
                self.refresh_target()
        return True

    def bind_window(self) -> None:
        self.set_status("busy", "请点一下要输入文字的终端窗口（30 秒内）")
        self.bind_btn.set_sensitive(False)

        def job():
            try:
                wid, err = dv.select_window(), None
            except StageError as e:
                wid, err = None, e
            GLib.idle_add(lambda: self._on_bound(wid, err) or False)

        threading.Thread(target=job, daemon=True).start()

    def _on_bound(self, wid, err) -> None:
        self.bind_btn.set_sensitive(True)
        if err or not wid:
            self.set_status("error", str(err or "没有选中窗口"))
            return
        if dv.is_own_window(wid, self.p.own_windows()):
            self.set_status("warn", "不能绑定本程序自己的窗口，请点终端窗口")
            return
        self.cfg["target_window"] = wid
        self.cfg["target_title"] = dv.window_title(wid)
        self.cfg.save()
        log.info("target: bound %s %s", wid, self.cfg["target_title"])
        self.refresh_target()
        self.set_status("ok", f"已绑定：{self.cfg['target_title']}")

    # ---------- editor & history ----------

    def _schedule_editor_save(self) -> None:
        if self._editor_timer:
            GLib.source_remove(self._editor_timer)

        def save():
            self._editor_timer = 0
            self.p.save_editor(text_of(self.editor))
            return False

        self._editor_timer = GLib.timeout_add(800, save)

    def _append_editor(self, text: str) -> None:
        cur = text_of(self.editor).rstrip()
        self.editor.get_buffer().set_text(f"{cur} {text}".strip() if cur else text)

    def set_editor_text(self, text: str) -> None:
        self.editor.get_buffer().set_text(text)

    def send_editor(self) -> None:
        if self.p.send_text(text_of(self.editor)):
            self.editor.get_buffer().set_text("")

    def _copy(self, text: str) -> None:
        if text.strip():
            self.p.copy(text.strip())

    def _selected(self) -> list[Utterance]:
        model, paths = self.history.get_selection().get_selected_rows()
        ids = sorted(model[path][COL_ID] for path in paths)
        return [self.p.items[i] for i in ids if i in self.p.items]

    def send_selected(self) -> None:
        for u in self._selected():
            self.p.send(u.id)

    def copy_selected(self) -> None:
        self._copy(" ".join(u.text for u in self._selected() if u.text))

    def edit_selected(self) -> None:
        for u in self._selected():
            if u.text:
                self._append_editor(u.text)

    def retry_selected(self) -> None:
        for u in self._selected():
            self.p.retry_recognition(u.id)

    def delete_selected(self) -> None:
        for u in self._selected():
            self.p.remove(u.id)
            if u.id not in self.p.items:
                it = self._rows.pop(u.id, None)
                if it is not None:
                    self.store.remove(it)

    def _on_item(self, u: Utterance) -> None:
        body = u.text or (u.error.reason if u.error else "")
        extra = f"  ⚠ {u.error.reason}" if (u.error and u.text) else ""
        note = f"  （{u.note}）" if u.note else ""
        row = [u.id, f"#{u.id} [{u.state}] {body}{extra}{note}", ITEM_COLOR.get(u.state, "#202124")]
        it = self._rows.get(u.id)
        if it is None:
            self._rows[u.id] = self.store.insert(0, row)
        else:
            self.store.set(it, [COL_TEXT, COL_COLOR], row[1:])
        self._show_selected_detail()

    def _show_selected_detail(self) -> None:
        sel = self._selected()
        if len(sel) == 1 and sel[0].error:
            e = sel[0].error
            self.detail.set_text(redact(f"{e}\n{e.detail}".strip()))
        else:
            self.detail.set_text("")

    # ---------- misc ----------

    def _save(self, key: str, value) -> None:
        self.cfg[key] = value
        self.cfg.save()

    def _set_on_top(self, on: bool) -> None:
        self._save("main_on_top", on)
        self.set_keep_above(on)
