"""Row widget shown inside the todo list."""

from __future__ import annotations

import datetime as _dt

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from memo.core.models import (
    PRIORITY_HIGH,
    PRIORITY_LOW,
    PRIORITY_NORMAL,
    Todo,
)
from memo.ui._color import darken, hex_to_rgba

_PRIORITY_KEY = {
    PRIORITY_HIGH: "high",
    PRIORITY_NORMAL: "normal",
    PRIORITY_LOW: "low",
}


def _format_due(due: str | None) -> tuple[str, str, str]:
    """Return (display_text, fg_color, bg_color) for the due-date pill."""
    if not due:
        return "", "", ""
    try:
        d = _dt.date.fromisoformat(due)
    except ValueError:
        return due, "#475569", "#F1F5F9"
    today = _dt.date.today()
    delta = (d - today).days
    if delta < 0:
        return f"逾期 {-delta} 天", "#B91C1C", "#FEE2E2"
    if delta == 0:
        return "今天", "#9A3412", "#FFEDD5"
    if delta == 1:
        return "明天", "#9A3412", "#FFEDD5"
    if delta <= 7:
        return f"{delta} 天后", "#1E40AF", "#DBEAFE"
    return d.strftime("%m-%d"), "#475569", "#F1F5F9"


class TodoRow(QWidget):
    completedToggled = Signal(int, bool)

    def __init__(self, todo: Todo, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._todo_id = todo.id

        outer = QHBoxLayout(self)
        outer.setContentsMargins(4, 7, 10, 7)
        outer.setSpacing(9)

        # 3px coloured priority stripe along the left edge of the row
        stripe = QFrame()
        stripe.setProperty("priorityStripe", _PRIORITY_KEY.get(todo.priority, "low"))
        stripe.setFixedWidth(3)
        stripe.setMinimumHeight(40)
        outer.addWidget(stripe)

        self.checkbox = QCheckBox()
        self.checkbox.setChecked(todo.completed)
        self.checkbox.toggled.connect(self._on_toggle)
        outer.addWidget(self.checkbox, 0, Qt.AlignmentFlag.AlignVCenter)

        col = QVBoxLayout()
        col.setContentsMargins(0, 0, 0, 0)
        col.setSpacing(3)

        self.title = QLabel(todo.title or "(无标题)")
        title_style = "font-size: 14px; font-weight: 600;"
        if todo.completed:
            title_style += "color: #94A3B8; text-decoration: line-through;"
        else:
            title_style += "color: #0F172A;"
        self.title.setStyleSheet(title_style)
        self.title.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        col.addWidget(self.title)

        meta = QHBoxLayout()
        meta.setContentsMargins(0, 0, 0, 0)
        meta.setSpacing(6)

        for tag in todo.tags[:3]:
            chip = QLabel(tag.name)
            # NB: do NOT use 8-digit hex like `{tag.color}1F` — Qt parses that
            # as #AARRGGBB and the colour comes out completely wrong. Always
            # use rgba() for tinted backgrounds. See memo/ui/_color.py.
            chip.setStyleSheet(
                f"color:{darken(tag.color, 0.45)};"
                f"background:{hex_to_rgba(tag.color, 0.20)};"
                "border-radius:9px; padding:3px 10px;"
                "font-size:11px; font-weight:600;"
            )
            meta.addWidget(chip)

        if len(todo.tags) > 3:
            more = QLabel(f"+{len(todo.tags) - 3}")
            more.setStyleSheet("color:#94A3B8; font-size:11px;")
            meta.addWidget(more)

        if todo.subtasks:
            done = sum(1 for s in todo.subtasks if s.completed)
            sub_lbl = QLabel(f"☑  {done}/{len(todo.subtasks)}")
            sub_lbl.setStyleSheet(
                "color:#475569; background:#F1F5F9; border-radius:9px;"
                "padding:3px 10px; font-size:11px; font-weight:500;"
            )
            meta.addWidget(sub_lbl)

        meta.addStretch(1)

        due_text, due_fg, due_bg = _format_due(todo.due_date)
        if due_text:
            due_lbl = QLabel(due_text)
            due_lbl.setStyleSheet(
                f"color:{due_fg}; background:{due_bg};"
                "border-radius:9px; padding:3px 12px;"
                "font-size:11px; font-weight:600;"
            )
            meta.addWidget(due_lbl)

        col.addLayout(meta)
        outer.addLayout(col, 1)

    def _on_toggle(self, checked: bool) -> None:
        self.completedToggled.emit(self._todo_id, checked)
