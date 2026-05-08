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

    assert window.task_table.columnCount() == 6
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


def test_main_window_shows_and_completes_next_reminder(monkeypatch, tmp_path):
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")

    import datetime as dt

    from PySide6.QtWidgets import QApplication

    from renew_curve.db import ReminderRepository, connect, init_db
    from renew_curve.models import ReminderDraft, TaskDraft
    from renew_curve.ui.main_window import MainWindow

    app = QApplication.instance() or QApplication([])
    db_path = tmp_path / "gui.db"
    with connect(db_path) as conn:
        init_db(conn)
        repo = ReminderRepository(conn)
        with conn:
            task_id = repo.create_task(
                TaskDraft(
                    title="下一次提醒測試",
                    category="Python",
                    difficulty="中級",
                    notes="",
                    reminder_method="遺忘曲線",
                    start_time=dt.datetime(2026, 5, 6, 9, 0),
                )
            )
            reminder_id = repo.create_reminder(
                ReminderDraft(
                    task_id=task_id,
                    remind_time=dt.datetime(2026, 5, 7, 9, 0),
                )
            )

    window = MainWindow(db_path)

    assert window.task_table.item(0, 3).text() == "2026-05-07 09:00"

    window.task_table.selectRow(0)
    window.complete_next_button.click()

    with connect(db_path) as conn:
        repo = ReminderRepository(conn)
        task = repo.get_task(task_id)
        reminder = repo.list_reminders(task_id)[0]

    assert reminder.id == reminder_id
    assert reminder.reminded is True
    assert task is not None
    assert task.is_completed is True
    assert window.task_table.item(0, 4).text() == "100%"

    window.close()
    app.processEvents()


def test_main_window_snoozes_next_reminder_with_saved_preference(
    monkeypatch, tmp_path
):
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")

    import datetime as dt

    from PySide6.QtWidgets import QApplication

    from renew_curve.db import ReminderRepository, connect, init_db
    from renew_curve.models import ReminderDraft, TaskDraft
    from renew_curve.ui.main_window import MainWindow

    app = QApplication.instance() or QApplication([])
    db_path = tmp_path / "gui.db"
    with connect(db_path) as conn:
        init_db(conn)
        repo = ReminderRepository(conn)
        with conn:
            repo.set_setting("default_snooze", "1h")
            task_id = repo.create_task(
                TaskDraft(
                    title="稍後提醒測試",
                    category="Python",
                    difficulty="中級",
                    notes="",
                    reminder_method="遺忘曲線",
                    start_time=dt.datetime(2026, 5, 6, 9, 0),
                )
            )
            repo.create_reminder(
                ReminderDraft(
                    task_id=task_id,
                    remind_time=dt.datetime(2026, 5, 7, 9, 0),
                )
            )

    window = MainWindow(db_path)
    window.task_table.selectRow(0)
    window.snooze_selected_next_reminder(now=dt.datetime(2026, 5, 7, 9, 30))

    with connect(db_path) as conn:
        repo = ReminderRepository(conn)
        reminder = repo.list_reminders(task_id)[0]

    assert reminder.remind_time == dt.datetime(2026, 5, 7, 10, 30)
    assert window.task_table.item(0, 3).text() == "2026-05-07 10:30"

    window.close()
    app.processEvents()


def test_main_window_uses_traditional_chinese_primary_labels(monkeypatch, tmp_path):
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")

    from PySide6.QtWidgets import QApplication

    from renew_curve.ui.main_window import MainWindow

    app = QApplication.instance() or QApplication([])
    window = MainWindow(tmp_path / "gui.db")

    assert window.new_task_button.text() == "新增任務"
    assert window.import_export_button.text() == "報表 / 資料"
    assert window.settings_button.text() == "個人化"
    assert window.task_table.horizontalHeaderItem(0).text() == "任務"
    assert window.task_table.horizontalHeaderItem(3).text() == "下一次"

    window.close()
    app.processEvents()


def test_main_window_matches_mockup_scroll_and_action_names(monkeypatch, tmp_path):
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")

    import datetime as dt

    from PySide6.QtWidgets import QApplication

    from renew_curve.ui.main_window import MainWindow

    app = QApplication.instance() or QApplication([])
    window = MainWindow(tmp_path / "gui.db")

    assert window.today_scroll.maximumHeight() <= 390
    assert window.today_scroll.widgetResizable() is True
    assert window.next_days_title.text() == "接下來 3 天"
    assert window.complete_next_button.text() == "完成下一次"

    card = window._build_reminder_card(
        type(
            "Item",
            (),
            {
                "task_title": "測試任務",
                "category": "測試",
                "notes": "備註",
                "remind_time": dt.datetime(2026, 5, 7, 9),
                "review_index": 1,
                "total_reviews": 3,
                "reminder_id": 1,
            },
        )()
    )
    buttons = card.findChildren(__import__("PySide6.QtWidgets").QtWidgets.QPushButton)
    assert [button.text() for button in buttons] == ["完成", "推延"]
    assert {button.objectName() for button in buttons} == {"OutlineActionButton"}

    window.close()
    app.processEvents()


def test_main_window_uses_mockup_calendar_and_tighter_main_spacing(monkeypatch, tmp_path):
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")

    from PySide6.QtWidgets import QApplication

    from renew_curve.ui.main_window import MainWindow, MockupCalendar

    app = QApplication.instance() or QApplication([])
    window = MainWindow(tmp_path / "gui.db")

    assert isinstance(window.calendar, MockupCalendar)
    assert window.calendar_today_button.text() == "回到今天"
    assert window.calendar_month_label.text()
    assert window.center_layout.contentsMargins().left() <= 22
    assert window.center_layout.spacing() <= 12
    assert 200 <= window.today_scroll.minimumHeight() <= 260

    window.close()
    app.processEvents()


def test_main_window_sections_table_and_calendar_legend_review(monkeypatch, tmp_path):
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")

    from PySide6.QtWidgets import QApplication, QLabel

    from renew_curve.ui.main_window import MainWindow

    app = QApplication.instance() or QApplication([])
    window = MainWindow(tmp_path / "gui.db")

    assert window.today_section.objectName() == "SectionPanel"
    assert window.all_tasks_section.objectName() == "SectionPanel"
    assert window.next_days_scroll.widgetResizable() is True
    assert window.next_days_scroll.maximumHeight() <= 390
    assert window.next_three_days_section.maximumHeight() <= 460
    assert window.today_section.maximumHeight() <= 380
    assert window.all_tasks_section.maximumHeight() <= 380
    assert window.task_table.columnCount() == 6
    assert window.task_table.horizontalHeaderItem(1).text() == "備註"
    assert window.task_table.maximumHeight() == window.task_table.minimumHeight()
    assert window.schedule_help_button.isHidden() is True

    swatches = window.calendar.findChildren(QLabel, "CalendarLegendSwatch")
    assert len(swatches) == 4
    assert "綠" not in window.calendar.legend_label.text()

    window.close()
    app.processEvents()


def test_main_window_stores_uploaded_personalization_assets(monkeypatch, tmp_path):
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")

    from PySide6.QtWidgets import QApplication

    from renew_curve.db import ReminderRepository, connect
    from renew_curve.ui.main_window import MainWindow

    app = QApplication.instance() or QApplication([])
    db_path = tmp_path / "gui.db"
    source = tmp_path / "sample-background.png"
    source.write_bytes(b"fake-image")
    window = MainWindow(db_path)

    window._store_personalization_asset(source, "backgrounds")

    copied = tmp_path / "assets" / "backgrounds" / source.name
    with connect(db_path) as conn:
        backgrounds = ReminderRepository(conn).list_background_assets()

    assert copied.read_bytes() == b"fake-image"
    assert [(name, path, active) for _, name, path, active in backgrounds] == [
        (source.name, str(copied), True)
    ]

    window.close()
    app.processEvents()


def test_uploaded_background_is_used_by_task_sections(monkeypatch, tmp_path):
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")

    from PySide6.QtWidgets import QApplication

    from renew_curve.ui.main_window import MainWindow, WallpaperPanel

    app = QApplication.instance() or QApplication([])
    db_path = tmp_path / "gui.db"
    source = tmp_path / "bg.jpg"
    source.write_bytes(b"fake-jpg")
    window = MainWindow(db_path)

    window._store_personalization_asset(source, "backgrounds")
    window._apply_active_background()

    copied = tmp_path / "assets" / "backgrounds" / source.name
    assert isinstance(window.today_section, WallpaperPanel)
    assert isinstance(window.all_tasks_section, WallpaperPanel)
    assert isinstance(window.next_three_days_section, WallpaperPanel)
    assert window.today_section.wallpaper_path == copied
    assert window.all_tasks_section.wallpaper_path == copied
    assert window.next_three_days_section.wallpaper_path == copied

    window.close()
    app.processEvents()


def test_calendar_month_navigation_refreshes_visible_month_counts(monkeypatch, tmp_path):
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")

    import datetime as dt

    from PySide6.QtWidgets import QApplication

    from renew_curve.db import ReminderRepository, connect, init_db
    from renew_curve.models import ReminderDraft, TaskDraft
    from renew_curve.ui.main_window import MainWindow

    app = QApplication.instance() or QApplication([])
    db_path = tmp_path / "gui.db"
    with connect(db_path) as conn:
        init_db(conn)
        repo = ReminderRepository(conn)
        with conn:
            task_id = repo.create_task(
                TaskDraft(
                    title="九月任務",
                    category="英文單字",
                    difficulty="初級",
                    notes="",
                    reminder_method="遺忘曲線",
                    start_time=dt.datetime(2026, 9, 1, 9, 0),
                )
            )
            repo.create_reminder(
                ReminderDraft(task_id, dt.datetime(2026, 9, 9, 9, 0))
            )

    window = MainWindow(db_path)
    window.refresh_dashboard(dt.date(2026, 5, 8))

    for _ in range(4):
        window.calendar.next_month_button.click()

    assert window.calendar.visible_month() == dt.date(2026, 9, 1)
    assert window.calendar._counts[dt.date(2026, 9, 9)] == 1

    window.close()
    app.processEvents()


def test_main_window_populates_report_dialog_summary(monkeypatch, tmp_path):
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")

    import datetime as dt

    from PySide6.QtWidgets import QApplication

    from renew_curve.db import ReminderRepository, connect, init_db
    from renew_curve.models import ReminderDraft, TaskDraft
    from renew_curve.ui.main_window import MainWindow

    app = QApplication.instance() or QApplication([])
    db_path = tmp_path / "gui.db"
    with connect(db_path) as conn:
        init_db(conn)
        repo = ReminderRepository(conn)
        with conn:
            task_id = repo.create_task(
                TaskDraft("報表測試", "工作", "初級", "", "遺忘曲線", dt.datetime(2026, 5, 1, 9, 0))
            )
            repo.create_reminder(
                ReminderDraft(task_id, dt.datetime(2026, 5, 6, 9, 0), reminded=True)
            )
            repo.create_reminder(
                ReminderDraft(task_id, dt.datetime(2026, 5, 7, 9, 0), reminded=False)
            )

    captured = {}

    class FakeDialog:
        def set_report_summary(self, stats, *, weekly_completed, weekly_total, weekly_rate):
            captured["stats"] = stats
            captured["weekly"] = (weekly_completed, weekly_total, weekly_rate)

    window = MainWindow(db_path)
    window._populate_report_dialog(FakeDialog(), today=dt.date(2026, 5, 7))

    assert captured["stats"].total_tasks == 1
    assert captured["weekly"] == (1, 2, 50.0)

    window.close()
    app.processEvents()
