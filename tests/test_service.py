from datetime import date

from app.schemas import CourseRecommendationRequest
from app.service import RecommendationService


class FakeEngine:
    def __init__(self):
        self.received = None

    def recommend(self, **kwargs):
        self.received = kwargs
        return (
            [
                {
                    "order": 1,
                    "spot_id": 101,
                    "nearby_place_id": None,
                    "category": "TOUR_SPOT",
                    "name": "첫 장소",
                    "distance_from_prev": 1.25,
                    "travel_time": 10.5,
                    "visit_duration": 470,
                    "lat": 35.1,
                    "lon": 129.1,
                    "similarity": 0.91,
                },
                {
                    "order": 2,
                    "spot_id": None,
                    "nearby_place_id": 202,
                    "category": "RESTAURANT",
                    "name": "둘째 장소",
                    "distance_from_prev": 2.0,
                    "travel_time": 20,
                    "return_travel_time": 15,
                    "visit_duration": 60,
                    "lat": 35.2,
                    "lon": 129.2,
                    "similarity": 0.82,
                },
            ],
            "추천 콘셉트",
        )


def test_service_maps_backend_enums_and_result_units():
    engine = FakeEngine()
    service = RecommendationService(engine)
    request = CourseRecommendationRequest.model_validate(
        {
            "travelTime": "ONE_NIGHT_TWO_DAYS",
            "travelCompanion": "PARTNER",
            "preferredTravelTheme": "HISTORY_CULTURE",
            "transportationMode": "BICYCLE",
            "travelStartDate": "2026-10-09",
            "savedSpotIds": [101],
            "savedNearbyPlaceIds": [202],
            "activeFestivalSpotIds": [303],
            "departureCategory": "PRESET",
            "departurePlaceId": "GYEONGJU_STATION",
        },
    )

    result = service.recommend(request)

    assert engine.received == {
        "duration": "1n2d",
        "companions": "couple",
        "theme": "history",
        "transport": "bicycle",
        "departure_category": "PRESET",
        "departure_place_id": "GYEONGJU_STATION",
        "travel_start_date": date(2026, 10, 9),
        "saved_spot_ids": {101},
        "saved_nearby_place_ids": {202},
        "active_festival_spot_ids": {303},
    }
    assert result.total_spot_count == 2
    assert result.total_duration_minute == 576
    assert result.items[0].distance_from_previous_meter == 1250
    assert result.items[0].duration_from_previous_second == 630
    assert result.items[0].day_number == 1
    assert result.items[0].transport_type is None
    assert result.items[1].day_number == 2
    assert result.items[1].transport_type == "BIKE"


def test_service_uses_general_theme_when_theme_is_missing():
    engine = FakeEngine()
    service = RecommendationService(engine)
    request = CourseRecommendationRequest.model_validate(
        {
            "travelTime": "HALF_DAY",
            "travelCompanion": "ALONE",
            "preferredTravelTheme": None,
            "transportationMode": "WALK_PUBLIC_TRANSIT",
        },
    )

    service.recommend(request)

    assert engine.received["theme"] == "general"
    assert engine.received["saved_spot_ids"] == set()
    assert engine.received["saved_nearby_place_ids"] == set()
    assert engine.received["active_festival_spot_ids"] == set()
    assert engine.received["departure_category"] is None
    assert engine.received["departure_place_id"] is None

