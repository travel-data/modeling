# OISO 모델링 FastAPI 작업 정리

## 1. 작업 목적

프론트에서 받은 여행 기간, 동행 유형, 선호 테마, 이동 수단, 출발 좌표를 이용해 임베딩 기반 관광 코스를 계산하는 Python 서비스를 만들었다.

권장 호출 구조는 다음과 같다.

```text
Frontend -> Spring Backend -> Python FastAPI
         <- 코스 저장/조회 <- 추천 계산 결과
```

FastAPI는 추천 계산을 담당하고, 사용자 인증과 추천 결과의 DB 저장은 Spring 백엔드가 담당한다. 브라우저가 FastAPI를 직접 호출하는 구조는 현재 범위에 포함하지 않았다.

## 2. 구현한 내용

- FastAPI 애플리케이션과 Swagger 문서 추가
- 기존 `TourCourseRecommender`를 재사용하는 서비스 계층 추가
- 서버 시작 시 모델과 관광지 임베딩을 한 번만 적재
- 동시에 들어온 요청이 추천기의 공용 DataFrame을 덮어쓰지 않도록 추천 실행 구간 잠금 처리
- 프론트/Spring enum과 Python 알고리즘 내부 값 간 변환 처리
- 프론트에서 허용하는 `preferredTravelTheme: null` 처리
- 위도와 경도 중 하나만 전달되는 잘못된 요청 검증
- 응답의 거리 단위를 km에서 m로, 이동 시간을 분에서 초로 변환
- liveness/readiness API 추가
- Dockerfile, 환경변수 예시, GitHub Actions CI 추가
- 실제 모델을 로드하지 않는 API/서비스 단위 테스트 추가

## 3. API

### 추천 생성

`POST /api/v1/recommendations/courses`

요청 예시:

```json
{
  "travelTime": "ONE_DAY",
  "travelCompanion": "PARTNER",
  "preferredTravelTheme": "NATURE_SCENERY",
  "transportationMode": "CAR",
  "withPet": false,
  "latitude": 35.8562,
  "longitude": 129.2247
}
```

`latitude`와 `longitude`는 둘 다 보내거나 둘 다 생략해야 한다. 둘 다 생략하면 추천 후보 좌표의 중심을 출발점으로 사용한다.

응답 예시:

```json
{
  "code": 2000,
  "message": "관광 코스 추천에 성공했습니다.",
  "data": {
    "concept": "연인과 데이트하기 좋은 아름다운 경치와 자연을 감상할 수 있는 관광지",
    "totalSpotCount": 1,
    "totalDurationMinute": 75,
    "items": [
      {
        "itemOrder": 1,
        "dayNumber": 1,
        "category": "TOUR_SPOT",
        "spotId": 10,
        "nearbyPlaceId": null,
        "name": "테스트 관광지",
        "latitude": 35.8562,
        "longitude": 129.2247,
        "distanceFromPreviousMeter": 1500,
        "durationFromPreviousSecond": 900,
        "visitDurationMinute": 60,
        "similarity": 0.87,
        "transportType": "CAR"
      }
    ]
  }
}
```

### 상태 확인

- `GET /health`: 프로세스 동작 여부 확인. 모델 적재 여부는 `data.modelLoaded`로 제공한다.
- `GET /ready`: 모델 적재가 끝나 추천 요청을 받을 수 있을 때만 200을 반환한다.
- Swagger UI: `/docs`
- OpenAPI JSON: `/openapi.json`

## 4. enum 변환

| 요청 값 | Python 내부 값 |
|---|---|
| `HALF_DAY` | `half_day` |
| `ONE_DAY` | `one_day` |
| `ONE_NIGHT_TWO_DAYS` | `1n2d` |
| `TWO_NIGHTS_THREE_DAYS` | `2n3d` |
| `THREE_NIGHTS_FOUR_DAYS` | `3n4d` |
| `ALONE` | `alone` |
| `PARTNER` | `couple` |
| `FRIENDS` | `friends` |
| `FAMILY` | `family` |
| `HISTORY_CULTURE` | `history` |
| `NATURE_SCENERY` | `scenery` |
| `FOOD` | `food` |
| 테마 미선택 | `general` |
| `WALK_PUBLIC_TRANSIT` | `public` |
| `BICYCLE` | `bicycle` |
| `CAR` | `car` |

코스 아이템의 `transportType`은 프론트 코스 타입에 맞춰 각각 `WALK`, `BIKE`, `CAR`로 반환한다.

## 5. 실행 방법

Python 3.11 기준:

```bash
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Docker 기준:

```bash
docker build -t oiso-modeling .
docker run --rm -p 8000:8000 --env-file .env oiso-modeling
```

환경변수는 `.env.example`을 참고한다. `TOUR_DATA_PATH`가 있으면 로컬 CSV를 사용하고, 없으면 `BACKEND_API_BASE_URL`의 `/api/v1/tour-spots`에서 관광지 데이터를 읽는다.

## 6. 테스트와 CI

```bash
pip install -r requirements-test.txt
pytest -q
```

GitHub Actions는 PR 및 `main`, `develop` 브랜치 push 시 다음을 검사한다.

- Python 소스 컴파일
- API/변환 로직 테스트
- Docker 이미지 빌드

이미지 레지스트리 push 및 서버 배포 단계는 배포 대상과 시크릿이 정해지지 않아 아직 포함하지 않았다.

## 7. 현재 제한 사항

- 여러 날 여행은 총 시간 예산만 늘리고, `dayNumber`는 현재 8시간 단위로 임시 분리한다.
- 숙소를 날짜 사이에 배치하거나 체크인/체크아웃을 최적화하지 않는다.
- 영업시간, 휴무일, 실시간 혼잡도는 아직 반영하지 않는다.
- `USE_ROUTE_API=false`이면 직선거리와 수단별 평균 속도로 이동 시간을 추정한다.
- 시작 시 관광지 전체 임베딩을 계산하므로 최초 준비 시간이 길 수 있다.
- 추천기는 요청마다 공용 DataFrame의 유사도 열을 갱신하므로 현재 프로세스당 추천 계산을 직렬화한다.

