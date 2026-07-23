"""
경주 관광 코스 추천 시스템

하이브리드 방식 (Rule-based + ML-based):
1. Sentence Transformer 임베딩 기반 의미적 매칭
2. Rule-based 제약조건 필터링
3. Greedy TSP로 경로 최적화
"""

import numpy as np
import pandas as pd
from sklearn.metrics.pairwise import cosine_similarity
from sentence_transformers import SentenceTransformer
from math import radians, sin, cos, sqrt, atan2
from typing import Dict, List, Optional, Tuple
import warnings

warnings.filterwarnings('ignore')


class TourCourseRecommender:
    """관광 코스 추천 시스템"""

    def __init__(
        self,
        tour_data_path: str,
        model_name: str = 'jhgan/ko-sroberta-multitask'
    ):
        """
        Args:
            tour_data_path: 관광지 데이터 CSV 경로
            model_name: Sentence Transformer 모델명
        """
        self.model = SentenceTransformer(model_name)
        self.df_tour = pd.read_csv(tour_data_path)
        self._preprocess_data()
        self._generate_embeddings()

    def _preprocess_data(self):
        """데이터 전처리"""
        # 텍스트 데이터 준비
        self.df_tour['text_for_embedding'] = self.df_tour.apply(
            lambda x: f"{x['name']} {x['overview'] if pd.notna(x['overview']) else ''}".strip(),
            axis=1
        )

        # 좌표 있는 데이터만 사용
        self.df_valid = self.df_tour[
            self.df_tour[['map_x', 'map_y']].notna().all(axis=1)
        ].copy()

        # 체류 시간 추가
        self.df_valid['visit_duration'] = self.df_valid['content_type_id'].apply(
            self._estimate_visit_duration
        )

        print(f"유효 관광지: {len(self.df_valid)}개")

    def _generate_embeddings(self):
        """관광지 임베딩 생성"""
        print("임베딩 생성 중...")
        self.spot_embeddings = self.model.encode(
            self.df_valid['text_for_embedding'].tolist(),
            show_progress_bar=True,
            batch_size=32
        )
        print(f"임베딩 완료: shape {self.spot_embeddings.shape}")

    @staticmethod
    def _haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """
        두 지점 간 거리 계산 (Haversine 공식)

        Args:
            lat1, lon1: 첫 번째 지점 (위도, 경도)
            lat2, lon2: 두 번째 지점 (위도, 경도)

        Returns:
            거리 (km)
        """
        R = 6371  # 지구 반지름 (km)
        lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
        c = 2 * atan2(sqrt(a), sqrt(1-a))
        return R * c

    @staticmethod
    def _estimate_travel_time(distance_km: float, transport_mode: str) -> float:
        """
        이동 시간 계산

        Args:
            distance_km: 거리 (km)
            transport_mode: 'walk', 'bicycle', 'public', 'car'

        Returns:
            이동 시간 (분)
        """
        speeds = {'walk': 4, 'bicycle': 15, 'public': 30, 'car': 50}
        time_minutes = (distance_km / speeds[transport_mode]) * 60
        if transport_mode == 'public':
            time_minutes += 10  # 대기 시간
        return time_minutes

    @staticmethod
    def _estimate_visit_duration(content_type_id: int) -> int:
        """
        관광지 타입별 예상 체류 시간

        Args:
            content_type_id: 관광지 타입 ID

        Returns:
            체류 시간 (분)
        """
        duration_map = {
            12: 60,   # 관광지
            14: 90,   # 문화시설
            15: 120,  # 축제/행사
            25: 45,   # 여행코스
            28: 180,  # 레포츠
            32: 30,   # 숙박
            38: 60,   # 쇼핑
            39: 60,   # 음식점
        }
        return duration_map.get(content_type_id, 60)

    @staticmethod
    def _get_time_budget(duration_type: str) -> int:
        """
        여행 기간별 시간 예산

        Args:
            duration_type: 'half_day', 'one_day', 'two_days'

        Returns:
            시간 예산 (분)
        """
        budgets = {'half_day': 240, 'one_day': 480, 'two_days': 960}
        return budgets.get(duration_type, 480)

    def _build_concept_text(
        self,
        duration: str,
        companions: str,
        theme: str,
        transport: str,
        with_pet: bool = False
    ) -> str:
        """
        사용자 선택을 자연어 텍스트로 변환

        Args:
            duration: 'half_day', 'one_day', 'two_days'
            companions: 'alone', 'family', 'couple', 'friends'
            theme: 'scenery', 'history', 'culture', 'food'
            transport: 'walk', 'bicycle', 'public', 'car'
            with_pet: 반려동물 동반 여부

        Returns:
            컨셉 텍스트
        """
        concept_map = {
            'companions': {
                'alone': '혼자 여행하기 좋은',
                'family': '가족과 함께 즐기기 좋은',
                'couple': '연인과 데이트하기 좋은',
                'friends': '친구들과 방문하기 좋은'
            },
            'theme': {
                'scenery': '아름다운 경치와 자연을 감상할 수 있는',
                'history': '역사와 문화유산을 체험할 수 있는',
                'culture': '전통 문화와 예술을 즐길 수 있는',
                'food': '맛있는 음식과 먹거리를 즐길 수 있는'
            }
        }

        text = f"{concept_map['companions'][companions]} {concept_map['theme'][theme]} 관광지"

        if with_pet:
            text += " 반려동물과 함께 갈 수 있는"

        return text

    def _filter_by_constraints(
        self,
        df: pd.DataFrame,
        with_pet: bool = False,
        transport: str = 'car'
    ) -> pd.DataFrame:
        """
        제약조건으로 필터링

        Args:
            df: 관광지 데이터프레임
            with_pet: 반려동물 동반 여부
            transport: 이동 수단

        Returns:
            필터링된 데이터프레임
        """
        filtered = df.copy()

        # 반려동물 동반
        if with_pet:
            filtered = filtered[
                (filtered['can_pet'] == 'Y') | (filtered['can_pet'].isna())
            ]

        # 자차 이용 시 주차 가능한 곳 우선
        if transport == 'car':
            filtered['parking_priority'] = filtered['can_parking'].apply(
                lambda x: 2 if x == 'Y' else 1 if pd.isna(x) else 0
            )

        return filtered

    def _greedy_tsp(
        self,
        df_candidates: pd.DataFrame,
        start_lat: float,
        start_lon: float,
        time_budget: int,
        transport: str
    ) -> List[Dict]:
        """
        Greedy TSP 알고리즘으로 경로 생성

        Args:
            df_candidates: 후보 관광지
            start_lat: 시작 위도
            start_lon: 시작 경도
            time_budget: 시간 예산 (분)
            transport: 이동 수단

        Returns:
            추천 코스 리스트
        """
        course = []
        remaining = df_candidates.copy()
        current_lat = start_lat
        current_lon = start_lon
        total_time = 0

        while len(remaining) > 0 and total_time < time_budget:
            # 현재 위치에서 가장 가까운 장소 찾기
            remaining['distance'] = remaining.apply(
                lambda x: self._haversine_distance(
                    current_lat, current_lon, x['map_y'], x['map_x']
                ),
                axis=1
            )

            # 가장 가까운 곳 선택
            nearest_idx = remaining['distance'].idxmin()
            nearest = remaining.loc[nearest_idx]

            # 이동 시간 계산
            travel_time = self._estimate_travel_time(nearest['distance'], transport)
            visit_time = nearest['visit_duration']

            # 시간 예산 체크
            if total_time + travel_time + visit_time > time_budget:
                break

            # 코스에 추가
            course.append({
                'order': len(course) + 1,
                'spot_id': int(nearest['spot_id']),
                'name': nearest['name'],
                'distance_from_prev': float(nearest['distance']),
                'travel_time': float(travel_time),
                'visit_duration': int(visit_time),
                'lat': float(nearest['map_y']),
                'lon': float(nearest['map_x']),
                'similarity': float(nearest['similarity'])
            })

            # 시간 누적
            total_time += travel_time + visit_time

            # 현재 위치 업데이트
            current_lat = nearest['map_y']
            current_lon = nearest['map_x']

            # 방문한 곳 제거
            remaining = remaining.drop(nearest_idx)

        return course

    def recommend(
        self,
        duration: str = 'one_day',
        companions: str = 'alone',
        theme: str = 'scenery',
        transport: str = 'car',
        with_pet: bool = False,
        start_lat: Optional[float] = None,
        start_lon: Optional[float] = None,
        top_k_candidates: int = 30
    ) -> Tuple[List[Dict], str]:
        """
        코스 추천 메인 함수

        Args:
            duration: 여행 기간
            companions: 동행인
            theme: 테마
            transport: 이동 수단
            with_pet: 반려동물 동반 여부
            start_lat: 시작 위도 (선택)
            start_lon: 시작 경도 (선택)
            top_k_candidates: 후보 개수

        Returns:
            (추천 코스 리스트, 컨셉 텍스트)
        """
        # 1. 사용자 컨셉 임베딩
        concept_text = self._build_concept_text(
            duration, companions, theme, transport, with_pet
        )
        concept_embedding = self.model.encode([concept_text])

        # 2. 유사도 계산
        similarities = cosine_similarity(concept_embedding, self.spot_embeddings)[0]
        self.df_valid['similarity'] = similarities

        # 3. 제약조건 필터링
        df_filtered = self._filter_by_constraints(self.df_valid, with_pet, transport)

        # 4. 상위 후보 선정
        df_candidates = df_filtered.nlargest(top_k_candidates, 'similarity').copy()

        # 5. 시작점 설정
        if start_lat is None or start_lon is None:
            start_lat = df_candidates['map_y'].mean()
            start_lon = df_candidates['map_x'].mean()

        # 6. 시간 예산
        time_budget = self._get_time_budget(duration)

        # 7. Greedy 경로 생성
        course = self._greedy_tsp(
            df_candidates, start_lat, start_lon, time_budget, transport
        )

        return course, concept_text

    def format_for_api(self, course: List[Dict], concept_text: str) -> Dict:
        """
        백엔드 API 응답 형식으로 변환

        Args:
            course: 추천 코스
            concept_text: 컨셉 텍스트

        Returns:
            API 응답 딕셔너리
        """
        return {
            "concept": concept_text,
            "total_spots": len(course),
            "total_time_minutes": sum(
                s['travel_time'] + s['visit_duration'] for s in course
            ),
            "course": course
        }

    def save_embeddings(self, embeddings_path: str, metadata_path: str):
        """
        임베딩 및 메타데이터 저장

        Args:
            embeddings_path: 임베딩 저장 경로 (.npy)
            metadata_path: 메타데이터 저장 경로 (.csv)
        """
        np.save(embeddings_path, self.spot_embeddings)
        self.df_valid.to_csv(metadata_path, index=False)
        print(f"임베딩 저장 완료: {embeddings_path}")
        print(f"메타데이터 저장 완료: {metadata_path}")


# 사용 예시
if __name__ == "__main__":
    # 추천 시스템 초기화
    recommender = TourCourseRecommender(
        tour_data_path="_TourSpot__202607062337.csv"
    )

    # 코스 추천
    course, concept = recommender.recommend(
        duration='one_day',
        companions='couple',
        theme='scenery',
        transport='car',
        with_pet=False
    )

    # 결과 출력
    print(f"\n=== 추천 코스 ===")
    print(f"컨셉: {concept}")
    print(f"총 {len(course)}개 장소\n")

    total_time = 0
    for spot in course:
        print(f"{spot['order']}. {spot['name']}")
        print(f"   거리: {spot['distance_from_prev']:.2f}km, "
              f"이동: {spot['travel_time']:.0f}분, "
              f"체류: {spot['visit_duration']}분")
        print(f"   유사도: {spot['similarity']:.3f}")
        total_time += spot['travel_time'] + spot['visit_duration']
        print()

    print(f"총 소요시간: {total_time:.0f}분 ({total_time/60:.1f}시간)")

    # API 형식 변환
    api_response = recommender.format_for_api(course, concept)
    print(f"\nAPI 응답 형식:")
    print(api_response)

    # 임베딩 저장
    recommender.save_embeddings(
        'spot_embeddings.npy',
        'spots_with_embeddings.csv'
    )
