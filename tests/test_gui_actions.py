def test_dialog_classes_import():
    from renew_curve.ui.dialogs import ImportExportDialog, TaskDialog

    assert ImportExportDialog.__name__ == "ImportExportDialog"
    assert TaskDialog.__name__ == "TaskDialog"


def test_main_window_exposes_import_export_actions():
    from renew_curve.ui.main_window import MainWindow

    assert hasattr(MainWindow, "open_import_export_dialog")
    assert hasattr(MainWindow, "_import_csv")
    assert hasattr(MainWindow, "_export_csv")


def test_task_dialog_exposes_schedule_mode_and_manual_times():
    from renew_curve.ui.dialogs import TaskDialog

    assert hasattr(TaskDialog, "set_categories")
    assert hasattr(TaskDialog, "preview_review_times")
    assert hasattr(TaskDialog, "manual_review_times")


def test_task_dialog_uses_scrollable_two_pane_mockup_layout(monkeypatch):
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")

    from PySide6.QtWidgets import QApplication

    from renew_curve.ui.dialogs import TaskDialog

    app = QApplication.instance() or QApplication([])
    dialog = TaskDialog()

    assert dialog.scroll_area.widgetResizable() is True
    assert dialog.create_button.text() == "新增任務"
    assert dialog.cancel_button.text() == "取消"
    assert dialog.manual_times_widget.isHidden() is True

    dialog.mode_combo.setCurrentText("手動輸入")
    assert dialog.manual_times_widget.isHidden() is False
    assert sum(not row.isHidden() for row in dialog.manual_time_rows) == dialog.review_count_spin.value()

    dialog.close()
    app.processEvents()


def test_main_window_can_create_manual_reminders():
    from renew_curve.ui.main_window import MainWindow

    assert hasattr(MainWindow, "_create_task_from_values")


def test_data_dialog_exposes_three_primary_actions():
    from renew_curve.ui.dialogs import DataDialog

    assert hasattr(DataDialog, "import_legacy_csv_button")
    assert hasattr(DataDialog, "export_full_backup_button")
    assert hasattr(DataDialog, "import_full_backup_button")


def test_data_dialog_labels_match_v8_backup_flow(monkeypatch):
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")

    from PySide6.QtWidgets import QApplication

    from renew_curve.ui.dialogs import DataDialog

    app = QApplication.instance() or QApplication([])
    dialog = DataDialog()

    assert dialog.import_legacy_csv_button.text() == "1. 匯入舊版 CSV"
    assert dialog.export_full_backup_button.text() == "2. 匯出完整資料"
    assert dialog.import_full_backup_button.text() == "3. 匯入完整資料"
    assert ".csv" in dialog.legacy_csv_hint.text()
    assert ".zip" in dialog.full_export_hint.text()
    assert ".zip" in dialog.full_import_hint.text()

    dialog.close()
    app.processEvents()


def test_main_window_exposes_full_backup_actions():
    from renew_curve.ui.main_window import MainWindow

    assert hasattr(MainWindow, "_export_full_backup")
    assert hasattr(MainWindow, "_import_full_backup")


def test_main_window_exposes_new_dashboard_refresh_methods():
    from renew_curve.ui.main_window import MainWindow

    assert hasattr(MainWindow, "refresh_dashboard")
    assert hasattr(MainWindow, "_load_day_reminders")
    assert hasattr(MainWindow, "_load_next_three_days")
    assert hasattr(MainWindow, "_load_all_tasks")
