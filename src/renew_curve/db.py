from __future__ import annotations

import datetime as dt
import os
import sqlite3
from pathlib import Path
from typing import Iterable

from renew_curve.models import Reminder, ReminderDraft, Task, TaskDraft
from renew_curve.scheduler import calculate_progress_percent


def connect(db_path: os.PathLike[str] | str) -> sqlite3.Connection:
    conn = sqlite3.connect(Path(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            legacy_id TEXT UNIQUE,
            title TEXT NOT NULL,
            category TEXT NOT NULL DEFAULT '',
            difficulty TEXT NOT NULL DEFAULT '',
            notes TEXT NOT NULL DEFAULT '',
            reminder_method TEXT NOT NULL DEFAULT '',
            start_time TEXT NOT NULL,
            is_completed INTEGER NOT NULL DEFAULT 0,
            progress_percent REAL NOT NULL DEFAULT 0.0
        );

        CREATE TABLE IF NOT EXISTS reminders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            legacy_id TEXT UNIQUE,
            task_id INTEGER NOT NULL,
            remind_time TEXT NOT NULL,
            reminded INTEGER NOT NULL DEFAULT 0,
            FOREIGN KEY (task_id) REFERENCES tasks (id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS backgrounds (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            legacy_id TEXT UNIQUE,
            name TEXT NOT NULL,
            path TEXT NOT NULL,
            is_active INTEGER NOT NULL DEFAULT 0
        );

        CREATE INDEX IF NOT EXISTS idx_tasks_legacy_id ON tasks (legacy_id);
        CREATE INDEX IF NOT EXISTS idx_tasks_is_completed ON tasks (is_completed);
        CREATE INDEX IF NOT EXISTS idx_reminders_task_id ON reminders (task_id);
        CREATE INDEX IF NOT EXISTS idx_reminders_remind_time ON reminders (remind_time);
        CREATE INDEX IF NOT EXISTS idx_reminders_reminded ON reminders (reminded);
        """
    )
    conn.commit()


class ReminderRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def create_task(
        self,
        draft: TaskDraft,
        *,
        legacy_id: str | None = None,
        is_completed: bool = False,
    ) -> int:
        cursor = self._conn.execute(
            """
            INSERT INTO tasks (
                legacy_id,
                title,
                category,
                difficulty,
                notes,
                reminder_method,
                start_time,
                is_completed
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                legacy_id,
                draft.title,
                draft.category,
                draft.difficulty,
                draft.notes,
                draft.reminder_method,
                _dump_datetime(draft.start_time),
                int(is_completed),
            ),
        )
        return int(cursor.lastrowid)

    def create_reminder(
        self, draft: ReminderDraft, *, legacy_id: str | None = None
    ) -> int:
        cursor = self._conn.execute(
            """
            INSERT INTO reminders (legacy_id, task_id, remind_time, reminded)
            VALUES (?, ?, ?, ?)
            """,
            (
                legacy_id,
                draft.task_id,
                _dump_datetime(draft.remind_time),
                int(draft.reminded),
            ),
        )
        self.recalculate_task_progress(draft.task_id)
        return int(cursor.lastrowid)

    def get_task(self, task_id: int) -> Task | None:
        row = self._conn.execute(
            """
            SELECT
                id,
                title,
                category,
                difficulty,
                notes,
                reminder_method,
                start_time,
                is_completed,
                progress_percent
            FROM tasks
            WHERE id = ?
            """,
            (task_id,),
        ).fetchone()
        if row is None:
            return None
        return _task_from_row(row)

    def list_tasks(self, *, include_completed: bool = True) -> list[Task]:
        if include_completed:
            rows: Iterable[sqlite3.Row] = self._conn.execute(
                """
                SELECT
                    id,
                    title,
                    category,
                    difficulty,
                    notes,
                    reminder_method,
                    start_time,
                    is_completed,
                    progress_percent
                FROM tasks
                ORDER BY start_time, id
                """
            )
        else:
            rows = self._conn.execute(
                """
                SELECT
                    id,
                    title,
                    category,
                    difficulty,
                    notes,
                    reminder_method,
                    start_time,
                    is_completed,
                    progress_percent
                FROM tasks
                WHERE is_completed = 0
                ORDER BY start_time, id
                """
            )
        return [_task_from_row(row) for row in rows]

    def list_reminders(self, task_id: int) -> list[Reminder]:
        rows = self._conn.execute(
            """
            SELECT id, task_id, remind_time, reminded
            FROM reminders
            WHERE task_id = ?
            ORDER BY remind_time, id
            """,
            (task_id,),
        )
        return [_reminder_from_row(row) for row in rows]

    def mark_reminder_done(self, reminder_id: int) -> None:
        row = self._conn.execute(
            "SELECT task_id FROM reminders WHERE id = ?", (reminder_id,)
        ).fetchone()
        if row is None:
            return

        self._conn.execute(
            "UPDATE reminders SET reminded = 1 WHERE id = ?", (reminder_id,)
        )
        self.recalculate_task_progress(int(row["task_id"]))

    def set_setting(self, key: str, value: str) -> None:
        self._conn.execute(
            "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
            (key, value),
        )

    def get_setting(self, key: str, default: str = "") -> str:
        row = self._conn.execute(
            "SELECT value FROM settings WHERE key = ?", (key,)
        ).fetchone()
        return default if row is None else str(row[0])

    def recalculate_task_progress(self, task_id: int) -> float:
        row = self._conn.execute(
            """
            SELECT COUNT(*) AS total, COALESCE(SUM(reminded), 0) AS completed
            FROM reminders
            WHERE task_id = ?
            """,
            (task_id,),
        ).fetchone()
        progress = calculate_progress_percent(
            int(row["total"]), int(row["completed"])
        )
        total = int(row["total"])
        completed = int(row["completed"])
        is_completed = total > 0 and completed == total
        self._conn.execute(
            "UPDATE tasks SET progress_percent = ?, is_completed = ? WHERE id = ?",
            (progress, int(is_completed), task_id),
        )
        return progress


def _dump_datetime(value: dt.datetime) -> str:
    return value.isoformat(timespec="seconds")


def _load_datetime(value: str) -> dt.datetime:
    return dt.datetime.fromisoformat(value)


def _task_from_row(row: sqlite3.Row) -> Task:
    return Task(
        id=int(row["id"]),
        title=str(row["title"]),
        category=str(row["category"]),
        difficulty=str(row["difficulty"]),
        notes=str(row["notes"]),
        reminder_method=str(row["reminder_method"]),
        start_time=_load_datetime(str(row["start_time"])),
        is_completed=bool(row["is_completed"]),
        progress_percent=float(row["progress_percent"]),
    )


def _reminder_from_row(row: sqlite3.Row) -> Reminder:
    return Reminder(
        id=int(row["id"]),
        task_id=int(row["task_id"]),
        remind_time=_load_datetime(str(row["remind_time"])),
        reminded=bool(row["reminded"]),
    )
