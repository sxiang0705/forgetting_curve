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


def test_repository_finds_and_snoozes_next_pending_reminder(tmp_path):
    db_path = tmp_path / "v8.db"
    with connect(db_path) as conn:
        init_db(conn)
        repo = ReminderRepository(conn)
        task_id = repo.create_task(
            TaskDraft(
                title="資料庫練習",
                category="Python",
                difficulty="中級",
                notes="indexes",
                reminder_method="遺忘曲線",
                start_time=dt.datetime(2026, 5, 6, 9, 0),
            )
        )
        done_id = repo.create_reminder(
            ReminderDraft(
                task_id=task_id,
                remind_time=dt.datetime(2026, 5, 7, 9, 0),
                reminded=True,
            )
        )
        next_id = repo.create_reminder(
            ReminderDraft(
                task_id=task_id,
                remind_time=dt.datetime(2026, 5, 9, 9, 0),
            )
        )
        repo.create_reminder(
            ReminderDraft(
                task_id=task_id,
                remind_time=dt.datetime(2026, 5, 13, 9, 0),
            )
        )

        next_reminder = repo.next_pending_reminder(task_id)
        assert next_reminder is not None
        assert next_reminder.id == next_id

        repo.snooze_reminder(next_id, dt.datetime(2026, 5, 10, 10, 30))
        snoozed = repo.next_pending_reminder(task_id)

    assert done_id != next_id
    assert snoozed is not None
    assert snoozed.id == next_id
    assert snoozed.remind_time == dt.datetime(2026, 5, 10, 10, 30)


def test_repository_lists_due_reminders_for_date(tmp_path):
    db_path = tmp_path / "v8.db"
    with connect(db_path) as conn:
        init_db(conn)
        repo = ReminderRepository(conn)
        task_id = repo.create_task(
            TaskDraft(
                title="英文單字 Unit 12",
                category="英文單字",
                difficulty="初級",
                notes="完整備註",
                reminder_method="遺忘曲線",
                start_time=dt.datetime(2026, 5, 6, 9, 0),
            )
        )
        due_id = repo.create_reminder(
            ReminderDraft(task_id=task_id, remind_time=dt.datetime(2026, 5, 7, 9, 0))
        )
        repo.create_reminder(
            ReminderDraft(task_id=task_id, remind_time=dt.datetime(2026, 5, 8, 9, 0))
        )

        items = repo.list_due_reminders_for_date(dt.date(2026, 5, 7))

    assert [item.reminder_id for item in items] == [due_id]
    assert items[0].task_title == "英文單字 Unit 12"
    assert items[0].notes == "完整備註"
    assert items[0].review_index == 1


def test_repository_counts_reminders_by_date_and_categories(tmp_path):
    db_path = tmp_path / "v8.db"
    with connect(db_path) as conn:
        init_db(conn)
        repo = ReminderRepository(conn)
        english_id = repo.create_task(
            TaskDraft("單字", "英文單字", "初級", "", "遺忘曲線", dt.datetime(2026, 5, 6, 9, 0))
        )
        cs_id = repo.create_task(
            TaskDraft("儲存單位", "計算機概論", "初級", "", "遺忘曲線", dt.datetime(2026, 5, 6, 10, 0))
        )
        repo.create_reminder(ReminderDraft(english_id, dt.datetime(2026, 5, 7, 9, 0)))
        repo.create_reminder(ReminderDraft(cs_id, dt.datetime(2026, 5, 7, 10, 0)))
        repo.create_reminder(ReminderDraft(cs_id, dt.datetime(2026, 5, 9, 10, 0)))

        counts = repo.count_pending_reminders_by_date(dt.date(2026, 5, 7), 3)
        categories = repo.list_categories()

    assert counts == {
        dt.date(2026, 5, 7): 2,
        dt.date(2026, 5, 8): 0,
        dt.date(2026, 5, 9): 1,
    }
    assert categories == ["英文單字", "計算機概論"]
