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
