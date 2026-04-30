"""SQLite access layer.

Owns the single ``sqlite3.Connection`` and exposes typed CRUD helpers for the
UI. Schema migrations are versioned via SQLite's built-in ``user_version``
pragma — bump ``SCHEMA_VERSION`` and add a branch in ``_migrate`` when
changing the schema.
"""

from __future__ import annotations

import datetime as _dt
import sqlite3
from pathlib import Path
from typing import Iterable

from memo.core import paths
from memo.core.models import Subtask, Tag, Todo

SCHEMA_VERSION = 1

_SCHEMA_V1 = """
CREATE TABLE IF NOT EXISTS todos (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  title         TEXT    NOT NULL,
  note_md       TEXT    NOT NULL DEFAULT '',
  priority      INTEGER NOT NULL DEFAULT 1,
  due_date      TEXT,
  completed     INTEGER NOT NULL DEFAULT 0,
  completed_at  TEXT,
  created_at    TEXT    NOT NULL,
  updated_at    TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS tags (
  id     INTEGER PRIMARY KEY AUTOINCREMENT,
  name   TEXT    NOT NULL UNIQUE,
  color  TEXT    NOT NULL DEFAULT '#7AA2F7'
);

CREATE TABLE IF NOT EXISTS todo_tags (
  todo_id INTEGER NOT NULL REFERENCES todos(id) ON DELETE CASCADE,
  tag_id  INTEGER NOT NULL REFERENCES tags(id)  ON DELETE CASCADE,
  PRIMARY KEY (todo_id, tag_id)
);

CREATE TABLE IF NOT EXISTS subtasks (
  id        INTEGER PRIMARY KEY AUTOINCREMENT,
  todo_id   INTEGER NOT NULL REFERENCES todos(id) ON DELETE CASCADE,
  text      TEXT    NOT NULL,
  completed INTEGER NOT NULL DEFAULT 0,
  position  INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_todos_completed ON todos(completed);
CREATE INDEX IF NOT EXISTS idx_todos_due       ON todos(due_date);
CREATE INDEX IF NOT EXISTS idx_subtasks_todo   ON subtasks(todo_id, position);
"""


_conn: sqlite3.Connection | None = None


def _now_iso() -> str:
    return _dt.datetime.now().isoformat(timespec="seconds")


def connect(db_file: Path | None = None) -> sqlite3.Connection:
    """Open (or reopen) the global connection. Idempotent for the same path."""
    global _conn
    target = db_file if db_file is not None else paths.db_path()
    if _conn is not None:
        _conn.close()
    conn = sqlite3.connect(str(target))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    _migrate(conn)
    _conn = conn
    return conn


def close() -> None:
    global _conn
    if _conn is not None:
        _conn.close()
        _conn = None


def _conn_or_raise() -> sqlite3.Connection:
    if _conn is None:
        return connect()
    return _conn


def _migrate(conn: sqlite3.Connection) -> None:
    cur = conn.execute("PRAGMA user_version")
    current = cur.fetchone()[0]
    if current < 1:
        conn.executescript(_SCHEMA_V1)
        conn.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
        conn.commit()


# ---------- Tags ----------

def list_tags_with_counts() -> list[Tag]:
    """Return all tags with their *active* todo counts (uncompleted)."""
    conn = _conn_or_raise()
    rows = conn.execute(
        """
        SELECT t.id, t.name, t.color,
               COALESCE(SUM(CASE WHEN td.completed = 0 THEN 1 ELSE 0 END), 0) AS cnt
          FROM tags t
          LEFT JOIN todo_tags tt ON tt.tag_id = t.id
          LEFT JOIN todos td     ON td.id = tt.todo_id
         GROUP BY t.id
         ORDER BY t.name COLLATE NOCASE
        """
    ).fetchall()
    return [Tag(id=r["id"], name=r["name"], color=r["color"], count=r["cnt"]) for r in rows]


def count_active_todos() -> int:
    conn = _conn_or_raise()
    row = conn.execute("SELECT COUNT(*) FROM todos WHERE completed = 0").fetchone()
    return int(row[0])


def count_all_todos() -> int:
    conn = _conn_or_raise()
    row = conn.execute("SELECT COUNT(*) FROM todos").fetchone()
    return int(row[0])


def create_tag(name: str, color: str = "#7AA2F7") -> Tag:
    conn = _conn_or_raise()
    cur = conn.execute("INSERT INTO tags(name, color) VALUES (?, ?)", (name.strip(), color))
    conn.commit()
    return Tag(id=cur.lastrowid, name=name.strip(), color=color, count=0)


def rename_tag(tag_id: int, name: str) -> None:
    conn = _conn_or_raise()
    conn.execute("UPDATE tags SET name = ? WHERE id = ?", (name.strip(), tag_id))
    conn.commit()


def delete_tag(tag_id: int) -> None:
    conn = _conn_or_raise()
    conn.execute("DELETE FROM tags WHERE id = ?", (tag_id,))
    conn.commit()


# ---------- Todos ----------

def _row_to_todo(r: sqlite3.Row) -> Todo:
    return Todo(
        id=r["id"],
        title=r["title"],
        note_md=r["note_md"],
        priority=r["priority"],
        due_date=r["due_date"],
        completed=bool(r["completed"]),
        completed_at=r["completed_at"],
        created_at=r["created_at"],
        updated_at=r["updated_at"],
    )


def list_todos(
    *,
    filter_: str = "active",   # 'all' | 'active' | 'done'
    tag_id: int | None = None,
    search: str = "",
) -> list[Todo]:
    """Return todos matching filter + tag + free-text search.

    Sort: incomplete first; due_date NULLs last but otherwise ascending; high
    priority before low; recently updated first.
    """
    conn = _conn_or_raise()
    where: list[str] = []
    params: list[object] = []

    if filter_ == "active":
        where.append("td.completed = 0")
    elif filter_ == "done":
        where.append("td.completed = 1")

    if tag_id is not None:
        where.append("td.id IN (SELECT todo_id FROM todo_tags WHERE tag_id = ?)")
        params.append(tag_id)

    s = search.strip()
    if s:
        where.append("(td.title LIKE ? OR td.note_md LIKE ?)")
        like = f"%{s}%"
        params.extend([like, like])

    sql = "SELECT td.* FROM todos td"
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += (
        " ORDER BY td.completed ASC,"
        " CASE WHEN td.due_date IS NULL THEN 1 ELSE 0 END ASC,"
        " td.due_date ASC,"
        " td.priority DESC,"
        " td.updated_at DESC"
    )

    rows = conn.execute(sql, params).fetchall()
    todos = [_row_to_todo(r) for r in rows]
    if not todos:
        return todos

    ids = [t.id for t in todos]
    qmarks = ",".join("?" for _ in ids)

    tag_rows = conn.execute(
        f"""
        SELECT tt.todo_id, t.id, t.name, t.color
          FROM todo_tags tt JOIN tags t ON t.id = tt.tag_id
         WHERE tt.todo_id IN ({qmarks})
         ORDER BY t.name COLLATE NOCASE
        """,
        ids,
    ).fetchall()
    by_id = {t.id: t for t in todos}
    for r in tag_rows:
        by_id[r["todo_id"]].tags.append(Tag(id=r["id"], name=r["name"], color=r["color"]))

    sub_rows = conn.execute(
        f"""
        SELECT id, todo_id, text, completed, position
          FROM subtasks
         WHERE todo_id IN ({qmarks})
         ORDER BY position ASC, id ASC
        """,
        ids,
    ).fetchall()
    for r in sub_rows:
        by_id[r["todo_id"]].subtasks.append(
            Subtask(
                id=r["id"],
                todo_id=r["todo_id"],
                text=r["text"],
                completed=bool(r["completed"]),
                position=r["position"],
            )
        )
    return todos


def get_todo(todo_id: int) -> Todo | None:
    conn = _conn_or_raise()
    r = conn.execute("SELECT * FROM todos WHERE id = ?", (todo_id,)).fetchone()
    if r is None:
        return None
    todo = _row_to_todo(r)
    todo.tags = [
        Tag(id=tr["id"], name=tr["name"], color=tr["color"])
        for tr in conn.execute(
            """
            SELECT t.id, t.name, t.color
              FROM tags t JOIN todo_tags tt ON tt.tag_id = t.id
             WHERE tt.todo_id = ?
             ORDER BY t.name COLLATE NOCASE
            """,
            (todo_id,),
        ).fetchall()
    ]
    todo.subtasks = [
        Subtask(
            id=sr["id"],
            todo_id=sr["todo_id"],
            text=sr["text"],
            completed=bool(sr["completed"]),
            position=sr["position"],
        )
        for sr in conn.execute(
            "SELECT * FROM subtasks WHERE todo_id = ? ORDER BY position ASC, id ASC",
            (todo_id,),
        ).fetchall()
    ]
    return todo


def create_todo(title: str) -> int:
    conn = _conn_or_raise()
    now = _now_iso()
    cur = conn.execute(
        "INSERT INTO todos(title, created_at, updated_at) VALUES (?, ?, ?)",
        (title, now, now),
    )
    conn.commit()
    return cur.lastrowid


def update_todo(
    todo_id: int,
    *,
    title: str,
    note_md: str,
    priority: int,
    due_date: str | None,
) -> None:
    conn = _conn_or_raise()
    conn.execute(
        """
        UPDATE todos
           SET title = ?, note_md = ?, priority = ?, due_date = ?, updated_at = ?
         WHERE id = ?
        """,
        (title, note_md, priority, due_date, _now_iso(), todo_id),
    )
    conn.commit()


def set_completed(todo_id: int, completed: bool) -> None:
    conn = _conn_or_raise()
    now = _now_iso()
    conn.execute(
        """
        UPDATE todos
           SET completed = ?, completed_at = ?, updated_at = ?
         WHERE id = ?
        """,
        (1 if completed else 0, now if completed else None, now, todo_id),
    )
    conn.commit()


def delete_todo(todo_id: int) -> None:
    conn = _conn_or_raise()
    conn.execute("DELETE FROM todos WHERE id = ?", (todo_id,))
    conn.commit()


# ---------- Todo <-> Tag ----------

def set_todo_tags(todo_id: int, tag_ids: Iterable[int]) -> None:
    conn = _conn_or_raise()
    with conn:
        conn.execute("DELETE FROM todo_tags WHERE todo_id = ?", (todo_id,))
        conn.executemany(
            "INSERT INTO todo_tags(todo_id, tag_id) VALUES (?, ?)",
            [(todo_id, t) for t in tag_ids],
        )
        conn.execute("UPDATE todos SET updated_at = ? WHERE id = ?", (_now_iso(), todo_id))


# ---------- Subtasks ----------

def set_subtasks(todo_id: int, items: list[tuple[str, bool]]) -> None:
    """Replace the subtasks for a todo with the given (text, completed) list."""
    conn = _conn_or_raise()
    with conn:
        conn.execute("DELETE FROM subtasks WHERE todo_id = ?", (todo_id,))
        for pos, (text, done) in enumerate(items):
            conn.execute(
                "INSERT INTO subtasks(todo_id, text, completed, position) VALUES (?, ?, ?, ?)",
                (todo_id, text, 1 if done else 0, pos),
            )
        conn.execute("UPDATE todos SET updated_at = ? WHERE id = ?", (_now_iso(), todo_id))


def toggle_subtask(subtask_id: int, completed: bool) -> None:
    conn = _conn_or_raise()
    with conn:
        conn.execute(
            "UPDATE subtasks SET completed = ? WHERE id = ?",
            (1 if completed else 0, subtask_id),
        )
        conn.execute(
            """
            UPDATE todos SET updated_at = ?
             WHERE id = (SELECT todo_id FROM subtasks WHERE id = ?)
            """,
            (_now_iso(), subtask_id),
        )
