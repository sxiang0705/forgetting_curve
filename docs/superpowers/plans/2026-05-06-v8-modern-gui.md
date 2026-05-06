# v8 Modern GUI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a PySide6 v8 desktop app with a modern left-sidebar GUI while safely importing CSV files exported by the legacy Tkinter version.

**Architecture:** Keep `curve.py` as the legacy app and build a new `src/renew_curve` package. Implement data, scheduling, and CSV compatibility as GUI-independent modules with pytest coverage before wiring them into PySide6 widgets.

**Tech Stack:** Python 3.13, SQLite, pytest, PySide6, standard-library CSV/datetime/pathlib/dataclasses.

---

## File Map

- Modify: `.gitignore` to ignore local/generated files.
- Create: `pyproject.toml` for dependencies and pytest configuration.
- Create: `src/renew_curve/__init__.py` for package metadata.
- Create: `src/renew_curve/models.py` for typed task/reminder/settings models.
- Create: `src/renew_curve/scheduler.py` for curve days, progress, due checks, and snooze calculations.
- Create: `src/renew_curve/db.py` for SQLite schema and repository operations.
- Create: `src/renew_curve/csv_compat.py` for legacy CSV import/export safety.
- Create: `src/renew_curve/app.py` for PySide6 startup.
- Create: `src/renew_curve/ui/main_window.py` for the sidebar/dashboard/calendar shell.
- Create: `src/renew_curve/ui/dialogs.py` for task and import dialogs.
- Create: `src/renew_curve/ui/theme.py` for theme, accent color, density, and stylesheet generation.
- Create: `tests/fixtures/legacy_export.csv` for a realistic legacy export.
- Create: `tests/test_scheduler.py` for curve/progress/snooze tests.
- Create: `tests/test_db.py` for database schema and repository tests.
- Create: `tests/test_csv_compat.py` for legacy import, replace/merge, safety, and export round-trip tests.
- Modify: `README.md` to document v8 usage and migration.
- Create: `update_record/curve_tool_record_v8.md` for the v8 changelog.

---

### Task 1: Scaffold v8 Package And Test Runner

**Files:**
- Modify: `.gitignore`
- Create: `pyproject.toml`
- Create: `src/renew_curve/__init__.py`
- Create: `tests/test_scheduler.py`

- [ ] **Step 1: Update ignore rules**

Add these entries to `.gitignore` without removing the existing lines:

```gitignore
.venv/
.pytest_cache/
.superpowers/
build/
dist/
*.db
*.sqlite
*.sqlite3
```

- [ ] **Step 2: Create project metadata**

Create `pyproject.toml`:

```toml
[project]
name = "renew-curve"
version = "8.0.0"
description = "Modern desktop forgetting-curve reminder tool"
requires-python = ">=3.10"
dependencies = [
  "PySide6>=6.7",
]

[project.optional-dependencies]
dev = [
  "pytest>=8.0",
]

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["src"]
```

- [ ] **Step 3: Create package marker**

Create `src/renew_curve/__init__.py`:

```python
"""v8 package for the Forgetting Curve Reminder Tool."""

__version__ = "8.0.0"
```

- [ ] **Step 4: Write first failing scheduler import test**

Create `tests/test_scheduler.py`:

```python
from renew_curve.scheduler import forgetting_curve_days


def test_forgetting_curve_days_for_five_reviews():
    assert forgetting_curve_days(5) == [1, 3, 7, 14, 30]
```

- [ ] **Step 5: Run test and verify it fails**

Run:

```powershell
python -m pytest tests/test_scheduler.py -q
```

Expected: FAIL because `renew_curve.scheduler` does not exist.

- [ ] **Step 6: Commit scaffold**

Run:

```powershell
git add .gitignore pyproject.toml src/renew_curve/__init__.py tests/test_scheduler.py
git commit -m "chore: scaffold v8 package"
```

---

### Task 2: Implement Scheduler And Progress Logic

**Files:**
- Create: `src/renew_curve/scheduler.py`
- Modify: `tests/test_scheduler.py`

- [ ] **Step 1: Expand failing scheduler tests**

Replace `tests/test_scheduler.py` with:

```python
import datetime as dt

import pytest

from renew_curve.scheduler import (
    calculate_progress_percent,
    forgetting_curve_days,
    generated_review_times,
    snooze_until,
)


def test_forgetting_curve_days_for_supported_counts():
    assert forgetting_curve_days(3) == [1, 3, 7]
    assert forgetting_curve_days(5) == [1, 3, 7, 14, 30]
    assert forgetting_curve_days(10) == [1, 3, 7, 14, 30, 60, 90, 120, 180, 365]


def test_forgetting_curve_days_rejects_unsupported_count():
    with pytest.raises(ValueError, match="review count"):
        forgetting_curve_days(2)


def test_generated_review_times_preserve_clock_time():
    start = dt.datetime(2026, 5, 6, 18, 30)
    assert generated_review_times(start, 3) == [
        dt.datetime(2026, 5, 7, 18, 30),
        dt.datetime(2026, 5, 9, 18, 30),
        dt.datetime(2026, 5, 13, 18, 30),
    ]


def test_calculate_progress_percent_handles_empty_and_partial():
    assert calculate_progress_percent(0, 0) == 0.0
    assert calculate_progress_percent(5, 0) == 0.0
    assert calculate_progress_percent(5, 2) == 40.0
    assert calculate_progress_percent(3, 3) == 100.0


def test_snooze_until_supports_expected_choices():
    now = dt.datetime(2026, 5, 6, 9, 0)
    assert snooze_until(now, "10m") == dt.datetime(2026, 5, 6, 9, 10)
    assert snooze_until(now, "1h") == dt.datetime(2026, 5, 6, 10, 0)
    assert snooze_until(now, "tomorrow") == dt.datetime(2026, 5, 7, 9, 0)
```

- [ ] **Step 2: Run tests and verify expected failures**

Run:

```powershell
python -m pytest tests/test_scheduler.py -q
```

Expected: FAIL because the new functions are missing.

- [ ] **Step 3: Implement scheduler module**

Create `src/renew_curve/scheduler.py`:

```python
from __future__ import annotations

import datetime as dt

_CURVE_DAYS = {
    3: [1, 3, 7],
    4: [1, 3, 7, 14],
    5: [1, 3, 7, 14, 30],
    6: [1, 3, 7, 14, 30, 60],
    7: [1, 3, 7, 14, 30, 60, 90],
    8: [1, 3, 7, 14, 30, 60, 90, 120],
    9: [1, 3, 7, 14, 30, 60, 90, 120, 180],
    10: [1, 3, 7, 14, 30, 60, 90, 120, 180, 365],
}


def forgetting_curve_days(review_count: int) -> list[int]:
    try:
        return list(_CURVE_DAYS[int(review_count)])
    except (KeyError, ValueError):
        raise ValueError("review count must be between 3 and 10") from None


def generated_review_times(start: dt.datetime, review_count: int) -> list[dt.datetime]:
    return [start + dt.timedelta(days=days) for days in forgetting_curve_days(review_count)]


def calculate_progress_percent(total: int, completed: int) -> float:
    if total <= 0:
        return 0.0
    bounded = max(0, min(completed, total))
    return round((bounded / total) * 100, 1)


def snooze_until(now: dt.datetime, choice: str) -> dt.datetime:
    if choice == "10m":
        return now + dt.timedelta(minutes=10)
    if choice == "1h":
        return now + dt.timedelta(hours=1)
    if choice == "tomorrow":
        return now + dt.timedelta(days=1)
    raise ValueError(f"unsupported snooze choice: {choice}")
```

- [ ] **Step 4: Run scheduler tests**

Run:

```powershell
python -m pytest tests/test_scheduler.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit scheduler**

Run:

```powershell
git add src/renew_curve/scheduler.py tests/test_scheduler.py
git commit -m "feat: add v8 scheduler logic"
```

---

### Task 3: Add Data Models And SQLite Repository

**Files:**
- Create: `src/renew_curve/models.py`
- Create: `src/renew_curve/db.py`
- Create: `tests/test_db.py`

- [ ] **Step 1: Write failing database tests**

Create `tests/test_db.py`:

```python
import datetime as dt

from renew_curve.db import ReminderRepository, connect, init_db
from renew_curve.models import ReminderDraft, TaskDraft


def test_init_db_creates_tables(tmp_path):
    db_path = tmp_path / "v8.db"
    with connect(db_path) as conn:
        init_db(conn)
        names = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }
    assert {"tasks", "reminders", "settings", "backgrounds"}.issubset(names)


def test_repository_creates_task_with_reminders_and_progress(tmp_path):
    db_path = tmp_path / "v8.db"
    with connect(db_path) as conn:
        init_db(conn)
        repo = ReminderRepository(conn)
        task_id = repo.create_task(
            TaskDraft(
                title="英文單字",
                category="英文",
                difficulty="中級",
                notes="unit 12",
                reminder_method="遺忘曲線",
                start_time=dt.datetime(2026, 5, 6, 9, 0),
            )
        )
        repo.create_reminder(ReminderDraft(task_id=task_id, remind_time=dt.datetime(2026, 5, 7, 9, 0)))
        repo.create_reminder(ReminderDraft(task_id=task_id, remind_time=dt.datetime(2026, 5, 9, 9, 0)))
        repo.mark_reminder_done(1)

        task = repo.get_task(task_id)
        reminders = repo.list_reminders(task_id)

    assert task is not None
    assert task.progress_percent == 50.0
    assert len(reminders) == 2
    assert reminders[0].reminded is True
```

- [ ] **Step 2: Run database tests and verify they fail**

Run:

```powershell
python -m pytest tests/test_db.py -q
```

Expected: FAIL because `renew_curve.db` and `renew_curve.models` do not exist.

- [ ] **Step 3: Implement models**

Create `src/renew_curve/models.py`:

```python
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass


@dataclass(frozen=True)
class TaskDraft:
    title: str
    category: str
    difficulty: str
    notes: str
    reminder_method: str
    start_time: dt.datetime


@dataclass(frozen=True)
class Task:
    id: int
    title: str
    category: str
    difficulty: str
    notes: str
    reminder_method: str
    start_time: dt.datetime
    is_completed: bool
    progress_percent: float


@dataclass(frozen=True)
class ReminderDraft:
    task_id: int
    remind_time: dt.datetime
    reminded: bool = False


@dataclass(frozen=True)
class Reminder:
    id: int
    task_id: int
    remind_time: dt.datetime
    reminded: bool


@dataclass(frozen=True)
class ImportSummary:
    tasks: int
    reminders: int
    mode: str
```

- [ ] **Step 4: Implement database repository**

Create `src/renew_curve/db.py`:

```python
from __future__ import annotations

import datetime as dt
import sqlite3
from pathlib import Path

from renew_curve.models import Reminder, ReminderDraft, Task, TaskDraft
from renew_curve.scheduler import calculate_progress_percent


def connect(db_path: str | Path) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            category TEXT NOT NULL DEFAULT '',
            difficulty TEXT NOT NULL DEFAULT '',
            notes TEXT NOT NULL DEFAULT '',
            reminder_method TEXT NOT NULL DEFAULT '',
            start_time TEXT NOT NULL,
            is_completed INTEGER NOT NULL DEFAULT 0,
            progress_percent REAL NOT NULL DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS reminders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id INTEGER NOT NULL,
            remind_time TEXT NOT NULL,
            reminded INTEGER NOT NULL DEFAULT 0,
            FOREIGN KEY(task_id) REFERENCES tasks(id) ON DELETE CASCADE
        );
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS backgrounds (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT NOT NULL,
            path TEXT NOT NULL,
            upload_time TEXT NOT NULL,
            is_active INTEGER NOT NULL DEFAULT 0
        );
        CREATE INDEX IF NOT EXISTS idx_reminders_due ON reminders(reminded, remind_time);
        CREATE INDEX IF NOT EXISTS idx_reminders_task ON reminders(task_id);
        CREATE INDEX IF NOT EXISTS idx_tasks_filter ON tasks(is_completed, category);
        """
    )
    conn.commit()


class ReminderRepository:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def create_task(self, draft: TaskDraft, *, legacy_id: int | None = None, is_completed: bool = False) -> int:
        fields = "title, category, difficulty, notes, reminder_method, start_time, is_completed"
        values = [
            draft.title,
            draft.category,
            draft.difficulty,
            draft.notes,
            draft.reminder_method,
            draft.start_time.isoformat(),
            1 if is_completed else 0,
        ]
        if legacy_id is not None:
            fields = "id, " + fields
            values = [legacy_id, *values]
        cur = self.conn.execute(
            f"INSERT INTO tasks ({fields}) VALUES ({','.join(['?'] * len(values))})",
            values,
        )
        self.conn.commit()
        return int(legacy_id if legacy_id is not None else cur.lastrowid)

    def create_reminder(self, draft: ReminderDraft, *, legacy_id: int | None = None) -> int:
        fields = "task_id, remind_time, reminded"
        values = [draft.task_id, draft.remind_time.isoformat(), 1 if draft.reminded else 0]
        if legacy_id is not None:
            fields = "id, " + fields
            values = [legacy_id, *values]
        cur = self.conn.execute(
            f"INSERT INTO reminders ({fields}) VALUES ({','.join(['?'] * len(values))})",
            values,
        )
        self.conn.commit()
        self.recalculate_task_progress(draft.task_id)
        return int(legacy_id if legacy_id is not None else cur.lastrowid)

    def get_task(self, task_id: int) -> Task | None:
        row = self.conn.execute(
            "SELECT id, title, category, difficulty, notes, reminder_method, start_time, is_completed, progress_percent FROM tasks WHERE id=?",
            (task_id,),
        ).fetchone()
        if row is None:
            return None
        return Task(
            id=row[0],
            title=row[1],
            category=row[2],
            difficulty=row[3],
            notes=row[4],
            reminder_method=row[5],
            start_time=dt.datetime.fromisoformat(row[6]),
            is_completed=bool(row[7]),
            progress_percent=float(row[8]),
        )

    def list_tasks(self) -> list[Task]:
        ids = [row[0] for row in self.conn.execute("SELECT id FROM tasks ORDER BY id")]
        return [task for task_id in ids if (task := self.get_task(task_id)) is not None]

    def list_reminders(self, task_id: int | None = None) -> list[Reminder]:
        if task_id is None:
            rows = self.conn.execute("SELECT id, task_id, remind_time, reminded FROM reminders ORDER BY id").fetchall()
        else:
            rows = self.conn.execute(
                "SELECT id, task_id, remind_time, reminded FROM reminders WHERE task_id=? ORDER BY id",
                (task_id,),
            ).fetchall()
        return [
            Reminder(id=row[0], task_id=row[1], remind_time=dt.datetime.fromisoformat(row[2]), reminded=bool(row[3]))
            for row in rows
        ]

    def mark_reminder_done(self, reminder_id: int) -> None:
        row = self.conn.execute("SELECT task_id FROM reminders WHERE id=?", (reminder_id,)).fetchone()
        if row is None:
            return
        task_id = int(row[0])
        self.conn.execute("UPDATE reminders SET reminded=1 WHERE id=?", (reminder_id,))
        self.conn.commit()
        self.recalculate_task_progress(task_id)

    def recalculate_task_progress(self, task_id: int) -> None:
        total = self.conn.execute("SELECT COUNT(*) FROM reminders WHERE task_id=?", (task_id,)).fetchone()[0]
        done = self.conn.execute("SELECT COUNT(*) FROM reminders WHERE task_id=? AND reminded=1", (task_id,)).fetchone()[0]
        percent = calculate_progress_percent(total, done)
        is_completed = 1 if total > 0 and done == total else 0
        self.conn.execute(
            "UPDATE tasks SET progress_percent=?, is_completed=? WHERE id=?",
            (percent, is_completed, task_id),
        )
        self.conn.commit()
```

- [ ] **Step 5: Run database tests**

Run:

```powershell
python -m pytest tests/test_db.py -q
```

Expected: PASS.

- [ ] **Step 6: Run scheduler and database tests together**

Run:

```powershell
python -m pytest tests/test_scheduler.py tests/test_db.py -q
```

Expected: PASS.

- [ ] **Step 7: Commit models and database**

Run:

```powershell
git add src/renew_curve/models.py src/renew_curve/db.py tests/test_db.py
git commit -m "feat: add v8 sqlite repository"
```

---

### Task 4: Implement Legacy CSV Compatibility

**Files:**
- Create: `tests/fixtures/legacy_export.csv`
- Create: `tests/test_csv_compat.py`
- Create: `src/renew_curve/csv_compat.py`

- [ ] **Step 1: Add legacy CSV fixture**

Create `tests/fixtures/legacy_export.csv`:

```csv
record_type,id,task_id,title,category,difficulty,notes,reminder_method,start_time,is_completed,progress_percent,remind_time,reminded
task,1,,英文單字 Unit 12,英文單字,中級,legacy notes,遺忘曲線,2026-05-01T09:00:00,0,50.0,,
task,2,,Python async,程式技能,高級,,手動輸入,2026-05-02T10:00:00,1,100.0,,
reminder,10,1,,,,,,,,2026-05-02T09:00:00,1
reminder,11,1,,,,,,,,2026-05-04T09:00:00,0
reminder,12,2,,,,,,,,2026-05-03T10:00:00,1
```

- [ ] **Step 2: Write failing CSV compatibility tests**

Create `tests/test_csv_compat.py`:

```python
import csv
from pathlib import Path

import pytest

from renew_curve.csv_compat import export_legacy_csv, import_legacy_csv
from renew_curve.db import ReminderRepository, connect, init_db


FIXTURE = Path(__file__).parent / "fixtures" / "legacy_export.csv"


def test_legacy_csv_imports_into_fresh_database(tmp_path):
    db_path = tmp_path / "v8.db"

    summary = import_legacy_csv(FIXTURE, db_path, mode="replace")

    with connect(db_path) as conn:
        repo = ReminderRepository(conn)
        tasks = repo.list_tasks()
        reminders = repo.list_reminders()

    assert summary.tasks == 2
    assert summary.reminders == 3
    assert [task.title for task in tasks] == ["英文單字 Unit 12", "Python async"]
    assert tasks[0].progress_percent == 50.0
    assert tasks[1].is_completed is True
    assert reminders[1].task_id == 1


def test_import_failure_leaves_existing_database_unchanged(tmp_path):
    db_path = tmp_path / "v8.db"
    bad_csv = tmp_path / "bad.csv"
    bad_csv.write_text("record_type,id,title\nbad,1,nope\n", encoding="utf-8")

    with connect(db_path) as conn:
        init_db(conn)
        repo = ReminderRepository(conn)

    with pytest.raises(ValueError, match="missing required"):
        import_legacy_csv(bad_csv, db_path, mode="replace")

    with connect(db_path) as conn:
        repo = ReminderRepository(conn)
        assert repo.list_tasks() == []


def test_merge_import_remaps_ids(tmp_path):
    db_path = tmp_path / "v8.db"
    import_legacy_csv(FIXTURE, db_path, mode="replace")
    summary = import_legacy_csv(FIXTURE, db_path, mode="merge")

    with connect(db_path) as conn:
        repo = ReminderRepository(conn)
        tasks = repo.list_tasks()
        reminders = repo.list_reminders()

    assert summary.tasks == 2
    assert len(tasks) == 4
    assert len(reminders) == 6
    assert max(task.id for task in tasks) > 2
    assert all(reminder.task_id in {task.id for task in tasks} for reminder in reminders)


def test_export_round_trip_preserves_legacy_columns(tmp_path):
    db_path = tmp_path / "v8.db"
    out_csv = tmp_path / "export.csv"
    round_trip_db = tmp_path / "round-trip.db"

    import_legacy_csv(FIXTURE, db_path, mode="replace")
    export_legacy_csv(db_path, out_csv)

    with out_csv.open("r", newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        assert {"record_type", "id", "task_id", "title", "remind_time", "reminded"}.issubset(reader.fieldnames or [])

    import_legacy_csv(out_csv, round_trip_db, mode="replace")
    with connect(round_trip_db) as conn:
        repo = ReminderRepository(conn)
        assert len(repo.list_tasks()) == 2
        assert len(repo.list_reminders()) == 3
```

- [ ] **Step 3: Run CSV tests and verify they fail**

Run:

```powershell
python -m pytest tests/test_csv_compat.py -q
```

Expected: FAIL because `renew_curve.csv_compat` does not exist.

- [ ] **Step 4: Implement CSV compatibility module**

Create `src/renew_curve/csv_compat.py` with these functions:

```python
from __future__ import annotations

import csv
import datetime as dt
import os
import sqlite3
import tempfile
from pathlib import Path

from renew_curve.db import ReminderRepository, connect, init_db
from renew_curve.models import ImportSummary, ReminderDraft, TaskDraft

REQUIRED_COLUMNS = {
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
}


def _read_rows(csv_path: str | Path) -> list[dict[str, str]]:
    with Path(csv_path).open("r", newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        fieldnames = set(reader.fieldnames or [])
        missing = REQUIRED_COLUMNS - fieldnames
        if missing:
            raise ValueError(f"missing required CSV columns: {', '.join(sorted(missing))}")
        return [dict(row) for row in reader]


def _parse_bool(value: str, *, field: str) -> bool:
    if value in ("", None):
        return False
    if str(value) in ("0", "1"):
        return str(value) == "1"
    raise ValueError(f"invalid {field}: {value}")


def _parse_int(value: str, *, field: str) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        raise ValueError(f"invalid {field}: {value}") from None


def _parse_datetime(value: str, *, field: str) -> dt.datetime:
    try:
        return dt.datetime.fromisoformat(value)
    except (TypeError, ValueError):
        raise ValueError(f"invalid {field}: {value}") from None


def _load_into_connection(rows: list[dict[str, str]], conn: sqlite3.Connection, *, mode: str) -> ImportSummary:
    repo = ReminderRepository(conn)
    task_rows = [row for row in rows if row.get("record_type") == "task"]
    reminder_rows = [row for row in rows if row.get("record_type") == "reminder"]
    if len(task_rows) + len(reminder_rows) != len(rows):
        raise ValueError("CSV contains unsupported record_type values")

    id_map: dict[int, int] = {}
    for row in task_rows:
        legacy_id = _parse_int(row["id"], field="task id")
        task_id = repo.create_task(
            TaskDraft(
                title=row.get("title", "").strip(),
                category=row.get("category", "").strip(),
                difficulty=row.get("difficulty", "").strip(),
                notes=row.get("notes", ""),
                reminder_method=row.get("reminder_method", ""),
                start_time=_parse_datetime(row.get("start_time", ""), field="start_time"),
            ),
            legacy_id=legacy_id if mode == "replace" else None,
            is_completed=_parse_bool(row.get("is_completed", "0"), field="is_completed"),
        )
        id_map[legacy_id] = task_id

    for row in reminder_rows:
        legacy_task_id = _parse_int(row.get("task_id", ""), field="task_id")
        if legacy_task_id not in id_map:
            raise ValueError(f"reminder references unknown task_id: {legacy_task_id}")
        repo.create_reminder(
            ReminderDraft(
                task_id=id_map[legacy_task_id],
                remind_time=_parse_datetime(row.get("remind_time", ""), field="remind_time"),
                reminded=_parse_bool(row.get("reminded", "0"), field="reminded"),
            ),
            legacy_id=_parse_int(row["id"], field="reminder id") if mode == "replace" else None,
        )

    for task_id in id_map.values():
        repo.recalculate_task_progress(task_id)
    return ImportSummary(tasks=len(task_rows), reminders=len(reminder_rows), mode=mode)


def import_legacy_csv(csv_path: str | Path, db_path: str | Path, *, mode: str) -> ImportSummary:
    if mode not in {"replace", "merge"}:
        raise ValueError("mode must be 'replace' or 'merge'")
    rows = _read_rows(csv_path)
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    if mode == "replace":
        fd, tmp_name = tempfile.mkstemp(prefix=db_path.stem + "-", suffix=".db", dir=str(db_path.parent))
        os.close(fd)
        tmp_path = Path(tmp_name)
        try:
            with connect(tmp_path) as conn:
                init_db(conn)
                summary = _load_into_connection(rows, conn, mode=mode)
            os.replace(tmp_path, db_path)
            return summary
        finally:
            if tmp_path.exists():
                tmp_path.unlink()

    with connect(db_path) as conn:
        init_db(conn)
        return _load_into_connection(rows, conn, mode=mode)


def export_legacy_csv(db_path: str | Path, csv_path: str | Path) -> None:
    with connect(db_path) as conn:
        repo = ReminderRepository(conn)
        tasks = repo.list_tasks()
        reminders = repo.list_reminders()

    fieldnames = [
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
    ]
    with Path(csv_path).open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for task in tasks:
            writer.writerow(
                {
                    "record_type": "task",
                    "id": task.id,
                    "task_id": "",
                    "title": task.title,
                    "category": task.category,
                    "difficulty": task.difficulty,
                    "notes": task.notes,
                    "reminder_method": task.reminder_method,
                    "start_time": task.start_time.isoformat(),
                    "is_completed": 1 if task.is_completed else 0,
                    "progress_percent": task.progress_percent,
                    "remind_time": "",
                    "reminded": "",
                }
            )
        for reminder in reminders:
            writer.writerow(
                {
                    "record_type": "reminder",
                    "id": reminder.id,
                    "task_id": reminder.task_id,
                    "title": "",
                    "category": "",
                    "difficulty": "",
                    "notes": "",
                    "reminder_method": "",
                    "start_time": "",
                    "is_completed": "",
                    "progress_percent": "",
                    "remind_time": reminder.remind_time.isoformat(),
                    "reminded": 1 if reminder.reminded else 0,
                }
            )
```

- [ ] **Step 5: Run CSV tests**

Run:

```powershell
python -m pytest tests/test_csv_compat.py -q
```

Expected: PASS.

- [ ] **Step 6: Run all non-GUI tests**

Run:

```powershell
python -m pytest tests/test_scheduler.py tests/test_db.py tests/test_csv_compat.py -q
```

Expected: PASS.

- [ ] **Step 7: Commit CSV compatibility**

Run:

```powershell
git add src/renew_curve/csv_compat.py tests/test_csv_compat.py tests/fixtures/legacy_export.csv
git commit -m "feat: support legacy csv migration"
```

---

### Task 5: Build PySide6 Main Window Shell

**Files:**
- Create: `src/renew_curve/app.py`
- Create: `src/renew_curve/ui/__init__.py`
- Create: `src/renew_curve/ui/theme.py`
- Create: `src/renew_curve/ui/main_window.py`
- Create: `tests/test_gui_imports.py`

- [ ] **Step 1: Write failing GUI import smoke test**

Create `tests/test_gui_imports.py`:

```python
def test_main_window_imports_without_starting_event_loop():
    from renew_curve.ui.main_window import MainWindow

    assert MainWindow.__name__ == "MainWindow"
```

- [ ] **Step 2: Run GUI import test and verify failure**

Run:

```powershell
python -m pytest tests/test_gui_imports.py -q
```

Expected: FAIL because `renew_curve.ui.main_window` does not exist.

- [ ] **Step 3: Create UI package marker**

Create `src/renew_curve/ui/__init__.py`:

```python
"""PySide6 UI components for v8."""
```

- [ ] **Step 4: Create theme stylesheet helper**

Create `src/renew_curve/ui/theme.py`:

```python
from __future__ import annotations

ACCENTS = {
    "blue": "#2563eb",
    "green": "#16a34a",
    "purple": "#7c3aed",
    "orange": "#f97316",
    "gray": "#475569",
}


def build_stylesheet(*, accent: str = "blue", dark: bool = False, compact: bool = False) -> str:
    primary = ACCENTS.get(accent, ACCENTS["blue"])
    bg = "#0f172a" if dark else "#f6f8fb"
    panel = "#111827" if dark else "#ffffff"
    text = "#e5e7eb" if dark else "#111827"
    muted = "#94a3b8" if dark else "#64748b"
    row_padding = "6px" if compact else "10px"
    return f"""
    QMainWindow {{
        background: {bg};
        color: {text};
        font-family: "Microsoft JhengHei UI", "Microsoft JhengHei", "Segoe UI";
    }}
    QWidget {{
        color: {text};
        font-size: 14px;
    }}
    #Sidebar {{
        background: #18212f;
        border-radius: 10px;
    }}
    QPushButton {{
        border: 0;
        border-radius: 8px;
        padding: {row_padding};
        background: #e5e7eb;
        color: #111827;
    }}
    QPushButton#PrimaryButton {{
        background: {primary};
        color: white;
        font-weight: 700;
    }}
    QFrame#Panel {{
        background: {panel};
        border: 1px solid rgba(148, 163, 184, 0.28);
        border-radius: 10px;
    }}
    QLabel#Muted {{
        color: {muted};
    }}
    QTableWidget {{
        background: {panel};
        border: 1px solid rgba(148, 163, 184, 0.28);
        border-radius: 10px;
        gridline-color: rgba(148, 163, 184, 0.25);
    }}
    """
```

- [ ] **Step 5: Create main window shell**

Create `src/renew_curve/ui/main_window.py`:

```python
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCalendarWidget,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from renew_curve.db import ReminderRepository, connect, init_db
from renew_curve.ui.theme import build_stylesheet


class MainWindow(QMainWindow):
    def __init__(self, db_path: str | Path = "renew_curve_v8.db"):
        super().__init__()
        self.db_path = Path(db_path)
        with connect(self.db_path) as conn:
            init_db(conn)
        self.setWindowTitle("Forgetting Curve v8")
        self.resize(1180, 720)
        self.setStyleSheet(build_stylesheet())
        self._build_ui()
        self.refresh_tasks()

    def _build_ui(self) -> None:
        root = QWidget()
        layout = QHBoxLayout(root)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(12)

        self.sidebar = self._build_sidebar()
        self.center = self._build_center()
        self.right_panel = self._build_right_panel()

        layout.addWidget(self.sidebar, 0)
        layout.addWidget(self.center, 1)
        layout.addWidget(self.right_panel, 0)
        self.setCentralWidget(root)

    def _build_sidebar(self) -> QFrame:
        frame = QFrame()
        frame.setObjectName("Sidebar")
        frame.setFixedWidth(128)
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(12, 14, 12, 14)
        logo = QLabel("FC")
        logo.setStyleSheet("color: white; font-size: 24px; font-weight: 800;")
        layout.addWidget(logo)
        for label in ["Tasks", "Calendar", "Import/Export", "Settings"]:
            button = QPushButton(label)
            button.setStyleSheet("background: transparent; color: #cbd5e1; text-align: left;")
            layout.addWidget(button)
        layout.addStretch(1)
        self.dnd_button = QPushButton("DND Off")
        layout.addWidget(self.dnd_button)
        return frame

    def _build_center(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        header = QHBoxLayout()
        title = QLabel("Review planner")
        title.setStyleSheet("font-size: 24px; font-weight: 800;")
        self.search = QLineEdit()
        self.search.setPlaceholderText("Search tasks or category")
        self.new_task_button = QPushButton("New task")
        self.new_task_button.setObjectName("PrimaryButton")
        header.addWidget(title)
        header.addStretch(1)
        header.addWidget(self.search)
        header.addWidget(self.new_task_button)
        layout.addLayout(header)

        stats = QHBoxLayout()
        self.due_today = self._stat_card("Due today", "0")
        self.completed = self._stat_card("Completed", "0")
        self.overdue = self._stat_card("Overdue", "0")
        stats.addWidget(self.due_today)
        stats.addWidget(self.completed)
        stats.addWidget(self.overdue)
        layout.addLayout(stats)

        self.task_table = QTableWidget(0, 5)
        self.task_table.setHorizontalHeaderLabels(["Task", "Category", "Next", "Progress", "Status"])
        self.task_table.verticalHeader().setVisible(False)
        self.task_table.setSelectionBehavior(QTableWidget.SelectRows)
        layout.addWidget(self.task_table, 1)
        return widget

    def _build_right_panel(self) -> QWidget:
        widget = QWidget()
        widget.setFixedWidth(330)
        layout = QVBoxLayout(widget)
        self.calendar = QCalendarWidget()
        self.calendar.setGridVisible(False)
        layout.addWidget(self.calendar)
        panel = QFrame()
        panel.setObjectName("Panel")
        panel_layout = QVBoxLayout(panel)
        panel_layout.addWidget(QLabel("Selected day"))
        self.selected_day_label = QLabel("No reminders selected")
        self.selected_day_label.setObjectName("Muted")
        panel_layout.addWidget(self.selected_day_label)
        panel_layout.addStretch(1)
        layout.addWidget(panel, 1)
        return widget

    def _stat_card(self, label: str, value: str) -> QFrame:
        frame = QFrame()
        frame.setObjectName("Panel")
        layout = QVBoxLayout(frame)
        muted = QLabel(label)
        muted.setObjectName("Muted")
        number = QLabel(value)
        number.setStyleSheet("font-size: 28px; font-weight: 800;")
        layout.addWidget(muted)
        layout.addWidget(number)
        return frame

    def refresh_tasks(self) -> None:
        with connect(self.db_path) as conn:
            repo = ReminderRepository(conn)
            tasks = repo.list_tasks()
        self.task_table.setRowCount(len(tasks))
        for row, task in enumerate(tasks):
            values = [task.title, task.category, "", f"{task.progress_percent:.0f}%", "Done" if task.is_completed else "Active"]
            for col, value in enumerate(values):
                self.task_table.setItem(row, col, QTableWidgetItem(value))
        self.task_table.resizeColumnsToContents()
```

- [ ] **Step 6: Create app entrypoint**

Create `src/renew_curve/app.py`:

```python
from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from renew_curve.ui.main_window import MainWindow


def main() -> int:
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 7: Run GUI import test**

Run:

```powershell
python -m pytest tests/test_gui_imports.py -q
```

Expected: PASS if PySide6 is installed. If PySide6 is missing, install dev dependencies first with `python -m pip install -e ".[dev]"`.

- [ ] **Step 8: Run full test suite**

Run:

```powershell
python -m pytest -q
```

Expected: PASS.

- [ ] **Step 9: Commit GUI shell**

Run:

```powershell
git add src/renew_curve/app.py src/renew_curve/ui tests/test_gui_imports.py
git commit -m "feat: add pySide6 v8 main window shell"
```

---

### Task 6: Add Import/Export Dialogs And Main Window Actions

**Files:**
- Create: `src/renew_curve/ui/dialogs.py`
- Modify: `src/renew_curve/ui/main_window.py`
- Create: `tests/test_gui_actions.py`

- [ ] **Step 1: Write failing dialog import test**

Create `tests/test_gui_actions.py`:

```python
def test_dialog_classes_import():
    from renew_curve.ui.dialogs import ImportExportDialog, TaskDialog

    assert ImportExportDialog.__name__ == "ImportExportDialog"
    assert TaskDialog.__name__ == "TaskDialog"
```

- [ ] **Step 2: Run dialog test and verify failure**

Run:

```powershell
python -m pytest tests/test_gui_actions.py -q
```

Expected: FAIL because `dialogs.py` does not exist.

- [ ] **Step 3: Create dialogs**

Create `src/renew_curve/ui/dialogs.py`:

```python
from __future__ import annotations

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
)


class TaskDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("New task")
        layout = QFormLayout(self)
        self.title_edit = QLineEdit()
        self.category_edit = QLineEdit()
        self.difficulty_combo = QComboBox()
        self.difficulty_combo.addItems(["初級", "中級", "高級"])
        self.notes_edit = QTextEdit()
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["遺忘曲線", "手動輸入"])
        layout.addRow("Task name", self.title_edit)
        layout.addRow("Category", self.category_edit)
        layout.addRow("Difficulty", self.difficulty_combo)
        layout.addRow("Notes", self.notes_edit)
        layout.addRow("Reminder mode", self.mode_combo)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)


class ImportExportDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Import / Export")
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Legacy CSV files from the Tkinter version are supported."))
        row = QHBoxLayout()
        self.import_replace_button = QPushButton("Import CSV - Replace")
        self.import_merge_button = QPushButton("Import CSV - Merge")
        self.export_button = QPushButton("Export CSV")
        row.addWidget(self.import_replace_button)
        row.addWidget(self.import_merge_button)
        row.addWidget(self.export_button)
        layout.addLayout(row)

    def choose_csv_open(self) -> str:
        path, _ = QFileDialog.getOpenFileName(self, "Choose CSV", "", "CSV files (*.csv);;All files (*.*)")
        return path

    def choose_csv_save(self) -> str:
        path, _ = QFileDialog.getSaveFileName(self, "Export CSV", "forgetting_curve_v8.csv", "CSV files (*.csv)")
        return path
```

- [ ] **Step 4: Wire sidebar import/export and new-task actions**

Modify `src/renew_curve/ui/main_window.py`:

```python
from PySide6.QtWidgets import QMessageBox
from renew_curve.csv_compat import export_legacy_csv, import_legacy_csv
from renew_curve.ui.dialogs import ImportExportDialog, TaskDialog
```

Store the import/export sidebar button as `self.import_export_button` and connect:

```python
self.new_task_button.clicked.connect(self.open_task_dialog)
self.import_export_button.clicked.connect(self.open_import_export_dialog)
```

Add methods:

```python
def open_task_dialog(self) -> None:
    dialog = TaskDialog(self)
    dialog.exec()


def open_import_export_dialog(self) -> None:
    dialog = ImportExportDialog(self)
    dialog.import_replace_button.clicked.connect(lambda: self._import_csv(dialog, "replace"))
    dialog.import_merge_button.clicked.connect(lambda: self._import_csv(dialog, "merge"))
    dialog.export_button.clicked.connect(lambda: self._export_csv(dialog))
    dialog.exec()


def _import_csv(self, dialog: ImportExportDialog, mode: str) -> None:
    path = dialog.choose_csv_open()
    if not path:
        return
    try:
        summary = import_legacy_csv(path, self.db_path, mode=mode)
    except Exception as exc:
        QMessageBox.critical(self, "Import failed", str(exc))
        return
    self.refresh_tasks()
    QMessageBox.information(self, "Import complete", f"Imported {summary.tasks} tasks and {summary.reminders} reminders.")


def _export_csv(self, dialog: ImportExportDialog) -> None:
    path = dialog.choose_csv_save()
    if not path:
        return
    try:
        export_legacy_csv(self.db_path, path)
    except Exception as exc:
        QMessageBox.critical(self, "Export failed", str(exc))
        return
    QMessageBox.information(self, "Export complete", "CSV export finished.")
```

- [ ] **Step 5: Run GUI action tests**

Run:

```powershell
python -m pytest tests/test_gui_actions.py tests/test_gui_imports.py -q
```

Expected: PASS.

- [ ] **Step 6: Run full test suite**

Run:

```powershell
python -m pytest -q
```

Expected: PASS.

- [ ] **Step 7: Commit import/export UI**

Run:

```powershell
git add src/renew_curve/ui/dialogs.py src/renew_curve/ui/main_window.py tests/test_gui_actions.py
git commit -m "feat: add v8 import export dialogs"
```

---

### Task 7: Add Personalization Settings

**Files:**
- Modify: `src/renew_curve/db.py`
- Modify: `src/renew_curve/ui/theme.py`
- Modify: `src/renew_curve/ui/main_window.py`
- Modify: `src/renew_curve/ui/dialogs.py`
- Create: `tests/test_settings.py`

- [ ] **Step 1: Write failing settings tests**

Create `tests/test_settings.py`:

```python
from renew_curve.db import ReminderRepository, connect, init_db


def test_settings_round_trip(tmp_path):
    db_path = tmp_path / "settings.db"
    with connect(db_path) as conn:
        init_db(conn)
        repo = ReminderRepository(conn)
        repo.set_setting("theme", "dark")
        repo.set_setting("accent", "green")
        assert repo.get_setting("theme", "light") == "dark"
        assert repo.get_setting("accent", "blue") == "green"
        assert repo.get_setting("density", "comfortable") == "comfortable"
```

- [ ] **Step 2: Run settings test and verify failure**

Run:

```powershell
python -m pytest tests/test_settings.py -q
```

Expected: FAIL because repository settings methods are missing.

- [ ] **Step 3: Add settings methods to repository**

Add to `ReminderRepository` in `src/renew_curve/db.py`:

```python
def set_setting(self, key: str, value: str) -> None:
    self.conn.execute(
        "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
        (key, value),
    )
    self.conn.commit()


def get_setting(self, key: str, default: str = "") -> str:
    row = self.conn.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
    return default if row is None else str(row[0])
```

- [ ] **Step 4: Run settings tests**

Run:

```powershell
python -m pytest tests/test_settings.py -q
```

Expected: PASS.

- [ ] **Step 5: Add settings UI**

Add a `SettingsDialog` to `src/renew_curve/ui/dialogs.py` with combo boxes for theme, accent, density, and default snooze:

```python
class SettingsDialog(QDialog):
    def __init__(self, parent=None, values: dict[str, str] | None = None):
        super().__init__(parent)
        values = values or {}
        self.setWindowTitle("Personalization")
        layout = QFormLayout(self)
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["light", "dark", "system"])
        self.theme_combo.setCurrentText(values.get("theme", "light"))
        self.accent_combo = QComboBox()
        self.accent_combo.addItems(["blue", "green", "purple", "orange", "gray"])
        self.accent_combo.setCurrentText(values.get("accent", "blue"))
        self.density_combo = QComboBox()
        self.density_combo.addItems(["comfortable", "compact"])
        self.density_combo.setCurrentText(values.get("density", "comfortable"))
        self.snooze_combo = QComboBox()
        self.snooze_combo.addItems(["10m", "1h", "tomorrow"])
        self.snooze_combo.setCurrentText(values.get("default_snooze", "1h"))
        layout.addRow("Theme", self.theme_combo)
        layout.addRow("Accent", self.accent_combo)
        layout.addRow("Task density", self.density_combo)
        layout.addRow("Default snooze", self.snooze_combo)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def values(self) -> dict[str, str]:
        return {
            "theme": self.theme_combo.currentText(),
            "accent": self.accent_combo.currentText(),
            "density": self.density_combo.currentText(),
            "default_snooze": self.snooze_combo.currentText(),
        }
```

- [ ] **Step 6: Wire settings sidebar action**

In `MainWindow`, import `SettingsDialog`, store the settings sidebar button as `self.settings_button`, connect it to `open_settings_dialog`, and add:

```python
def open_settings_dialog(self) -> None:
    with connect(self.db_path) as conn:
        repo = ReminderRepository(conn)
        current = {
            "theme": repo.get_setting("theme", "light"),
            "accent": repo.get_setting("accent", "blue"),
            "density": repo.get_setting("density", "comfortable"),
            "default_snooze": repo.get_setting("default_snooze", "1h"),
        }
    dialog = SettingsDialog(self, current)
    if dialog.exec() != dialog.Accepted:
        return
    values = dialog.values()
    with connect(self.db_path) as conn:
        repo = ReminderRepository(conn)
        for key, value in values.items():
            repo.set_setting(key, value)
    self.setStyleSheet(build_stylesheet(accent=values["accent"], dark=values["theme"] == "dark", compact=values["density"] == "compact"))
```

- [ ] **Step 7: Run settings and GUI tests**

Run:

```powershell
python -m pytest tests/test_settings.py tests/test_gui_actions.py tests/test_gui_imports.py -q
```

Expected: PASS.

- [ ] **Step 8: Commit personalization**

Run:

```powershell
git add src/renew_curve/db.py src/renew_curve/ui/theme.py src/renew_curve/ui/main_window.py src/renew_curve/ui/dialogs.py tests/test_settings.py
git commit -m "feat: add v8 personalization settings"
```

---

### Task 8: Update Documentation And v8 Record

**Files:**
- Modify: `README.md`
- Create: `update_record/curve_tool_record_v8.md`

- [ ] **Step 1: Update README**

Modify `README.md` to include:

```markdown
## v8 Preview

v8 is a modern PySide6 desktop version of the Forgetting Curve Reminder Tool. It keeps the original learning/reminder purpose while introducing a new sidebar-based interface, safer CSV migration, and personalization settings.

### Run v8 from source

```bash
python -m pip install -e ".[dev]"
python -m renew_curve.app
```

### Import legacy CSV

CSV files exported from the legacy Tkinter version can be imported in v8 through `Import/Export`.

Two modes are available:

- Replace: validate the CSV, build a temporary database, and replace the current v8 database only after validation succeeds.
- Merge: keep existing v8 data and add the CSV tasks/reminders with remapped IDs.

If validation fails, the current v8 database is left unchanged.
```

Also clarify that report/email features are not included in the v8 scope unless they are approved as a future explicitly scoped release.

- [ ] **Step 2: Create v8 update record**

Create `update_record/curve_tool_record_v8.md`:

```markdown
# 遺忘曲線提醒工具更新紀錄（v8）

v8 是一次現代化重構版本，重點是新的 PySide6 介面與舊資料安全轉移。

## 主要更新

- 新增 PySide6/Qt 版本入口。
- 採用左側 sidebar、中央任務工作區、右側月曆的現代化桌面布局。
- 保留舊版 `curve.py` 作為 legacy 版本，降低轉換風險。
- 新增獨立資料層、排程層與 CSV 相容層。
- 支援匯入舊版 CSV 的 `task` / `reminder` 格式。
- 匯入 CSV 時先驗證與建立臨時資料庫，成功後才替換正式資料。
- 支援 CSV 覆蓋匯入與合併匯入。
- 新增主題、強調色、列表密度與預設稍後提醒等個人化設定。

## 資料承接保證

- 舊版 CSV 必須可匯入新版資料庫。
- 匯入失敗不會破壞目前 v8 資料庫。
- 匯入後會重新計算任務進度。
- 新版匯出的 CSV 仍保留舊版欄位，方便再次匯入。

## 測試

- 新增 pytest 測試覆蓋遺忘曲線排程、進度計算、SQLite repository、舊 CSV 匯入、匯出後再匯入，以及匯入失敗保護。

## 已知範圍

- v8 暫不包含 Email 報表寄送與進階圖表。
- 背景圖片完整備份不透過 CSV 處理，個人化設定保存在 v8 SQLite settings 表。
```

- [ ] **Step 3: Run full verification**

Run:

```powershell
python -m pytest -q
python -m py_compile src/renew_curve/app.py curve.py
```

Expected: both commands complete successfully.

- [ ] **Step 4: Commit docs**

Run:

```powershell
git add README.md update_record/curve_tool_record_v8.md
git commit -m "docs: document v8 migration release"
```

---

### Task 9: Manual GUI Verification And Final Git Check

**Files:**
- No expected source edits unless verification finds a bug.

- [ ] **Step 1: Start v8 app**

Run:

```powershell
python -m renew_curve.app
```

Expected: PySide6 window opens with left sidebar, central task workspace, and right calendar panel.

- [ ] **Step 2: Manual import verification**

In the GUI:

1. Open `Import/Export`.
2. Import `tests/fixtures/legacy_export.csv` using replace mode.
3. Confirm the task table shows `英文單字 Unit 12` and `Python async`.
4. Export a CSV to a temporary path.
5. Import that exported CSV into a fresh database through the tested function or GUI replace mode.

Expected: data appears and no error dialog is shown.

- [ ] **Step 3: Manual personalization verification**

In the GUI:

1. Open `Settings`.
2. Change accent color and density.
3. Confirm the stylesheet updates.
4. Reopen settings and confirm saved values appear.

Expected: settings persist in SQLite.

- [ ] **Step 4: Final automated verification**

Run:

```powershell
python -m pytest -q
python -m py_compile src/renew_curve/app.py curve.py
git status --short
```

Expected:

- pytest passes.
- py_compile passes.
- Git status shows only intentional tracked changes or is clean after commits.

- [ ] **Step 5: Final commit for verification fixes if needed**

If verification required source fixes, commit them:

```powershell
git add <fixed-files>
git commit -m "fix: polish v8 verification issues"
```

If no fixes were needed, do not create an empty commit.
