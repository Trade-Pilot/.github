# Trade Pilot - 백엔드 아키텍처

> 전체 서비스 구성, 통신 방식, 인증/인가 전략, 옵저빌리티 설계

---

## 1. 서비스 구성

### 전체 구조도

```
┌───────────────────────────────────────────────────────────────────┐
│                    Frontend (React / FSD)                          │
└───────────────────────────────────────────────────────────────────┘
                              │ HTTPS
                              ▼
┌───────────────────────────────────────────────────────────────────┐
│              API Gateway  (JWT 검증 / 라우팅 / Rate Limit)           │
└───────────────────────────────────────────────────────────────────┘
                              │ HTTP (X-User-Id 헤더)
          ┌───────────────────┼───────────────────┐
          ▼                   ▼                   ▼
┌──────────────┐   ┌──────────────────┐   ┌──────────────────┐
│ User Service │   │ Market Service   │   │  Agent Service   │
└──────────────┘   └──────────────────┘   └──────────────────┘
          │              │  ▲  │                  ▲  ▲
          │         Kafka│  │  │ gRPC (캔들 조회)   │  │
          │              ▼  │  └──────────────────┘  │ gRPC
          │     ┌──────────────────┐                 │ (전략 실행)
          │     │ Exchange Service │       ┌──────────────────────┐
          │     └──────────────────┘       │  Simulation Service  │
          └────────────────────────────────┘       └──────────────────────┘
          │                                          │ gRPC
          │       ┌──────────────────────────────────┘
          │       │ (candle data — Market gRPC)
          │
          │   ┌──────────────────────┐
          │   │  VirtualTrade Service│ ◀── Market (Kafka: 실시간 이벤트)
          │   └──────────────────────┘ ◀── Agent  (Kafka: 전략 신호)
          │              │ Kafka (NOTIFICATION_COMMAND_TOPIC)
          │
          │   ┌──────────────────────┐
          │   │    Trade Service     │ ◀── Agent    (Kafka: 전략 신호)
          │   └──────────────────────┘ ──▶ Exchange (Kafka: 주문 실행)
          │              │ Kafka (NOTIFICATION_COMMAND_TOPIC)
          │              │
          │   ┌──────────┘
          │   │ Market   (Kafka: NOTIFICATION_COMMAND_TOPIC — 수집 오류 알림)
          │   │ User     (Kafka: USER_WITHDRAWN_EVENT_TOPIC)
          │   ▼
          └──▶┌──────────────────────┐
              │  Notification Service│
              └──────────────────────┘
```

**핵심 의존 관계:**

- `VirtualTrade`와 `Trade`는 **완전 독립** — 서로를 의존하지 않음
- `Trade → Exchange`: 실주문 실행은 Exchange Service가 거래소 API 어댑터 역할
- `Agent → Market`: 전략 신호 생성을 위한 캔들 데이터 조회 (gRPC)
- `Simulation → Market`: 백테스팅 대용량 캔들 조회 (gRPC)
- `Simulation → Agent`: 백테스팅 전략 실행 (gRPC, 기존 설계)

### 서비스 목록

| 서비스                  | 책임                      | 설계 상태           |
| -------------------- | ----------------------- | --------------- |
| API Gateway          | JWT 검증, 라우팅, Rate Limit | ✅ 설계 완료         |
| User Service         | 계정 관리, 인증, JWT 발급/갱신    | ✅ 설계 완료         |
| Exchange Service     | 거래소 API 어댑터, 계정 인증 정보 관리 | ✅ 설계 완료         |
| Market Service       | 심볼/캔들 수집·저장             | ✅ 설계 완료         |
| Agent Service        | 전략 관리, 신호 생성, 기술적 지표    | ✅ 설계 완료         |
| Simulation Service   | 백테스팅 (TimeTravelEngine) | ✅ 설계 완료         |
| VirtualTrade Service | 실시간 가상거래                | ✅ 설계 완료         |
| Trade Service        | 실제 거래 실행                | ✅ 설계 완료         |
| Notification Service | 알림 채널 관리, 메시지 발송        | ✅ 설계 완료         |

---

## 2. 보안 전략 (Security)

### 2.1 민감 정보 암호화 (Encryption at Rest)
거래소 API Key 등 민감 정보는 DB에 평문으로 저장하지 않는다.
- **알고리즘**: AES-256-GCM (Authenticated Encryption).
- **키 관리**: **AWS KMS** 또는 **HashiCorp Vault**를 사용하여 마스터 키를 관리한다.
- **범위**: `Exchange Service`의 계좌 Secret Key, `User Service`의 외부 연동 토큰 등.

### 2.2 gRPC 보안
- **mTLS (Mutual TLS)**: 서비스 간 gRPC 통신 시 상호 인증을 위해 mTLS를 적용한다.
- **Internal API Key**: mTLS 외에 추가로 `X-Internal-Secret` 헤더를 통해 사전에 정의된 서비스 키를 검증한다.

### 2.3 Kafka 보안
- **SASL/SCRAM**: Kafka 클러스터 접근 시 사용자 인증을 수행한다.
- **ACL (Access Control List)**: 각 서비스가 자신의 권한이 있는 토픽에만 Produce/Consume 하도록 제한한다.

---

## 3. 성능 및 확장성 전략 (Performance & Scalability)

### 3.1 수집 샤딩 (Worker Sharding)
- **Market Service**의 수집 부하 분산을 위해 `Consistency Hashing` 기반 샤딩을 적용한다.
- **샤딩 키**: `MarketSymbolId` (UUID).
- **분산 방식**: 각 수집 워커(Pod)는 자신이 담당할 해시 버킷을 인지하고, 해당 심볼의 스케줄만 실행한다.

### 3.2 다단계 캐싱 (Multi-level Caching)
- **L1 (Local Cache)**: 자주 조회되는 설정 정보 등은 Caffeine 사용 (TTL 1~5분).
- **L2 (Global Cache)**: Redis를 사용하여 캔들 데이터, 에이전트 상태 등 공유 캐싱.

### 3.3 WebSocket 통합 진입점 (Multiplexing)
프론트엔드의 커넥션 효율을 위해 개별 서비스가 아닌 **API Gateway를 단일 WebSocket 엔드포인트**로 사용한다.
*   **경로**: `wss://api.trade-pilot.com/ws`
*   **방식**: 사용자가 구독하고 싶은 주제(Topic)를 메시지로 전송하면, Gateway가 내부 서비스를 대리 구독하여 메시지를 통합 전달한다.

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

---

## 6. Kafka 토픽 명명 규칙 및 메시지 표준

### 6.1 토픽 명명 규칙

**패턴**:

| 메시지 타입 | 패턴 | 설명 |
|------------|------|------|
| `command` | `command.{수신자}.{발신자}.{액션}` | 요청 전달 — 수신자가 처리 |
| `reply` | `reply.{수신자}.{발신자}.{액션}` | 응답 전달 — command의 발신자가 수신 |
| `reply-failure` | `reply-failure.{수신자}.{발신자}.{액션}` | 실패 응답 |
| `event` | `event.{발행자}.{액션}` | 단방향 이벤트 (발행 후 잊기) |

> **핵심**: `command`의 발신자가 `reply`의 수신자가 된다.
> 예: VirtualTrade → Agent로 command 발행 시, reply는 Agent → VirtualTrade로 돌아온다.

**예시**:
```
# Command: VirtualTrade(발신) → Agent(수신)
command.agent.virtual-trade.analyze-strategy

# Reply: Agent(발신) → VirtualTrade(수신) — command의 발신/수신이 뒤바뀜
reply.virtual-trade.agent.analyze-strategy

# Event: 발행자만 명시
event.virtual-trade.execution
event.agent.agent-terminated

# Exchange Service
command.exchange.market.find-all-symbol       # Market(발신) → Exchange(수신)
reply.market.exchange.find-all-symbol         # Exchange(발신) → Market(수신)
command.exchange.trade.submit-order           # Trade(발신) → Exchange(수신)
command.exchange.trade.cancel-order

# 도메인 이벤트 (CDC 스타일)
trade-pilot.agentservice.agent       (eventType: agent-terminated)
trade-pilot.userservice.user         (eventType: user-withdrawn)
```

**전역 토픽**:
```
trade-pilot.notification.command     (NOTIFICATION_COMMAND_TOPIC)
```

### 6.2 메시지 Envelope

모든 Kafka 메시지는 공통 Envelope로 래핑:

```kotlin
data class KafkaEnvelope<T>(
    val messageIdentifier: UUID,      // 메시지 고유 ID (멱등성 보장)
    val timestamp: OffsetDateTime,
    val traceIdentifier: String,      // 분산 추적용
    val callback: String?,            // Reply 토픽 (Command 전용)
    val payload: T,                   // 실제 메시지
)
```

### 6.3 Command/Reply 패턴

```kotlin
// Command 발행 시 callback 지정
KafkaEnvelope(
    messageIdentifier = UUID.randomUUID(),
    timestamp = now,
    traceIdentifier = currentTraceId,
    callback = "reply.agent.virtual-trade.analyze-strategy",
    payload = AnalyzeAgentCommand(...)
)

// Consumer는 callback 토픽으로 Reply 발행
kafkaTemplate.send(envelope.callback!!, reply)
```

### 6.4 멱등성 보장

모든 Consumer는 `processed_events` 테이블로 중복 처리 방지:

```sql
CREATE TABLE processed_events (
    topic       VARCHAR(255) NOT NULL,
    partition   INT          NOT NULL,
    offset      BIGINT       NOT NULL,
    consumed_at TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    PRIMARY KEY (topic, partition, offset)
);
```

```kotlin
@Transactional
fun consume(record: ConsumerRecord<String, KafkaEnvelope<T>>) {
    val key = ProcessedEventKey(record.topic(), record.partition(), record.offset())

    if (processedEventRepository.existsById(key)) {
        log.debug("Already processed: $key")
        return
    }

    // 비즈니스 로직 처리
    handleMessage(record.value().payload)

    // 처리 완료 기록
    processedEventRepository.save(ProcessedEvent(key, now()))
}
```

---

## 7. 옵저빌리티 (Observability)

### 7.1 Health Check

모든 서비스는 다음 엔드포인트 제공:

```
GET /actuator/health
GET /actuator/health/liveness
GET /actuator/health/readiness
```

**Custom Health Indicators**:
- Database 연결
- Kafka 연결
- Redis 연결
- 외부 의존 서비스 (gRPC)

### 7.2 Metrics (Prometheus)

**필수 메트릭**:
```
# HTTP 요청
http_server_requests_seconds_count{uri, method, status}
http_server_requests_seconds_sum

# Kafka Consumer
kafka_consumer_records_consumed_total{topic}
kafka_consumer_lag{topic, partition}

# gRPC
grpc_server_handled_total{service, method, code}
grpc_server_handling_seconds

# 비즈니스 메트릭 (서비스별)
agent_signal_generated_total{signal_type}
market_candle_collected_total{symbol, interval}
trade_order_submitted_total{side, type, status}
```

### 7.3 Distributed Tracing

**구현**: OpenTelemetry + Jaeger/Tempo

**Trace ID 전파**:
```
HTTP → X-Trace-Id 헤더
Kafka → KafkaEnvelope.traceId
gRPC → grpc-trace-bin 메타데이터
```

**Span 분류**:
- HTTP: `http.method`, `http.url`, `http.status_code`
- Kafka: `messaging.system=kafka`, `messaging.destination=topic`
- gRPC: `rpc.system=grpc`, `rpc.service`, `rpc.method`
- DB: `db.system=postgresql`, `db.statement`

### 7.4 Logging

**로그 레벨 기준**:
```
ERROR: 시스템 장애, 데이터 손실 가능성
WARN:  복구 가능한 오류, Rate Limit 초과
INFO:  비즈니스 이벤트 (주문 체결, 신호 생성)
DEBUG: 디버깅 정보 (프로덕션에서 비활성화)
```

**Structured Logging** (JSON):
```json
{
  "timestamp": "2024-01-01T12:00:00Z",
  "level": "INFO",
  "traceIdentifier": "abc123",
  "service": "agent-service",
  "message": "Signal generated",
  "userIdentifier": "uuid",
  "agentIdentifier": "uuid",
  "signalType": "BUY"
}
```

### 7.5 알람 정책

**Severity 분류**:

**P0 (Critical - 즉시 대응)**:
- 서비스 Health Check 실패 (5분 이상)
- DB 연결 끊김
- DLQ 메시지 발생 (어떤 서비스든)
- Kafka Consumer Lag 서비스별 임계값 초과:

| 서비스 | P0 Lag | P1 Lag | 근거 |
|--------|--------|--------|------|
| Trade Service | > 5,000 | > 1,000 | 실거래 지연은 직접적 손실 |
| Agent Service | > 3,000 | > 500 | 신호 생성 지연 → 체결 타이밍 이탈 |
| VirtualTrade Service | > 5,000 | > 1,000 | 가상거래 지연은 학습 데이터 왜곡 |
| Exchange Service | > 3,000 | > 500 | 주문 제출 지연 → 가격 이탈 |
| Market Service | > 10,000 | > 3,000 | 수집 지연은 허용 범위 넓음 |
| Notification Service | > 30,000 | > 10,000 | 알림 지연은 심각도 낮음 |

**P1 (High - 30분 내 대응)**:
- API 에러율 > 5%
- 주문 제출 실패율 > 10%
- 캔들 수집 실패 연속 3회 이상
- 미체결 LIMIT 주문 3개 이상 && 각 1시간 이상 대기

**P2 (Medium - 업무시간 내 대응)**:
- 디스크 사용률 > 80%
- Memory 사용률 > 85%
- Portfolio Reconciliation 불일치
- Account Reconciliation 불일치

---

## 8. 재시도 및 에러 처리 전략

### 8.1 재시도 정책

**Kafka Consumer**:
```yaml
재시도 횟수: 3회
백오프: 지수 백오프 (1s, 2s, 4s)
DLQ: 3회 실패 시 Dead Letter Queue로 이동
```

**DLQ (Dead Letter Queue) 정책**:

```yaml
토픽 네이밍: dlq.{원본토픽명}
  예시:
    dlq.command.agent.trade.analyze-strategy
    dlq.event.trade.execution
    dlq.event.virtual-trade.execution

보관 기간: 7일 (retention.ms = 604800000)
파티션 수: 원본 토픽과 동일
```

```kotlin
// 각 서비스의 DLQ Consumer 구현 패턴
@KafkaListener(topicPattern = "dlq\\..*", groupId = "{service-name}-dlq-consumer")
fun handleDLQ(record: ConsumerRecord<String, String>) {
    logger.error("DLQ 메시지 수신: topic=${record.topic()}, key=${record.key()}")
    // 1. 관리자 알림 발송 (NOTIFICATION_COMMAND_TOPIC)
    // 2. DLQ 메트릭 증가
    // 3. DB에 DLQ 레코드 저장 (수동 분석용, 선택적)
}
```

**gRPC Client**:
```yaml
재시도 횟수: 3회 (GET 계열), 0회 (POST/PUT)
타임아웃: 5초 (조회), 30초 (대용량 조회)
재시도 가능 코드: UNAVAILABLE, DEADLINE_EXCEEDED
```

**HTTP 외부 API** (거래소 등):
```yaml
재시도 횟수: 2회
타임아웃: 10초
재시도 간격: 1초
```

**스케줄러 작업**:
```yaml
Market Candle 수집:
  자동 재시도: 3회 (retryCount < MAX_RETRY_COUNT)
  재시도 간격: 다음 스케줄 사이클 (1분)
  3회 초과 시: PAUSED 상태, 수동 복구 필요
```

### 8.2 Circuit Breaker

**적용 대상**:
- Exchange Service → 거래소 API
- 모든 gRPC 클라이언트

**설정** (Resilience4j):
```yaml
failureRateThreshold: 50%        # 실패율 50% 초과 시 Open
slowCallRateThreshold: 50%       # 느린 호출 50% 초과 시 Open
slowCallDurationThreshold: 5s    # 5초 이상이면 느린 호출
waitDurationInOpenState: 60s     # Open 상태 유지 시간
permittedNumberOfCallsInHalfOpenState: 10
```

### 8.3 에러 코드 체계

**형식**: `{서비스코드}{일련번호}`

```
User Service:         U001~U999
Exchange Service:     EX001~EX999
Market Service:       MS001~MS999
Agent Service:        A001~A999
Simulation Service:   S001~S999
VirtualTrade Service: VT001~VT999
Trade Service:        T001~T999
Notification Service: N001~N999
```

**HTTP 상태 코드 매핑**:
```
도메인 에러 타입     → HTTP 상태
NOT_FOUND          → 404
INVALID_STATE      → 409 Conflict
VALIDATION_ERROR   → 400 Bad Request
UNAUTHORIZED       → 401
FORBIDDEN          → 403
RATE_LIMIT_EXCEEDED → 429
INTERNAL_ERROR     → 500
```

---

## 9. 데이터 보관 정책

### 9.1 보관 기간

**Hot Storage (PostgreSQL)**:
```
이벤트 로그:        3개월
  - StrategyDecisionLog
  - PortfolioHistory (SIGNAL 타입)
  - NotificationLog

실행 이력:          1년
  - Order
  - Execution
  - Signal

운영 데이터:        30일 후 Hard Delete
  - ProcessedEvents
  - Outbox (발행 성공 후 7일)
  - RefreshToken (만료 30일 후)

마스터 데이터:      영구
  - User
  - Strategy
  - Agent
  - Portfolio
  - MarketSymbol
```

**Warm Storage (BigQuery / S3 Parquet)**:
```
3개월~2년:
  - 모든 이벤트 로그
  - 집계 분석용 데이터
```

**Cold Storage (S3 Glacier)**:
```
2년~:
  - 규제 준수용 감사 데이터
  - 압축 아카이브
```

### 9.2 데이터 아카이빙 스케줄

**매월 1일 실행**:
```sql
-- 3개월 이전 데이터를 BigQuery로 이동
INSERT INTO bigquery.strategy_decision_log
SELECT * FROM strategy_decision_log
WHERE created_at < NOW() - INTERVAL '3 months';

DELETE FROM strategy_decision_log
WHERE created_at < NOW() - INTERVAL '3 months';
```

**매년 1월 1일 실행**:
```
- BigQuery → S3 Parquet 변환
- 2년 이전 데이터 Glacier 이동
```

### 9.3 데이터 삭제 정책

**Soft Delete** (논리 삭제):
```
- User (회원 탈퇴)
- NotificationChannel
- NotificationPreference
- ExchangeAccount

※ 감사 목적으로 데이터는 보존, isDeleted=true 플래그로 비활성화
```

**Hard Delete** (물리 삭제):
```
- RefreshToken (만료 30일 후)
- Outbox (발행 성공 후 7일)
- ProcessedEvents (처리 후 7일)
```

---

## 10. API Gateway 상세

### 10.1 인증 및 인가

**JWT 검증**:
```yaml
알고리즘: RS256
Public Key: User Service에서 제공 (/auth/public-key)
검증 항목:
  - 서명 유효성
  - 만료 시간 (exp)
  - 발급자 (iss = "trade-pilot")
```

**헤더 주입**:
```
검증 성공 시:
  X-User-Id: {userIdentifier}
  X-User-Role: {role}

내부 서비스는 이 헤더를 신뢰하고 사용
```

### 10.2 Rate Limiting

**사용자별 Rate Limit**:
```yaml
인증 사용자 (USER):
  - 300 req/min (userIdentifier 기준)

인증 사용자 (ADMIN):
  - Rate Limit 없음 (내부 운영 도구)

미인증 (PUBLIC):
  - 20 req/min (IP 기준)
```

**엔드포인트별 Rate Limit**:
```yaml
POST /auth/sign-up:     20 req/min (IP 기준)
POST /auth/sign-in:     20 req/min (IP 기준, 무차별 대입 방지)
POST /orders:           100 req/min
GET /*:                 300 req/min
```

### 10.3 라우팅 규칙

```nginx
/auth/**                          → User Service
/users/**                         → User Service
/exchange-accounts/**             → Exchange Service
/market-symbols/**                → Market Service
/market-candle-collect-tasks/**   → Market Service
/strategies/**                    → Agent Service
/agents/**                        → Agent Service
/backtests/**                     → Simulation Service
/virtual-trades/**                → VirtualTrade Service
/trade-registrations/**           → Trade Service
/notification-channels/**        → Notification Service
/notification-preferences/**     → Notification Service
/notification-logs/**            → Notification Service
/notification-templates/**       → Notification Service (ADMIN)
/admin/**                         → API Gateway (자체, 권한 관리)
```

### 10.4 CORS 설정

```yaml
allowed-origins:
  - https://trade-pilot.com
  - https://*.trade-pilot.com
allowed-methods: GET, POST, PUT, DELETE, OPTIONS
allowed-headers: Authorization, Content-Type
max-age: 3600
```

---

## 11. 보안 체크리스트

### 11.1 인증/인가
- [x] JWT RS256 사용
- [x] Refresh Token DB 저장 및 무효화 가능
- [x] API Gateway에서 JWT 검증
- [x] 서비스 간 mTLS 적용
- [x] Kafka SASL/SCRAM 인증

### 11.2 암호화
- [x] 민감 정보 AES-256-GCM 암호화 (Exchange API Key)
- [x] HTTPS 강제 (HTTP → HTTPS 리다이렉트)
- [x] DB 연결 암호화 (SSL/TLS)
- [ ] 암호화 키 로테이션 정책 (TODO)

### 11.3 입력 검증
- [x] DTO Validation (@Valid, JSR-303)
- [x] SQL Injection 방지 (JPA Prepared Statement)
- [x] XSS 방지 (Response Encoding)
- [x] CSRF 방지 (SameSite Cookie, CORS)

### 11.4 권한 검증
- [x] 사용자별 리소스 소유권 검증 (userIdentifier 일치 확인)
- [x] ADMIN 전용 API 분리
- [x] Kafka ACL (토픽별 접근 제어)

---

## 12. 배포 및 운영

### 12.1 컨테이너화

**Dockerfile 표준**:
```dockerfile
FROM eclipse-temurin:21-jre-alpine
WORKDIR /app
COPY build/libs/*.jar app.jar
EXPOSE 8080
ENTRYPOINT ["java", "-jar", "app.jar"]
```

**리소스 제한**:
```yaml
resources:
  requests:
    memory: 512Mi
    cpu: 500m
  limits:
    memory: 1Gi
    cpu: 1000m
```

### 12.2 환경별 설정

```
dev:  개발 환경 (로컬 Docker Compose)
stg:  스테이징 (프로덕션 데이터 복제본)
prod: 프로덕션
```

**환경 변수 관리**:
```yaml
DB 연결: Kubernetes Secret
Kafka: ConfigMap
암호화 키: Vault / AWS Secrets Manager
```

### 12.3 롤링 업데이트

```yaml
strategy:
  type: RollingUpdate
  rollingUpdate:
    maxSurge: 1        # 동시에 추가 가능한 Pod 수
    maxUnavailable: 0  # 업데이트 중 중단 가능한 Pod 수
```

**배포 절차**:
1. Health Check 통과 확인
2. 카나리 배포 (10% 트래픽)
3. 메트릭 모니터링 (에러율, 레이턴시)
4. 점진적 확대 (50% → 100%)
5. 롤백 준비 (이전 이미지 보관)

---

## 부록: 서비스 의존성 매트릭스

| 서비스 | User | Exchange | Market | Agent | Simulation | VirtualTrade | Trade | Notification |
|--------|------|----------|--------|-------|------------|--------------|-------|--------------|
| User | - | - | - | - | - | - | - | ✅ Event |
| Exchange | - | - | - | - | - | - | ✅ Command | - |
| Market | - | ✅ Command | - | - | - | - | - | ✅ Event |
| Agent | - | - | ✅ gRPC | - | - | ✅ Command | ✅ Command | - |
| Simulation | - | - | ✅ gRPC | ✅ gRPC | - | - | - | - |
| VirtualTrade | - | - | ✅ gRPC | ✅ Command | - | - | - | ✅ Command |
| Trade | - | ✅ Command | ✅ gRPC | ✅ Command | - | - | - | ✅ Command |
| Notification | - | - | - | - | - | - | - | - |

**범례**:
- ✅ Command: Kafka Command/Reply
- ✅ Event: Kafka Event (단방향)
- ✅ gRPC: 동기 호출
