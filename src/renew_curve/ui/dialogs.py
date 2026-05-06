from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
)


class TaskDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("New task")

        self.title_edit = QLineEdit()
        self.category_edit = QLineEdit()
        self.difficulty_combo = QComboBox()
        self.difficulty_combo.addItems(["初級", "中級", "高級"])
        self.notes_edit = QTextEdit()
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["遺忘曲線", "手動輸入"])

        form = QFormLayout()
        form.addRow("Title", self.title_edit)
        form.addRow("Category", self.category_edit)
        form.addRow("Difficulty", self.difficulty_combo)
        form.addRow("Notes", self.notes_edit)
        form.addRow("Mode", self.mode_combo)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(buttons)


class ImportExportDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Import / Export")

        description = QLabel(
            "Legacy CSV files from the Tkinter version are supported."
        )
        description.setWordWrap(True)

        self.import_replace_button = QPushButton("Import replace")
        self.import_merge_button = QPushButton("Import merge")
        self.export_button = QPushButton("Export")

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
            "Choose CSV to import",
            "",
            "CSV files (*.csv);;All files (*.*)",
        )
        return Path(path) if path else None

    def choose_csv_save(self) -> Path | None:
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Choose CSV export path",
            "",
            "CSV files (*.csv);;All files (*.*)",
        )
        return Path(path) if path else None
