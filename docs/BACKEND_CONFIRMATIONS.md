# 백엔드와 확인이 필요한 사항

아래 항목은 구현이 잘못되어 미완성인 목록이 아니라, Spring 연동 계약 또는 배포 정책을 확정해야 하는 항목이다.

## 우선 확인

1. 호출 구조
   - 제안: 프론트는 Spring만 호출하고, Spring이 내부적으로 FastAPI를 호출한다.
   - FastAPI는 로그인 쿠키나 사용자 ID를 직접 다루지 않는다.

2. Spring 공개 API 경로
   - 제안: `POST /api/v1/tour-courses/recommend`
   - Spring이 저장된 사용자 선호정보를 조회해 FastAPI 요청을 만들지, 프론트 요청 본문을 그대로 전달할지 확인이 필요하다.

3. 추천 결과 저장 시점
   - 제안: FastAPI는 계산 결과만 반환하고 Spring이 `TourCourse`와 코스 아이템을 저장한다.
   - 추천 버튼을 누르는 즉시 저장할지, 사용자가 추천 결과를 확인하고 확정할 때 저장할지 결정이 필요하다.

4. 요청/응답 enum
   - 요청 enum은 현재 프론트의 `TravelTime`, `TravelCompanion`, `PreferredTravelTheme`, `TransportationMode`와 맞췄다.
   - 응답 `transportType`은 코스 API 프론트 타입인 `WALK | BIKE | CAR`와 맞췄다. Spring DTO enum도 같은지 확인이 필요하다.

5. 공통 응답 코드
   - 성공 코드를 `2000`, 검증 실패 코드를 `4000`으로 구현했다.
   - 기존 Swagger 예시에는 API마다 `0`과 `2000`이 섞여 있으므로 Python 내부 API도 어느 규칙을 사용할지 확인이 필요하다.

## 데이터/API 계약 확인

6. 관광지 목록 API의 페이징 응답
   - Python은 `GET /api/v1/tour-spots?page=0&size=100`을 호출하고 `data.places` 또는 `data.items`를 읽는다.
   - 실제 필드명, 페이지가 0부터 시작하는지, 내부 서비스에서 인증 없이 호출 가능한지 확인이 필요하다.

7. 이동 계산 API 요청/응답
   - Python 예상 요청은 `origin`, `destination`, `transportationMode`이다.
   - 예상 응답 필드는 `distanceMeter`, `durationSecond`이다.
   - 실제 DTO가 다르면 맞춰야 한다. 확정 전까지 기본값 `USE_ROUTE_API=false`로 둔다.

8. 서비스 간 인증
   - 배포 환경에서 Spring API가 인증을 요구한다면 사용자 쿠키 전달 대신 서비스 전용 토큰 또는 내부망 정책이 필요하다.
   - 임시로 `BACKEND_AUTH_COOKIE` 환경변수를 지원하지만 운영 방식으로 권장하지 않는다.

9. 장소 식별자 규칙
   - `TOUR_SPOT`은 `spotId`, `RESTAURANT`와 `ACCOMMODATION`은 `nearbyPlaceId`를 사용하는 것으로 구현했다.
   - 코스 저장 DTO도 이 규칙을 강제하는지 확인이 필요하다.

## 추천 정책 확인

10. 여러 날 코스 정책
    - 현재 `dayNumber`는 누적 8시간 단위의 임시 값이다.
    - 하루 시작/종료 시간, 숙소 배치, 다음 날 출발 위치를 어떤 규칙으로 정할지 기획·백엔드와 합의가 필요하다.

11. 식당과 숙소 포함 정책
    - 관광지 통합 목록에 식당·숙소가 항상 포함되는지, 테마가 `FOOD`일 때 식당을 몇 개 배치할지, 숙소는 몇 박 코스부터 필수인지 확인이 필요하다.

12. 선호 테마 미선택 정책
    - 프론트 타입이 `preferredTravelTheme: null`을 허용해 현재는 일반 관광 문장으로 추천한다.
    - 백엔드에서 테마를 필수로 바꿀 계획이면 FastAPI 검증도 필수값으로 바꿀 수 있다.

13. 추천 개수와 제한시간
    - 현재 상위 후보 30개를 대상으로 여행 시간 예산이 찰 때까지 장소를 추가한다.
    - 최대 장소 수, 식사 시간, 장소별 체류 시간 정책을 확정해야 한다.

## 배포/CI·CD 확인

14. Python 서비스 배포 대상
    - 서버 또는 클라우드 서비스, 컨테이너 레지스트리, 운영 URL/포트가 필요하다.
    - 이 값이 정해지면 GitHub Actions에 이미지 push 및 배포 단계를 추가할 수 있다.

15. Spring에서 사용할 FastAPI 주소
    - 예: 로컬 `http://localhost:8000`, 운영 `http://oiso-modeling:8000` 또는 별도 HTTPS 주소.
    - Spring 환경변수 이름과 연결 timeout/retry 정책을 정해야 한다.

16. 모델 파일 다운로드 정책
    - 현재 컨테이너 시작 시 Hugging Face 모델을 받을 수 있다.
    - 운영 서버의 외부 네트워크가 막혀 있으면 이미지 빌드 시 모델을 포함하거나 별도 모델 볼륨을 연결해야 한다.

17. 관광지/임베딩 갱신 정책
    - 관광 데이터 동기화 후 Python 프로세스를 재시작할지, 별도 reload API를 만들지 정해야 한다.
    - 무인증 내부 reload API는 데이터/자원 오용 위험이 있어 인증 방식과 함께 확정해야 한다.

