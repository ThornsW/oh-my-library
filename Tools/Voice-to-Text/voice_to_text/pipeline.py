"""Recording -> recognition -> delivery, one utterance at a time and in order.

Rules that keep text from being duplicated or lost:
- Every utterance has an id; automatic delivery happens at most once per id.
- Recognition may run in parallel, but delivery strictly follows recording order.
- Anything that could not be delivered stays in the list as PENDING (and in
  cache/pending.json across restarts) until the user sends, copies or deletes it.
"""

from __future__ import annotations

import json
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Callable

from gi.repository import GLib

from . import deliver as dv
from .asr import transcribe
from .audio import Recorder
from .config import Config
from .errors import ForegroundChanged, Stage, StageError
from .log import log, redact
from .postprocess import clean


class Signal:
    """Minimal observer list; emit() runs callbacks on the caller's thread."""

    def __init__(self):
        self._fns: list[Callable] = []

    def connect(self, fn: Callable) -> None:
        self._fns.append(fn)

    def emit(self, *args) -> None:
        for fn in list(self._fns):
            fn(*args)


def on_main(fn: Callable, *args) -> None:
    """Run fn(*args) on the GLib/GTK main thread (safe to call from any thread)."""
    def run():
        fn(*args)
        return False
    GLib.idle_add(run)


class State:
    RECORDING = "录音中"
    RECOGNIZING = "识别中"
    QUEUED = "排队发送"
    DELIVERING = "发送中"
    PASTED = "已粘贴"
    SUBMITTED = "已提交"
    PENDING = "待发送"
    FAILED = "失败"
    EDITOR = "在编辑框"
    COPIED = "已复制"


UNSENT = {State.QUEUED, State.DELIVERING, State.PENDING}


@dataclass
class Utterance:
    id: int
    created: float
    state: str
    text: str = ""
    error: StageError | None = None
    note: str = ""
    seconds: float = 0.0
    wav: bytes | None = None  # kept until recognized, for "重新识别"
    target: int | None = None


class Pipeline:
    """Runs on the GLib main loop; worker threads hand results back via on_main()."""

    def __init__(self, cfg: Config, own_windows: Callable[[], set[int]],
                 ours_active: Callable[[], bool] = lambda: False):
        self.item_changed = Signal()  # (Utterance)
        self.recording_changed = Signal()  # (bool)
        self.level = Signal()  # (dB float)
        self.editor_append = Signal()  # (str)
        self.notice = Signal()  # (kind: info|busy|ok|warn|error, message)
        self.cfg = cfg
        self.own_windows = own_windows
        self.ours_active = ours_active
        self.items: dict[int, Utterance] = {}
        self._next_id = 1
        self._auto_queue: list[int] = []  # ids waiting for automatic delivery, in order
        self._delivering: int | None = None
        self._asr_pool = ThreadPoolExecutor(max_workers=2, thread_name_prefix="asr")
        self._delivery_pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix="deliver")
        self.recorder: Recorder | None = None
        self._rec_item: Utterance | None = None
        self.toggle_mode = False  # recording started by a short tap; next tap stops it
        self.last_external: int | None = None  # follow mode: last active window not ours
        self._max_timer = 0  # GLib source id of the max-duration timer

    # ---------- helpers ----------

    def _new(self, state: str, **kw) -> Utterance:
        u = Utterance(id=self._next_id, created=time.time(), state=state, **kw)
        self._next_id += 1
        self.items[u.id] = u
        return u

    def _set(self, u: Utterance, state: str, error: StageError | None = None, note: str = "") -> None:
        u.state, u.error, u.note = state, error, note
        self.item_changed.emit(u)
        self._save_pending()

    def delivery_settings(self) -> dv.DeliverySettings:
        c = self.cfg
        return dv.DeliverySettings(c["paste_keys"], c["enter_keys"],
                                   int(c["delay_before_paste_ms"]), int(c["delay_before_enter_ms"]))

    def current_target(self) -> int | None:
        if self.cfg["target_mode"] == "follow":
            return self.last_external
        return self.cfg["target_window"] or None

    def poll_active_window(self) -> None:
        """Called periodically; remembers the last window that is not ours."""
        try:
            cur = dv.active_window()
        except StageError:
            return
        if cur and not dv.is_own_window(cur, self.own_windows()):
            self.last_external = cur

    @property
    def recording(self) -> bool:
        return self.recorder is not None

    # ---------- recording ----------

    def start_recording(self) -> None:
        if self.recorder:
            return
        if self.cfg["target_mode"] == "follow":
            self.poll_active_window()
        rec = Recorder(self.cfg["audio_device"], on_level=lambda db: on_main(self.level.emit, db))
        try:
            rec.start()
        except StageError as e:
            self.notice.emit("error", str(e))
            log.warning("record: %s", e)
            return
        self.recorder = rec
        self.toggle_mode = False
        self._rec_item = self._new(State.RECORDING, target=self.current_target())
        self.item_changed.emit(self._rec_item)
        self._max_timer = GLib.timeout_add(int(float(self.cfg["max_seconds"]) * 1000), self._on_max_duration)
        self.recording_changed.emit(True)
        log.info("record: start #%d device=%s", self._rec_item.id, self.cfg["audio_device"] or "default")

    def _on_max_duration(self) -> bool:
        self._max_timer = 0
        if self.recorder:
            self.notice.emit("warn", f"已到最长录音时间 {self.cfg['max_seconds']} 秒，自动结束")
            self.stop_recording(tail=False)
        return False

    def _stop_max_timer(self) -> None:
        if self._max_timer:
            GLib.source_remove(self._max_timer)
            self._max_timer = 0

    def stop_recording(self, tail: bool = True) -> None:
        """The user released (or tapped stop). Keep recording for tail_ms so the
        last syllable is not cut off; the button is free again immediately."""
        rec, u = self.recorder, self._rec_item
        if not rec or not u:
            return
        self.recorder, self._rec_item = None, None
        self._stop_max_timer()
        self.toggle_mode = False
        self.recording_changed.emit(False)
        if self.cfg["auto_paste"]:
            self._auto_queue.append(u.id)  # reserve the slot now so order follows speaking order
        tail_ms = int(self.cfg["tail_ms"]) if tail else 0
        if tail_ms > 0:
            self.notice.emit("busy", f"收尾录音 {tail_ms / 1000:.1f} 秒…")
            GLib.timeout_add(tail_ms, lambda: self._finish_recording(rec, u) or False)
        else:
            self._finish_recording(rec, u)

    def _finish_recording(self, rec: Recorder, u: Utterance) -> None:
        try:
            recording = rec.stop()
        except StageError as e:
            self._set(u, State.FAILED, e)
            self.notice.emit("error", str(e))
            self._pump()
            return
        u.seconds = recording.seconds
        log.info("record: stop #%d %.1fs peak=%.1fdB", u.id, recording.seconds, recording.peak_db)
        err = None
        if recording.seconds < float(self.cfg["min_seconds"]):
            err = StageError(Stage.RECORD, f"录音太短（{recording.seconds:.1f} 秒）")
        elif recording.peak_db < float(self.cfg["silence_threshold_db"]):
            err = StageError(Stage.RECORD, f"没有录到声音（最大音量 {recording.peak_db:.0f} dB）："
                             "检查麦克风是否开启、系统默认录音设备是否正确；"
                             "远程桌面或虚拟机里要确认声音已转发进来")
        if err:
            self._set(u, State.FAILED, err)
            self.notice.emit("error", str(err))
            self._pump()  # a failed sentence must not block the ones after it
            return
        u.wav = recording.wav()
        self._recognize(u)

    def cancel_recording(self) -> None:
        if self.recorder and self._rec_item:
            self.recorder.abort()
            self._set(self._rec_item, State.FAILED, StageError(Stage.RECORD, "已取消"))
        self.recorder, self._rec_item = None, None
        self._stop_max_timer()
        self.recording_changed.emit(False)

    # ---------- recognition ----------

    def _recognize(self, u: Utterance) -> None:
        self._set(u, State.RECOGNIZING)
        self.notice.emit("busy", "识别中…")
        provider = dict(self.cfg.provider())
        args = (provider, u.wav, self.cfg["language"], self.cfg["context"],
                float(self.cfg["request_timeout_s"]))

        def job():
            try:
                on_main(self._on_asr_done, u.id, transcribe(*args), None)
            except StageError as e:
                on_main(self._on_asr_done, u.id, None, e)
            except Exception as e:  # never let a worker die silently
                log.exception("asr: unexpected")
                on_main(self._on_asr_done, u.id, None, StageError(Stage.ASR, "识别时出现意外错误", redact(repr(e))))

        self._asr_pool.submit(job)

    def retry_recognition(self, uid: int) -> None:
        u = self.items.get(uid)
        if u and u.wav and u.state == State.FAILED:
            self._recognize(u)

    def _on_asr_done(self, uid: int, text: str | None, err: StageError | None) -> None:
        u = self.items.get(uid)
        if not u:
            return
        if err:
            log.warning("asr: #%d %s %s", uid, err, err.detail)
            self._set(u, State.FAILED, err)
            self.notice.emit("error", str(err))
            self._pump()
            return
        u.text = clean(text or "", self.cfg["replacements"], self.cfg["strip_trailing_period"])
        u.wav = None
        if not u.text:
            self._set(u, State.FAILED, StageError(Stage.ASR, "整理后文字为空"))
        elif uid in self._auto_queue:
            self._set(u, State.QUEUED)
        else:
            self._set(u, State.EDITOR)
            self.editor_append.emit(u.text)
            self.notice.emit("ok", "识别完成，已放入编辑框")
        self._pump()

    # ---------- delivery ----------

    def _pump(self) -> None:
        """Start the next automatic delivery, strictly in recording order."""
        if self._delivering is not None:
            return
        while self._auto_queue:
            head = self.items.get(self._auto_queue[0])
            if head is None:
                self._auto_queue.pop(0)
                continue
            if head.state in (State.RECORDING, State.RECOGNIZING):
                return  # wait so a later sentence never overtakes an earlier one
            self._auto_queue.pop(0)
            if head.state == State.QUEUED:
                self._deliver(head, check_foreground=True)
                return

    def _deliver(self, u: Utterance, check_foreground: bool) -> None:
        self._delivering = u.id
        target = u.target if self.cfg["target_mode"] == "follow" and u.target else self.current_target()
        # If one of our windows has focus, the user is with us: no need to ask X11.
        allowed = self.own_windows() if check_foreground and not self.ours_active() else None
        settings, enter = self.delivery_settings(), bool(self.cfg["auto_enter"])
        text = u.text
        self._set(u, State.DELIVERING)
        self.notice.emit("busy", "发送中…")

        def job():
            try:
                on_main(self._on_delivery_done, u.id, dv.deliver(text, target, settings, enter, allowed), None)
            except StageError as e:
                on_main(self._on_delivery_done, u.id, None, e)
            except Exception as e:
                log.exception("deliver: unexpected")
                on_main(self._on_delivery_done, u.id, None, StageError(Stage.PASTE, "投递时出现意外错误", repr(e)))

        self._delivery_pool.submit(job)

    def _on_delivery_done(self, uid: int, result: dv.DeliveryResult | None, err: StageError | None) -> None:
        self._delivering = None
        u = self.items.get(uid)
        if u:
            if err:
                log.warning("deliver: #%d %s %s", uid, err, err.detail)
                self._set(u, State.PENDING, err)
                self.notice.emit("warn" if isinstance(err, ForegroundChanged) else "error",
                                 f"{err}（文字已保留，可点「发送」）")
            else:
                self._set(u, State.SUBMITTED if result.entered else State.PASTED, note=result.note)
                short = u.text if len(u.text) <= 24 else u.text[:24] + "…"
                if result.note:
                    self.notice.emit("warn", f"{result.note}：{short}")
                else:
                    self.notice.emit("ok", ("已提交：" if result.entered else "已粘贴：") + short)
        self._pump()

    def send(self, uid: int) -> None:
        """User explicitly asked to send this item (again)."""
        u = self.items.get(uid)
        if not u or not u.text or u.state in (State.DELIVERING, State.RECOGNIZING, State.RECORDING):
            return
        self._set(u, State.QUEUED)
        self._auto_queue.append(uid)
        self._pump()

    def send_text(self, text: str) -> Utterance | None:
        text = clean(text)
        if not text:
            return None
        u = self._new(State.QUEUED, text=text, target=self.current_target())
        self.item_changed.emit(u)
        self._auto_queue.append(u.id)
        self._pump()
        return u

    def copy(self, text: str) -> None:
        def job():
            try:
                dv.set_clipboard(text)
            except StageError as e:
                on_main(self.notice.emit, "error", str(e))

        self._delivery_pool.submit(job)
        self.notice.emit("ok", "已复制到剪贴板")

    def press_enter(self) -> None:
        target, settings = self.current_target(), self.delivery_settings()

        def job():
            try:
                dv.press_enter(target, settings)
            except StageError as e:
                on_main(self.notice.emit, "error", str(e))

        self._delivery_pool.submit(job)

    def remove(self, uid: int) -> None:
        u = self.items.get(uid)
        if u and u.state not in (State.RECORDING, State.RECOGNIZING, State.DELIVERING):
            del self.items[uid]
            self._save_pending()

    # ---------- persistence of unsent text ----------

    @property
    def _pending_path(self):
        return self.cfg.cache_dir / "pending.json"

    def _save_pending(self, editor: str | None = None) -> None:
        if editor is not None:
            self._editor_snapshot = editor
        editor = getattr(self, "_editor_snapshot", "")
        items = [{"text": u.text, "created": u.created}
                 for u in sorted(self.items.values(), key=lambda x: x.id)
                 if u.state in UNSENT and u.text]
        path = self._pending_path
        try:
            if items or editor.strip():
                path.parent.mkdir(parents=True, exist_ok=True)
                tmp = path.with_suffix(".tmp")
                tmp.write_text(json.dumps({"editor": editor, "items": items}, ensure_ascii=False, indent=1),
                               encoding="utf-8")
                tmp.replace(path)
            elif path.exists():
                path.unlink()
        except OSError as e:
            log.warning("pending: save failed %s", e)

    def save_editor(self, editor: str) -> None:
        self._save_pending(editor)

    def load_pending(self) -> str:
        """Restore unsent items; returns saved editor text."""
        path = self._pending_path
        if not path.exists():
            return ""
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as e:
            log.warning("pending: load failed %s", e)
            return ""
        for it in data.get("items", []):
            u = self._new(State.PENDING, text=it.get("text", ""), note="上次未发送")
            u.created = it.get("created", u.created)
            self.item_changed.emit(u)
        self._editor_snapshot = data.get("editor", "")
        return self._editor_snapshot

    def shutdown(self) -> None:
        if self.recorder:
            self.recorder.abort()
        self._asr_pool.shutdown(wait=False, cancel_futures=True)
        self._delivery_pool.shutdown(wait=False, cancel_futures=True)
