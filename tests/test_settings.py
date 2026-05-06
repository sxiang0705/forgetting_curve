import datetime as dt

import pytest

from renew_curve.db import ReminderRepository, connect, init_db
from renew_curve.models import TaskDraft


def test_settings_round_trip(tmp_path):
    db_path = tmp_path / "settings.db"
    with connect(db_path) as conn:
        init_db(conn)
        repo = ReminderRepository(conn)
        with conn:
            repo.set_setting("theme", "dark")
            repo.set_setting("accent", "green")
        assert repo.get_setting("theme", "light") == "dark"
        assert repo.get_setting("accent", "blue") == "green"
        assert repo.get_setting("density", "comfortable") == "comfortable"


def test_setting_rolls_back_with_outer_transaction(tmp_path):
    db_path = tmp_path / "settings.db"
    with connect(db_path) as conn:
        init_db(conn)
        repo = ReminderRepository(conn)

        with pytest.raises(RuntimeError):
            with conn:
                repo.create_task(
                    TaskDraft(
                        title="Rollback task",
                        category="General",
                        difficulty="Easy",
                        notes="",
                        reminder_method="Manual",
                        start_time=dt.datetime(2026, 5, 6, 9, 0),
                    )
                )
                repo.set_setting("theme", "dark")
                raise RuntimeError("rollback")

        assert repo.list_tasks() == []
        assert repo.get_setting("theme", "light") == "light"
