# Trade Pilot — 데이터 인터페이스, 서비스 간 통신

> 이 문서는 `backend/architecture.md`에서 분할되었습니다.

---

## 4. 데이터 인터페이스 표준

### 4.1 공통 에러 응답 (ApiErrorResponse)
모든 REST API 실패 시 아래 객체를 JSON으로 반환한다.
```kotlin
data class ApiErrorResponse(
    val code:      String,              // 도메인 코드 (A010 등)
    val message:   String,              // 사용자 노출용 기본 메시지
    val timestamp: OffsetDateTime,
    val path:      String,
    val details:   Map<String, String>? // 필드별 에러 (Optional)
)
```

---

## 5. 서비스 간 통신 원칙

### 5.1 동기 통신 (gRPC)

**사용 시나리오**:
- 데이터 조회 (캔들, 심볼 메타데이터)
- 백테스팅 등 스트리밍 응답이 필요한 경우
- 응답이 즉시 필요한 요청-응답 패턴

**원칙**:
- **타임아웃 설정 필수**: 모든 gRPC 호출은 명시적 타임아웃 설정
- **에러 전파**: gRPC 상태 코드를 도메인 에러로 변환
- **재시도 제한**: 멱등한 조회는 최대 3회, 비멱등 작업은 재시도 금지

**타임아웃 기준**:
```
조회 (GetRecentCandles):        5초
대용량 조회 (GetHistoricalCandles): 30초
스트리밍 (BacktestStrategy):    30분
```

### 5.2 비동기 통신 (Kafka)

**사용 시나리오**:
- 도메인 이벤트 발행 (상태 변경 알림)
- 커맨드 전달 (신호 생성 요청, 주문 실행)
- 서비스 간 결합도를 낮춰야 하는 경우

**원칙**:
- **At-Least-Once 보장**: Consumer는 멱등성 처리 필수 (`processed_events` 테이블)
- **Outbox 패턴**: DB 트랜잭션과 Kafka 발행의 원자성이 필요한 경우 사용
- **Saga 패턴**: 분산 트랜잭션은 Saga로 구현 (보상 트랜잭션 정의)

### 5.3 REST API

**사용 시나리오**:
- 프론트엔드 ↔ 백엔드 통신
- 외부 시스템 연동

**원칙**:
- **API Gateway 경유**: 모든 외부 요청은 API Gateway를 통해 라우팅
- **JWT 검증**: Gateway에서 JWT 검증 후 `X-User-Id` 헤더 주입
- **공통 에러 응답**: `ApiErrorResponse` 포맷 통일

### 5.4 탈퇴 사용자 요청 차단

회원 탈퇴(`UserWithdrawnEvent`) 후 각 서비스의 비동기 정리가 완료되기 전에
탈퇴 사용자의 JWT가 유효한 상태로 API 요청이 도달할 수 있다.

**Gateway 레벨 차단**:
- User Service가 `WITHDRAWN` 상태를 반환하면 Gateway에서 `403 ACCOUNT_WITHDRAWN` 반환
- JWT 만료(15분) 전까지는 Gateway가 직접 차단할 수 없으므로, **각 서비스에서도 방어**

**서비스 레벨 방어**:
- 쓰기 작업(POST/PUT/DELETE) 수행 전에 `X-User-Id`로 User Service에 상태 확인하거나,
  로컬 `processed_events` 테이블에서 `UserWithdrawnEvent` 수신 여부를 확인
- 읽기 작업(GET)은 탈퇴 후에도 일시적으로 허용 (데이터가 soft delete 되기 전까지)

> 탈퇴 후 최대 15분(JWT 만료) + 수초(이벤트 전파) 동안 요청이 도달할 수 있다.
> 이 간극은 JWT 만료 시간을 줄이거나, Gateway에 실시간 블랙리스트(Redis)를 추가하여 단축할 수 있다.
