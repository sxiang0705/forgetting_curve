from __future__ import annotations

import datetime as dt
from collections.abc import Callable
from pathlib import Path

from PySide6.QtCore import QDateTime, Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDateTimeEdit,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from renew_curve.models import ReportStats
from renew_curve.scheduler import generated_review_times, validate_manual_review_times


class SettingsDialog(QDialog):
    def __init__(
        self,
        parent=None,
        current: dict[str, str] | None = None,
        upload_background: Callable[[Path], None] | None = None,
        upload_sticker: Callable[[Path], None] | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("個人化")
        self.resize(960, 560)
        current = current or {}
        self._upload_background = upload_background
        self._upload_sticker = upload_sticker

        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["light", "dark", "system"])
        self._set_current(self.theme_combo, current.get("theme", "light"))

        self.accent_combo = QComboBox()
        self.accent_combo.addItems(["blue", "green", "purple", "orange", "gray"])
        self._set_current(self.accent_combo, current.get("accent", "blue"))

        self.density_combo = QComboBox()
        self.density_combo.addItems(["comfortable", "compact"])
        self._set_current(self.density_combo, current.get("density", "comfortable"))

        self.snooze_combo = QComboBox()
        self.snooze_combo.addItems(["10m", "1h", "tomorrow"])
        self._set_current(self.snooze_combo, current.get("default_snooze", "10m"))

        self.theme_style_combo = QComboBox()
        self.theme_style_combo.addItems(["clean_mountain", "healing_pastel", "dark_focus"])
        self._set_current(
            self.theme_style_combo, current.get("theme_style", "clean_mountain")
        )

        self.sticker_scope_combo = QComboBox()
        self.sticker_scope_combo.addItems(["main_only", "all_windows", "disabled"])
        self._set_current(
            self.sticker_scope_combo, current.get("sticker_scope", "main_only")
        )

        self.functional_sticker_density_combo = QComboBox()
        self.functional_sticker_density_combo.addItems(["low", "normal", "high"])
        self._set_current(
            self.functional_sticker_density_combo,
            current.get("functional_window_sticker_density", "low"),
        )

        self.background_overlay_spin = QSpinBox()
        self.background_overlay_spin.setRange(0, 100)
        self.background_overlay_spin.setValue(int(current.get("background_overlay", "60")))

        self.background_blur_spin = QSpinBox()
        self.background_blur_spin.setRange(0, 30)
        self.background_blur_spin.setValue(int(current.get("background_blur", "0")))

        self.background_darken_spin = QSpinBox()
        self.background_darken_spin.setRange(0, 100)
        self.background_darken_spin.setValue(int(current.get("background_darken", "20")))

        self.background_assets: list[tuple[int, str, str, bool]] = []
        self.sticker_assets: list[tuple[int, str, str, bool]] = []

        self.interface_section_title = QLabel("介面風格")
        self.interface_section_title.setStyleSheet("font-size: 22px; font-weight: 800;")
        self.interface_help_label = QLabel(
            "主題模式會決定整體氣氛；重點色、密度與推延偏好會套用到所有主要視窗。"
        )
        self.interface_help_label.setObjectName("Muted")
        self.interface_help_label.setWordWrap(True)
        self.accent_help_label = QLabel("重點色會套用在按鈕、選取狀態與月曆焦點。")
        self.accent_help_label.setObjectName("Muted")
        self.accent_help_label.setWordWrap(True)
        self.density_help_label = QLabel("密度會影響留白與列表高度，16 吋與 27 吋螢幕都會較好閱讀。")
        self.density_help_label.setObjectName("Muted")
        self.density_help_label.setWordWrap(True)
        interface_form = QFormLayout()
        interface_form.addRow("主題", self.theme_combo)
        interface_form.addRow("重點色", self.accent_combo)
        interface_form.addRow("介面密度", self.density_combo)
        interface_form.addRow("預設推延", self.snooze_combo)
        interface_form.addRow("主題模式", self.theme_style_combo)
        interface_form.addRow("貼圖顯示範圍", self.sticker_scope_combo)
        interface_form.addRow("功能視窗貼圖密度", self.functional_sticker_density_combo)

        interface_panel = QFrame()
        interface_panel.setObjectName("Panel")
        interface_layout = QVBoxLayout(interface_panel)
        interface_layout.addWidget(self.interface_section_title)
        interface_layout.addWidget(self.interface_help_label)
        interface_layout.addWidget(self.accent_help_label)
        interface_layout.addWidget(self.density_help_label)
        interface_layout.addLayout(interface_form)

        self.assets_section_title = QLabel("我的素材")
        self.assets_section_title.setStyleSheet("font-size: 22px; font-weight: 800;")
        asset_panel = QFrame()
        asset_panel.setObjectName("Panel")
        asset_layout = QVBoxLayout(asset_panel)
        asset_layout.addWidget(self.assets_section_title)

        self.upload_background_button = QPushButton("上傳背景圖片")
        self.upload_sticker_button = QPushButton("上傳貼圖 PNG / GIF")
        self.upload_background_button.clicked.connect(self._choose_and_upload_background)
        self.upload_sticker_button.clicked.connect(self._choose_and_upload_sticker)
        asset_layout.addWidget(self.upload_background_button)
        asset_layout.addWidget(self.upload_sticker_button)

        sliders = QFormLayout()
        sliders.addRow("背景透明遮罩", self.background_overlay_spin)
        sliders.addRow("背景模糊", self.background_blur_spin)
        sliders.addRow("背景暗化", self.background_darken_spin)
        asset_layout.addLayout(sliders)

        self.background_list = QVBoxLayout()
        self.sticker_list = QVBoxLayout()
        lists = QWidget()
        lists_layout = QVBoxLayout(lists)
        lists_layout.setContentsMargins(0, 0, 0, 0)
        lists_layout.addWidget(QLabel("背景圖片"))
        lists_layout.addLayout(self.background_list)
        lists_layout.addWidget(QLabel("小貼圖"))
        lists_layout.addLayout(self.sticker_list)
        self.asset_scroll = QScrollArea()
        self.asset_scroll.setWidgetResizable(True)
        self.asset_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.asset_scroll.setWidget(lists)
        self.asset_scroll.setMinimumHeight(170)
        self.asset_scroll.setMaximumHeight(240)
        asset_layout.addWidget(self.asset_scroll)

        left_content = QWidget()
        left_layout = QVBoxLayout(left_content)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(14)
        left_layout.addWidget(interface_panel)
        left_layout.addWidget(asset_panel, 1)

        self.preview_title = QLabel("預覽")
        self.preview_title.setStyleSheet("font-size: 22px; font-weight: 800;")
        preview_panel = QFrame()
        preview_panel.setObjectName("PersonalizationPreview")
        preview_layout = QVBoxLayout(preview_panel)
        preview_layout.addWidget(self.preview_title)
        preview_layout.addWidget(QLabel("今天任務"))
        preview_task = QFrame()
        preview_task.setObjectName("Panel")
        preview_task_layout = QVBoxLayout(preview_task)
        preview_task_layout.addWidget(QLabel("英文單字 Unit 12"))
        note = QLabel("背景、主題色與貼圖會套用在正式畫面與功能視窗。")
        note.setObjectName("Muted")
        note.setWordWrap(True)
        preview_task_layout.addWidget(note)
        preview_layout.addWidget(preview_task)
        preview_layout.addStretch(1)

        header = QHBoxLayout()
        title = QLabel("個人化")
        title.setStyleSheet("font-size: 24px; font-weight: 800;")
        header.addWidget(title, 1)
        self.close_button = QPushButton("×")
        self.close_button.setFixedSize(36, 36)
        self.close_button.clicked.connect(self.reject)
        header.addWidget(self.close_button)

        body = QHBoxLayout()
        body.setSpacing(16)
        body.addWidget(left_content, 1)
        body.addWidget(preview_panel, 2)

        self.apply_button = QPushButton("套用設定")
        self.apply_button.setObjectName("PrimaryButton")
        self.apply_button.clicked.connect(self.accept)
        footer = QHBoxLayout()
        footer.addStretch(1)
        footer.addWidget(self.apply_button)

        layout = QVBoxLayout(self)
        layout.addLayout(header)
        layout.addLayout(body, 1)
        layout.addLayout(footer)
        self._render_asset_lists()

    def values(self) -> dict[str, str]:
        return {
            "theme": self.theme_combo.currentText(),
            "accent": self.accent_combo.currentText(),
            "density": self.density_combo.currentText(),
            "default_snooze": self.snooze_combo.currentText(),
            "theme_style": self.theme_style_combo.currentText(),
            "sticker_scope": self.sticker_scope_combo.currentText(),
            "functional_window_sticker_density": self.functional_sticker_density_combo.currentText(),
            "background_overlay": str(self.background_overlay_spin.value()),
            "background_blur": str(self.background_blur_spin.value()),
            "background_darken": str(self.background_darken_spin.value()),
        }

    def set_background_assets(self, assets: list[tuple[int, str, str, bool]]) -> None:
        self.background_assets = assets
        self._render_asset_lists()

    def set_sticker_assets(self, assets: list[tuple[int, str, str, bool]]) -> None:
        self.sticker_assets = assets
        self._render_asset_lists()

    def choose_background_file(self) -> Path | None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "上傳背景圖片",
            "",
            "Images (*.png *.jpg *.jpeg *.webp *.bmp)",
        )
        return Path(path) if path else None

    def choose_sticker_file(self) -> Path | None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "上傳貼圖",
            "",
            "Images (*.png *.gif *.jpg *.jpeg *.webp *.bmp)",
        )
        return Path(path) if path else None

    def _choose_and_upload_background(self) -> None:
        path = self.choose_background_file()
        if path is not None and self._upload_background is not None:
            self._upload_background(path)

    def _choose_and_upload_sticker(self) -> None:
        path = self.choose_sticker_file()
        if path is not None and self._upload_sticker is not None:
            self._upload_sticker(path)

    def _render_asset_lists(self) -> None:
        if not hasattr(self, "background_list"):
            return
        self._fill_asset_list(self.background_list, self.background_assets, "尚未上傳背景")
        self._fill_asset_list(self.sticker_list, self.sticker_assets, "尚未上傳貼圖")

    def _fill_asset_list(
        self,
        layout: QVBoxLayout,
        assets: list[tuple[int, str, str, bool]],
        empty_text: str,
    ) -> None:
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        if not assets:
            empty = QLabel(empty_text)
            empty.setObjectName("Muted")
            layout.addWidget(empty)
            return
        for _asset_id, name, _path, active in assets:
            row = QFrame()
            row.setObjectName("AssetRow")
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(8, 6, 8, 6)
            row_layout.addWidget(QLabel(name), 1)
            state = QLabel("使用中" if active else "未使用")
            state.setObjectName("Muted")
            row_layout.addWidget(state)
            layout.addWidget(row)

    @staticmethod
    def _set_current(combo: QComboBox, value: str) -> None:
        index = combo.findText(value)
        if index >= 0:
            combo.setCurrentIndex(index)


class TaskDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("新增任務")

        self.title_edit = QLineEdit()
        self.category_edit = QComboBox()
        self.category_edit.setEditable(True)
        self.difficulty_combo = QComboBox()
        self.difficulty_combo.addItems(["初級", "中級", "高級"])
        self.notes_edit = QTextEdit()
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["遺忘曲線", "手動輸入"])
        self.schedule_help_label = QLabel(
            "遺忘曲線會依開始時間自動產生複習點；手動輸入可自行指定每一次提醒時間。"
        )
        self.schedule_help_label.setObjectName("Muted")
        self.schedule_help_label.setWordWrap(True)
        self.start_edit = QDateTimeEdit(QDateTime.currentDateTime())
        self.start_edit.setCalendarPopup(True)
        self.start_edit.setDisplayFormat("yyyy-MM-dd HH:mm")
        self.review_count_spin = QSpinBox()
        self.review_count_spin.setRange(3, 10)
        self.review_count_spin.setValue(5)
        self.manual_time_edits: list[QDateTimeEdit] = []
        self.manual_time_rows: list[QWidget] = []
        for _ in range(10):
            edit = QDateTimeEdit(QDateTime.currentDateTime())
            edit.setCalendarPopup(True)
            edit.setDisplayFormat("yyyy-MM-dd HH:mm")
            self.manual_time_edits.append(edit)

        self.manual_times_widget = QWidget()
        self.manual_times_layout = QVBoxLayout(self.manual_times_widget)
        self.manual_times_layout.setContentsMargins(0, 0, 0, 0)
        self.manual_times_layout.setSpacing(8)
        for index, edit in enumerate(self.manual_time_edits, start=1):
            row_widget = QWidget()
            row = QHBoxLayout(row_widget)
            row.setContentsMargins(0, 0, 0, 0)
            row.addWidget(QLabel(f"第 {index} 次"))
            row.addWidget(edit, 1)
            self.manual_time_rows.append(row_widget)
            self.manual_times_layout.addWidget(row_widget)

        form = QFormLayout()
        form.addRow("任務名稱", self.title_edit)
        form.addRow("分類", self.category_edit)
        form.addRow("難度", self.difficulty_combo)
        form.addRow("筆記", self.notes_edit)
        form.addRow("提醒模式", self.mode_combo)
        form.addRow("", self.schedule_help_label)
        form.addRow("開始時間", self.start_edit)
        form.addRow("複習次數", self.review_count_spin)

        left_panel = QFrame()
        left_panel.setObjectName("Panel")
        left_layout = QVBoxLayout(left_panel)
        left_layout.addLayout(form)
        left_layout.addWidget(self.manual_times_widget)

        self.preview_layout = QVBoxLayout()
        preview_panel = QFrame()
        preview_panel.setObjectName("Panel")
        preview_layout = QVBoxLayout(preview_panel)
        title = QLabel("複習日期預覽")
        title.setStyleSheet("font-size: 22px; font-weight: 800;")
        hint = QLabel("新增前先確認會產生哪些提醒。")
        hint.setObjectName("Muted")
        preview_layout.addWidget(title)
        preview_layout.addWidget(hint)
        preview_layout.addLayout(self.preview_layout)
        preview_layout.addStretch(1)

        content = QWidget()
        content_layout = QHBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(16)
        content_layout.addWidget(left_panel, 2)
        content_layout.addWidget(preview_panel, 1)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll_area.setWidget(content)

        self.cancel_button = QPushButton("取消")
        self.cancel_button.clicked.connect(self.reject)
        self.create_button = QPushButton("新增任務")
        self.create_button.setObjectName("PrimaryButton")
        self.create_button.clicked.connect(self.accept)
        footer = QHBoxLayout()
        footer.addStretch(1)
        footer.addWidget(self.cancel_button)
        footer.addWidget(self.create_button)

        layout = QVBoxLayout(self)
        layout.addWidget(self.scroll_area)
        layout.addLayout(footer)

        self.resize(980, 560)
        self.mode_combo.currentTextChanged.connect(self._sync_schedule_mode)
        self.start_edit.dateTimeChanged.connect(lambda _value: self._render_preview())
        self.review_count_spin.valueChanged.connect(lambda _value: self._sync_schedule_mode())
        for edit in self.manual_time_edits:
            edit.dateTimeChanged.connect(lambda _value: self._render_preview())
        self._sync_schedule_mode()

    def set_categories(self, categories: list[str]) -> None:
        self.category_edit.clear()
        self.category_edit.addItems(categories)
        self.category_edit.setEditable(True)

    def _sync_schedule_mode(self, *_args: object) -> None:
        is_manual = self.mode_combo.currentText() == "手動輸入"
        for index, row in enumerate(self.manual_time_rows):
            row.setVisible(is_manual and index < self.review_count_spin.value())
        self.manual_times_widget.setVisible(is_manual)
        self._render_preview()

    def _render_preview(self) -> None:
        while self.preview_layout.count():
            item = self.preview_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        try:
            times = self.preview_review_times()
        except ValueError as exc:
            label = QLabel(str(exc))
            label.setObjectName("Muted")
            self.preview_layout.addWidget(label)
            return
        start_time = self._start_time()
        for index, remind_time in enumerate(times, start=1):
            row = QFrame()
            row.setObjectName("PreviewRow")
            layout = QHBoxLayout(row)
            badge = QLabel(str(index))
            badge.setObjectName("CountPill")
            badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
            badge.setFixedWidth(48)
            layout.addWidget(badge)
            text = QLabel(
                f"{remind_time.strftime('%Y-%m-%d %H:%M')}\n"
                f"開始後 {max((remind_time.date() - start_time.date()).days, 0)} 天"
            )
            text.setWordWrap(True)
            layout.addWidget(text, 1)
            self.preview_layout.addWidget(row)

    def preview_review_times(self) -> list[dt.datetime]:
        start_time = self._start_time()
        if self.mode_combo.currentText() == "遺忘曲線":
            return generated_review_times(start_time, self.review_count_spin.value())
        return self.manual_review_times()

    def manual_review_times(self) -> list[dt.datetime]:
        values: list[dt.datetime] = []
        for edit in self.manual_time_edits[: self.review_count_spin.value()]:
            value = edit.dateTime().toPython()
            if isinstance(value, dt.datetime) and value.tzinfo is not None:
                value = value.replace(tzinfo=None)
            values.append(value)
        return validate_manual_review_times(values, self.review_count_spin.value())

    def _start_time(self) -> dt.datetime:
        start_time = self.start_edit.dateTime().toPython()
        if isinstance(start_time, dt.datetime) and start_time.tzinfo is not None:
            start_time = start_time.replace(tzinfo=None)
        return start_time

    def values(self) -> dict[str, object]:
        start_time = self._start_time()
        return {
            "title": self.title_edit.text().strip(),
            "category": self.category_edit.currentText().strip(),
            "difficulty": self.difficulty_combo.currentText(),
            "notes": self.notes_edit.toPlainText().strip(),
            "reminder_method": self.mode_combo.currentText(),
            "start_time": start_time,
            "review_count": self.review_count_spin.value(),
            "review_times": self.preview_review_times(),
        }


class DataDialog(QDialog):
    import_legacy_csv_button = None
    export_full_backup_button = None
    import_full_backup_button = None

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("報表 / 資料")
        self.resize(920, 560)

        description = QLabel(
            "這裡只保留三個主要入口。CSV 用於舊版資料轉移，完整資料請使用 ZIP。"
        )
        description.setWordWrap(True)

        self.import_legacy_csv_button = QPushButton("1. 匯入舊版 CSV")
        self.export_full_backup_button = QPushButton("2. 匯出完整資料")
        self.import_full_backup_button = QPushButton("3. 匯入完整資料")
        self.close_button = QPushButton("×")
        self.close_button.setFixedSize(36, 36)
        self.close_button.clicked.connect(self.accept)

        self.legacy_csv_hint = QLabel("請上傳舊版 Forgetting Curve 匯出的 .csv。")
        self.legacy_csv_hint.setWordWrap(True)
        self.full_export_hint = QLabel(
            "會下載 .zip，包含 SQLite 資料庫、背景、貼圖與個人化設定。"
        )
        self.full_export_hint.setWordWrap(True)
        self.full_import_hint = QLabel(
            "請上傳 v8 完整資料包 .zip；系統會先驗證再替換目前資料。"
        )
        self.full_import_hint.setWordWrap(True)

        header = QHBoxLayout()
        title = QLabel("報表 / 資料")
        title.setStyleSheet("font-size: 24px; font-weight: 800;")
        header.addWidget(title, 1)
        header.addWidget(self.close_button)

        actions_panel = QFrame()
        actions_panel.setObjectName("Panel")
        actions_layout = QVBoxLayout(actions_panel)
        actions_title = QLabel("資料操作")
        actions_title.setStyleSheet("font-size: 22px; font-weight: 800;")
        actions_layout.addWidget(actions_title)
        actions_layout.addWidget(description)
        actions_layout.addWidget(self.import_legacy_csv_button)
        actions_layout.addWidget(self.legacy_csv_hint)
        actions_layout.addWidget(self.export_full_backup_button)
        actions_layout.addWidget(self.full_export_hint)
        actions_layout.addWidget(self.import_full_backup_button)
        actions_layout.addWidget(self.full_import_hint)
        warning = QLabel(
            "CSV 只給舊版資料轉移使用；完整備份與還原請使用 ZIP，避免傳錯格式。"
        )
        warning.setWordWrap(True)
        warning.setObjectName("WarningNote")
        actions_layout.addWidget(warning)
        actions_layout.addStretch(1)

        stats_panel = QFrame()
        stats_panel.setObjectName("Panel")
        stats_layout = QVBoxLayout(stats_panel)
        stats_title = QLabel("前 7 天總完成率")
        stats_title.setStyleSheet("font-size: 22px; font-weight: 800;")
        stats_layout.addWidget(stats_title)
        weekly_note = QLabel(
            "計算方式：前 7 天所有到期提醒加總後，以完成數 / 應完成數計算。"
        )
        weekly_note.setWordWrap(True)
        stats_layout.addWidget(weekly_note)
        self.weekly_rate_value = QLabel("--")
        self.weekly_rate_value.setStyleSheet("font-size: 42px; font-weight: 900;")
        self.weekly_fraction_label = QLabel("尚未載入統計")
        self.weekly_fraction_label.setObjectName("Muted")
        stats_layout.addWidget(self.weekly_rate_value)
        stats_layout.addWidget(self.weekly_fraction_label)

        self.total_tasks_value = QLabel("0")
        self.today_reminders_value = QLabel("0")
        self.pending_reminders_value = QLabel("0")
        self.completed_reminders_value = QLabel("0")
        self.total_completion_value = QLabel("0%")
        metric_row = QHBoxLayout()
        metric_row.addWidget(self._metric_card("全部任務", self.total_tasks_value))
        metric_row.addWidget(self._metric_card("今日任務", self.today_reminders_value))
        metric_row.addWidget(self._metric_card("總完成率", self.total_completion_value))
        stats_layout.addLayout(metric_row)

        reminder_row = QHBoxLayout()
        reminder_row.addWidget(
            self._metric_card("未完成提醒", self.pending_reminders_value)
        )
        reminder_row.addWidget(
            self._metric_card("已完成提醒", self.completed_reminders_value)
        )
        stats_layout.addLayout(reminder_row)
        stats_layout.addStretch(1)

        body = QHBoxLayout()
        body.addWidget(stats_panel, 1)
        body.addWidget(actions_panel, 1)

        layout = QVBoxLayout(self)
        layout.addLayout(header)
        layout.addLayout(body)

    def set_report_summary(
        self,
        stats: ReportStats,
        *,
        weekly_completed: int,
        weekly_total: int,
        weekly_rate: float,
    ) -> None:
        self.total_tasks_value.setText(str(stats.total_tasks))
        self.today_reminders_value.setText(str(stats.today_reminders))
        self.pending_reminders_value.setText(str(stats.pending_reminders))
        self.completed_reminders_value.setText(str(stats.completed_reminders))
        self.total_completion_value.setText(f"{stats.total_completion_percent:.0f}%")
        self.weekly_rate_value.setText(f"{weekly_rate:.0f}%")
        self.weekly_fraction_label.setText(
            f"{weekly_completed} / {weekly_total} 筆提醒已完成"
        )

    def _metric_card(self, title: str, value_label: QLabel) -> QFrame:
        card = QFrame()
        card.setObjectName("Panel")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(10, 8, 10, 8)
        label = QLabel(title)
        label.setObjectName("Muted")
        value_label.setStyleSheet("font-size: 24px; font-weight: 800;")
        layout.addWidget(label)
        layout.addWidget(value_label)
        return card

    def choose_csv_open(self) -> Path | None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "匯入舊版 CSV",
            "",
            "CSV files (*.csv)",
        )
        return Path(path) if path else None

    def choose_zip_open(self) -> Path | None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "匯入完整資料",
            "",
            "ZIP files (*.zip)",
        )
        return Path(path) if path else None

    def choose_zip_save(self) -> Path | None:
        path, _ = QFileDialog.getSaveFileName(
            self,
            "匯出完整資料",
            "",
            "ZIP files (*.zip)",
        )
        return Path(path) if path else None

    def choose_csv_save(self) -> Path | None:
        path, _ = QFileDialog.getSaveFileName(
            self,
            "匯出 CSV 備份",
            "",
            "CSV files (*.csv)",
        )
        return Path(path) if path else None


class ImportExportDialog(DataDialog):
    pass
