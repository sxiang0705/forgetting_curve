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


def test_personalization_defaults_include_global_scope():
    from renew_curve.ui.personalization import default_personalization_settings

    defaults = default_personalization_settings()

    assert defaults["theme_style"] == "clean_mountain"
    assert defaults["sticker_scope"] == "main_only"
    assert defaults["functional_window_sticker_density"] == "low"


def test_personalization_stylesheet_uses_theme_style():
    from renew_curve.ui.personalization import stylesheet_for_personalization

    css = stylesheet_for_personalization(
        {
            "theme_style": "healing_pastel",
            "density": "comfortable",
            "accent": "blue",
        }
    )

    assert "#2563eb" in css
    assert "QFrame#Panel" in css


def test_init_db_creates_stickers_table(tmp_path):
    db_path = tmp_path / "settings.db"
    with connect(db_path) as conn:
        init_db(conn)
        names = {
            row[0]
            for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        }
    assert "stickers" in names


def test_settings_dialog_exposes_theme_and_asset_sections():
    from renew_curve.ui.dialogs import SettingsDialog

    assert hasattr(SettingsDialog, "values")
    assert hasattr(SettingsDialog, "set_background_assets")
    assert hasattr(SettingsDialog, "set_sticker_assets")
