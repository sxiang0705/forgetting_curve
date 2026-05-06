def test_main_window_imports_without_starting_event_loop():
    from renew_curve.ui.main_window import MainWindow

    assert MainWindow.__name__ == "MainWindow"


def test_main_window_builds_offscreen_and_refreshes_after_replace_import(
    monkeypatch, tmp_path
):
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")

    from PySide6.QtWidgets import QApplication

    from renew_curve.csv_compat import import_legacy_csv
    from renew_curve.ui.main_window import MainWindow
    from tests.test_csv_compat import FIXTURE

    app = QApplication.instance() or QApplication([])
    db_path = tmp_path / "gui.db"
    window = MainWindow(db_path)

    assert window.task_table.columnCount() == 5
    assert window.task_table.rowCount() == 0

    import_legacy_csv(FIXTURE, db_path, mode="replace")
    window.refresh_tasks()

    assert window.task_table.rowCount() == 2

    window.close()
    app.processEvents()


def test_new_task_dialog_acceptance_creates_curve_task(monkeypatch, tmp_path):
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")

    import datetime as dt

    from PySide6.QtWidgets import QApplication, QDialog

    from renew_curve.db import ReminderRepository, connect
    from renew_curve.ui import main_window
    from renew_curve.ui.main_window import MainWindow

    class AcceptedTaskDialog:
        def __init__(self, parent=None):
            self.parent = parent

        def exec(self):
            return QDialog.DialogCode.Accepted

        def values(self):
            return {
                "title": "資料庫索引複習",
                "category": "Python",
                "difficulty": "中級",
                "notes": "確認查詢計畫",
                "reminder_method": "遺忘曲線",
                "start_time": dt.datetime(2026, 5, 6, 9, 0),
                "review_count": 3,
            }

    monkeypatch.setattr(main_window, "TaskDialog", AcceptedTaskDialog)

    app = QApplication.instance() or QApplication([])
    db_path = tmp_path / "gui.db"
    window = MainWindow(db_path)

    window.open_task_dialog()

    with connect(db_path) as conn:
        repo = ReminderRepository(conn)
        tasks = repo.list_tasks()
        reminders = repo.list_reminders(tasks[0].id)

    assert [task.title for task in tasks] == ["資料庫索引複習"]
    assert len(reminders) == 3
    assert window.task_table.rowCount() == 1

    window.close()
    app.processEvents()
