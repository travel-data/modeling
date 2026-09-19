# 경주 관광 코스 추천 알고리즘

## 📋 개요

사용자가 선택한 컨셉(여행기간, 동행인, 테마, 이동수단)에 맞는 관광 코스를 자동으로 추천하는 AI 시스템입니다.

## 🎯 주요 기능

### 사용자 입력
- **여행 시작일과 기간**: 반나절 / 1일 / 1박2일 / 2박3일 / 3박4일
- **동행인**: 혼자 / 가족 / 연인 / 친구
- **테마**: 경치 / 역사 / 문화 / 음식
- **이동 수단**: 도보 / 대중교통 / 자차 / 자전거
- **개인화 정보**: 저장 장소, 여행 기간과 겹치는 축제

### 추천 결과
- 순서가 있는 관광 코스 (1→2→3...)
- 각 장소의 이동 거리, 이동 시간, 체류 시간
- 총 소요 시간 계산
- 지도 시각화

## 🛠 알고리즘 구조

### 1단계: 컨셉 매칭 (Embedding)
```
테마와 동행 유형 → 각각 텍스트 변환 → 임베딩
관광지 설명 → 임베딩
코사인 유사도 계산 → 카테고리별 상위 80개 후보 선정
```

**사용 모델**: `jhgan/ko-sroberta-multitask` (한국어 특화)

### 2단계: 개인화 점수 및 일정 구성
```
테마 50% + 저장 장소 20% + 동행 유형 10%
+ 여행 기간 내 축제 10% + 이동 효율 10%
→ 실제 이동시간 + 체류시간 계산
→ 시간 예산 내 반복
→ 코스 완성
```

- 저장 장소 보너스는 해당 장소까지 이동시간이 30분 이내일 때 적용한다.
- 행사형 관광지는 여행 기간과 겹치는 축제만 후보로 사용한다.
- 음식점은 방문일과 `restDate`가 겹치면 후보에서 제외한다.

### 3단계: 시간 관리
- **반나절**: 4시간 (240분)
- **1일**: 8시간 (480분)
- **1박2일**: 16시간 (960분)

기본적으로 경로 API의 실제 이동시간을 사용한다. API를 사용할 수 없을 때는 다음 평균속도로 추정한다.
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

## 🚀 사용 방법

### 1. 환경 설정
```bash
pip install sentence-transformers scikit-learn pandas numpy matplotlib
```

### 2. 데이터 준비
- `_TourSpot__202607062337.csv`

### 3. 실행
```python
from recommender import TourCourseRecommender

recommender = TourCourseRecommender(
    api_base_url='https://oiso.duckdns.org',
    use_route_api=True,
)

course, concept = recommender.recommend(
    duration='one_day',      # 'half_day', 'one_day', 'two_days'
    companions='couple',     # 'alone', 'family', 'couple', 'friends'
    theme='scenery',         # 'scenery', 'history', 'culture', 'food'
    transport='car',         # 'walk', 'bicycle', 'public', 'car'
    start_lat=35.83,         # 선택: 시작 위도
    start_lon=129.21         # 선택: 시작 경도
)
```

## 📈 현재 성능

### 장점 ✅
- **빠른 속도**: 임베딩 1회 생성 후 재사용
- **의미적 매칭**: 단순 키워드가 아닌 문맥 기반
- **실용적**: 실제 이동 시간 고려
- **유연함**: 기간·동행인·테마·이동수단 조합 처리

### 한계 ⚠️
- Greedy 알고리즘 → 최적 경로 보장 안 됨
- 경로 API 실패 시 평균속도 기반 추정값 사용
- 영업시간과 날씨 미반영
- 자유 형식 휴무일 문구 중 지원하지 않는 표현은 정보 없음으로 처리

## 🔧 향후 개선 사항

### 우선순위 1: 경로 최적화
- [ ] 2-opt 알고리즘 적용
- [ ] Genetic Algorithm 시도
- [ ] 실제 도로 거리 API 연동 (Kakao, Tmap)

### 우선순위 2: 여러 날 일정 개선
- [ ] 날짜별 체류 시간 세분화
- [ ] 날짜별 시작·종료 시간 설정

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
