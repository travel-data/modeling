"""Deterministic rules that turn a recommendation into a usable itinerary."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ItineraryPlan:
    days: int
    restaurant_counts: tuple[int, ...]


ITINERARY_PLANS = {
    "half_day": ItineraryPlan(days=1, restaurant_counts=(1,)),
    "one_day": ItineraryPlan(days=1, restaurant_counts=(2,)),
    "two_days": ItineraryPlan(days=2, restaurant_counts=(2, 1)),
    "1n2d": ItineraryPlan(days=2, restaurant_counts=(2, 1)),
    "2n3d": ItineraryPlan(days=3, restaurant_counts=(2, 2, 1)),
    "3n4d": ItineraryPlan(days=4, restaurant_counts=(2, 2, 2, 1)),
}


def required_day_categories(restaurant_count: int) -> list[str]:
    if restaurant_count == 1:
        return ["TOUR_SPOT", "RESTAURANT", "TOUR_SPOT"]
    if restaurant_count == 2:
        return [
            "TOUR_SPOT",
            "RESTAURANT",
            "TOUR_SPOT",
            "RESTAURANT",
            "TOUR_SPOT",
        ]
    raise ValueError("A day must contain one or two restaurants.")


def planned_item_count(duration: str) -> int:
    """Return the exact number of places produced by the itinerary rules."""
    plan = ITINERARY_PLANS[duration]
    day_items = sum(
        len(required_day_categories(restaurant_count))
        for restaurant_count in plan.restaurant_counts
    )
    accommodations = max(plan.days - 1, 0)
    return day_items + accommodations
