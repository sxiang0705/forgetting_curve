from __future__ import annotations

import csv
import datetime as dt
import os
import uuid
from dataclasses import dataclass
from pathlib import Path

from renew_curve.db import ReminderRepository, connect, init_db
from renew_curve.models import ImportSummary, ReminderDraft, TaskDraft


REQUIRED_COLUMNS = (
    "record_type",
    "id",
    "task_id",
    "title",
    "category",
    "difficulty",
    "notes",
    "reminder_method",
    "start_time",
    "is_completed",
    "progress_percent",
    "remind_time",
    "reminded",
)


@dataclass(frozen=True)
class _LegacyTask:
    legacy_id: int
    draft: TaskDraft
    is_completed: bool
    progress_percent: float


@dataclass(frozen=True)
class _LegacyReminder:
    legacy_id: int
    legacy_task_id: int
    remind_time: dt.datetime
    reminded: bool


@dataclass(frozen=True)
class _LegacyRows:
    tasks: list[_LegacyTask]
    reminders: list[_LegacyReminder]


def import_legacy_csv(
    csv_path: os.PathLike[str] | str,
    db_path: os.PathLike[str] | str,
    *,
    mode: str,
) -> ImportSummary:
    if mode not in {"replace", "merge"}:
        raise ValueError(f"unsupported import mode: {mode}")

    rows = _parse_legacy_csv(Path(csv_path))
    target = Path(db_path)
    if mode == "replace":
        return _replace_import(rows, target)
    return _merge_import(rows, target)


def export_legacy_csv(
    db_path: os.PathLike[str] | str,
    csv_path: os.PathLike[str] | str,
) -> None:
    conn = connect(db_path)
    try:
        init_db(conn)
        task_rows = conn.execute(
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
        ).fetchall()
        reminder_rows = conn.execute(
            """
            SELECT id, task_id, remind_time, reminded
            FROM reminders
            ORDER BY task_id, remind_time, id
            """
        ).fetchall()
    finally:
        conn.close()

    output = Path(csv_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=REQUIRED_COLUMNS)
        writer.writeheader()
        for row in task_rows:
            writer.writerow(
                {
                    "record_type": "task",
                    "id": row["id"],
                    "task_id": "",
                    "title": row["title"],
                    "category": row["category"],
                    "difficulty": row["difficulty"],
                    "notes": row["notes"],
                    "reminder_method": row["reminder_method"],
                    "start_time": row["start_time"],
                    "is_completed": int(row["is_completed"]),
                    "progress_percent": float(row["progress_percent"]),
                    "remind_time": "",
                    "reminded": "",
                }
            )
        for row in reminder_rows:
            writer.writerow(
                {
                    "record_type": "reminder",
                    "id": row["id"],
                    "task_id": row["task_id"],
                    "title": "",
                    "category": "",
                    "difficulty": "",
                    "notes": "",
                    "reminder_method": "",
                    "start_time": "",
                    "is_completed": "",
                    "progress_percent": "",
                    "remind_time": row["remind_time"],
                    "reminded": int(row["reminded"]),
                }
            )


def _replace_import(rows: _LegacyRows, db_path: Path) -> ImportSummary:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    temp_db = db_path.with_name(f".{db_path.name}.{uuid.uuid4().hex}.tmp")
    settings = _read_existing_settings(db_path)
    try:
        _write_rows(temp_db, rows, store_legacy_ids=True)
        _write_settings(temp_db, settings)
        os.replace(temp_db, db_path)
    finally:
        if temp_db.exists():
            temp_db.unlink()
    return ImportSummary(
        tasks=len(rows.tasks), reminders=len(rows.reminders), mode="replace"
    )


def _merge_import(rows: _LegacyRows, db_path: Path) -> ImportSummary:
    _write_rows(db_path, rows, store_legacy_ids=False)
    return ImportSummary(
        tasks=len(rows.tasks), reminders=len(rows.reminders), mode="merge"
    )


def _write_rows(db_path: Path, rows: _LegacyRows, *, store_legacy_ids: bool) -> None:
    conn = connect(db_path)
    try:
        init_db(conn)
        repo = ReminderRepository(conn)
        with conn:
            id_map: dict[int, int] = {}
            for task in rows.tasks:
                new_id = repo.create_task(
                    task.draft,
                    legacy_id=str(task.legacy_id) if store_legacy_ids else None,
                    is_completed=task.is_completed,
                )
                id_map[task.legacy_id] = new_id

            for reminder in rows.reminders:
                task_id = id_map[reminder.legacy_task_id]
                repo.create_reminder(
                    ReminderDraft(
                        task_id=task_id,
                        remind_time=reminder.remind_time,
                        reminded=reminder.reminded,
                    ),
                    legacy_id=str(reminder.legacy_id) if store_legacy_ids else None,
                )

            for task_id in id_map.values():
                repo.recalculate_task_progress(task_id)
    finally:
        conn.close()


def _read_existing_settings(db_path: Path) -> dict[str, str]:
    if not db_path.exists():
        return {}

    conn = connect(db_path)
    try:
        init_db(conn)
        rows = conn.execute("SELECT key, value FROM settings").fetchall()
        return {str(row["key"]): str(row["value"]) for row in rows}
    finally:
        conn.close()


def _write_settings(db_path: Path, settings: dict[str, str]) -> None:
    if not settings:
        return

    conn = connect(db_path)
    try:
        init_db(conn)
        repo = ReminderRepository(conn)
        with conn:
            for key, value in settings.items():
                repo.set_setting(key, value)
    finally:
        conn.close()


def _parse_legacy_csv(csv_path: Path) -> _LegacyRows:
    with csv_path.open("r", newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        fieldnames = set(reader.fieldnames or [])
        missing = set(REQUIRED_COLUMNS) - fieldnames
        if missing:
            raise ValueError(
                "missing required columns: " + ", ".join(sorted(missing))
            )

        tasks: list[_LegacyTask] = []
        reminders: list[_LegacyReminder] = []
        for line_number, row in enumerate(reader, start=2):
            record_type = _required_text(row, "record_type", line_number)
            if record_type == "task":
                tasks.append(_parse_task(row, line_number))
            elif record_type == "reminder":
                reminders.append(_parse_reminder(row, line_number))
            else:
                raise ValueError(
                    f"unsupported record_type on line {line_number}: {record_type}"
                )

    task_ids = {task.legacy_id for task in tasks}
    for reminder in reminders:
        if reminder.legacy_task_id not in task_ids:
            raise ValueError(
                f"reminder {reminder.legacy_id} references unknown task "
                f"{reminder.legacy_task_id}"
            )

    return _LegacyRows(tasks=tasks, reminders=reminders)


def _parse_task(row: dict[str, str], line_number: int) -> _LegacyTask:
    return _LegacyTask(
        legacy_id=_parse_int(row, "id", line_number),
        draft=TaskDraft(
            title=_required_text(row, "title", line_number),
            category=row["category"],
            difficulty=row["difficulty"],
            notes=row["notes"],
            reminder_method=row["reminder_method"],
            start_time=_parse_datetime(row, "start_time", line_number),
        ),
        is_completed=_parse_bool(row, "is_completed", line_number),
        progress_percent=_parse_float(row, "progress_percent", line_number),
    )


def _parse_reminder(row: dict[str, str], line_number: int) -> _LegacyReminder:
    return _LegacyReminder(
        legacy_id=_parse_int(row, "id", line_number),
        legacy_task_id=_parse_int(row, "task_id", line_number),
        remind_time=_parse_datetime(row, "remind_time", line_number),
        reminded=_parse_bool(row, "reminded", line_number),
    )


def _required_text(row: dict[str, str], column: str, line_number: int) -> str:
    value = row[column]
    if value == "":
        raise ValueError(f"missing required value for {column} on line {line_number}")
    return value


def _parse_int(row: dict[str, str], column: str, line_number: int) -> int:
    value = _required_text(row, column, line_number)
    try:
        return int(value)
    except ValueError as exc:
        raise ValueError(
            f"invalid integer for {column} on line {line_number}: {value}"
        ) from exc


def _parse_float(row: dict[str, str], column: str, line_number: int) -> float:
    value = _required_text(row, column, line_number)
    try:
        return float(value)
    except ValueError as exc:
        raise ValueError(
            f"invalid float for {column} on line {line_number}: {value}"
        ) from exc


def _parse_bool(row: dict[str, str], column: str, line_number: int) -> bool:
    value = _required_text(row, column, line_number)
    if value == "0":
        return False
    if value == "1":
        return True
    raise ValueError(f"invalid boolean for {column} on line {line_number}: {value}")


def _parse_datetime(row: dict[str, str], column: str, line_number: int) -> dt.datetime:
    value = _required_text(row, column, line_number)
    try:
        return dt.datetime.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(
            f"invalid datetime for {column} on line {line_number}: {value}"
        ) from exc
