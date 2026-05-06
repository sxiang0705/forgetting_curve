from __future__ import annotations

import datetime as dt
from contextlib import closing
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCalendarWidget,
    QDialog,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from renew_curve.csv_compat import export_legacy_csv, import_legacy_csv
from renew_curve.db import ReminderRepository, connect, init_db
from renew_curve.models import ReminderDraft, Task, TaskDraft
from renew_curve.scheduler import generated_review_times, snooze_until
from renew_curve.ui.dialogs import ImportExportDialog, SettingsDialog, TaskDialog
from renew_curve.ui.theme import build_stylesheet


class MainWindow(QMainWindow):
    def __init__(self, db_path: str = "renew_curve_v8.db") -> None:
        super().__init__()
        self.db_path = Path(db_path)
        with closing(connect(self.db_path)) as conn:
            init_db(conn)

        self.setWindowTitle("Renew Curve v8")
        self.resize(1180, 760)
        self.setStyleSheet(
            self._stylesheet_for_settings(self._load_personalization_settings())
        )

        self._build_ui()
        self.refresh_tasks()

    def close_database(self) -> None:
        pass

    def closeEvent(self, event: QCloseEvent) -> None:
        self.close_database()
        super().closeEvent(event)

    def refresh_tasks(self) -> None:
        with closing(connect(self.db_path)) as conn:
            repository = ReminderRepository(conn)
            tasks = repository.list_tasks()
            next_reminders = {
                task.id: repository.next_pending_reminder(task.id) for task in tasks
            }

        self.task_table.setRowCount(len(tasks))
        self._row_task_ids: list[int] = []
        self._row_next_reminder_ids: list[int | None] = []
        self._row_next_reminder_times: list[dt.datetime | None] = []

        for row_index, task in enumerate(tasks):
            next_reminder = next_reminders[task.id]
            self._row_task_ids.append(task.id)
            self._row_next_reminder_ids.append(
                None if next_reminder is None else next_reminder.id
            )
            self._row_next_reminder_times.append(
                None if next_reminder is None else next_reminder.remind_time
            )
            values = [
                task.title,
                task.category,
                self._format_next_reminder(next_reminder.remind_time)
                if next_reminder is not None
                else "無",
                f"{task.progress_percent:.0f}%",
                self._status_label(task),
            ]
            for column_index, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.task_table.setItem(row_index, column_index, item)

        self.total_tasks_value.setText(str(len(tasks)))
        active_count = sum(not task.is_completed for task in tasks)
        done_count = len(tasks) - active_count
        self.active_tasks_value.setText(str(active_count))
        self.completed_tasks_value.setText(str(done_count))

    def _build_ui(self) -> None:
        root = QWidget()
        root_layout = QHBoxLayout(root)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        root_layout.addWidget(self._build_sidebar())
        root_layout.addWidget(self._build_center(), 1)
        root_layout.addWidget(self._build_right_panel())

        self.setCentralWidget(root)

    def _build_sidebar(self) -> QWidget:
        sidebar = QWidget()
        sidebar.setObjectName("Sidebar")
        sidebar.setFixedWidth(180)

        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(16, 18, 16, 18)
        layout.setSpacing(10)

        logo = QLabel("FC")
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo.setFixedSize(44, 44)
        logo.setStyleSheet(
            "font-size: 20px; font-weight: 700; border-radius: 8px;"
            "background: #2563eb; color: white;"
        )
        layout.addWidget(logo, 0, Qt.AlignmentFlag.AlignLeft)
        layout.addSpacing(12)

        for label in ("任務", "日曆"):
            button = QPushButton(label)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            layout.addWidget(button)

        self.import_export_button = QPushButton("匯入/匯出")
        self.import_export_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.import_export_button.clicked.connect(self.open_import_export_dialog)
        layout.addWidget(self.import_export_button)

        self.settings_button = QPushButton("個人化")
        self.settings_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.settings_button.clicked.connect(self.open_settings_dialog)
        layout.addWidget(self.settings_button)

        layout.addStretch(1)

        dnd_button = QPushButton("勿擾關閉")
        dnd_button.setCursor(Qt.CursorShape.PointingHandCursor)
        layout.addWidget(dnd_button)

        return sidebar

    def _build_center(self) -> QWidget:
        center = QWidget()
        layout = QVBoxLayout(center)
        layout.setContentsMargins(28, 24, 24, 24)
        layout.setSpacing(18)

        header = QHBoxLayout()
        title = QLabel("複習計畫")
        title.setStyleSheet("font-size: 28px; font-weight: 700;")
        header.addWidget(title)
        header.addStretch(1)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("搜尋任務")
        self.search_input.setFixedWidth(260)
        header.addWidget(self.search_input)

        self.new_task_button = QPushButton("新增任務")
        self.new_task_button.setObjectName("PrimaryButton")
        self.new_task_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.new_task_button.clicked.connect(self.open_task_dialog)
        header.addWidget(self.new_task_button)

        self.complete_next_button = QPushButton("完成下一次")
        self.complete_next_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.complete_next_button.clicked.connect(self.complete_selected_next_reminder)
        header.addWidget(self.complete_next_button)

        self.snooze_next_button = QPushButton("稍後提醒")
        self.snooze_next_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.snooze_next_button.clicked.connect(self.snooze_selected_next_reminder)
        header.addWidget(self.snooze_next_button)
        layout.addLayout(header)

        stats = QHBoxLayout()
        stats.setSpacing(12)
        self.total_tasks_value = QLabel("0")
        self.active_tasks_value = QLabel("0")
        self.completed_tasks_value = QLabel("0")
        stats.addWidget(self._build_stat_card("總數", self.total_tasks_value))
        stats.addWidget(self._build_stat_card("進行中", self.active_tasks_value))
        stats.addWidget(self._build_stat_card("已完成", self.completed_tasks_value))
        layout.addLayout(stats)

        self.task_table = QTableWidget(0, 5)
        self.task_table.setHorizontalHeaderLabels(
            ["任務", "分類", "下一次", "進度", "狀態"]
        )
        self.task_table.setAlternatingRowColors(True)
        self.task_table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        self.task_table.setShowGrid(False)
        self.task_table.verticalHeader().setVisible(False)
        self.task_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        for column in range(1, 5):
            self.task_table.horizontalHeader().setSectionResizeMode(
                column, QHeaderView.ResizeToContents
            )
        layout.addWidget(self.task_table, 1)

        return center

    def _build_stat_card(self, label_text: str, value_label: QLabel) -> QFrame:
        card = QFrame()
        card.setObjectName("Panel")
        card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(4)

        label = QLabel(label_text)
        label.setObjectName("Muted")
        value_label.setStyleSheet("font-size: 24px; font-weight: 700;")
        layout.addWidget(label)
        layout.addWidget(value_label)

        return card

    def _build_right_panel(self) -> QWidget:
        panel = QWidget()
        panel.setFixedWidth(320)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 24, 28, 24)
        layout.setSpacing(14)

        calendar_frame = QFrame()
        calendar_frame.setObjectName("Panel")
        calendar_layout = QVBoxLayout(calendar_frame)
        calendar_layout.setContentsMargins(12, 12, 12, 12)
        self.calendar = QCalendarWidget()
        calendar_layout.addWidget(self.calendar)
        layout.addWidget(calendar_frame)

        day_frame = QFrame()
        day_frame.setObjectName("Panel")
        day_layout = QVBoxLayout(day_frame)
        day_layout.setContentsMargins(14, 12, 14, 12)
        day_title = QLabel("選取日期")
        day_title.setStyleSheet("font-size: 18px; font-weight: 700;")
        self.selected_day_label = QLabel(
            self.calendar.selectedDate().toString("yyyy-MM-dd")
        )
        self.selected_day_label.setObjectName("Muted")
        day_layout.addWidget(day_title)
        day_layout.addWidget(self.selected_day_label)
        day_layout.addStretch(1)
        layout.addWidget(day_frame, 1)

        return panel

    @staticmethod
    def _status_label(task: Task) -> str:
        return "已完成" if task.is_completed else "進行中"

    @staticmethod
    def _format_next_reminder(remind_time: dt.datetime) -> str:
        return remind_time.strftime("%Y-%m-%d %H:%M")

    def open_task_dialog(self) -> None:
        dialog = TaskDialog(self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        values = dialog.values()
        title = str(values["title"]).strip()
        if not title:
            QMessageBox.warning(self, "Task required", "Please enter a task title.")
            return

        start_time = values["start_time"]
        with closing(connect(self.db_path)) as conn:
            init_db(conn)
            repository = ReminderRepository(conn)
            with conn:
                task_id = repository.create_task(
                    TaskDraft(
                        title=title,
                        category=str(values["category"]),
                        difficulty=str(values["difficulty"]),
                        notes=str(values["notes"]),
                        reminder_method=str(values["reminder_method"]),
                        start_time=start_time,
                    )
                )
                if values["reminder_method"] == "遺忘曲線":
                    for remind_time in generated_review_times(
                        start_time, int(values["review_count"])
                    ):
                        repository.create_reminder(
                            ReminderDraft(task_id=task_id, remind_time=remind_time)
                        )

        self.refresh_tasks()

    def complete_selected_next_reminder(self) -> None:
        reminder_id = self._selected_next_reminder_id()
        if reminder_id is None:
            QMessageBox.information(self, "No reminder", "No pending reminder selected.")
            return

        with closing(connect(self.db_path)) as conn:
            init_db(conn)
            repository = ReminderRepository(conn)
            with conn:
                repository.mark_reminder_done(reminder_id)

        self.refresh_tasks()

    def snooze_selected_next_reminder(self, now: dt.datetime | None = None) -> None:
        row = self._selected_row()
        if row is None:
            QMessageBox.information(self, "No task", "Please select a task first.")
            return

        reminder_id = self._row_next_reminder_ids[row]
        current_time = self._row_next_reminder_times[row]
        if reminder_id is None or current_time is None:
            QMessageBox.information(self, "No reminder", "No pending reminder selected.")
            return

        settings = self._load_personalization_settings()
        choice = settings.get("default_snooze", "10m")
        base_time = max(now or dt.datetime.now(), current_time)
        new_time = snooze_until(base_time, choice)
        with closing(connect(self.db_path)) as conn:
            init_db(conn)
            repository = ReminderRepository(conn)
            with conn:
                repository.snooze_reminder(reminder_id, new_time)

        self.refresh_tasks()

    def _selected_next_reminder_id(self) -> int | None:
        row = self._selected_row()
        if row is None:
            return None
        return self._row_next_reminder_ids[row]

    def _selected_row(self) -> int | None:
        rows = self.task_table.selectionModel().selectedRows()
        if not rows:
            return None
        row = rows[0].row()
        if row < 0 or row >= len(self._row_next_reminder_ids):
            return None
        return row

    def open_import_export_dialog(self) -> None:
        dialog = ImportExportDialog(self)
        dialog.import_replace_button.clicked.connect(
            lambda: self._import_csv(dialog, "replace")
        )
        dialog.import_merge_button.clicked.connect(
            lambda: self._import_csv(dialog, "merge")
        )
        dialog.export_button.clicked.connect(lambda: self._export_csv(dialog))
        dialog.exec()

    def open_settings_dialog(self) -> None:
        current = self._load_personalization_settings()
        dialog = SettingsDialog(self, current)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        values = dialog.values()
        with closing(connect(self.db_path)) as conn:
            init_db(conn)
            repository = ReminderRepository(conn)
            with conn:
                for key, value in values.items():
                    repository.set_setting(key, value)

        self.setStyleSheet(self._stylesheet_for_settings(values))

    def _load_personalization_settings(self) -> dict[str, str]:
        defaults = {
            "theme": "light",
            "accent": "blue",
            "density": "comfortable",
            "default_snooze": "10m",
        }
        with closing(connect(self.db_path)) as conn:
            init_db(conn)
            repository = ReminderRepository(conn)
            return {
                key: repository.get_setting(key, default)
                for key, default in defaults.items()
            }

    @staticmethod
    def _stylesheet_for_settings(settings: dict[str, str]) -> str:
        return build_stylesheet(
            accent=settings.get("accent", "blue"),
            dark=settings.get("theme") == "dark",
            compact=settings.get("density") == "compact",
        )

    def _import_csv(self, dialog: ImportExportDialog, mode: str) -> None:
        path = dialog.choose_csv_open()
        if path is None:
            return

        try:
            summary = import_legacy_csv(path, self.db_path, mode=mode)
        except Exception as exc:
            QMessageBox.critical(self, "Import failed", str(exc))
            return

        self.refresh_tasks()
        QMessageBox.information(
            self,
            "Import complete",
            f"Imported {summary.tasks} tasks and {summary.reminders} reminders.",
        )

    def _export_csv(self, dialog: ImportExportDialog) -> None:
        path = dialog.choose_csv_save()
        if path is None:
            return

        try:
            export_legacy_csv(self.db_path, path)
        except Exception as exc:
            QMessageBox.critical(self, "Export failed", str(exc))
            return

        QMessageBox.information(self, "Export complete", f"Exported to {path}.")
