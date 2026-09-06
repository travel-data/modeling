from fastapi.testclient import TestClient

from app.main import create_app
from app.schemas import CourseRecommendationData, CourseRecommendationItem


VALID_REQUEST = {
    "travelTime": "ONE_DAY",
    "travelCompanion": "PARTNER",
    "preferredTravelTheme": "NATURE_SCENERY",
    "transportationMode": "CAR",
    "withPet": False,
    "latitude": 35.8562,
    "longitude": 129.2247,
}


class FakeRecommendationService:
    def recommend(self, _request):
        return CourseRecommendationData(
            concept="연인과 자연을 즐기는 관광지",
            total_spot_count=1,
            total_duration_minute=75,
            items=[
                CourseRecommendationItem(
                    item_order=1,
                    day_number=1,
                    category="TOUR_SPOT",
                    spot_id=10,
                    nearby_place_id=None,
                    name="테스트 관광지",
                    latitude=35.8562,
                    longitude=129.2247,
                    distance_from_previous_meter=1500,
                    duration_from_previous_second=900,
                    visit_duration_minute=60,
                    similarity=0.87,
                    transport_type="CAR",
                ),
            ],
        )


def test_health_reports_loaded_model():
    app = create_app(recommendation_service=FakeRecommendationService())

    with TestClient(app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "code": 2000,
        "message": "서비스가 실행 중입니다.",
        "data": {"status": "UP", "modelLoaded": True},
    }


def test_recommendation_uses_camel_case_contract():
    app = create_app(recommendation_service=FakeRecommendationService())

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/recommendations/courses",
            json=VALID_REQUEST,
        )

    assert response.status_code == 200
    body = response.json()
    assert body["code"] == 2000
    assert body["data"]["totalSpotCount"] == 1
    assert body["data"]["totalDurationMinute"] == 75
    assert body["data"]["items"][0]["spotId"] == 10
    assert body["data"]["items"][0]["transportType"] == "CAR"


def test_theme_can_be_null_to_match_frontend_preference_contract():
    app = create_app(recommendation_service=FakeRecommendationService())
    request = {**VALID_REQUEST, "preferredTravelTheme": None}

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/recommendations/courses",
            json=request,
        )

    assert response.status_code == 200


def test_coordinates_must_be_provided_as_a_pair():
    app = create_app(recommendation_service=FakeRecommendationService())
    request = {**VALID_REQUEST, "longitude": None}

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/recommendations/courses",
            json=request,
        )

    assert response.status_code == 422
    assert response.json()["code"] == 4000


def test_unknown_enum_is_rejected():
    app = create_app(recommendation_service=FakeRecommendationService())
    request = {**VALID_REQUEST, "travelTime": "WEEK"}

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/recommendations/courses",
            json=request,
        )

    assert response.status_code == 422
    assert response.json()["code"] == 4000

