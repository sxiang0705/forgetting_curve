from __future__ import annotations

import datetime as dt
from pathlib import Path

from PySide6.QtCore import QDateTime
from PySide6.QtWidgets import (
    QComboBox,
    QDateTimeEdit,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QTextEdit,
    QVBoxLayout,
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

        form = QFormLayout()
        form.addRow("主題", self.theme_combo)
        form.addRow("重點色", self.accent_combo)
        form.addRow("介面密度", self.density_combo)
        form.addRow("預設稍後提醒", self.snooze_combo)

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
        }

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
        for _ in range(10):
            edit = QDateTimeEdit(QDateTime.currentDateTime())
            edit.setCalendarPopup(True)
            edit.setDisplayFormat("yyyy-MM-dd HH:mm")
            self.manual_time_edits.append(edit)

        form = QFormLayout()
        form.addRow("任務名稱", self.title_edit)
        form.addRow("分類", self.category_edit)
        form.addRow("難度", self.difficulty_combo)
        form.addRow("筆記", self.notes_edit)
        form.addRow("提醒模式", self.mode_combo)
        form.addRow("開始時間", self.start_edit)
        form.addRow("複習次數", self.review_count_spin)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(buttons)

    def set_categories(self, categories: list[str]) -> None:
        self.category_edit.clear()
        self.category_edit.addItems(categories)
        self.category_edit.setEditable(True)

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


class ImportExportDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("匯入 / 匯出")

        description = QLabel(
            "支援匯入舊版 Tkinter 匯出的 CSV 檔案。"
        )
        description.setWordWrap(True)

        self.import_replace_button = QPushButton("取代匯入")
        self.import_merge_button = QPushButton("合併匯入")
        self.export_button = QPushButton("匯出")

        actions = QHBoxLayout()
        actions.addWidget(self.import_replace_button)
        actions.addWidget(self.import_merge_button)
        actions.addWidget(self.export_button)

        layout = QVBoxLayout(self)
        layout.addWidget(description)
        layout.addLayout(actions)

    def choose_csv_open(self) -> Path | None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "選擇要匯入的 CSV",
            "",
            "CSV files (*.csv);;All files (*.*)",
        )
        return Path(path) if path else None

    def choose_csv_save(self) -> Path | None:
        path, _ = QFileDialog.getSaveFileName(
            self,
            "選擇 CSV 匯出位置",
            "",
            "CSV files (*.csv);;All files (*.*)",
        )
        return Path(path) if path else None
