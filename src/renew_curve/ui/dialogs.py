from __future__ import annotations

import datetime as dt
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

from renew_curve.scheduler import generated_review_times, validate_manual_review_times


class SettingsDialog(QDialog):
    def __init__(self, parent=None, current: dict[str, str] | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("個人化")
        current = current or {}

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

        form = QFormLayout()
        form.addRow("主題", self.theme_combo)
        form.addRow("重點色", self.accent_combo)
        form.addRow("介面密度", self.density_combo)
        form.addRow("預設稍後提醒", self.snooze_combo)
        form.addRow("介面風格", self.theme_style_combo)
        form.addRow("貼圖顯示範圍", self.sticker_scope_combo)
        form.addRow("功能視窗貼圖密度", self.functional_sticker_density_combo)
        form.addRow("背景透明遮罩", self.background_overlay_spin)
        form.addRow("背景模糊", self.background_blur_spin)
        form.addRow("背景暗化", self.background_darken_spin)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(buttons)

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

    def set_sticker_assets(self, assets: list[tuple[int, str, str, bool]]) -> None:
        self.sticker_assets = assets

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
        stats_layout.addWidget(
            QLabel("計算方式：前 7 天所有到期提醒加總後，以完成數 / 應完成數計算。")
        )
        stats_layout.addStretch(1)

        body = QHBoxLayout()
        body.addWidget(stats_panel, 1)
        body.addWidget(actions_panel, 1)

        layout = QVBoxLayout(self)
        layout.addLayout(header)
        layout.addLayout(body)

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
