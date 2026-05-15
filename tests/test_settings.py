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


def test_settings_dialog_uses_personalization_sections(monkeypatch):
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")

    from PySide6.QtWidgets import QApplication

    from renew_curve.ui.dialogs import SettingsDialog

    app = QApplication.instance() or QApplication([])
    dialog = SettingsDialog()

    assert dialog.interface_section_title.text() == "基本偏好"
    assert dialog.background_assets_title.text() == "背景庫"
    assert dialog.sticker_assets_title.text() == "貼圖庫"
    assert dialog.preview_title.text() == "預覽"
    assert dialog.background_asset_scroll.widgetResizable() is True
    assert dialog.sticker_asset_scroll.widgetResizable() is True
    assert dialog.apply_button.text() == "套用設定"
    assert dialog.close_button.text() == "×"

    dialog.close()
    app.processEvents()


def test_settings_dialog_basic_preferences_are_compact(monkeypatch):
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")

    from PySide6.QtWidgets import QApplication, QGridLayout

    from renew_curve.ui.dialogs import SettingsDialog

    app = QApplication.instance() or QApplication([])
    dialog = SettingsDialog()

    assert isinstance(dialog.interface_form_layout, QGridLayout)
    assert dialog.interface_form_layout.columnCount() >= 4
    assert dialog.interface_help_label.isHidden() is True
    assert dialog.accent_help_label.isHidden() is True
    assert dialog.density_help_label.isHidden() is True
    assert dialog.interface_panel.maximumHeight() <= 220

    dialog.close()
    app.processEvents()


def test_settings_dialog_exposes_section_background_selectors_and_preview(monkeypatch):
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")

    from PySide6.QtWidgets import QApplication

    from renew_curve.ui.dialogs import SettingsDialog

    app = QApplication.instance() or QApplication([])
    dialog = SettingsDialog(
        current={
            "background_mode": "selected",
            "today_background_id": "2",
            "next_background_id": "3",
            "all_background_id": "4",
        }
    )

    dialog.set_background_assets(
        [
            (4, "all.jpg", "C:/tmp/all.jpg", True),
            (3, "next.jpg", "C:/tmp/next.jpg", True),
            (2, "today.jpg", "C:/tmp/today.jpg", True),
        ]
    )
    dialog.set_sticker_assets([(9, "sticker.png", "C:/tmp/sticker.png", True)])

    assert dialog.today_background_combo.currentData() == "2"
    assert dialog.next_background_combo.currentData() == "3"
    assert dialog.all_background_combo.currentData() == "4"
    assert dialog.today_preview_panel.background_path == "C:/tmp/today.jpg"
    assert dialog.next_preview_panel.background_path == "C:/tmp/next.jpg"
    assert dialog.all_preview_panel.background_path == "C:/tmp/all.jpg"
    assert dialog.preview_panel is dialog.today_preview_panel
    assert dialog.today_preview_panel.sticker_path == "C:/tmp/sticker.png"

    dialog.background_blur_spin.setValue(8)
    dialog.background_darken_spin.setValue(30)
    assert dialog.today_preview_panel.blur_radius == 8
    assert dialog.next_preview_panel.darken_alpha == int(255 * 30 / 100)

    values = dialog.values()
    assert values["background_mode"] == "selected"
    assert values["today_background_id"] == "2"
    assert values["next_background_id"] == "3"
    assert values["all_background_id"] == "4"

    dialog.close()
    app.processEvents()


def test_settings_dialog_disables_selectors_in_random_modes(monkeypatch):
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")

    from PySide6.QtWidgets import QApplication

    from renew_curve.ui.dialogs import SettingsDialog

    app = QApplication.instance() or QApplication([])
    dialog = SettingsDialog(
        current={
            "background_mode": "random",
            "sticker_mode": "random",
            "selected_sticker_id": "9",
        }
    )
    dialog.set_background_assets([(2, "bg.jpg", "C:/tmp/bg.jpg", True)])
    dialog.set_sticker_assets([(9, "sticker.png", "C:/tmp/sticker.png", True)])

    assert dialog.today_background_combo.isEnabled() is False
    assert dialog.next_background_combo.isEnabled() is False
    assert dialog.all_background_combo.isEnabled() is False
    assert dialog.selected_sticker_combo.isEnabled() is False

    dialog.background_mode_combo.setCurrentIndex(
        dialog.background_mode_combo.findData("selected")
    )
    dialog.sticker_mode_combo.setCurrentIndex(dialog.sticker_mode_combo.findData("selected"))

    assert dialog.today_background_combo.isEnabled() is True
    assert dialog.selected_sticker_combo.isEnabled() is True
    assert dialog.values()["sticker_mode"] == "selected"
    assert dialog.values()["selected_sticker_id"] == "9"

    dialog.close()
    app.processEvents()


def test_settings_dialog_asset_rows_have_fixed_thumbnail_and_elided_name(monkeypatch):
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")

    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QApplication, QLabel, QScrollArea

    from renew_curve.ui.dialogs import SettingsDialog

    app = QApplication.instance() or QApplication([])
    long_name = "this-is-a-very-long-background-file-name-that-should-not-push-layout.jpg"
    dialog = SettingsDialog()
    dialog.set_background_assets([(7, long_name, "C:/tmp/bg.jpg", True)])
    dialog.set_sticker_assets([(9, "cute-sticker.png", "C:/tmp/sticker.png", True)])

    thumbnails = dialog.findChildren(QLabel, "AssetThumbnail")
    names = dialog.findChildren(QLabel, "AssetName")
    name_scrolls = dialog.findChildren(QScrollArea, "AssetNameScroll")

    assert thumbnails
    assert all(label.minimumWidth() == 48 for label in thumbnails)
    assert all(label.maximumWidth() == 48 for label in thumbnails)
    assert all(label.maximumHeight() == 48 for label in thumbnails)
    assert any(label.toolTip() == long_name for label in names)
    long_name_label = next(label for label in names if label.toolTip() == long_name)
    assert long_name_label.text() == long_name
    assert long_name_label.minimumWidth() > 320
    assert name_scrolls
    assert all(scroll.widgetResizable() is False for scroll in name_scrolls)
    assert all(
        scroll.horizontalScrollBarPolicy() == Qt.ScrollBarPolicy.ScrollBarAsNeeded
        for scroll in name_scrolls
    )
    assert dialog.background_asset_scroll.horizontalScrollBarPolicy() == (
        Qt.ScrollBarPolicy.ScrollBarAsNeeded
    )
    assert dialog.sticker_asset_scroll.horizontalScrollBarPolicy() == (
        Qt.ScrollBarPolicy.ScrollBarAsNeeded
    )

    dialog.close()
    app.processEvents()


def test_settings_dialog_explains_interface_fields_and_uploads_assets(monkeypatch):
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")

    from pathlib import Path

    from PySide6.QtWidgets import QApplication

    from renew_curve.ui.dialogs import SettingsDialog

    app = QApplication.instance() or QApplication([])
    captured: list[tuple[str, Path]] = []
    dialog = SettingsDialog(
        upload_background=lambda path: captured.append(("background", path)),
        upload_sticker=lambda path: captured.append(("sticker", path)),
    )

    assert "基本偏好" in dialog.interface_help_label.text()
    assert "重點色會套用在按鈕" in dialog.accent_help_label.text()
    assert "密度會影響留白" in dialog.density_help_label.text()

    monkeypatch.setattr(
        SettingsDialog,
        "choose_background_file",
        lambda self: Path("C:/tmp/background.png"),
    )
    monkeypatch.setattr(
        SettingsDialog,
        "choose_sticker_file",
        lambda self: Path("C:/tmp/sticker.png"),
    )
    dialog.upload_background_button.click()
    dialog.upload_sticker_button.click()

    assert captured == [
        ("background", Path("C:/tmp/background.png")),
        ("sticker", Path("C:/tmp/sticker.png")),
    ]

    dialog.close()
    app.processEvents()


def test_settings_dialog_keeps_asset_list_scrollable(monkeypatch):
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")

    from PySide6.QtWidgets import QApplication

    from renew_curve.ui.dialogs import SettingsDialog

    app = QApplication.instance() or QApplication([])
    dialog = SettingsDialog()

    assert dialog.background_asset_scroll.widgetResizable() is True
    assert dialog.sticker_asset_scroll.widgetResizable() is True
    assert 200 <= dialog.background_asset_scroll.minimumHeight() <= 240
    assert dialog.background_asset_scroll.maximumHeight() <= 340
    assert 200 <= dialog.sticker_asset_scroll.minimumHeight() <= 240
    assert dialog.sticker_asset_scroll.maximumHeight() <= 340

    dialog.close()
    app.processEvents()


def test_settings_dialog_deletes_assets_through_callbacks(monkeypatch):
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")

    from PySide6.QtWidgets import QApplication

    from renew_curve.ui.dialogs import SettingsDialog

    app = QApplication.instance() or QApplication([])
    deleted: list[tuple[str, int]] = []
    dialog = SettingsDialog(
        delete_background=lambda asset_id: deleted.append(("background", asset_id)),
        delete_sticker=lambda asset_id: deleted.append(("sticker", asset_id)),
    )
    dialog.set_background_assets([(7, "bg.png", "C:/tmp/bg.png", True)])
    dialog.set_sticker_assets([(9, "cat.png", "C:/tmp/cat.png", True)])

    dialog.background_delete_buttons[7].click()
    dialog.sticker_delete_buttons[9].click()

    assert deleted == [("background", 7), ("sticker", 9)]

    dialog.close()
    app.processEvents()


def test_settings_dialog_asset_columns_split_evenly(monkeypatch):
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")

    from PySide6.QtWidgets import QApplication

    from renew_curve.ui.dialogs import SettingsDialog

    app = QApplication.instance() or QApplication([])
    dialog = SettingsDialog()

    assert dialog.asset_columns_layout.stretch(
        dialog.asset_columns_layout.indexOf(dialog.background_panel)
    ) == 1
    assert dialog.asset_columns_layout.stretch(
        dialog.asset_columns_layout.indexOf(dialog.sticker_panel)
    ) == 1

    dialog.close()
    app.processEvents()


def test_settings_dialog_background_selectors_do_not_force_wide_library(monkeypatch):
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")

    from PySide6.QtWidgets import QApplication, QComboBox, QSizePolicy

    from renew_curve.ui.dialogs import SettingsDialog

    app = QApplication.instance() or QApplication([])
    dialog = SettingsDialog()
    dialog.set_background_assets(
        [
            (
                7,
                "20250903204550_85c2ed011d958f960697985207052522.jpg",
                "C:/tmp/bg.jpg",
                True,
            )
        ]
    )

    for combo in (
        dialog.today_background_combo,
        dialog.next_background_combo,
        dialog.all_background_combo,
    ):
        assert combo.sizeAdjustPolicy() == (
            QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon
        )
        assert combo.minimumContentsLength() <= 18
        assert combo.sizePolicy().horizontalPolicy() == QSizePolicy.Policy.Ignored

    dialog.close()
    app.processEvents()


def test_settings_dialog_gives_asset_libraries_more_width(monkeypatch):
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")

    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QApplication, QLabel

    from renew_curve.ui.dialogs import SettingsDialog

    app = QApplication.instance() or QApplication([])
    dialog = SettingsDialog()
    dialog.set_sticker_assets(
        [
            (
                9,
                "very-long-sticker-file-name-that-should-have-readable-room.png",
                "C:/tmp/sticker.png",
                True,
            )
        ]
    )

    assert dialog.width() >= dialog.minimumWidth()
    assert dialog.minimumWidth() >= 320
    assert dialog.body_layout.stretch(dialog.body_layout.indexOf(dialog.left_content)) == 3
    assert dialog.body_layout.stretch(dialog.body_layout.indexOf(dialog.preview_container)) == 2
    assert dialog.asset_columns_layout.stretch(
        dialog.asset_columns_layout.indexOf(dialog.sticker_panel)
    ) == dialog.asset_columns_layout.stretch(
        dialog.asset_columns_layout.indexOf(dialog.background_panel)
    )
    names = dialog.findChildren(QLabel, "AssetName")
    assert names
    assert all(label.minimumWidth() >= 300 for label in names)

    dialog.close()
    app.processEvents()


def test_settings_dialog_opens_wider_for_asset_management(monkeypatch):
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")

    from PySide6.QtWidgets import QApplication

    from renew_curve.ui.dialogs import SettingsDialog

    app = QApplication.instance() or QApplication([])
    dialog = SettingsDialog()

    assert 320 <= dialog.minimumWidth() <= dialog.width()
    assert 500 <= dialog.minimumHeight() <= dialog.height()
    assert dialog.maximumWidth() >= dialog.width()
    assert dialog.maximumHeight() >= dialog.height()
    assert dialog.body_scroll.widgetResizable() is True

    dialog.close()
    app.processEvents()


def test_settings_dialog_refits_when_shown_on_available_screen(monkeypatch):
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")

    from PySide6.QtWidgets import QApplication

    from renew_curve.ui.dialogs import SettingsDialog

    app = QApplication.instance() or QApplication([])
    screen = app.primaryScreen()
    assert screen is not None
    available = screen.availableGeometry()
    dialog = SettingsDialog()

    dialog.show()
    app.processEvents()

    assert dialog.width() <= available.width()
    assert dialog.height() <= available.height()
    assert dialog.maximumWidth() <= available.width()
    assert dialog.maximumHeight() <= available.height()

    dialog.close()
    app.processEvents()


def test_settings_dialog_size_fits_common_16_inch_screen():
    from renew_curve.ui.dialogs import responsive_window_size

    width, height, min_width, min_height = responsive_window_size(
        available_width=1366,
        available_height=728,
        preferred_width=1440,
        preferred_height=740,
        minimum_width=960,
        minimum_height=560,
    )

    assert width <= 1260
    assert height <= 650
    assert min_width <= width
    assert min_height <= height

    large_width, large_height, _min_width, _min_height = responsive_window_size(
        available_width=2560,
        available_height=1392,
        preferred_width=1440,
        preferred_height=740,
        minimum_width=960,
        minimum_height=560,
    )
    assert large_width == 1440
    assert large_height == 740


def test_data_dialog_uses_responsive_scrollable_body(monkeypatch):
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")

    from PySide6.QtWidgets import QApplication

    from renew_curve.ui.dialogs import DataDialog

    app = QApplication.instance() or QApplication([])
    dialog = DataDialog()

    assert dialog.body_scroll.widgetResizable() is True
    assert dialog.minimumWidth() <= dialog.width()
    assert dialog.minimumHeight() <= dialog.height()
    assert dialog.maximumWidth() >= dialog.width()
    assert dialog.maximumHeight() >= dialog.height()

    dialog.close()
    app.processEvents()


def test_settings_dialog_keeps_delete_buttons_inside_asset_rows(monkeypatch):
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")

    from PySide6.QtWidgets import QApplication, QFrame, QPushButton

    from renew_curve.ui.dialogs import SettingsDialog

    app = QApplication.instance() or QApplication([])
    long_name = "20250903204550_85c2ed011d958f960697985207052522.jpg"
    dialog = SettingsDialog()
    dialog.set_background_assets([(7, long_name, "C:/tmp/bg.jpg", True)])
    dialog.set_sticker_assets([(9, "images (1).jpg", "C:/tmp/sticker.jpg", True)])

    rows = dialog.findChildren(QFrame, "AssetRow")
    delete_buttons = dialog.findChildren(QPushButton, "AssetDeleteButton")

    assert rows
    assert delete_buttons
    assert all(row.minimumWidth() <= 1 for row in rows)
    assert all(button.isVisibleTo(button.parentWidget()) for button in delete_buttons)

    dialog.close()
    app.processEvents()


def test_settings_dialog_uses_movie_for_gif_sticker_preview_and_thumbnail(
    monkeypatch, tmp_path
):
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")

    from PySide6.QtWidgets import QApplication, QLabel

    from renew_curve.ui.dialogs import SettingsDialog

    app = QApplication.instance() or QApplication([])
    sticker = tmp_path / "animated.gif"
    sticker.write_bytes(
        b"GIF89a\x01\x00\x01\x00\x80\x00\x00\x00\x00\x00\xff\xff\xff!"
        b"\xf9\x04\x00\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01\x00"
        b"\x00\x02\x02D\x01\x00;"
    )
    dialog = SettingsDialog()
    dialog.set_sticker_assets([(9, "animated.gif", str(sticker), True)])

    thumbnails = dialog.findChildren(QLabel, "AssetThumbnail")

    assert any(label.movie() is not None for label in thumbnails)
    assert dialog.today_preview_panel._sticker_movie is not None
    assert dialog.next_preview_panel._sticker_movie is not None
    assert dialog.all_preview_panel._sticker_movie is not None

    dialog.close()
    app.processEvents()


def test_settings_dialog_asset_titles_stay_top_aligned(monkeypatch):
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")

    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QApplication, QSizePolicy

    from renew_curve.ui.dialogs import SettingsDialog

    app = QApplication.instance() or QApplication([])
    dialog = SettingsDialog()

    assert dialog.background_panel_layout.alignment() & Qt.AlignmentFlag.AlignTop
    assert dialog.sticker_panel_layout.alignment() & Qt.AlignmentFlag.AlignTop
    assert (
        dialog.background_assets_title.sizePolicy().verticalPolicy()
        == QSizePolicy.Policy.Fixed
    )
    assert (
        dialog.sticker_assets_title.sizePolicy().verticalPolicy()
        == QSizePolicy.Policy.Fixed
    )

    dialog.close()
    app.processEvents()
