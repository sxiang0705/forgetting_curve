def test_dialog_classes_import():
    from renew_curve.ui.dialogs import ImportExportDialog, TaskDialog

    assert ImportExportDialog.__name__ == "ImportExportDialog"
    assert TaskDialog.__name__ == "TaskDialog"


def test_main_window_exposes_import_export_actions():
    from renew_curve.ui.main_window import MainWindow

    assert hasattr(MainWindow, "open_import_export_dialog")
    assert hasattr(MainWindow, "_import_csv")
    assert hasattr(MainWindow, "_export_csv")
