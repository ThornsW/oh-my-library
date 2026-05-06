"""New todo creation dialog and persistence helper."""

from __future__ import annotations

from dataclasses import dataclass, field

from memo.core import db
from memo.core.models import PRIORITY_NORMAL


@dataclass
class NewTodoData:
    title: str
    priority: int = PRIORITY_NORMAL
    due_date: str | None = None
    tag_ids: list[int] = field(default_factory=list)
    subtasks: list[tuple[str, bool]] = field(default_factory=list)


def create_todo_from_data(data: NewTodoData) -> int:
    title = data.title.strip()
    if not title:
        raise ValueError("title is required")

    todo_id = db.create_todo(title)
    try:
        db.update_todo(
            todo_id,
            title=title,
            note_md="",
            priority=data.priority,
            due_date=data.due_date,
        )
        db.set_todo_tags(todo_id, data.tag_ids)
        db.set_subtasks(todo_id, data.subtasks)
    except Exception:
        db.delete_todo(todo_id)
        raise
    return todo_id
