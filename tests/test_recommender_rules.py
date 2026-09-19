from datetime import date

from app.availability import is_closed_on


def test_weekly_rest_day_is_excluded():
    monday = date(2026, 9, 21)
    tuesday = date(2026, 9, 22)

    assert is_closed_on("매주 월요일", monday) is True
    assert is_closed_on("매주 월요일", tuesday) is False


def test_ordinal_rest_day_is_excluded_only_on_matching_week():
    first_monday = date(2026, 9, 7)
    second_monday = date(2026, 9, 14)

    assert is_closed_on(
        "매월 첫째 월요일 휴무",
        first_monday,
    ) is True
    assert is_closed_on(
        "매월 첫째 월요일 휴무",
        second_monday,
    ) is False


def test_always_open_text_is_not_excluded():
    assert is_closed_on(
        "연중무휴",
        date(2026, 9, 21),
    ) is False


def test_explicit_rest_date_is_excluded():
    assert is_closed_on(
        "2026-09-21 임시휴무",
        date(2026, 9, 21),
    ) is True


def test_same_month_day_in_a_different_year_is_not_excluded():
    assert is_closed_on(
        "2025-09-21 임시휴무",
        date(2026, 9, 21),
    ) is False
