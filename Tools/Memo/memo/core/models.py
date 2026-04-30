"""Plain dataclasses representing rows from the DB."""

from __future__ import annotations

from dataclasses import dataclass, field

PRIORITY_LOW = 0
PRIORITY_NORMAL = 1
PRIORITY_HIGH = 2

PRIORITY_LABELS = {
    PRIORITY_LOW: "低",
    PRIORITY_NORMAL: "中",
    PRIORITY_HIGH: "高",
}


@dataclass
class Tag:
    id: int
    name: str
    color: str = "#7AA2F7"
    count: int = 0


@dataclass
class Subtask:
    id: int
    todo_id: int
    text: str
    completed: bool = False
    position: int = 0


@dataclass
class Todo:
    id: int
    title: str
    note_md: str = ""
    priority: int = PRIORITY_NORMAL
    due_date: str | None = None  # ISO 'YYYY-MM-DD' or None
    completed: bool = False
    completed_at: str | None = None
    created_at: str = ""
    updated_at: str = ""
    tags: list[Tag] = field(default_factory=list)
    subtasks: list[Subtask] = field(default_factory=list)
