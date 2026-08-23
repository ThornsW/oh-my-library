from __future__ import annotations

from memo.core.models import PRIORITY_HIGH, PRIORITY_LOW, PRIORITY_NORMAL


def test_migrate_is_idempotent(db):
    # Reconnect; second migrate should be a no-op (no error, version stays at 1)
    db.connect()
    cur = db._conn_or_raise().execute("PRAGMA user_version")  # noqa: SLF001
    assert cur.fetchone()[0] == db.SCHEMA_VERSION


def test_create_and_get_todo(db):
    todo_id = db.create_todo("Write report")
    todo = db.get_todo(todo_id)
    assert todo is not None
    assert todo.title == "Write report"
    assert todo.completed is False
    assert todo.priority == PRIORITY_NORMAL


def test_update_todo_persists_fields(db):
    todo_id = db.create_todo("draft")
    db.update_todo(
        todo_id,
        title="final",
        note_md="# Hello",
        priority=PRIORITY_HIGH,
        due_date="2026-05-01",
    )
    todo = db.get_todo(todo_id)
    assert todo.title == "final"
    assert todo.note_md == "# Hello"
    assert todo.priority == PRIORITY_HIGH
    assert todo.due_date == "2026-05-01"


def test_set_completed_round_trip(db):
    todo_id = db.create_todo("ship it")
    db.set_completed(todo_id, True)
    assert db.get_todo(todo_id).completed is True
    db.set_completed(todo_id, False)
    assert db.get_todo(todo_id).completed is False


def test_tags_with_counts_and_membership(db):
    work = db.create_tag("work")
    personal = db.create_tag("personal")
    a = db.create_todo("A")
    b = db.create_todo("B")
    c = db.create_todo("C")

    db.set_todo_tags(a, [work.id])
    db.set_todo_tags(b, [work.id, personal.id])
    db.set_todo_tags(c, [personal.id])
    db.set_completed(c, True)

    by_name = {t.name: t for t in db.list_tags_with_counts()}
    # Only active todos contribute to counts: a, b for work; b for personal
    assert by_name["work"].count == 2
    assert by_name["personal"].count == 1


def test_filter_and_sort_order(db):
    high_due_soon = db.create_todo("urgent meeting")
    db.update_todo(
        high_due_soon,
        title="urgent meeting",
        note_md="",
        priority=PRIORITY_HIGH,
        due_date="2026-05-01",
    )

    low_due_later = db.create_todo("read paper")
    db.update_todo(
        low_due_later,
        title="read paper",
        note_md="",
        priority=PRIORITY_LOW,
        due_date="2026-06-01",
    )

    no_due_normal = db.create_todo("brainstorm")
    db.update_todo(
        no_due_normal,
        title="brainstorm",
        note_md="",
        priority=PRIORITY_NORMAL,
        due_date=None,
    )

    done = db.create_todo("write tests")
    db.set_completed(done, True)

    titles = [t.title for t in db.list_todos(filter_="active")]
    # active filter excludes "write tests"; with-due come before nodues; earlier-due first
    assert titles == ["urgent meeting", "read paper", "brainstorm"]

    titles_all = [t.title for t in db.list_todos(filter_="all")]
    # done items go to the end (completed ASC)
    assert titles_all[-1] == "write tests"


def test_search_matches_title_and_note(db):
    a = db.create_todo("alpha task")
    db.update_todo(a, title="alpha task", note_md="", priority=1, due_date=None)
    b = db.create_todo("beta")
    db.update_todo(b, title="beta", note_md="contains alpha keyword", priority=1, due_date=None)
    db.create_todo("gamma")

    found = [t.title for t in db.list_todos(filter_="all", search="alpha")]
    assert set(found) == {"alpha task", "beta"}


def test_subtasks_replace_whole_list(db):
    todo_id = db.create_todo("compound task")
    db.set_subtasks(todo_id, [("step 1", False), ("step 2", True), ("step 3", False)])
    todo = db.get_todo(todo_id)
    assert [s.text for s in todo.subtasks] == ["step 1", "step 2", "step 3"]
    assert [s.completed for s in todo.subtasks] == [False, True, False]

    db.set_subtasks(todo_id, [("only step", False)])
    todo = db.get_todo(todo_id)
    assert [s.text for s in todo.subtasks] == ["only step"]


def test_cascade_deletes(db):
    work = db.create_tag("work")
    todo_id = db.create_todo("project")
    db.set_todo_tags(todo_id, [work.id])
    db.set_subtasks(todo_id, [("a", False), ("b", False)])

    # deleting the todo wipes its subtasks and todo_tags via FK cascade
    db.delete_todo(todo_id)
    conn = db._conn_or_raise()  # noqa: SLF001
    assert conn.execute("SELECT COUNT(*) FROM subtasks").fetchone()[0] == 0
    assert conn.execute("SELECT COUNT(*) FROM todo_tags").fetchone()[0] == 0
    # tag itself stays
    assert conn.execute("SELECT COUNT(*) FROM tags").fetchone()[0] == 1


def test_delete_tag_keeps_todo(db):
    work = db.create_tag("work")
    todo_id = db.create_todo("project")
    db.set_todo_tags(todo_id, [work.id])

    db.delete_tag(work.id)
    todo = db.get_todo(todo_id)
    assert todo is not None
    assert todo.tags == []
