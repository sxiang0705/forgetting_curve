from __future__ import annotations

import datetime as dt
from contextlib import closing
from pathlib import Path

from PySide6.QtCore import QDate, Qt
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
    QScrollArea,
    QSizePolicy,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from renew_curve.backup import export_full_backup, import_full_backup
from renew_curve.csv_compat import export_legacy_csv, import_legacy_csv
from renew_curve.db import ReminderRepository, connect, init_db
from renew_curve.models import ReminderDraft, Task, TaskDraft
from renew_curve.scheduler import generated_review_times, snooze_until
from renew_curve.ui.dialogs import DataDialog, ImportExportDialog, SettingsDialog, TaskDialog
from renew_curve.ui.personalization import (
    default_personalization_settings,
    stylesheet_for_personalization,
)


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

        self._selected_day = dt.date.today()
        self._selected_category = "全部"
        self._build_ui()
        self.refresh_dashboard()

    def close_database(self) -> None:
        pass

    def closeEvent(self, event: QCloseEvent) -> None:
        self.close_database()
        super().closeEvent(event)

    def refresh_dashboard(self, selected_day: dt.date | None = None) -> None:
        day = selected_day or self._selected_day
        self._selected_day = day
        self._load_day_reminders(day)
        self._load_next_three_days(day)
        self._load_all_tasks()
        self._render_day_reminders(day)
        self._render_next_three_days()
        self._render_all_tasks()

    def refresh_tasks(self) -> None:
        self.refresh_dashboard()

    def _load_day_reminders(self, day: dt.date) -> None:
        with closing(connect(self.db_path)) as conn:
            init_db(conn)
            repository = ReminderRepository(conn)
            self._current_day_items = repository.list_due_reminders_for_date(day)

    def _load_next_three_days(self, start_day: dt.date) -> None:
        with closing(connect(self.db_path)) as conn:
            init_db(conn)
            repository = ReminderRepository(conn)
            self._next_three_days = {
                start_day + dt.timedelta(days=offset): repository.list_due_reminders_for_date(
                    start_day + dt.timedelta(days=offset)
                )
                for offset in range(1, 4)
            }

    def _load_all_tasks(self) -> None:
        with closing(connect(self.db_path)) as conn:
            init_db(conn)
            repository = ReminderRepository(conn)
            self._all_tasks = repository.list_tasks()
            self._all_next_reminders = {
                task.id: repository.next_pending_reminder(task.id)
                for task in self._all_tasks
            }

    def _render_all_tasks(self) -> None:
        self._render_category_chips()
        tasks = [
            task
            for task in self._all_tasks
            if self._selected_category == "全部"
            or task.category == self._selected_category
        ]
        next_reminders = self._all_next_reminders
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

    def _render_category_chips(self) -> None:
        if not hasattr(self, "category_chips_layout"):
            return
        self._clear_layout(self.category_chips_layout)
        categories = ["全部"] + sorted(
            {task.category for task in self._all_tasks if task.category.strip()}
        )
        if self._selected_category not in categories:
            self._selected_category = "全部"
        for category in categories:
            button = QPushButton(category)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.setObjectName(
                "ChipButtonActive"
                if category == self._selected_category
                else "ChipButton"
            )
            button.clicked.connect(
                lambda _checked=False, selected=category: self._select_category(
                    selected
                )
            )
            self.category_chips_layout.addWidget(button)
        self.category_chips_layout.addStretch(1)

    def _select_category(self, category: str) -> None:
        self._selected_category = category
        self._render_all_tasks()

    def _render_day_reminders(self, day: dt.date) -> None:
        self.day_title_label.setText(
            "今天任務" if day == dt.date.today() else day.strftime("%m/%d 任務")
        )
        self.selected_day_label.setText(day.strftime("%Y-%m-%d"))
        self._clear_layout(self.today_tasks_layout)

        if not self._current_day_items:
            empty = QLabel("這一天沒有待複習任務。")
            empty.setObjectName("Muted")
            self.today_tasks_layout.addWidget(empty)
        for item in self._current_day_items:
            self.today_tasks_layout.addWidget(self._build_reminder_card(item))
        self.today_tasks_layout.addStretch(1)

    def _render_next_three_days(self) -> None:
        self._clear_layout(self.next_three_days_layout)
        for day, items in self._next_three_days.items():
            row = QFrame()
            row.setObjectName("Panel")
            row_layout = QVBoxLayout(row)
            row_layout.setContentsMargins(10, 8, 10, 8)
            row_layout.setSpacing(8)

            header = QHBoxLayout()
            date_label = QLabel(
                "今天" if day == dt.date.today() else day.strftime("%m/%d")
            )
            date_label.setStyleSheet("font-weight: 700;")
            header.addWidget(date_label, 1)
            count = QLabel(str(len(items)))
            count.setAlignment(Qt.AlignmentFlag.AlignCenter)
            count.setObjectName("CountPill")
            count.setFixedWidth(36)
            header.addWidget(count)
            row_layout.addLayout(header)

            if not items:
                empty = QLabel("無任務")
                empty.setObjectName("Muted")
                row_layout.addWidget(empty)
            for item in items[:4]:
                task = QLabel(
                    f"{item.task_title}\n{item.remind_time.strftime('%H:%M')}  {item.category}"
                )
                task.setObjectName("NextMiniTask")
                task.setWordWrap(True)
                row_layout.addWidget(task)
            if len(items) > 4:
                more = QLabel(f"還有 {len(items) - 4} 筆")
                more.setObjectName("Muted")
                row_layout.addWidget(more)
            self.next_three_days_layout.addWidget(row)
        self.next_three_days_layout.addStretch(1)

    def _build_reminder_card(self, item) -> QFrame:
        card = QFrame()
        card.setObjectName("Panel")
        layout = QHBoxLayout(card)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(12)

        content = QVBoxLayout()
        title = QLabel(item.task_title)
        title.setStyleSheet("font-size: 17px; font-weight: 700;")
        meta = QLabel(
            f"{item.category}  {item.remind_time.strftime('%H:%M')}  "
            f"第 {item.review_index} 次複習"
        )
        meta.setObjectName("Muted")
        notes = QLabel(f"備註：{item.notes}" if item.notes else "備註：無")
        notes.setWordWrap(True)
        content.addWidget(title)
        content.addWidget(meta)
        content.addWidget(notes)
        layout.addLayout(content, 1)

        complete_button = QPushButton("完成")
        complete_button.setObjectName("OutlineActionButton")
        complete_button.setCursor(Qt.CursorShape.PointingHandCursor)
        complete_button.clicked.connect(
            lambda _checked=False, reminder_id=item.reminder_id: self._complete_reminder(
                reminder_id
            )
        )
        snooze_button = QPushButton("推延")
        snooze_button.setObjectName("OutlineActionButton")
        snooze_button.setCursor(Qt.CursorShape.PointingHandCursor)
        snooze_button.clicked.connect(
            lambda _checked=False, reminder_id=item.reminder_id: self._snooze_reminder(
                reminder_id
            )
        )
        layout.addWidget(complete_button)
        layout.addWidget(snooze_button)
        return card

    def _clear_layout(self, layout: QVBoxLayout) -> None:
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

    def _on_calendar_selected(self) -> None:
        qdate = self.calendar.selectedDate()
        self.refresh_dashboard(dt.date(qdate.year(), qdate.month(), qdate.day()))

    def _return_to_today(self) -> None:
        today = dt.date.today()
        self.calendar.setSelectedDate(QDate(today.year, today.month, today.day))
        self.refresh_dashboard(today)

    def _complete_reminder(self, reminder_id: int) -> None:
        with closing(connect(self.db_path)) as conn:
            init_db(conn)
            repository = ReminderRepository(conn)
            with conn:
                repository.mark_reminder_done(reminder_id)
        self.refresh_dashboard()

    def _snooze_reminder(self, reminder_id: int) -> None:
        settings = self._load_personalization_settings()
        choice = settings.get("default_snooze", "10m")
        with closing(connect(self.db_path)) as conn:
            init_db(conn)
            row = conn.execute(
                "SELECT remind_time FROM reminders WHERE id = ?",
                (reminder_id,),
            ).fetchone()
            if row is None:
                return
            current_time = dt.datetime.fromisoformat(str(row["remind_time"]))
            new_time = snooze_until(current_time, choice)
            repository = ReminderRepository(conn)
            with conn:
                repository.snooze_reminder_group(reminder_id, new_time - current_time)
        self.refresh_dashboard()

    def _build_ui(self) -> None:
        root = QWidget()
        root_layout = QHBoxLayout(root)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        root_layout.addWidget(self._build_sidebar())
        root_layout.addWidget(self._build_center(), 1)

        self.setCentralWidget(root)

    def _build_sidebar(self) -> QWidget:
        sidebar = QWidget()
        sidebar.setObjectName("Sidebar")
        sidebar.setFixedWidth(330)

        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(16, 18, 16, 18)
        layout.setSpacing(14)

        brand_row = QHBoxLayout()
        logo = QLabel("FC")
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo.setFixedSize(44, 44)
        logo.setStyleSheet(
            "font-size: 20px; font-weight: 700; border-radius: 8px;"
            "background: #2563eb; color: white;"
        )
        brand = QLabel("Renew Curve v8")
        brand.setStyleSheet("font-size: 18px; font-weight: 700;")
        brand_row.addWidget(logo)
        brand_row.addWidget(brand, 1)
        layout.addLayout(brand_row)

        calendar_frame = QFrame()
        calendar_frame.setObjectName("Panel")
        calendar_layout = QVBoxLayout(calendar_frame)
        calendar_layout.setContentsMargins(10, 10, 10, 10)
        self.calendar = QCalendarWidget()
        self.calendar.selectionChanged.connect(self._on_calendar_selected)
        calendar_layout.addWidget(self.calendar)
        self.today_button = QPushButton("回到今天")
        self.today_button.clicked.connect(self._return_to_today)
        calendar_layout.addWidget(self.today_button)
        layout.addWidget(calendar_frame)

        next_frame = QFrame()
        next_frame.setObjectName("Panel")
        next_layout = QVBoxLayout(next_frame)
        next_layout.setContentsMargins(12, 12, 12, 12)
        next_header = QHBoxLayout()
        self.next_days_title = QLabel("接下來 3 天")
        self.next_days_title.setStyleSheet("font-size: 18px; font-weight: 700;")
        next_header.addWidget(self.next_days_title, 1)
        next_caption = QLabel("列出每日任務")
        next_caption.setObjectName("Muted")
        next_header.addWidget(next_caption)
        next_layout.addLayout(next_header)
        self.next_three_days_layout = QVBoxLayout()
        next_layout.addLayout(self.next_three_days_layout)
        layout.addWidget(next_frame, 1)

        return sidebar

    def _build_center(self) -> QWidget:
        center = QWidget()
        layout = QVBoxLayout(center)
        layout.setContentsMargins(28, 24, 24, 24)
        layout.setSpacing(18)

        header = QHBoxLayout()
        self.day_title_label = QLabel("今天任務")
        self.day_title_label.setStyleSheet("font-size: 28px; font-weight: 700;")
        header.addWidget(self.day_title_label)
        header.addStretch(1)

        self.import_export_button = QPushButton("報表 / 資料")
        self.import_export_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.import_export_button.clicked.connect(self.open_import_export_dialog)
        header.addWidget(self.import_export_button)

        self.schedule_help_button = QPushButton("排程說明")
        self.schedule_help_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.schedule_help_button.clicked.connect(self.open_schedule_help_dialog)
        header.addWidget(self.schedule_help_button)

        self.settings_button = QPushButton("個人化")
        self.settings_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.settings_button.clicked.connect(self.open_settings_dialog)
        header.addWidget(self.settings_button)

        self.new_task_button = QPushButton("新增任務")
        self.new_task_button.setObjectName("PrimaryButton")
        self.new_task_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.new_task_button.clicked.connect(self.open_task_dialog)
        header.addWidget(self.new_task_button)
        layout.addLayout(header)

        self.selected_day_label = QLabel("")
        self.selected_day_label.setObjectName("Muted")
        layout.addWidget(self.selected_day_label)

        # Compatibility buttons for existing keyboard/test paths; visible task cards
        # now carry the primary completion and snooze actions.
        self.complete_next_button = QPushButton("完成下一次")
        self.complete_next_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.complete_next_button.clicked.connect(self.complete_selected_next_reminder)
        self.complete_next_button.hide()

        self.snooze_next_button = QPushButton("稍後提醒")
        self.snooze_next_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.snooze_next_button.clicked.connect(self.snooze_selected_next_reminder)
        self.snooze_next_button.hide()

        self.today_tasks_container = QWidget()
        self.today_tasks_container.setObjectName("TodayTasks")
        self.today_tasks_layout = QVBoxLayout(self.today_tasks_container)
        self.today_tasks_layout.setContentsMargins(0, 0, 0, 0)
        self.today_tasks_layout.setSpacing(10)
        self.today_scroll = QScrollArea()
        self.today_scroll.setWidgetResizable(True)
        self.today_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.today_scroll.setWidget(self.today_tasks_container)
        self.today_scroll.setMinimumHeight(260)
        self.today_scroll.setMaximumHeight(370)
        layout.addWidget(self.today_scroll)

        all_title = QLabel("所有任務")
        all_title.setStyleSheet("font-size: 20px; font-weight: 700;")
        layout.addWidget(all_title)

        self.category_chips_layout = QHBoxLayout()
        self.category_chips_layout.setSpacing(8)
        layout.addLayout(self.category_chips_layout)

        self.task_table = QTableWidget(0, 5)
        self.task_table.setObjectName("AllTasks")
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
        self.task_table.setMinimumHeight(240)
        self.task_table.setMaximumHeight(300)
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
        with closing(connect(self.db_path)) as conn:
            init_db(conn)
            repository = ReminderRepository(conn)
            if hasattr(dialog, "set_categories"):
                dialog.set_categories(repository.list_categories())

        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        values = dialog.values()
        try:
            self._create_task_from_values(values)
        except ValueError as exc:
            QMessageBox.warning(self, "新增任務失敗", str(exc))
            return

        self.refresh_tasks()

    def _create_task_from_values(self, values: dict[str, object]) -> int:
        title = str(values["title"]).strip()
        if not title:
            raise ValueError("請輸入任務名稱。")

        start_time = values["start_time"]
        review_times = values.get("review_times")
        if not isinstance(start_time, dt.datetime):
            raise ValueError("開始時間格式錯誤。")
        if review_times is None and values.get("reminder_method") == "遺忘曲線":
            review_times = generated_review_times(
                start_time, int(values.get("review_count", 5))
            )
        if not isinstance(review_times, list):
            raise ValueError("複習時間格式錯誤。")

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
                for remind_time in review_times:
                    if not isinstance(remind_time, dt.datetime):
                        raise ValueError("複習時間格式錯誤。")
                    repository.create_reminder(
                        ReminderDraft(task_id=task_id, remind_time=remind_time)
                    )
                return task_id

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
        dialog = DataDialog(self)
        dialog.import_legacy_csv_button.clicked.connect(
            lambda: self._import_csv(dialog, "replace")
        )
        dialog.export_full_backup_button.clicked.connect(
            lambda: self._export_full_backup(dialog)
        )
        dialog.import_full_backup_button.clicked.connect(
            lambda: self._import_full_backup(dialog)
        )
        dialog.exec()

    def open_schedule_help_dialog(self) -> None:
        QMessageBox.information(
            self,
            "排程說明",
            "新增任務可選「遺忘曲線」或「手動輸入」。\n\n"
            "遺忘曲線會依開始時間自動產生 1、3、7、14、30 天等複習點；"
            "推延會整批推動同一任務尚未完成的後續提醒，避免複習間距被打亂。",
        )

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
        defaults = default_personalization_settings()
        with closing(connect(self.db_path)) as conn:
            init_db(conn)
            repository = ReminderRepository(conn)
            return {
                key: repository.get_setting(key, default)
                for key, default in defaults.items()
            }

    @staticmethod
    def _stylesheet_for_settings(settings: dict[str, str]) -> str:
        return stylesheet_for_personalization(settings)

    def _assets_dir(self) -> Path:
        return self.db_path.parent / "assets"

    def _export_full_backup(self, dialog: DataDialog) -> None:
        path = dialog.choose_zip_save()
        if path is None:
            return

        try:
            export_full_backup(self.db_path, self._assets_dir(), path)
        except Exception as exc:
            QMessageBox.critical(self, "匯出失敗", str(exc))
            return

        QMessageBox.information(self, "匯出完成", f"已匯出完整資料到 {path}。")

    def _import_full_backup(self, dialog: DataDialog) -> None:
        path = dialog.choose_zip_open()
        if path is None:
            return

        try:
            import_full_backup(path, self.db_path, self._assets_dir())
        except Exception as exc:
            QMessageBox.critical(self, "匯入失敗", str(exc))
            return

        self.refresh_tasks()
        QMessageBox.information(self, "匯入完成", "完整資料已還原。")

    def _import_csv(self, dialog: DataDialog, mode: str) -> None:
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
