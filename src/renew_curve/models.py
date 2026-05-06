from __future__ import annotations

import datetime as dt
from dataclasses import dataclass


@dataclass(frozen=True)
class TaskDraft:
    title: str
    category: str
    difficulty: str
    notes: str
    reminder_method: str
    start_time: dt.datetime


@dataclass(frozen=True)
class Task:
    id: int
    title: str
    category: str
    difficulty: str
    notes: str
    reminder_method: str
    start_time: dt.datetime
    is_completed: bool
    progress_percent: float


@dataclass(frozen=True)
class ReminderDraft:
    task_id: int
    remind_time: dt.datetime
    reminded: bool = False


@dataclass(frozen=True)
class Reminder:
    id: int
    task_id: int
    remind_time: dt.datetime
    reminded: bool


@dataclass(frozen=True)
class ImportSummary:
    tasks: int
    reminders: int
    mode: str
