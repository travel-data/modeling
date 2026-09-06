"""Request and response contracts shared with the Spring backend."""

from __future__ import annotations

from enum import Enum
from typing import Generic, Optional, TypeVar

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ApiModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True)


class TravelTime(str, Enum):
    HALF_DAY = "HALF_DAY"
    ONE_DAY = "ONE_DAY"
    ONE_NIGHT_TWO_DAYS = "ONE_NIGHT_TWO_DAYS"
    TWO_NIGHTS_THREE_DAYS = "TWO_NIGHTS_THREE_DAYS"
    THREE_NIGHTS_FOUR_DAYS = "THREE_NIGHTS_FOUR_DAYS"


class TravelCompanion(str, Enum):
    ALONE = "ALONE"
    PARTNER = "PARTNER"
    FRIENDS = "FRIENDS"
    FAMILY = "FAMILY"


class PreferredTravelTheme(str, Enum):
    HISTORY_CULTURE = "HISTORY_CULTURE"
    NATURE_SCENERY = "NATURE_SCENERY"
    FOOD = "FOOD"


class TransportationMode(str, Enum):
    WALK_PUBLIC_TRANSIT = "WALK_PUBLIC_TRANSIT"
    BICYCLE = "BICYCLE"
    CAR = "CAR"


class CourseRecommendationRequest(ApiModel):
    travel_time: TravelTime = Field(alias="travelTime")
    travel_companion: TravelCompanion = Field(alias="travelCompanion")
    preferred_travel_theme: Optional[PreferredTravelTheme] = Field(
        default=None,
        alias="preferredTravelTheme",
    )
    transportation_mode: TransportationMode = Field(alias="transportationMode")
    with_pet: bool = Field(default=False, alias="withPet")
    latitude: Optional[float] = Field(default=None, ge=-90, le=90)
    longitude: Optional[float] = Field(default=None, ge=-180, le=180)

    @model_validator(mode="after")
    def validate_start_coordinates(self) -> "CourseRecommendationRequest":
        if (self.latitude is None) != (self.longitude is None):
            raise ValueError("latitude and longitude must be provided together.")
        return self


class CourseRecommendationItem(ApiModel):
    item_order: int = Field(ge=1, alias="itemOrder")
    day_number: int = Field(ge=1, alias="dayNumber")
    category: str
    spot_id: Optional[int] = Field(default=None, alias="spotId")
    nearby_place_id: Optional[int] = Field(default=None, alias="nearbyPlaceId")
    name: str
    latitude: float
    longitude: float
    distance_from_previous_meter: int = Field(
        ge=0,
        alias="distanceFromPreviousMeter",
    )
    duration_from_previous_second: int = Field(
        ge=0,
        alias="durationFromPreviousSecond",
    )
    visit_duration_minute: int = Field(ge=0, alias="visitDurationMinute")
    similarity: float
    transport_type: str = Field(alias="transportType")


class CourseRecommendationData(ApiModel):
    concept: str
    total_spot_count: int = Field(ge=0, alias="totalSpotCount")
    total_duration_minute: int = Field(ge=0, alias="totalDurationMinute")
    items: list[CourseRecommendationItem]


T = TypeVar("T")


class ApiResponse(ApiModel, Generic[T]):
    code: int
    message: str
    data: T


class HealthData(ApiModel):
    status: str
    model_loaded: bool = Field(alias="modelLoaded")
