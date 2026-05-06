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
        repo.create_reminder(
            ReminderDraft(
                task_id=task_id, remind_time=dt.datetime(2026, 5, 7, 9, 0)
            )
        )
        repo.create_reminder(
            ReminderDraft(
                task_id=task_id, remind_time=dt.datetime(2026, 5, 9, 9, 0)
            )
        )
        repo.mark_reminder_done(1)

        task = repo.get_task(task_id)
        reminders = repo.list_reminders(task_id)

    assert task is not None
    assert task.progress_percent == 50.0
    assert len(reminders) == 2
    assert reminders[0].reminded is True
