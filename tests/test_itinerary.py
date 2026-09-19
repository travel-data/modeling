import pytest

from app.itinerary import (
    ITINERARY_PLANS,
    classify_departure,
    day_starts_at_departure,
    is_trip_return_slot,
    planned_item_count,
    required_day_categories,
)
from app.route_contract import build_route_request


@pytest.mark.parametrize(
    ("duration", "restaurant_count"),
    [
        ("half_day", 1),
        ("one_day", 2),
        ("1n2d", 3),
        ("2n3d", 5),
        ("3n4d", 7),
    ],
)
def test_itinerary_restaurant_counts(duration, restaurant_count):
    plan = ITINERARY_PLANS[duration]

    assert len(plan.restaurant_counts) == plan.days
    assert sum(plan.restaurant_counts) == restaurant_count
    assert all(count in (1, 2) for count in plan.restaurant_counts)


def test_each_day_alternates_attractions_and_restaurants():
    assert required_day_categories(1) == [
        "TOUR_SPOT",
        "RESTAURANT",
        "TOUR_SPOT",
    ]
    assert required_day_categories(2) == [
        "TOUR_SPOT",
        "RESTAURANT",
        "TOUR_SPOT",
        "RESTAURANT",
        "TOUR_SPOT",
    ]


@pytest.mark.parametrize(
    ("duration", "item_count"),
    [
        ("half_day", 3),
        ("one_day", 5),
        ("1n2d", 8),
        ("2n3d", 13),
        ("3n4d", 18),
    ],
)
def test_itinerary_has_a_fixed_item_count(duration, item_count):
    assert planned_item_count(duration) == item_count


def test_accommodation_departure_is_reused_at_the_start_of_every_day():
    assert day_starts_at_departure(0, "accommodation") is True
    assert day_starts_at_departure(1, "accommodation") is True
    assert day_starts_at_departure(1, "start_point") is False


def test_departure_is_classified_by_nearby_accommodation_distance():
    assert classify_departure(0.02, 0.05) == "accommodation"
    assert classify_departure(0.08, 0.05) == "start_point"
    assert classify_departure(None, 0.05) == "start_point"


def test_general_start_point_is_used_as_the_final_return_point():
    assert is_trip_return_slot(2, 2, 2, 3, "start_point") is True
    assert is_trip_return_slot(1, 2, 2, 3, "start_point") is False
    assert is_trip_return_slot(2, 2, 2, 3, "accommodation") is False


def test_route_request_matches_backend_openapi_contract():
    request = build_route_request(35.85, 129.22, 35.86, 129.23, "car")

    assert request == {
        "origin": {"latitude": 35.85, "longitude": 129.22},
        "destination": {"latitude": 35.86, "longitude": 129.23},
        "transportType": "CAR",
    }
