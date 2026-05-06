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
        self.category_edit = QLineEdit()
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

    def values(self) -> dict[str, object]:
        start_time = self.start_edit.dateTime().toPython()
        if isinstance(start_time, dt.datetime) and start_time.tzinfo is not None:
            start_time = start_time.replace(tzinfo=None)
        return {
            "title": self.title_edit.text().strip(),
            "category": self.category_edit.text().strip(),
            "difficulty": self.difficulty_combo.currentText(),
            "notes": self.notes_edit.toPlainText().strip(),
            "reminder_method": self.mode_combo.currentText(),
            "start_time": start_time,
            "review_count": self.review_count_spin.value(),
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
