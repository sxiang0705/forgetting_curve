import datetime as dt

import pytest

from renew_curve.scheduler import (
    calculate_progress_percent,
    forgetting_curve_days,
    generated_review_times,
    snooze_until,
    validate_manual_review_times,
)


def test_forgetting_curve_days_for_supported_counts():
    assert forgetting_curve_days(3) == [1, 3, 7]
    assert forgetting_curve_days(5) == [1, 3, 7, 14, 30]
    assert forgetting_curve_days(10) == [1, 3, 7, 14, 30, 60, 90, 120, 180, 365]


def test_forgetting_curve_days_rejects_unsupported_count():
    with pytest.raises(ValueError, match="review count"):
        forgetting_curve_days(2)


def test_generated_review_times_preserve_clock_time():
    start = dt.datetime(2026, 5, 6, 18, 30)
    assert generated_review_times(start, 3) == [
        dt.datetime(2026, 5, 7, 18, 30),
        dt.datetime(2026, 5, 9, 18, 30),
        dt.datetime(2026, 5, 13, 18, 30),
    ]


def test_calculate_progress_percent_handles_empty_and_partial():
    assert calculate_progress_percent(0, 0) == 0.0
    assert calculate_progress_percent(5, 0) == 0.0
    assert calculate_progress_percent(5, 2) == 40.0
    assert calculate_progress_percent(3, 3) == 100.0


def test_snooze_until_supports_expected_choices():
    now = dt.datetime(2026, 5, 6, 9, 0)
    assert snooze_until(now, "10m") == dt.datetime(2026, 5, 6, 9, 10)
    assert snooze_until(now, "1h") == dt.datetime(2026, 5, 6, 10, 0)
    assert snooze_until(now, "tomorrow") == dt.datetime(2026, 5, 7, 9, 0)


def test_validate_manual_review_times_requires_matching_count():
    with pytest.raises(ValueError, match="expected 3 review times"):
        validate_manual_review_times(
            [dt.datetime(2026, 5, 8, 9, 0)],
            review_count=3,
        )


def test_validate_manual_review_times_sorts_and_rejects_duplicates():
    values = validate_manual_review_times(
        [
            dt.datetime(2026, 5, 10, 9, 0),
            dt.datetime(2026, 5, 8, 9, 0),
        ],
        review_count=2,
    )
    assert values == [
        dt.datetime(2026, 5, 8, 9, 0),
        dt.datetime(2026, 5, 10, 9, 0),
    ]

    with pytest.raises(ValueError, match="duplicate review time"):
        validate_manual_review_times(
            [
                dt.datetime(2026, 5, 8, 9, 0),
                dt.datetime(2026, 5, 8, 9, 0),
            ],
            review_count=2,
        )
