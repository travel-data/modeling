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
    return sum(
        len(required_day_categories(restaurant_count))
        for restaurant_count in plan.restaurant_counts
    )


def day_starts_at_departure(day_index: int, departure_type: str) -> bool:
    return day_index == 0 or departure_type == "accommodation"


def classify_departure(
    nearest_accommodation_distance_km: float | None,
    match_radius_km: float,
) -> str:
    if (
        nearest_accommodation_distance_km is not None
        and nearest_accommodation_distance_km <= match_radius_km
    ):
        return "accommodation"
    return "start_point"


def is_trip_return_slot(
    day_number: int,
    total_days: int,
    slot_index: int,
    slot_count: int,
    departure_type: str,
) -> bool:
    return (
        departure_type == "start_point"
        and day_number == total_days
        and slot_index == slot_count - 1
    )
