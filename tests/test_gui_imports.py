def test_main_window_imports_without_starting_event_loop():
    from renew_curve.ui.main_window import MainWindow

    assert MainWindow.__name__ == "MainWindow"


def test_main_window_builds_offscreen_and_closes_database(monkeypatch, tmp_path):
    import sqlite3

    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")

    from PySide6.QtWidgets import QApplication

    from renew_curve.ui.main_window import MainWindow

    app = QApplication.instance() or QApplication([])
    window = MainWindow(tmp_path / "gui.db")

    assert window.task_table.columnCount() == 5
    assert window.task_table.rowCount() == 0

    conn = window.conn
    window.close()
    app.processEvents()

    try:
        conn.execute("SELECT 1")
    except sqlite3.ProgrammingError as exc:
        assert "closed" in str(exc).lower()
    else:
        raise AssertionError("MainWindow did not close its database connection")
