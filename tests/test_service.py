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
            "latitude": 35.8,
            "longitude": 129.2,
        },
    )

    result = service.recommend(request)

    assert engine.received == {
        "duration": "1n2d",
        "companions": "couple",
        "theme": "history",
        "transport": "bicycle",
        "start_lat": 35.8,
        "start_lon": 129.2,
    }
    assert result.total_spot_count == 2
    assert result.total_duration_minute == 561
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

