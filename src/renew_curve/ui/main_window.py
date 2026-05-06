from __future__ import annotations

from contextlib import closing
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCalendarWidget,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPushButton,
    QSizePolicy,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from renew_curve.db import ReminderRepository, connect, init_db
from renew_curve.models import Task
from renew_curve.ui.theme import build_stylesheet


class MainWindow(QMainWindow):
    def __init__(self, db_path: str = "renew_curve_v8.db") -> None:
        super().__init__()
        self.db_path = Path(db_path)
        with closing(connect(self.db_path)) as conn:
            init_db(conn)

        self.setWindowTitle("Renew Curve v8")
        self.resize(1180, 760)
        self.setStyleSheet(build_stylesheet())

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

        self.task_table.setRowCount(len(tasks))

        for row_index, task in enumerate(tasks):
            values = [
                task.title,
                task.category,
                "",
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

        for label in ("Tasks", "Calendar", "Import/Export", "Settings"):
            button = QPushButton(label)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            layout.addWidget(button)

        layout.addStretch(1)

        dnd_button = QPushButton("DND Off")
        dnd_button.setCursor(Qt.CursorShape.PointingHandCursor)
        layout.addWidget(dnd_button)

        return sidebar

    def _build_center(self) -> QWidget:
        center = QWidget()
        layout = QVBoxLayout(center)
        layout.setContentsMargins(28, 24, 24, 24)
        layout.setSpacing(18)

        header = QHBoxLayout()
        title = QLabel("Review planner")
        title.setStyleSheet("font-size: 28px; font-weight: 700;")
        header.addWidget(title)
        header.addStretch(1)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search tasks")
        self.search_input.setFixedWidth(260)
        header.addWidget(self.search_input)

        new_task_button = QPushButton("New task")
        new_task_button.setObjectName("PrimaryButton")
        new_task_button.setCursor(Qt.CursorShape.PointingHandCursor)
        header.addWidget(new_task_button)
        layout.addLayout(header)

        stats = QHBoxLayout()
        stats.setSpacing(12)
        self.total_tasks_value = QLabel("0")
        self.active_tasks_value = QLabel("0")
        self.completed_tasks_value = QLabel("0")
        stats.addWidget(self._build_stat_card("Total", self.total_tasks_value))
        stats.addWidget(self._build_stat_card("Active", self.active_tasks_value))
        stats.addWidget(self._build_stat_card("Completed", self.completed_tasks_value))
        layout.addLayout(stats)

        self.task_table = QTableWidget(0, 5)
        self.task_table.setHorizontalHeaderLabels(
            ["Task", "Category", "Next", "Progress", "Status"]
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
        day_title = QLabel("Selected day")
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
        return "Done" if task.is_completed else "Active"
