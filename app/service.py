"""Adapter between the HTTP contract and the existing recommendation engine."""

from __future__ import annotations

from math import ceil
from threading import Lock
from typing import Any

from app.config import Settings
from app.schemas import (
    CourseRecommendationData,
    CourseRecommendationItem,
    CourseRecommendationRequest,
    PreferredTravelTheme,
    TransportationMode,
    TravelCompanion,
    TravelTime,
)


TRAVEL_TIME_MAP = {
    TravelTime.HALF_DAY: "half_day",
    TravelTime.ONE_DAY: "one_day",
    TravelTime.ONE_NIGHT_TWO_DAYS: "1n2d",
    TravelTime.TWO_NIGHTS_THREE_DAYS: "2n3d",
    TravelTime.THREE_NIGHTS_FOUR_DAYS: "3n4d",
}

COMPANION_MAP = {
    TravelCompanion.ALONE: "alone",
    TravelCompanion.PARTNER: "couple",
    TravelCompanion.FRIENDS: "friends",
    TravelCompanion.FAMILY: "family",
}

THEME_MAP = {
    PreferredTravelTheme.HISTORY_CULTURE: "history",
    PreferredTravelTheme.NATURE_SCENERY: "scenery",
    PreferredTravelTheme.FOOD: "food",
}

TRANSPORT_MAP = {
    TransportationMode.WALK_PUBLIC_TRANSIT: "public",
    TransportationMode.BICYCLE: "bicycle",
    TransportationMode.CAR: "car",
}

COURSE_TRANSPORT_MAP = {
    TransportationMode.WALK_PUBLIC_TRANSIT: "WALK",
    TransportationMode.BICYCLE: "BIKE",
    TransportationMode.CAR: "CAR",
}


class RecommendationService:
    """Owns the model instance and serializes access to its mutable data frame."""

    def __init__(self, engine: Any):
        self._engine = engine
        self._recommend_lock = Lock()

    @classmethod
    def from_settings(cls, settings: Settings) -> "RecommendationService":
        # Importing here keeps health/schema tooling lightweight. The large ML
        # dependencies are loaded only when the recommendation engine starts.
        from recommender import TourCourseRecommender

        source = (
            {"tour_data_path": settings.tour_data_path}
            if settings.tour_data_path
            else {"api_base_url": settings.backend_api_base_url}
        )
        engine = TourCourseRecommender(
            model_name=settings.model_name,
            api_timeout=settings.api_timeout,
            api_page_size=settings.api_page_size,
            auth_cookie=settings.backend_auth_cookie,
            use_route_api=settings.use_route_api,
            **source,
        )
        return cls(engine)

    def recommend(
        self,
        request: CourseRecommendationRequest,
    ) -> CourseRecommendationData:
        with self._recommend_lock:
            course, concept = self._engine.recommend(
                duration=TRAVEL_TIME_MAP[request.travel_time],
                companions=COMPANION_MAP[request.travel_companion],
                theme=(
                    THEME_MAP[request.preferred_travel_theme]
                    if request.preferred_travel_theme is not None
                    else "general"
                ),
                transport=TRANSPORT_MAP[request.transportation_mode],
                departure_category=(
                    request.departure_category.value
                    if request.departure_category is not None
                    else None
                ),
                departure_place_id=request.departure_place_id,
                travel_start_date=request.travel_start_date,
                saved_spot_ids=set(request.saved_spot_ids),
                saved_nearby_place_ids=set(request.saved_nearby_place_ids),
                active_festival_spot_ids=set(request.active_festival_spot_ids),
            )

        return self._to_response(
            course=course,
            concept=concept,
            transportation_mode=request.transportation_mode,
        )

    @staticmethod
    def _to_response(
        course: list[dict[str, Any]],
        concept: str,
        transportation_mode: TransportationMode,
    ) -> CourseRecommendationData:
        items: list[CourseRecommendationItem] = []
        elapsed_minutes = 0.0

        for place in course:
            # New itinerary results include a day number. The elapsed-time
            # fallback keeps older engine results compatible.
            day_number = int(
                place.get("day_number", int(elapsed_minutes // 480) + 1),
            )
            travel_minutes = float(place.get("travel_time", 0))
            return_minutes = float(place.get("return_travel_time", 0))
            visit_minutes = int(place.get("visit_duration", 0))

            items.append(
                CourseRecommendationItem(
                    item_order=int(place["order"]),
                    day_number=day_number,
                    category=str(place.get("category", "TOUR_SPOT")),
                    spot_id=_optional_int(place.get("spot_id")),
                    nearby_place_id=_optional_int(place.get("nearby_place_id")),
                    name=str(place["name"]),
                    latitude=float(place["lat"]),
                    longitude=float(place["lon"]),
                    distance_from_previous_meter=max(
                        0,
                        round(float(place.get("distance_from_prev", 0)) * 1000),
                    ),
                    duration_from_previous_second=max(
                        0,
                        round(travel_minutes * 60),
                    ),
                    visit_duration_minute=max(0, visit_minutes),
                    similarity=float(place.get("similarity", 0)),
                    transport_type=(
                        None
                        if int(place["order"]) == 1
                        else COURSE_TRANSPORT_MAP[transportation_mode]
                    ),
                ),
            )
            elapsed_minutes += travel_minutes + visit_minutes + return_minutes

        return CourseRecommendationData(
            concept=concept,
            total_spot_count=len(items),
            total_duration_minute=ceil(elapsed_minutes),
            items=items,
        )


def _optional_int(value: Any) -> int | None:
    if value is None:
        return None
    return int(value)
