# New Todo Dialog Design

## Goal

Replace the current title-only new todo prompt with a full creation dialog. When the user clicks "新建" or presses `Ctrl+N`, they can set the todo title, tags, subtasks, due date, and priority before the todo is created.

## User Experience

- The toolbar "新建" action opens a modal dialog titled "新建待办".
- The dialog contains:
  - title input, required
  - priority selector, defaulting to normal
  - optional due date controlled by a "截止" checkbox
  - existing tag checklist
  - editable subtask list
- The primary button is "创建"; the secondary button is "取消".
- If the title is empty, the dialog stays open and shows the same style of warning already used by the detail editor.
- After creation, the sidebar and todo list refresh, and the new todo is selected.

## Architecture

Add `memo/ui/new_todo_dialog.py` with a `NewTodoDialog` class. The dialog owns UI state only and exposes a small result object through a method such as `todo_data()`.

`MainWindow._on_new_todo()` will:

1. instantiate `NewTodoDialog`
2. return early if the dialog is cancelled
3. create the todo with the entered title
4. update priority and due date
5. assign selected tags
6. create subtasks
7. refresh sidebar/list and select the new todo

The existing detail editor remains responsible for editing an existing todo. It will not gain draft-state behavior.

## Data Flow

The dialog will read available tags from `db.list_tags_with_counts()` when it is constructed. It will return selected tag ids, subtask tuples, due date string or `None`, and priority. Creation will reuse existing database helpers:

- `db.create_todo(title)`
- `db.update_todo(todo_id, title=..., note_md="", priority=..., due_date=...)`
- `db.set_todo_tags(todo_id, tag_ids)`
- `db.set_subtasks(todo_id, subtasks)`

No schema change is required.

## Components

- `NewTodoDialog`: new modal form for creation.
- Existing `SubtaskList`: reused for subtask entry.
- Existing priority constants and labels from `memo.core.models`.
- Existing tag data from `memo.core.db`.

## Error Handling

- Empty titles are rejected in the dialog before database writes.
- If there are no tags, the tag area shows a disabled empty state rather than failing.
- Database errors are allowed to surface through the existing application behavior; no new recovery layer is added.

## Testing

Add focused tests that instantiate the dialog with an isolated database and verify:

- entered title, priority, due date, selected tags, and subtasks are exposed correctly
- empty titles are rejected

Existing database tests already cover tag and subtask persistence. If needed, add a small integration-style test for the create flow helper if the creation code is extracted from `MainWindow`.
