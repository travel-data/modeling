"""Availability rules for free-form place schedule data."""

from __future__ import annotations

from datetime import date
import re
from typing import Optional


def is_closed_on(rest_date: Optional[str], visit_date: date) -> bool:
    """Return true only when a supported rest-date rule clearly matches."""
    if not rest_date:
        return False

    normalized = re.sub(r"\s+", "", rest_date)
    if any(token in normalized for token in ("연중무휴", "무휴", "없음")):
        return False

    compact_date = visit_date.strftime("%Y%m%d")
    explicit_dates = re.findall(
        r"\d{4}[./-]?\d{1,2}[./-]?\d{1,2}",
        normalized,
    )
    if any(_normalize_full_date(token) == compact_date for token in explicit_dates):
        return True

    without_full_dates = re.sub(
        r"\d{4}[./-]?\d{1,2}[./-]?\d{1,2}",
        "",
        normalized,
    )
    month_day_dates = re.findall(
        r"(?<!\d)\d{1,2}[./-]\d{1,2}(?!\d)",
        without_full_dates,
    )
    if any(_normalize_month_day(token) == visit_date.strftime("%m%d") for token in month_day_dates):
        return True

    weekday_tokens = ("월요일", "화요일", "수요일", "목요일", "금요일", "토요일", "일요일")
    weekday_token = weekday_tokens[visit_date.weekday()]
    if weekday_token not in normalized:
        return False

    ordinal_map = {
        "첫째": 1,
        "첫번째": 1,
        "둘째": 2,
        "두번째": 2,
        "셋째": 3,
        "세번째": 3,
        "넷째": 4,
        "네번째": 4,
        "다섯째": 5,
        "다섯번째": 5,
    }
    mentioned_ordinals = [
        ordinal
        for label, ordinal in ordinal_map.items()
        if label in normalized
    ]
    if not mentioned_ordinals:
        return True

    week_of_month = (visit_date.day - 1) // 7 + 1
    return week_of_month in mentioned_ordinals


def _normalize_full_date(value: str) -> str:
    parts = [part for part in re.split(r"\D", value) if part]
    if len(parts) == 1 and len(parts[0]) == 8:
        return parts[0]
    if len(parts) != 3:
        return ""
    year, month, day = parts
    return f"{int(year):04d}{int(month):02d}{int(day):02d}"


def _normalize_month_day(value: str) -> str:
    parts = [part for part in re.split(r"\D", value) if part]
    if len(parts) != 2:
        return ""
    month, day = parts
    return f"{int(month):02d}{int(day):02d}"
