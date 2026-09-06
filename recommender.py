"""
Gyeongju tour course recommender.

This module can run with either:
1. a local CSV export, or
2. the OISO backend API.

The recommendation flow is:
- build text embeddings for places
- compare user preference text with place embeddings
- filter by simple constraints
- build a course with a greedy nearest-place route
"""

from __future__ import annotations

from math import atan2, cos, radians, sin, sqrt
from typing import Dict, List, Optional, Tuple
import warnings

import numpy as np
import pandas as pd
import requests
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

warnings.filterwarnings("ignore")


class TourCourseRecommender:
    """Hybrid recommender: semantic matching + rule filters + greedy routing."""

    CATEGORY_TO_CONTENT_TYPE = {
        "TOUR_SPOT": 12,
        "RESTAURANT": 39,
        "ACCOMMODATION": 32,
    }

    TRANSPORT_TO_API_MODE = {
        "walk": "WALK_PUBLIC_TRANSIT",
        "public": "WALK_PUBLIC_TRANSIT",
        "bicycle": "BICYCLE",
        "car": "CAR",
    }

    def __init__(
        self,
        tour_data_path: Optional[str] = None,
        model_name: str = "jhgan/ko-sroberta-multitask",
        api_base_url: Optional[str] = None,
        api_timeout: int = 10,
        api_page_size: int = 100,
        auth_cookie: Optional[str] = None,
        use_route_api: bool = False,
    ):
        self.model = SentenceTransformer(model_name)
        self.api_base_url = api_base_url.rstrip("/") if api_base_url else None
        self.api_timeout = api_timeout
        self.api_page_size = api_page_size
        self.use_route_api = use_route_api
        self.session = requests.Session()

        if auth_cookie:
            self.session.headers.update({"Cookie": auth_cookie})

        if self.api_base_url:
            self.df_tour = self._load_tour_data_from_api()
        elif tour_data_path:
            self.df_tour = pd.read_csv(tour_data_path)
        else:
            raise ValueError("Either tour_data_path or api_base_url is required.")

        self._preprocess_data()
        self._generate_embeddings()

    def _request(self, method: str, path: str, **kwargs) -> Dict:
        if not self.api_base_url:
            raise ValueError("api_base_url is required for API requests.")

        response = self.session.request(
            method,
            f"{self.api_base_url}{path}",
            timeout=self.api_timeout,
            **kwargs,
        )
        response.raise_for_status()
        payload = response.json()

        if isinstance(payload, dict) and "data" in payload:
            return payload["data"]

        return payload

    @staticmethod
    def _extract_list_payload(data):
        if isinstance(data, list):
            return data, len(data), None

        if not isinstance(data, dict):
            return [], 0, None

        items = data.get("places") or data.get("items") or data.get("courses") or []
        total_count = data.get("totalCount", len(items))
        current_page = data.get("page")

        return items, total_count, current_page

    @classmethod
    def _normalize_api_place(cls, item: Dict) -> Dict:
        category = item.get("category") or "TOUR_SPOT"
        content_type_id = item.get("contentTypeId") or item.get("content_type_id")
        content_type_id = content_type_id or cls.CATEGORY_TO_CONTENT_TYPE.get(category, 12)

        spot_id = item.get("spotId") or item.get("spot_id")
        nearby_place_id = item.get("nearbyPlaceId") or item.get("nearby_place_id")

        return {
            "spot_id": spot_id,
            "nearby_place_id": nearby_place_id,
            "category": category,
            "name": item.get("name", ""),
            "img": item.get("img") or item.get("imageUrl") or "",
            "content": item.get("content") or "",
            "address": item.get("address") or "",
            "can_parking": item.get("canParking") or item.get("can_parking"),
            "can_pet": item.get("canPet") or item.get("can_pet"),
            "crowd_level": item.get("crowdLevel") or item.get("crowd_level"),
            "overview": item.get("overview") or "",
            "homepage": item.get("homepage") or item.get("homepageUrl"),
            "map_x": item.get("longitude") or item.get("mapX") or item.get("map_x"),
            "map_y": item.get("latitude") or item.get("mapY") or item.get("map_y"),
            "content_id": item.get("contentId") or item.get("content_id"),
            "content_type_id": content_type_id,
            "tel": item.get("tel") or item.get("inquiryInfo"),
        }

    def _load_tour_data_from_api(self) -> pd.DataFrame:
        rows = []
        page = 0

        while True:
            data = self._request(
                "GET",
                "/api/v1/tour-spots",
                params={"page": page, "size": self.api_page_size},
            )
            items, total_count, current_page = self._extract_list_payload(data)

            rows.extend(self._normalize_api_place(item) for item in items)

            if not items:
                break

            if len(rows) >= total_count:
                break

            if current_page is None and len(items) < self.api_page_size:
                break

            page += 1

        return pd.DataFrame(rows)

    def _preprocess_data(self):
        self.df_tour["overview"] = self.df_tour["overview"].fillna("")
        self.df_tour["name"] = self.df_tour["name"].fillna("")
        self.df_tour["text_for_embedding"] = self.df_tour.apply(
            lambda x: f"{x['name']} {x['overview']}".strip(),
            axis=1,
        )

        self.df_valid = self.df_tour[
            self.df_tour[["map_x", "map_y"]].notna().all(axis=1)
        ].copy()

        self.df_valid["map_x"] = self.df_valid["map_x"].astype(float)
        self.df_valid["map_y"] = self.df_valid["map_y"].astype(float)
        self.df_valid["visit_duration"] = self.df_valid["content_type_id"].apply(
            self._estimate_visit_duration,
        )

        print(f"Valid places: {len(self.df_valid)}")

    def _generate_embeddings(self):
        print("Generating embeddings...")
        self.spot_embeddings = self.model.encode(
            self.df_valid["text_for_embedding"].tolist(),
            show_progress_bar=True,
            batch_size=32,
        )
        print(f"Embeddings ready: shape {self.spot_embeddings.shape}")

    @staticmethod
    def _haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        radius_km = 6371
        lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
        c = 2 * atan2(sqrt(a), sqrt(1 - a))
        return radius_km * c

    @staticmethod
    def _estimate_travel_time(distance_km: float, transport_mode: str) -> float:
        speeds = {"walk": 4, "bicycle": 15, "public": 30, "car": 50}
        time_minutes = (distance_km / speeds[transport_mode]) * 60
        if transport_mode == "public":
            time_minutes += 10
        return time_minutes

    @staticmethod
    def _estimate_visit_duration(content_type_id: int) -> int:
        duration_map = {
            12: 60,
            14: 60,
            15: 90,
            25: 45,
            28: 90,
            32: 30,
            38: 45,
            39: 60,
        }
        return duration_map.get(int(content_type_id), 60)

    @staticmethod
    def _get_time_budget(duration_type: str) -> int:
        budgets = {
            "half_day": 240,
            "one_day": 480,
            "two_days": 960,
            "1n2d": 960,
            "2n3d": 1440,
            "3n4d": 1920,
        }
        return budgets.get(duration_type, 480)

    def _build_concept_text(
        self,
        duration: str,
        companions: str,
        theme: str,
        transport: str,
        with_pet: bool = False,
    ) -> str:
        concept_map = {
            "companions": {
                "alone": "혼자 여행하기 좋은",
                "family": "가족과 함께 즐기기 좋은",
                "couple": "연인과 데이트하기 좋은",
                "friends": "친구들과 방문하기 좋은",
            },
            "theme": {
                "general": "다양한 볼거리와 즐길 거리가 있는",
                "scenery": "아름다운 경치와 자연을 감상할 수 있는",
                "history": "역사와 문화유산을 체험할 수 있는",
                "culture": "전통 문화와 예술을 즐길 수 있는",
                "food": "맛있는 음식과 먹거리를 즐길 수 있는",
            },
        }

        text = (
            f"{concept_map['companions'][companions]} "
            f"{concept_map['theme'][theme]} 관광지"
        )

        if with_pet:
            text += " 반려동물과 함께 갈 수 있는"

        return text

    def _filter_by_constraints(
        self,
        df: pd.DataFrame,
        with_pet: bool = False,
        transport: str = "car",
    ) -> pd.DataFrame:
        filtered = df.copy()

        if with_pet and "can_pet" in filtered.columns:
            filtered = filtered[
                (filtered["can_pet"] == "Y")
                | (filtered["can_pet"] == True)
                | (filtered["can_pet"].isna())
            ]

        if transport == "car" and "can_parking" in filtered.columns:
            filtered["parking_priority"] = filtered["can_parking"].apply(
                lambda x: 2 if x == "Y" or x is True else 1 if pd.isna(x) else 0,
            )

        return filtered

    def _calculate_route_with_api(
        self,
        start_lat: float,
        start_lon: float,
        end_lat: float,
        end_lon: float,
        transport: str,
    ) -> Optional[Tuple[float, float]]:
        if not self.use_route_api:
            return None

        try:
            data = self._request(
                "POST",
                "/api/v1/routes/calculate",
                json={
                    "origin": {"latitude": start_lat, "longitude": start_lon},
                    "destination": {"latitude": end_lat, "longitude": end_lon},
                    "transportationMode": self.TRANSPORT_TO_API_MODE[transport],
                },
            )
        except Exception:
            return None

        distance_meter = (
            data.get("distanceMeter")
            or data.get("distanceMeters")
            or data.get("distance")
        )
        duration_second = (
            data.get("durationSecond")
            or data.get("durationSeconds")
            or data.get("duration")
        )

        if distance_meter is None or duration_second is None:
            return None

        return float(distance_meter) / 1000, float(duration_second) / 60

    def _distance_and_travel_time(
        self,
        start_lat: float,
        start_lon: float,
        end_lat: float,
        end_lon: float,
        transport: str,
    ) -> Tuple[float, float]:
        api_result = self._calculate_route_with_api(
            start_lat,
            start_lon,
            end_lat,
            end_lon,
            transport,
        )
        if api_result:
            return api_result

        distance = self._haversine_distance(start_lat, start_lon, end_lat, end_lon)
        return distance, self._estimate_travel_time(distance, transport)

    def _greedy_tsp(
        self,
        df_candidates: pd.DataFrame,
        start_lat: float,
        start_lon: float,
        time_budget: int,
        transport: str,
    ) -> List[Dict]:
        course = []
        remaining = df_candidates.copy()
        current_lat = start_lat
        current_lon = start_lon
        total_time = 0

        while len(remaining) > 0 and total_time < time_budget:
            remaining["distance"] = remaining.apply(
                lambda x: self._haversine_distance(
                    current_lat,
                    current_lon,
                    x["map_y"],
                    x["map_x"],
                ),
                axis=1,
            )

            nearest_idx = remaining["distance"].idxmin()
            nearest = remaining.loc[nearest_idx]

            distance, travel_time = self._distance_and_travel_time(
                current_lat,
                current_lon,
                nearest["map_y"],
                nearest["map_x"],
                transport,
            )
            visit_time = nearest["visit_duration"]

            if total_time + travel_time + visit_time > time_budget:
                break

            course.append(
                {
                    "order": len(course) + 1,
                    "spot_id": (
                        int(nearest["spot_id"])
                        if pd.notna(nearest.get("spot_id"))
                        else None
                    ),
                    "nearby_place_id": (
                        int(nearest["nearby_place_id"])
                        if pd.notna(nearest.get("nearby_place_id"))
                        else None
                    ),
                    "category": nearest.get("category", "TOUR_SPOT"),
                    "name": nearest["name"],
                    "distance_from_prev": float(distance),
                    "travel_time": float(travel_time),
                    "visit_duration": int(visit_time),
                    "lat": float(nearest["map_y"]),
                    "lon": float(nearest["map_x"]),
                    "similarity": float(nearest["similarity"]),
                },
            )

            total_time += travel_time + visit_time
            current_lat = nearest["map_y"]
            current_lon = nearest["map_x"]
            remaining = remaining.drop(nearest_idx)

        return course

    def recommend(
        self,
        duration: str = "one_day",
        companions: str = "alone",
        theme: str = "scenery",
        transport: str = "car",
        with_pet: bool = False,
        start_lat: Optional[float] = None,
        start_lon: Optional[float] = None,
        top_k_candidates: int = 30,
    ) -> Tuple[List[Dict], str]:
        concept_text = self._build_concept_text(
            duration,
            companions,
            theme,
            transport,
            with_pet,
        )
        concept_embedding = self.model.encode([concept_text])

        similarities = cosine_similarity(concept_embedding, self.spot_embeddings)[0]
        self.df_valid["similarity"] = similarities

        df_filtered = self._filter_by_constraints(self.df_valid, with_pet, transport)
        df_candidates = df_filtered.nlargest(top_k_candidates, "similarity").copy()

        if start_lat is None or start_lon is None:
            start_lat = df_candidates["map_y"].mean()
            start_lon = df_candidates["map_x"].mean()

        time_budget = self._get_time_budget(duration)
        course = self._greedy_tsp(
            df_candidates,
            start_lat,
            start_lon,
            time_budget,
            transport,
        )

        return course, concept_text

    def format_for_api(self, course: List[Dict], concept_text: str) -> Dict:
        return {
            "concept": concept_text,
            "total_spots": len(course),
            "total_time_minutes": sum(
                s["travel_time"] + s["visit_duration"] for s in course
            ),
            "course": course,
        }

    def save_embeddings(self, embeddings_path: str, metadata_path: str):
        np.save(embeddings_path, self.spot_embeddings)
        self.df_valid.to_csv(metadata_path, index=False)
        print(f"Saved embeddings: {embeddings_path}")
        print(f"Saved metadata: {metadata_path}")


if __name__ == "__main__":
    recommender = TourCourseRecommender(
        api_base_url="https://oiso.duckdns.org",
        use_route_api=False,
        # CSV fallback example:
        # tour_data_path="_TourSpot__202607062337.csv",
    )

    course, concept = recommender.recommend(
        duration="one_day",
        companions="couple",
        theme="scenery",
        transport="car",
        with_pet=False,
    )

    print("\n=== Recommended Course ===")
    print(f"Concept: {concept}")
    print(f"Total places: {len(course)}\n")

    total_time = 0
    for spot in course:
        print(f"{spot['order']}. {spot['name']}")
        print(
            f"   Distance: {spot['distance_from_prev']:.2f}km, "
            f"Travel: {spot['travel_time']:.0f}min, "
            f"Visit: {spot['visit_duration']}min"
        )
        print(f"   Similarity: {spot['similarity']:.3f}")
        total_time += spot["travel_time"] + spot["visit_duration"]
        print()

    print(f"Total time: {total_time:.0f}min ({total_time / 60:.1f}h)")
    print("\nAPI response format:")
    print(recommender.format_for_api(course, concept))
