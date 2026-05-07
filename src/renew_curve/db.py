from __future__ import annotations

import datetime as dt
import os
import sqlite3
from pathlib import Path
from typing import Iterable

from renew_curve.models import (
    Reminder,
    ReminderDraft,
    ReminderItem,
    ReportStats,
    Task,
    TaskDraft,
)
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

    def next_pending_reminder(self, task_id: int) -> Reminder | None:
        row = self._conn.execute(
            """
            SELECT id, task_id, remind_time, reminded
            FROM reminders
            WHERE task_id = ? AND reminded = 0
            ORDER BY remind_time, id
            LIMIT 1
            """,
            (task_id,),
        ).fetchone()
        return None if row is None else _reminder_from_row(row)

    def list_due_reminders_for_date(self, day: dt.date) -> list[ReminderItem]:
        start = dt.datetime.combine(day, dt.time.min)
        end = start + dt.timedelta(days=1)
        rows = self._conn.execute(
            """
            SELECT
                reminders.id AS reminder_id,
                reminders.task_id,
                reminders.remind_time,
                tasks.title,
                tasks.category,
                tasks.difficulty,
                tasks.notes,
                tasks.progress_percent,
                (
                    SELECT COUNT(*)
                    FROM reminders AS earlier
                    WHERE earlier.task_id = reminders.task_id
                      AND earlier.remind_time <= reminders.remind_time
                ) AS review_index,
                (
                    SELECT COUNT(*)
                    FROM reminders AS all_reviews
                    WHERE all_reviews.task_id = reminders.task_id
                ) AS total_reviews
            FROM reminders
            JOIN tasks ON tasks.id = reminders.task_id
            WHERE reminders.reminded = 0
              AND reminders.remind_time >= ?
              AND reminders.remind_time < ?
            ORDER BY reminders.remind_time, reminders.id
            """,
            (_dump_datetime(start), _dump_datetime(end)),
        )
        return [
            ReminderItem(
                reminder_id=int(row["reminder_id"]),
                task_id=int(row["task_id"]),
                task_title=str(row["title"]),
                category=str(row["category"]),
                difficulty=str(row["difficulty"]),
                notes=str(row["notes"]),
                remind_time=_load_datetime(str(row["remind_time"])),
                review_index=int(row["review_index"]),
                total_reviews=int(row["total_reviews"]),
                progress_percent=float(row["progress_percent"]),
            )
            for row in rows
        ]

    def count_pending_reminders_by_date(
        self, start_day: dt.date, days: int
    ) -> dict[dt.date, int]:
        result = {start_day + dt.timedelta(days=offset): 0 for offset in range(days)}
        start = dt.datetime.combine(start_day, dt.time.min)
        end = start + dt.timedelta(days=days)
        rows = self._conn.execute(
            """
            SELECT substr(remind_time, 1, 10) AS day_key, COUNT(*) AS count
            FROM reminders
            WHERE reminded = 0 AND remind_time >= ? AND remind_time < ?
            GROUP BY day_key
            """,
            (_dump_datetime(start), _dump_datetime(end)),
        )
        for row in rows:
            result[dt.date.fromisoformat(str(row["day_key"]))] = int(row["count"])
        return result

    def list_categories(self) -> list[str]:
        rows = self._conn.execute(
            """
            SELECT DISTINCT category
            FROM tasks
            WHERE trim(category) != ''
            ORDER BY category
            """
        )
        return [str(row["category"]) for row in rows]

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

    def snooze_reminder(self, reminder_id: int, remind_time: dt.datetime) -> None:
        row = self._conn.execute(
            "SELECT task_id FROM reminders WHERE id = ?", (reminder_id,)
        ).fetchone()
        if row is None:
            return

        self._conn.execute(
            "UPDATE reminders SET remind_time = ?, reminded = 0 WHERE id = ?",
            (_dump_datetime(remind_time), reminder_id),
        )
        self.recalculate_task_progress(int(row["task_id"]))

    def snooze_reminder_group(self, reminder_id: int, delta: dt.timedelta) -> int:
        row = self._conn.execute(
            "SELECT task_id, remind_time FROM reminders WHERE id = ? AND reminded = 0",
            (reminder_id,),
        ).fetchone()
        if row is None:
            return 0

        task_id = int(row["task_id"])
        current_time = _load_datetime(str(row["remind_time"]))
        pending = self._conn.execute(
            """
            SELECT id, remind_time
            FROM reminders
            WHERE task_id = ? AND reminded = 0 AND remind_time >= ?
            ORDER BY remind_time, id
            """,
            (task_id, _dump_datetime(current_time)),
        ).fetchall()
        for item in pending:
            new_time = _load_datetime(str(item["remind_time"])) + delta
            self._conn.execute(
                "UPDATE reminders SET remind_time = ? WHERE id = ?",
                (_dump_datetime(new_time), int(item["id"])),
            )
        self.recalculate_task_progress(task_id)
        return len(pending)

    def report_stats(self, today: dt.date) -> ReportStats:
        total_tasks = int(self._conn.execute("SELECT COUNT(*) FROM tasks").fetchone()[0])
        start = dt.datetime.combine(today, dt.time.min)
        end = start + dt.timedelta(days=1)
        today_reminders = int(
            self._conn.execute(
                """
                SELECT COUNT(*)
                FROM reminders
                WHERE reminded = 0 AND remind_time >= ? AND remind_time < ?
                """,
                (_dump_datetime(start), _dump_datetime(end)),
            ).fetchone()[0]
        )
        pending = int(
            self._conn.execute(
                "SELECT COUNT(*) FROM reminders WHERE reminded = 0"
            ).fetchone()[0]
        )
        completed = int(
            self._conn.execute(
                "SELECT COUNT(*) FROM reminders WHERE reminded = 1"
            ).fetchone()[0]
        )
        total = pending + completed
        return ReportStats(
            total_tasks=total_tasks,
            today_reminders=today_reminders,
            pending_reminders=pending,
            completed_reminders=completed,
            total_completion_percent=calculate_progress_percent(total, completed),
        )

    def weekly_completion_rate(self, end_day: dt.date) -> tuple[int, int, float]:
        start_day = end_day - dt.timedelta(days=6)
        start = dt.datetime.combine(start_day, dt.time.min)
        end = dt.datetime.combine(end_day + dt.timedelta(days=1), dt.time.min)
        row = self._conn.execute(
            """
            SELECT COUNT(*) AS total, COALESCE(SUM(reminded), 0) AS completed
            FROM reminders
            WHERE remind_time >= ? AND remind_time < ?
            """,
            (_dump_datetime(start), _dump_datetime(end)),
        ).fetchone()
        completed = int(row["completed"])
        total = int(row["total"])
        return completed, total, calculate_progress_percent(total, completed)

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
