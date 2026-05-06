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
        reminders = []
        for task in tasks:
            reminders.extend(repo.list_reminders(task.id))

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
        reminders = []
        for task in tasks:
            reminders.extend(repo.list_reminders(task.id))

    assert summary.tasks == 2
    assert len(tasks) == 4
    assert len(reminders) == 6
    assert max(task.id for task in tasks) > 2
    task_ids = {task.id for task in tasks}
    assert all(reminder.task_id in task_ids for reminder in reminders)


def test_export_round_trip_preserves_legacy_columns(tmp_path):
    db_path = tmp_path / "v8.db"
    out_csv = tmp_path / "export.csv"
    round_trip_db = tmp_path / "round-trip.db"

    import_legacy_csv(FIXTURE, db_path, mode="replace")
    export_legacy_csv(db_path, out_csv)

    with out_csv.open("r", newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        assert {
            "record_type",
            "id",
            "task_id",
            "title",
            "remind_time",
            "reminded",
        }.issubset(reader.fieldnames or [])

    import_legacy_csv(out_csv, round_trip_db, mode="replace")
    with connect(round_trip_db) as conn:
        repo = ReminderRepository(conn)
        tasks = repo.list_tasks()
        reminders = []
        for task in tasks:
            reminders.extend(repo.list_reminders(task.id))
        assert len(tasks) == 2
        assert len(reminders) == 3
