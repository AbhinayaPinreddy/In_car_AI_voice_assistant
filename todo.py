import sqlite3
from pathlib import Path

DB_DIR = Path("database")
DB_DIR.mkdir(parents=True, exist_ok=True)

conn = sqlite3.connect(DB_DIR / "todo.db")

cursor = conn.cursor()

cursor.execute(
    '''
    CREATE TABLE IF NOT EXISTS todos(
        id INTEGER PRIMARY KEY,
        task TEXT NOT NULL,
        done INTEGER NOT NULL DEFAULT 0
    )
    '''
)

conn.commit()


def _migrate_schema():
    # Add 'done' column if upgrading from older schema.
    cursor.execute("PRAGMA table_info(todos)")
    cols = {row[1] for row in cursor.fetchall()}
    if "done" not in cols:
        cursor.execute("ALTER TABLE todos ADD COLUMN done INTEGER NOT NULL DEFAULT 0")
        conn.commit()


_migrate_schema()


def add_task(task):
    task = task.strip()
    if not task:
        return "Please say the task clearly. I could not hear a task name."

    cursor.execute(
        "INSERT INTO todos(task, done) VALUES(?, 0)",
        (task,)
    )

    conn.commit()

    return "Task added successfully"


def get_tasks(show_done=True):
    if show_done:
        cursor.execute("SELECT id, task, done FROM todos ORDER BY id DESC")
    else:
        cursor.execute("SELECT id, task, done FROM todos WHERE done = 0 ORDER BY id DESC")

    tasks = cursor.fetchall()

    if not tasks:
        return "No tasks found"

    pending = []
    completed = []

    for task_id, task_text, done in tasks:
        line = f"{task_id}. {task_text}"
        if int(done) == 1:
            completed.append(line)
        else:
            pending.append(line)

    result = ""
    if pending:
        result += "Pending tasks:\n" + "\n".join(pending) + "\n"
    if completed and show_done:
        result += "Completed tasks:\n" + "\n".join(completed) + "\n"
    return result.strip()


def mark_task_done(task_id):
    try:
        task_id = int(task_id)
    except Exception:
        return "Please say a valid task number."

    cursor.execute("UPDATE todos SET done = 1 WHERE id = ?", (task_id,))
    conn.commit()
    if cursor.rowcount == 0:
        return f"I could not find task {task_id}."
    return f"Marked task {task_id} as done."


def delete_task(task_id):
    try:
        task_id = int(task_id)
    except Exception:
        return "Please say a valid task number."

    cursor.execute("DELETE FROM todos WHERE id = ?", (task_id,))
    conn.commit()
    if cursor.rowcount == 0:
        return f"I could not find task {task_id}."
    return f"Deleted task {task_id}."