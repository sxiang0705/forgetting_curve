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


def test_main_window_can_create_manual_reminders():
    from renew_curve.ui.main_window import MainWindow

    assert hasattr(MainWindow, "_create_task_from_values")


def test_data_dialog_exposes_three_primary_actions():
    from renew_curve.ui.dialogs import DataDialog

    assert hasattr(DataDialog, "import_legacy_csv_button")
    assert hasattr(DataDialog, "export_full_backup_button")
    assert hasattr(DataDialog, "import_full_backup_button")


def test_main_window_exposes_full_backup_actions():
    from renew_curve.ui.main_window import MainWindow

    assert hasattr(MainWindow, "_export_full_backup")
    assert hasattr(MainWindow, "_import_full_backup")
