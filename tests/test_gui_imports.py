def test_main_window_imports_without_starting_event_loop():
    from renew_curve.ui.main_window import MainWindow

    assert MainWindow.__name__ == "MainWindow"


def test_app_icon_path_points_to_repo_icon():
    from renew_curve.app import app_icon_path

    icon = app_icon_path()

    assert icon.name == "FC_3_icon.ico"
    assert icon.exists()


def test_app_icon_path_uses_pyinstaller_meipass(monkeypatch, tmp_path):
    import sys

    from renew_curve.app import app_icon_path

    monkeypatch.setattr(sys, "_MEIPASS", str(tmp_path), raising=False)

    assert app_icon_path() == tmp_path / "resources" / "icons" / "FC_3_icon.ico"


def test_main_window_brand_title_stays_left_aligned(monkeypatch, tmp_path):
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")

    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QApplication, QLabel

    from renew_curve.ui.main_window import MainWindow

    app = QApplication.instance() or QApplication([])
    window = MainWindow(tmp_path / "gui.db")

    brand_label = next(
        label for label in window.findChildren(QLabel) if label.text() == "Renew Curve v8"
    )

    assert brand_label.objectName() == "BrandTitle"
    assert brand_label.alignment() == (
        Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
    )

    window.close()
    app.processEvents()


def test_sidebar_layout_allocates_height_proportionally(monkeypatch, tmp_path):
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")

    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QApplication, QWidget

    from renew_curve.ui.main_window import MainWindow

    app = QApplication.instance() or QApplication([])
    window = MainWindow(tmp_path / "gui.db")
    sidebar = window.findChild(QWidget, "Sidebar")
    assert sidebar is not None

    sidebar_layout = sidebar.layout()
    calendar_frame = window.calendar.parentWidget()

    assert sidebar_layout.alignment() & Qt.AlignmentFlag.AlignTop
    assert sidebar_layout.stretch(sidebar_layout.indexOf(calendar_frame)) == 5
    assert sidebar_layout.stretch(sidebar_layout.indexOf(window.next_three_days_section)) == 4
    assert sidebar_layout.itemAt(sidebar_layout.count() - 1).spacerItem() is None

    window.close()
    app.processEvents()


def test_main_window_uses_proportional_shell_layout(monkeypatch, tmp_path):
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")

    from PySide6.QtWidgets import QApplication, QSizePolicy, QWidget

    from renew_curve.ui.main_window import MainWindow

    app = QApplication.instance() or QApplication([])
    window = MainWindow(tmp_path / "gui.db")
    root_layout = window.centralWidget().layout()
    sidebar = window.findChild(QWidget, "Sidebar")
    assert sidebar is not None

    assert sidebar.minimumWidth() >= 280
    assert sidebar.maximumWidth() <= 460
    assert sidebar.sizePolicy().horizontalPolicy() == QSizePolicy.Policy.Preferred
    assert root_layout.stretch(0) == 1
    assert root_layout.stretch(1) == 3

    window.close()
    app.processEvents()


def test_main_window_minimum_size_fits_common_16_inch_screen(monkeypatch, tmp_path):
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")

    from PySide6.QtWidgets import QApplication

    from renew_curve.ui.main_window import MainWindow

    app = QApplication.instance() or QApplication([])
    window = MainWindow(tmp_path / "gui.db")

    assert window.minimumWidth() <= 980
    assert window.minimumHeight() <= 640
    assert window.width() <= 1180
    assert window.height() <= 760
    assert window.maximumWidth() >= 10000
    assert window.maximumHeight() >= 10000

    window.close()
    app.processEvents()


def test_calendar_days_expand_with_sidebar_space(monkeypatch, tmp_path):
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")

    from PySide6.QtWidgets import QApplication, QPushButton, QSizePolicy

    from renew_curve.ui.main_window import MainWindow

    app = QApplication.instance() or QApplication([])
    window = MainWindow(tmp_path / "gui.db")
    day_button = next(
        button
        for button in window.calendar.findChildren(QPushButton)
        if button.objectName().startswith("CalendarDay")
    )

    assert day_button.minimumHeight() >= 36
    assert day_button.maximumHeight() > 1000
    assert day_button.sizePolicy().verticalPolicy() == QSizePolicy.Policy.Expanding

    window.close()
    app.processEvents()


def test_all_tasks_section_keeps_content_away_from_frame(monkeypatch, tmp_path):
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")

    from PySide6.QtWidgets import QApplication

    from renew_curve.ui.main_window import MainWindow

    app = QApplication.instance() or QApplication([])
    window = MainWindow(tmp_path / "gui.db")

    margins = window.all_tasks_section.layout().contentsMargins()

    assert margins.left() >= 22
    assert margins.top() >= 16
    assert margins.right() >= 22
    assert margins.bottom() >= 18

    window.close()
    app.processEvents()


def test_all_tasks_table_leaves_bottom_padding_inside_section(monkeypatch, tmp_path):
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")

    from PySide6.QtWidgets import QApplication

    from renew_curve.ui.main_window import MainWindow

    app = QApplication.instance() or QApplication([])
    window = MainWindow(tmp_path / "gui.db")

    assert window.all_tasks_section.maximumHeight() > 1000
    assert window.task_table.maximumHeight() > 1000
    assert window.task_table.minimumHeight() >= 180

    window.close()
    app.processEvents()


def test_center_task_sections_share_available_height_by_ratio(monkeypatch, tmp_path):
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")

    from PySide6.QtWidgets import QApplication

    from renew_curve.ui.main_window import MainWindow

    app = QApplication.instance() or QApplication([])
    window = MainWindow(tmp_path / "gui.db")

    assert window.center_layout.stretch(window.center_layout.indexOf(window.today_section)) == 4
    assert window.center_layout.stretch(window.center_layout.indexOf(window.all_tasks_section)) == 6
    assert window.center_layout.itemAt(window.center_layout.count() - 1).spacerItem() is None

    window.close()
    app.processEvents()


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

    assert window.today_scroll.maximumHeight() > 1000
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
    assert 150 <= window.today_scroll.minimumHeight() <= 220

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
    assert window.next_days_scroll.maximumHeight() > 1000
    assert window.next_three_days_section.maximumHeight() > 1000
    assert window.today_section.maximumHeight() > 1000
    assert window.all_tasks_section.maximumHeight() > 1000
    assert window.task_table.columnCount() == 6
    assert window.task_table.horizontalHeaderItem(1).text() == "備註"
    assert window.task_table.maximumHeight() > window.task_table.minimumHeight()
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


def test_main_window_uses_section_specific_background_settings(monkeypatch, tmp_path):
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")

    from PySide6.QtWidgets import QApplication

    from renew_curve.db import ReminderRepository, connect, init_db
    from renew_curve.ui.main_window import MainWindow

    app = QApplication.instance() or QApplication([])
    db_path = tmp_path / "gui.db"
    today = tmp_path / "today.jpg"
    next_days = tmp_path / "next.jpg"
    all_tasks = tmp_path / "all.jpg"
    for path in (today, next_days, all_tasks):
        path.write_bytes(b"fake")

    with connect(db_path) as conn:
        init_db(conn)
        repo = ReminderRepository(conn)
        with conn:
            today_id = repo.add_background_asset("today.jpg", str(today))
            next_id = repo.add_background_asset("next.jpg", str(next_days))
            all_id = repo.add_background_asset("all.jpg", str(all_tasks))
            repo.set_setting("today_background_id", str(today_id))
            repo.set_setting("next_background_id", str(next_id))
            repo.set_setting("all_background_id", str(all_id))

    window = MainWindow(db_path)
    window._apply_active_background()

    assert window.today_section.wallpaper_path == today
    assert window.next_three_days_section.wallpaper_path == next_days
    assert window.all_tasks_section.wallpaper_path == all_tasks

    window.close()
    app.processEvents()


def test_main_window_applies_background_blur_and_darken_settings(monkeypatch, tmp_path):
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")

    from PySide6.QtWidgets import QApplication

    from renew_curve.db import ReminderRepository, connect, init_db
    from renew_curve.ui.main_window import MainWindow

    app = QApplication.instance() or QApplication([])
    db_path = tmp_path / "gui.db"
    background = tmp_path / "bg.jpg"
    background.write_bytes(b"fake")
    with connect(db_path) as conn:
        init_db(conn)
        repo = ReminderRepository(conn)
        with conn:
            repo.add_background_asset("bg.jpg", str(background))
            repo.set_setting("background_blur", "12")
            repo.set_setting("background_darken", "35")

    window = MainWindow(db_path)
    window._apply_active_background()

    assert window.today_section.background_blur_radius == 12
    assert window.today_section.background_darken_alpha == int(255 * 35 / 100)

    window.close()
    app.processEvents()


def test_uploaded_sticker_is_used_by_task_sections(monkeypatch, tmp_path):
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")

    from PySide6.QtWidgets import QApplication

    from renew_curve.ui.main_window import MainWindow

    app = QApplication.instance() or QApplication([])
    db_path = tmp_path / "gui.db"
    source = tmp_path / "sticker.jpg"
    source.write_bytes(b"fake-jpg")
    window = MainWindow(db_path)

    window._store_personalization_asset(source, "stickers")
    window._apply_active_stickers()

    copied = tmp_path / "assets" / "stickers" / source.name
    assert window.today_section.sticker_path == copied
    assert window.all_tasks_section.sticker_path == copied
    assert window.next_three_days_section.sticker_path == copied

    window.close()
    app.processEvents()


def test_uploaded_gif_sticker_uses_movie_animation(monkeypatch, tmp_path):
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")

    from PySide6.QtWidgets import QApplication

    from renew_curve.ui.main_window import MainWindow

    app = QApplication.instance() or QApplication([])
    db_path = tmp_path / "gui.db"
    source = tmp_path / "sticker.gif"
    source.write_bytes(
        b"GIF89a\x01\x00\x01\x00\x80\x00\x00\x00\x00\x00\xff\xff\xff!"
        b"\xf9\x04\x00\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01\x00"
        b"\x00\x02\x02D\x01\x00;"
    )
    window = MainWindow(db_path)

    window._store_personalization_asset(source, "stickers")
    window._apply_active_stickers()

    assert window.today_section._sticker_movie is not None
    assert window.today_section._sticker_label.movie() is window.today_section._sticker_movie
    assert window.all_tasks_section._sticker_movie is not None
    assert window.next_three_days_section._sticker_movie is not None

    window.close()
    app.processEvents()


def test_main_window_deletes_background_asset_file_and_record(monkeypatch, tmp_path):
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")

    from PySide6.QtWidgets import QApplication

    from renew_curve.db import ReminderRepository, connect
    from renew_curve.ui.main_window import MainWindow

    app = QApplication.instance() or QApplication([])
    db_path = tmp_path / "gui.db"
    source = tmp_path / "bg.jpg"
    source.write_bytes(b"fake-jpg")
    window = MainWindow(db_path)

    window._store_personalization_asset(source, "backgrounds")
    copied = tmp_path / "assets" / "backgrounds" / source.name
    with connect(db_path) as conn:
        asset_id = ReminderRepository(conn).list_background_assets()[0][0]

    window._delete_personalization_asset(asset_id, "backgrounds")

    with connect(db_path) as conn:
        backgrounds = ReminderRepository(conn).list_background_assets()

    assert not copied.exists()
    assert backgrounds == []

    window.close()
    app.processEvents()


def test_main_window_random_background_values_choose_existing_assets(
    monkeypatch, tmp_path
):
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")

    from PySide6.QtWidgets import QApplication

    from renew_curve.db import ReminderRepository, connect, init_db
    from renew_curve.ui.main_window import MainWindow

    app = QApplication.instance() or QApplication([])
    db_path = tmp_path / "gui.db"
    first = tmp_path / "first.jpg"
    second = tmp_path / "second.jpg"
    first.write_bytes(b"first")
    second.write_bytes(b"second")
    with connect(db_path) as conn:
        init_db(conn)
        repo = ReminderRepository(conn)
        with conn:
            first_id = repo.add_background_asset("first.jpg", str(first))
            second_id = repo.add_background_asset("second.jpg", str(second))

    window = MainWindow(db_path)
    values = window._random_background_values()

    assert set(values) == {
        "today_background_id",
        "next_background_id",
        "all_background_id",
    }
    assert set(values.values()).issubset({str(first_id), str(second_id)})

    window.close()
    app.processEvents()


def test_main_window_random_mode_selects_backgrounds_on_apply(
    monkeypatch, tmp_path
):
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")

    from PySide6.QtWidgets import QApplication

    from renew_curve.db import ReminderRepository, connect, init_db
    from renew_curve.ui.main_window import MainWindow

    app = QApplication.instance() or QApplication([])
    db_path = tmp_path / "gui.db"
    first = tmp_path / "first.jpg"
    second = tmp_path / "second.jpg"
    first.write_bytes(b"first")
    second.write_bytes(b"second")
    with connect(db_path) as conn:
        init_db(conn)
        repo = ReminderRepository(conn)
        with conn:
            repo.add_background_asset("first.jpg", str(first))
            repo.add_background_asset("second.jpg", str(second))
            repo.set_setting("background_mode", "random")

    choices: list[str] = []

    def choose_last(values):
        choices.append(values[-1])
        return values[-1]

    monkeypatch.setattr("renew_curve.ui.main_window.random.choice", choose_last)
    window = MainWindow(db_path)

    assert window.today_section.wallpaper_path == second
    assert window.next_three_days_section.wallpaper_path == second
    assert window.all_tasks_section.wallpaper_path == second
    assert len(choices) == 3

    window.close()
    app.processEvents()


def test_main_window_random_sticker_mode_selects_sticker_on_startup(
    monkeypatch, tmp_path
):
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")

    from PySide6.QtWidgets import QApplication

    from renew_curve.db import ReminderRepository, connect, init_db
    from renew_curve.ui.main_window import MainWindow

    app = QApplication.instance() or QApplication([])
    db_path = tmp_path / "gui.db"
    first = tmp_path / "first.png"
    second = tmp_path / "second.png"
    first.write_bytes(b"first")
    second.write_bytes(b"second")
    with connect(db_path) as conn:
        init_db(conn)
        repo = ReminderRepository(conn)
        with conn:
            repo.add_sticker_asset("first.png", str(first))
            repo.add_sticker_asset("second.png", str(second))
            repo.set_setting("sticker_mode", "random")

    monkeypatch.setattr(
        "renew_curve.ui.main_window.random.choice", lambda values: values[-1]
    )
    window = MainWindow(db_path)

    assert window.today_section.sticker_path == second
    assert window.next_three_days_section.sticker_path == second
    assert window.all_tasks_section.sticker_path == second

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
