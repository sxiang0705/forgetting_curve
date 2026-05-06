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
        first_reminder_id = repo.create_reminder(
            ReminderDraft(
                task_id=task_id, remind_time=dt.datetime(2026, 5, 7, 9, 0)
            )
        )
        repo.create_reminder(
            ReminderDraft(
                task_id=task_id, remind_time=dt.datetime(2026, 5, 9, 9, 0)
            )
        )
        repo.mark_reminder_done(first_reminder_id)

        task = repo.get_task(task_id)
        reminders = repo.list_reminders(task_id)

    assert task is not None
    assert task.progress_percent == 50.0
    assert len(reminders) == 2
    assert reminders[0].reminded is True


def test_repository_marks_task_completed_after_all_reminders_done(tmp_path):
    db_path = tmp_path / "v8.db"
    with connect(db_path) as conn:
        init_db(conn)
        repo = ReminderRepository(conn)
        task_id = repo.create_task(
            TaskDraft(
                title="數學複習",
                category="數學",
                difficulty="高級",
                notes="chapter 4",
                reminder_method="遺忘曲線",
                start_time=dt.datetime(2026, 5, 6, 10, 0),
            )
        )
        first_reminder_id = repo.create_reminder(
            ReminderDraft(
                task_id=task_id, remind_time=dt.datetime(2026, 5, 7, 10, 0)
            )
        )
        second_reminder_id = repo.create_reminder(
            ReminderDraft(
                task_id=task_id, remind_time=dt.datetime(2026, 5, 9, 10, 0)
            )
        )

        repo.mark_reminder_done(first_reminder_id)
        repo.mark_reminder_done(second_reminder_id)

        task = repo.get_task(task_id)
        active_tasks = repo.list_tasks(include_completed=False)

    assert task is not None
    assert task.progress_percent == 100.0
    assert task.is_completed is True
    assert task.id not in {active_task.id for active_task in active_tasks}


def test_repository_operations_roll_back_with_outer_transaction(tmp_path):
    db_path = tmp_path / "v8.db"
    with connect(db_path) as conn:
        init_db(conn)
        repo = ReminderRepository(conn)

        try:
            with conn:
                task_id = repo.create_task(
                    TaskDraft(
                        title="歷史整理",
                        category="歷史",
                        difficulty="初級",
                        notes="week 3",
                        reminder_method="遺忘曲線",
                        start_time=dt.datetime(2026, 5, 6, 11, 0),
                    )
                )
                repo.create_reminder(
                    ReminderDraft(
                        task_id=task_id,
                        remind_time=dt.datetime(2026, 5, 7, 11, 0),
                    )
                )
                raise RuntimeError("abort import")
        except RuntimeError:
            pass

        task_count = conn.execute("SELECT COUNT(*) FROM tasks").fetchone()[0]
        reminder_count = conn.execute("SELECT COUNT(*) FROM reminders").fetchone()[0]

    assert task_count == 0
    assert reminder_count == 0
