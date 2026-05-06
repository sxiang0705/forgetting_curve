from __future__ import annotations

import datetime as dt

_CURVE_DAYS = {
    3: [1, 3, 7],
    4: [1, 3, 7, 14],
    5: [1, 3, 7, 14, 30],
    6: [1, 3, 7, 14, 30, 60],
    7: [1, 3, 7, 14, 30, 60, 90],
    8: [1, 3, 7, 14, 30, 60, 90, 120],
    9: [1, 3, 7, 14, 30, 60, 90, 120, 180],
    10: [1, 3, 7, 14, 30, 60, 90, 120, 180, 365],
}


def forgetting_curve_days(review_count: int) -> list[int]:
    try:
        return list(_CURVE_DAYS[int(review_count)])
    except (KeyError, ValueError):
        raise ValueError("review count must be between 3 and 10") from None


def generated_review_times(start: dt.datetime, review_count: int) -> list[dt.datetime]:
    return [start + dt.timedelta(days=days) for days in forgetting_curve_days(review_count)]


def calculate_progress_percent(total: int, completed: int) -> float:
    if total <= 0:
        return 0.0
    bounded = max(0, min(completed, total))
    return round((bounded / total) * 100, 1)


def snooze_until(now: dt.datetime, choice: str) -> dt.datetime:
    if choice == "10m":
        return now + dt.timedelta(minutes=10)
    if choice == "1h":
        return now + dt.timedelta(hours=1)
    if choice == "tomorrow":
        return now + dt.timedelta(days=1)
    raise ValueError(f"unsupported snooze choice: {choice}")
