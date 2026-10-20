"""Errors that carry the pipeline stage, so the UI can say where things went wrong."""

from __future__ import annotations


class Stage:
    CONFIG = "配置"
    RECORD = "录音"
    ASR = "识别"
    TARGET = "找窗口"
    FOCUS = "切焦点"
    CLIPBOARD = "剪贴板"
    PASTE = "粘贴"
    ENTER = "回车"


class StageError(Exception):
    """A failure in one pipeline stage.

    reason: one short sentence for the status bar.
    detail: technical detail for the log / details panel (redacted before display).
    """

    def __init__(self, stage: str, reason: str, detail: str = ""):
        super().__init__(f"[{stage}] {reason}")
        self.stage = stage
        self.reason = reason
        self.detail = detail


class ForegroundChanged(StageError):
    """The user is in another window; delivering now could put text in the wrong place."""

    def __init__(self, title: str):
        super().__init__(
            Stage.FOCUS,
            f"当前前台是「{title or '未知窗口'}」，为避免发错位置，没有自动发送",
        )
