# 경주 관광 코스 추천 알고리즘

## 📋 개요

사용자가 선택한 컨셉(여행기간, 동행인, 테마, 이동수단)에 맞는 관광 코스를 자동으로 추천하는 AI 시스템입니다.

## 🎯 주요 기능

### 사용자 입력
- **여행 기간**: 반나절 / 1일 / 1박2일
- **동행인**: 혼자 / 가족 / 연인 / 친구 (+ 반려동물 유무)
- **테마**: 경치 / 역사 / 문화 / 음식
- **이동 수단**: 도보 / 대중교통 / 자차 / 자전거

### 추천 결과
- 순서가 있는 관광 코스 (1→2→3...)
- 각 장소의 이동 거리, 이동 시간, 체류 시간
- 총 소요 시간 계산
- 지도 시각화

## 🛠 알고리즘 구조

### 1단계: 컨셉 매칭 (Embedding)
```
사용자 컨셉 → 텍스트 변환 → 임베딩
관광지 설명 → 임베딩
코사인 유사도 계산 → 상위 30개 후보 선정
```

**사용 모델**: `jhgan/ko-sroberta-multitask` (한국어 특화)

### 2단계: 제약조건 필터링
- 반려동물 동반 가능 여부
- 주차 가능 여부 (자차 선택 시)

### 3단계: 경로 최적화 (Greedy TSP)
```
시작점 → 가장 가까운 미방문지 선택
→ 이동시간 + 체류시간 계산
→ 시간 예산 내 반복
→ 코스 완성
```

### 4단계: 시간 관리
- **반나절**: 4시간 (240분)
- **1일**: 8시간 (480분)
- **1박2일**: 16시간 (960분)

이동시간 = 거리 ÷ 속도
- 도보: 4km/h
- 자전거: 15km/h
- 대중교통: 30km/h (+대기 10분)
- 자차: 50km/h

## 📊 데이터

### TourSpot (관광지)
- 총 662개, 좌표 유효 데이터 약 600개
- 주요 컬럼:
  - `spot_id`, `name`, `overview` (설명)
  - `map_x`, `map_y` (경도, 위도)
  - `content_type_id` (관광지 타입)
  - `can_pet`, `can_parking`

### AccommodationDetail (숙박)
- 총 330개 객실
- 주요 컬럼:
  - `spot_id`, `room_title`, `base_count`, `max_count`
  - 가격, 편의시설 정보

## 🚀 사용 방법

### 1. 환경 설정
```bash
pip install sentence-transformers scikit-learn pandas numpy matplotlib
```

### 2. 데이터 준비
- `_TourSpot__202607062337.csv`
- `_AccommodationDetail__202607062338.csv`

### 3. 실행
```python
# Jupyter Notebook 실행
jupyter notebook course_recommender.ipynb

# 추천 함수 호출
course, concept = recommend_course(
    duration='one_day',      # 'half_day', 'one_day', 'two_days'
    companions='couple',     # 'alone', 'family', 'couple', 'friends'
    theme='scenery',         # 'scenery', 'history', 'culture', 'food'
    transport='car',         # 'walk', 'bicycle', 'public', 'car'
    with_pet=False,
    start_lat=35.83,         # 선택: 시작 위도
    start_lon=129.21         # 선택: 시작 경도
)
```

## 📈 현재 성능

### 장점 ✅
- **빠른 속도**: 임베딩 1회 생성 후 재사용
- **의미적 매칭**: 단순 키워드가 아닌 문맥 기반
- **실용적**: 실제 이동 시간 고려
- **유연함**: 다양한 제약조건 처리

### 한계 ⚠️
- Greedy 알고리즘 → 최적 경로 보장 안 됨
- 직선 거리 사용 → 실제 도로 거리와 차이
- 영업시간, 날씨 미반영
- 1박2일 처리 미구현 (숙소 배정 로직 필요)

## 🔧 향후 개선 사항

### 우선순위 1: 경로 최적화
- [ ] 2-opt 알고리즘 적용
- [ ] Genetic Algorithm 시도
- [ ] 실제 도로 거리 API 연동 (Kakao, Tmap)

### 우선순위 2: 1박2일 처리
- [ ] 숙소 위치 기준 1일차/2일차 분할
- [ ] 숙소 근처 관광지 우선 배정
- [ ] 체크인/체크아웃 시간 고려

### 우선순위 3: 추가 제약조건
- [ ] 영업시간 필터링
- [ ] 계절/날씨 고려
- [ ] 혼잡도 정보 활용 (crowd_level)

### 우선순위 4: 개인화
- [ ] 사용자 과거 방문 이력 반영
- [ ] 리뷰/평점 기반 추천
- [ ] 연령대별 맞춤 추천

## 📁 파일 구조

```
modeling/
├── README.md                              # 이 파일
├── data_analysis.ipynb                    # 데이터 탐색 및 분석
├── course_recommender.ipynb               # 추천 알고리즘 메인
├── _TourSpot__202607062337.csv            # 관광지 데이터
├── _AccommodationDetail__202607062338.csv # 숙박 데이터
├── spot_embeddings.npy                    # (생성됨) 임베딩 캐시
└── spots_with_embeddings.csv              # (생성됨) 전처리 데이터
```

## 🔬 예시 결과

### 입력
```python
duration='one_day'
companions='couple'
theme='scenery'
transport='car'
```

### 출력
```
컨셉: 연인과 데이트하기 좋은 아름다운 경치와 자연을 감상할 수 있는 관광지
총 5개 장소

1. 토함산 자연휴양림
   거리: 5.2km, 이동: 6분, 체류: 60분
   
2. 감은사지 삼층석탑
   거리: 12.3km, 이동: 15분, 체류: 45분
   
3. 주상절리 파도소리길
   거리: 8.1km, 이동: 10분, 체류: 60분
   
...

총 소요시간: 420분 (7.0시간)
```

## 💡 백엔드 연동 가이드

### API 엔드포인트 설계 예시
```
POST /api/recommend-course
Request Body:
{
  "duration": "one_day",
  "companions": "couple",
  "theme": "scenery",
  "transport": "car",
  "with_pet": false,
  "start_location": {
    "lat": 35.83,
    "lon": 129.21
  }
}

Response:
{
  "concept": "연인과 데이트하기 좋은...",
  "total_spots": 5,
  "total_time_minutes": 420,
  "course": [
    {
      "order": 1,
      "spot_id": 12345,
      "name": "토함산 자연휴양림",
      "distance_from_prev": 5.2,
      "travel_time": 6,
      "visit_duration": 60,
      "lat": 35.789,
      "lon": 129.456,
      "similarity": 0.82
    },
    ...
  ]
}
```

### Python 패키징
```python
# recommender.py
class CourseRecommender:
    def __init__(self, model_name='jhgan/ko-sroberta-multitask'):
        self.model = SentenceTransformer(model_name)
        self.load_data()
        self.load_embeddings()
    
    def recommend(self, **kwargs):
        # 추천 로직
        pass
```

## 📄 라이선스
MIT License
