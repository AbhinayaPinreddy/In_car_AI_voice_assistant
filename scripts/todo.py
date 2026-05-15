"""To-do list backed by SQLite with safe per-call connections."""

from __future__ import annotations

import contextlib
import sqlite3
from typing import Optional

from config import DB_PATH

DB_PATH.parent.mkdir(parents=True, exist_ok=True)


@contextlib.contextmanager
def _db():
    """Yield a (connection, cursor) pair and auto-commit / close."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("PRAGMA journal_mode=WAL")
    cur = conn.cursor()
    try:
        yield conn, cur
        conn.commit()
    finally:
        conn.close()


def _ensure_schema() -> None:
    with _db() as (conn, cur):
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS todos (
                id   INTEGER PRIMARY KEY AUTOINCREMENT,
                task TEXT    NOT NULL,
                done INTEGER NOT NULL DEFAULT 0
            )
            """
        )
        # Migrate: add 'done' if this is a legacy DB without it
        cur.execute("PRAGMA table_info(todos)")
        if "done" not in {row[1] for row in cur.fetchall()}:
            cur.execute("ALTER TABLE todos ADD COLUMN done INTEGER NOT NULL DEFAULT 0")


_ensure_schema()


def add_task(task: str) -> str:
    task = task.strip()
    if not task:
        return "I did not catch the task name. Please say it again."
    with _db() as (conn, cur):
        cur.execute("INSERT INTO todos (task, done) VALUES (?, 0)", (task,))
    return f"Added to your list: {task}."


def get_tasks(show_done: bool = False) -> str:
    with _db() as (conn, cur):
        cur.execute("SELECT id, task, done FROM todos ORDER BY id ASC")
        rows = cur.fetchall()

    if not rows:
        return "Your to-do list is empty."

    pending = [f"{tid}: {text}" for tid, text, done in rows if not done]
    done_tasks = [f"{tid}: {text}" for tid, text, done in rows if done]

    if not pending and not (show_done and done_tasks):
        return "Everything on your list is done. Nothing left to do."

    parts: list[str] = []
    if pending:
        parts.append("Open tasks — " + ", ".join(pending))
    if show_done and done_tasks:
        parts.append("Completed — " + ", ".join(done_tasks))
    return ". ".join(parts) + "."


def mark_task_done(task_id: str) -> str:
    try:
        tid = int(task_id)
    except (ValueError, TypeError):
        return "Please say a valid task number."
    with _db() as (conn, cur):
        cur.execute("UPDATE todos SET done = 1 WHERE id = ?", (tid,))
        if cur.rowcount == 0:
            return f"I could not find task number {tid}."
    return f"Marked task {tid} as done."


def delete_task(task_id: str) -> str:
    try:
        tid = int(task_id)
    except (ValueError, TypeError):
        return "Please say a valid task number."
    with _db() as (conn, cur):
        cur.execute("DELETE FROM todos WHERE id = ?", (tid,))
        if cur.rowcount == 0:
            return f"I could not find task number {tid}."
    return f"Deleted task {tid}."
