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
          │                                └──────────────────────┘
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
| API Gateway          | JWT 검증, 라우팅, Rate Limit | 설계 필요           |
| User Service         | 계정 관리, 인증, JWT 발급/갱신    | ✅ 설계 완료         |
| Exchange Service     | 거래소 API 어댑터 (업비트 등)     | 설계 필요           |
| Market Service       | 심볼/캔들 수집·저장             | ✅ 설계 완료         |
| Agent Service        | 전략 관리, 신호 생성, 기술적 지표    | 설계 필요           |
| Simulation Service   | 백테스팅 (TimeTravelEngine) | 설계 필요           |
| VirtualTrade Service | 실시간 가상거래                | 설계 필요           |
| Trade Service        | 실제 거래 실행                | 설계 예정 (Phase 4) |
| Notification Service | 알림 채널 관리, 메시지 발송        | ✅ 설계 완료         |

---

## 2. 헥사고날 아키텍처 네이밍 규칙

모든 서비스에 동일하게 적용되는 네이밍 컨벤션이다.

### Output Port (domain/port/out)

외부 시스템·저장소와의 의존 역전을 표현하는 인터페이스.

| 유형 | 형식 | 예시 |
|------|------|------|
| 조회 | `Find{도메인}Output` | `FindMarketCandleOutput`, `FindStrategyOutput` |
| 저장 | `Save{도메인}Output` | `SaveStrategyOutput`, `SaveSignalOutput` |
| 삭제 | `Delete{도메인}Output` | `DeleteNotificationLogOutput` |
| 발행 | `Publish{도메인}Output` | `PublishOutboxOutput` |

### Output Adapter (infrastructure)

Output Port를 구현하는 인프라 클래스. **`{도메인}{방식}Adapter`** 형식을 따른다.

| 방식 | 형식 | 예시 |
|------|------|------|
| JPA (DB) | `{도메인}JpaAdapter` | `StrategyJpaAdapter`, `PortfolioJpaAdapter` |
| gRPC | `{도메인}GrpcAdapter` | `MarketGrpcAdapter` |
| Kafka | `{도메인}KafkaAdapter` | `OutboxKafkaAdapter` |

```
// 포트와 어댑터의 관계 예시
domain/port/out/FindMarketCandleOutput.kt  ← 인터페이스 (포트)
infrastructure/grpc/MarketGrpcAdapter.kt   ← 구현체 (어댑터)

domain/port/out/FindStrategyOutput.kt      ← 인터페이스 (포트)
infrastructure/persistence/StrategyJpaAdapter.kt ← 구현체 (어댑터)
```

### Input Port (domain/port/in)

애플리케이션 진입점을 표현하는 인터페이스 (Use Case).

| 형식 | 예시 |
|------|------|
| `{행위}{도메인}UseCase` | `AnalyzeAgentUseCase`, `CreateStrategyUseCase` |

---

## 3. 서비스 간 통신 원칙

### 기본 규칙

- **모든 서비스 간 통신은 Kafka 비동기를 기본**으로 한다
- API Gateway → Service 구간만 동기 HTTP 허용
- 서비스 간 직접 REST 호출 금지
- **gRPC는 예외적으로 허용** — 아래 조건을 모두 만족하는 경우에 한해 사용 가능

### gRPC 예외 허용 규칙

Kafka가 부적합한 특수한 경우에 한해 gRPC를 허용한다.
**모든 gRPC 예외는 아키텍처 문서에 사유와 함께 명시**해야 한다.

**허용 조건:**
- 대용량 데이터를 동기 스트리밍으로 전달해야 하는 경우 (수십만 건 이상)
- Kafka Command/Reply 패턴으로 구현 시 타임아웃 또는 메모리 문제가 명확히 예상되는 경우
- 실시간 양방향 스트리밍이 필요한 경우

**현재 승인된 gRPC 예외:**

| 구간 | 방향 | 사유 |
|------|------|------|
| `Simulation → Agent` | Server Streaming | 백테스팅 시 수십만 건 캔들 전달 + 신호 스트리밍 수신. Kafka Command/Reply로는 타임아웃·메모리 한계 |
| `Agent → Market` | Unary / Server Streaming | 전략 신호 생성을 위한 캔들 데이터 조회. 수백~수천 건 범위의 지표 계산용 데이터를 동기적으로 조회 |
| `Simulation → Market` | Server Streaming | 백테스팅용 대용량 과거 캔들 조회 (수십만 건). 동일 캔들 데이터를 반복 조회하므로 Market Service 측 캐시 적용 필수 |

```
Simulation ──gRPC Server Streaming──▶ Agent
              AnalyzeStrategyRequest   │
              {candles: [500,000건]}   │
                                       │ 스트리밍 응답
Simulation ◀── AnalyzeStrategyReply ──│
              {signal: BUY/SELL/HOLD} (건별 스트리밍)

Agent ──────gRPC Unary──────────────▶ Market
              GetCandlesRequest        │
              {symbol, interval, limit}│
                                       │
Agent ◀─────── GetCandlesReply ───────│
              {candles: [...]}
```

### 통신 패턴

#### Command / Reply 패턴 (요청-응답)

응답이 필요한 경우 사용한다. `requestId`(또는 `taskId`)로 요청과 응답을 매핑하고,
`CompletableFuture` + 타임아웃으로 응답을 기다린다.

```
Producer                    Consumer
   │                            │
   │── COMMAND_TOPIC ──────────▶│
   │   {requestId: UUID, ...}   │
   │                            │ 처리
   │◀─ REPLY_TOPIC ─────────────│
   │   {requestId: UUID, ...}   │
```

**적용 예시**
- `Market → Exchange`: 심볼 목록 조회, 캔들 데이터 조회
- `Trade → Exchange`: 실주문 실행, 주문 취소

#### Event 패턴 (단방향)

응답이 필요 없는 사실 전달에 사용한다. Publisher는 Consumer를 알지 못한다.

```
Publisher                   Consumer(s)
   │                            │
   │── EVENT_TOPIC ────────────▶│ Consumer A
   │                       ────▶│ Consumer B (동일 이벤트 다수 구독 가능)
```

**적용 예시**
- `Market → VirtualTrade`: 실시간 캔들 수집 완료 이벤트
- `VirtualTrade → Notification`: 주문 체결 알림 커맨드

### Kafka 토픽 명명 규칙

토픽 이름(실제 Kafka 브로커에 생성되는 문자열)과 Kotlin 상수 이름은 별개의 규칙을 따른다.

#### 실제 토픽 이름 (Kafka broker)

| 유형 | 형식 | 예시 |
|------|------|------|
| Command | `command.{수신 도메인}.{발신 도메인}.{행위}` | `command.exchange.market.find-all-candle` |
| Reply (성공) | `reply.{발신 도메인}.{수신 도메인}.{행위}` | `reply.market.exchange.find-all-candle` |
| Reply (실패) | `reply-failure.{발신 도메인}.{수신 도메인}.{행위}` | `reply-failure.market.exchange.find-all-candle` |
| Domain Event | `{프로젝트}.{서비스명}.{도메인}` | `trade-pilot.marketservice.market-candle-collect-task` |
| Notification | `command.notification.send` | 단일 토픽 (다수 서비스 발행) |

- 도메인·서비스명은 **kebab-case** (소문자 + 하이픈)
- 행위는 동사-명사 순 kebab-case (`find-all-candle`, `place-order`, `analyze-strategy`)

#### Kotlin 상수 이름 (코드 내 상수)

| 유형 | 형식 | 예시 |
|------|------|------|
| Command | `{VERB}_{RESOURCE}_COMMAND_TOPIC` | `FIND_ALL_MARKET_CANDLE_COMMAND_TOPIC` |
| Reply (성공) | `{VERB}_{RESOURCE}_REPLY_TOPIC` | `FIND_ALL_MARKET_CANDLE_REPLY_TOPIC` |
| Reply (실패) | `{VERB}_{RESOURCE}_REPLY_FAILURE_TOPIC` | `FIND_ALL_MARKET_CANDLE_REPLY_FAILURE_TOPIC` |
| Domain Event | `{DOMAIN}_{RESOURCE}_EVENT_TOPIC` | `MARKET_CANDLE_COLLECT_TASK_EVENT_TOPIC` |

상수 값에 실제 토픽 이름 문자열을 대입한다.

```kotlin
// market-service: KafkaTopics.kt
object KafkaTopics {
    const val FIND_ALL_MARKET_CANDLE_COMMAND_TOPIC  = "command.exchange.market.find-all-candle"
    const val FIND_ALL_MARKET_CANDLE_REPLY_TOPIC    = "reply.market.exchange.find-all-candle"
    const val MARKET_CANDLE_COLLECT_TASK_EVENT_TOPIC = "trade-pilot.marketservice.market-candle-collect-task"
}
```

### Kafka 페이로드 규칙

모든 Kafka 메시지는 아래 규칙을 따른다.

- **직렬화**: JSON (Jackson), 필드명은 camelCase
- **페이로드 타입**: 명확한 Kotlin data class 사용 (`Map<String, Any>` 금지)
- **Command / Reply**: `CommandBaseMessageEnvelope<T>` 로 감싼다
- **Domain Event**: `AbstractDomainEventEnvelope<T>` 를 상속한다

#### Envelope 구조

```kotlin
// Command / Reply 공통 래퍼
data class CommandBaseMessageEnvelope<T : CommandBaseMessage>(
    val envelopeIdentifier: String = UUID.randomUUID().toString(),
    val commandType: String,   // 요청 토픽 이름 (예: "command.exchange.market.find-all-candle")
    val callback: String?,     // Reply 토픽 이름 (없으면 null — 단방향 커맨드)
    val data: T,
    val createdDate: OffsetDateTime = OffsetDateTime.now(),
)
interface CommandBaseMessage

// Domain Event 공통 래퍼
abstract class AbstractDomainEventEnvelope<T : DomainEventMessage>(
    open val envelopeIdentifier: UUID = UUID.randomUUID(),
    open val aggregateIdentifier: String,  // 집계 루트 ID
    open val aggregateType: String,        // 도메인 이벤트 토픽 이름
                                           // (예: "trade-pilot.marketservice.market-candle-collect-task")
    open val eventType: String,            // 이벤트 행위 (예: "collect-task-completed", kebab-case)
    open val data: T,
    open val createdDate: OffsetDateTime = OffsetDateTime.now(),
)
interface DomainEventMessage
```

**필드 의미 정리:**

| 필드 | 클래스 | 값 형식 | 예시 |
|------|--------|---------|------|
| `commandType` | `CommandBaseMessageEnvelope` | 요청 토픽 이름 (실제 Kafka 토픽) | `command.exchange.market.find-all-candle` |
| `callback` | `CommandBaseMessageEnvelope` | Reply 토픽 이름 (없으면 null) | `reply.market.exchange.find-all-candle` |
| `aggregateType` | `AbstractDomainEventEnvelope` | 도메인 이벤트 토픽 이름 (실제 Kafka 토픽) | `trade-pilot.marketservice.market-candle-collect-task` |
| `eventType` | `AbstractDomainEventEnvelope` | 이벤트 행위 (kebab-case 동사구) | `collect-task-completed`, `user-withdrawn` |

**`callback` 필드 활용**: VirtualTrade와 Trade가 각자의 reply 토픽으로 라우팅받기 위해 `callback`에 자신의 reply 토픽을 지정한다.

```kotlin
// VirtualTrade → Agent
CommandBaseMessageEnvelope(
    commandType = "command.agent.virtual-trade.analyze-strategy",
    callback    = "reply.virtual-trade.agent.analyze-strategy",
    data        = AnalyzeStrategyCommand(...),
)

// Trade → Agent
CommandBaseMessageEnvelope(
    commandType = "command.agent.trade.analyze-strategy",
    callback    = "reply.trade.agent.analyze-strategy",
    data        = AnalyzeStrategyCommand(...),
)
```

**Domain Event 예시:**

```kotlin
// Market Service — 캔들 수집 완료 이벤트
class MarketCandleCollectTaskEventEnvelope(
    override val aggregateIdentifier: String,  // collectTaskId
    override val aggregateType: String = "trade-pilot.marketservice.market-candle-collect-task",
    override val eventType: String     = "collect-task-completed",
    override val data: MarketCandleCollectTaskCompletedEvent,
) : AbstractDomainEventEnvelope<MarketCandleCollectTaskCompletedEvent>()

// User Service — 회원 탈퇴 이벤트
class UserEventEnvelope(
    override val aggregateIdentifier: String,  // userId
    override val aggregateType: String = "trade-pilot.userservice.user",
    override val eventType: String,            // "user-withdrawn"
    override val data: UserDomainEventMessage,
) : AbstractDomainEventEnvelope<UserDomainEventMessage>()
```

---

## 4. Kafka 토픽 전체 맵

> 표에는 **실제 Kafka 토픽 이름**을 기재한다. Kotlin 상수 이름은 괄호 안에 병기.

### Market ↔ Exchange

| 실제 토픽 이름 (상수 이름) | 발행 | 구독 | 설명 |
|--------------------------|------|------|------|
| `command.exchange.market.find-all-symbol`<br>(`FIND_ALL_MARKET_SYMBOL_COMMAND_TOPIC`) | Market | Exchange | 심볼 목록 조회 요청 |
| `reply.market.exchange.find-all-symbol`<br>(`FIND_ALL_MARKET_SYMBOL_REPLY_TOPIC`) | Exchange | Market | 심볼 목록 응답 |
| `command.exchange.market.find-all-candle`<br>(`FIND_ALL_MARKET_CANDLE_COMMAND_TOPIC`) | Market | Exchange | 캔들 데이터 조회 요청 |
| `reply.market.exchange.find-all-candle`<br>(`FIND_ALL_MARKET_CANDLE_REPLY_TOPIC`) | Exchange | Market | 캔들 데이터 응답 |
| `reply-failure.market.exchange.find-all-candle`<br>(`FIND_ALL_MARKET_CANDLE_REPLY_FAILURE_TOPIC`) | Exchange | Market | 캔들 조회 실패 응답 |

### Market (내부 / 외부 발행)

| 실제 토픽 이름 (상수 이름) | 발행 | 구독 | 설명 |
|--------------------------|------|------|------|
| `trade-pilot.marketservice.market-candle-collect-task`<br>(`MARKET_CANDLE_COLLECT_TASK_EVENT_TOPIC`) | Market | Market (내부) | MIN_1 수집 완료 → 파생 간격 계산 트리거 |
| `trade-pilot.marketservice.market-candle`<br>(`MARKET_CANDLE_REALTIME_EVENT_TOPIC`) | Market | VirtualTrade, Trade | 실시간 캔들 수집 완료 → 전략 실행 트리거 **(TBD)** |

### Agent (Kafka — 실시간 단건 신호)

VirtualTrade와 Trade는 동일한 Agent command 토픽으로 발행하되, Envelope의 `callback` 필드로 각자의 reply 토픽을 지정한다.

| 실제 토픽 이름 (상수 이름) | 발행 | 구독 | 설명 |
|--------------------------|------|------|------|
| `command.agent.virtual-trade.analyze-strategy`<br>(`VIRTUAL_TRADE_ANALYZE_STRATEGY_COMMAND_TOPIC`) | VirtualTrade | Agent | 가상거래 전략 신호 생성 요청 |
| `reply.virtual-trade.agent.analyze-strategy`<br>(`VIRTUAL_TRADE_ANALYZE_STRATEGY_REPLY_TOPIC`) | Agent | VirtualTrade | 신호 응답 (BUY / SELL / HOLD) |
| `command.agent.trade.analyze-strategy`<br>(`TRADE_ANALYZE_STRATEGY_COMMAND_TOPIC`) | Trade | Agent | 실거래 전략 신호 생성 요청 |
| `reply.trade.agent.analyze-strategy`<br>(`TRADE_ANALYZE_STRATEGY_REPLY_TOPIC`) | Agent | Trade | 신호 응답 (BUY / SELL / HOLD) |

> **Simulation ↔ Agent 통신은 gRPC 사용** (Section 2 예외 규칙 참조)
> **Agent ↔ Market 캔들 데이터 조회는 gRPC 사용** (Section 2 예외 규칙 참조)

### Trade ↔ Exchange

| 실제 토픽 이름 (상수 이름) | 발행 | 구독 | 설명 |
|--------------------------|------|------|------|
| `command.exchange.trade.place-order`<br>(`PLACE_ORDER_COMMAND_TOPIC`) | Trade | Exchange | 실주문 실행 요청 |
| `reply.trade.exchange.place-order`<br>(`PLACE_ORDER_REPLY_TOPIC`) | Exchange | Trade | 실주문 실행 응답 |
| `command.exchange.trade.cancel-order`<br>(`CANCEL_ORDER_COMMAND_TOPIC`) | Trade | Exchange | 주문 취소 요청 |
| `reply.trade.exchange.cancel-order`<br>(`CANCEL_ORDER_REPLY_TOPIC`) | Exchange | Trade | 주문 취소 응답 |

### User → 전체 서비스

| 실제 토픽 이름 (상수 이름) | 발행 | 구독 | 설명 |
|--------------------------|------|------|------|
| `trade-pilot.userservice.user`<br>(`USER_WITHDRAWN_EVENT_TOPIC`) | User | Notification, Agent, VirtualTrade, Trade | 회원 탈퇴 → 각 서비스 연관 데이터 정리 |

### Notification Command (단일 진입점)

| 실제 토픽 이름 (상수 이름) | 발행 | 구독 | 설명 |
|--------------------------|------|------|------|
| `command.notification.send`<br>(`NOTIFICATION_COMMAND_TOPIC`) | VirtualTrade, Trade, Market, (기타) | Notification | 알림 발송 요청. 각 서비스가 `SendNotificationCommand` 발행 |

> Notification Service는 다른 도메인을 의존하지 않는다.
> 각 서비스가 알림이 필요할 때 `NOTIFICATION_COMMAND_TOPIC`에 발행하는 방향으로
> 의존 관계가 역전된다. (Notification ← 각 서비스)

### 토픽 파티션 키 규칙

| 토픽 유형 | 파티션 키 |
|-----------|-----------|
| 심볼/캔들 관련 | `symbolIdentifier` |
| 전략/신호 관련 | `strategyIdentifier` |
| 주문/거래 관련 | `accountIdentifier` |
| 알림 커맨드 | `userId` |
| 사용자 생명주기 이벤트 | `userId` |

---

## 5. 인증/인가 전략

> 자세한 내용은 [auth-strategy.md](./auth-strategy.md) 참조

### 왜 API Gateway를 선택했는가

모든 인증/인가는 API Gateway에서 처리한다. 이 선택의 핵심 이유는 다음과 같다.

- **단일 책임 분리**: 각 마이크로서비스가 인증 로직을 가질 필요가 없어 도메인 로직에 집중 가능
- **JWT 자체 검증 (RS256)**: User Service에 검증 요청 없이 Public Key만으로 Gateway가 독립 검증
  → User Service 부하 없음, 검증 지연 없음
- **헤더 기반 인터페이스**: Gateway가 검증 후 `X-User-Id` / `X-User-Role` 헤더만 하위 서비스에 전달
  → 서비스 코드에 인증 로직 전혀 없음, 인프라 교체 시 코드 무변경

```
Client ──HTTPS──▶ API Gateway
                    │ JWT 검증 (RS256, JWKS 자체 조회)
                    │ X-User-Id 헤더 추가
                    │ X-User-Role 헤더 추가
                    ▼
                 Services
                    │ 헤더만 신뢰
                    │ 인증 로직 없음
```

```kotlin
// 모든 서비스에서 인증은 이것만.
@GetMapping("/strategies")
fun getStrategies(
    @RequestHeader("X-User-Id") userId: UUID
): List<StrategyResponse> { ... }
```

### 엔드포인트 권한 관리

권한 규칙을 코드에 하드코딩하면 변경할 때마다 재배포가 필요하다.
**DB + Redis 캐시**로 규칙을 관리해 런타임에 적용한다.

#### 권한 레벨

| Role | 설명 |
|------|------|
| `ADMIN` | 시스템 관리자 (수집 제어, 계정 관리 등) |
| `USER` | 일반 사용자 |
| `PUBLIC` | 인증 불필요 (로그인, 회원가입, JWKS 등) |

#### DB 스키마

```sql
CREATE TABLE endpoint_permission (
    id            BIGSERIAL PRIMARY KEY,
    http_method   VARCHAR(10),            -- NULL = 모든 메서드
    path_pattern  VARCHAR(255) NOT NULL,  -- Ant 패턴 (예: /users/{userId}/suspend)
    required_role VARCHAR(20)  NOT NULL
        CHECK (required_role IN ('PUBLIC', 'USER', 'ADMIN')),
    description   VARCHAR(255),
    priority      INT     NOT NULL DEFAULT 0, -- 낮을수록 먼저 평가
    is_active     BOOLEAN NOT NULL DEFAULT TRUE,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_ep_active ON endpoint_permission (is_active, priority);
```

**규칙 평가 순서**: `priority ASC` 기준으로 첫 번째 매칭 규칙을 적용한다. 매칭 규칙이 없으면 접근을 거부한다.

#### 캐시 전략

```
Redis Key : endpoint-permissions:all
TTL       : 10분
구조      : List<EndpointPermissionDto> (JSON 직렬화)
갱신 시점 : 규칙 생성/수정/삭제 시 Admin API가 캐시를 즉시 evict
           → 다음 요청 시 DB 재조회 후 캐시 재적재
```

엔드포인트 수가 적어(<100) 전체 목록을 단일 키로 관리한다.
per-endpoint 캐시는 패턴 매칭 순서 보장이 어렵기 때문에 사용하지 않는다.

#### 핵심 컴포넌트

```kotlin
// 1. HeaderAuthenticationFilter — X-User-Role 헤더 → SecurityContext 주입
@Component
class HeaderAuthenticationFilter : OncePerRequestFilter() {
    override fun doFilterInternal(
        request: HttpServletRequest,
        response: HttpServletResponse,
        chain: FilterChain,
    ) {
        val role = request.getHeader("X-User-Role")
        if (role != null) {
            val auth = PreAuthenticatedAuthenticationToken(
                request.getHeader("X-User-Id"), null,
                listOf(SimpleGrantedAuthority("ROLE_$role"))
            ).also { it.isAuthenticated = true }
            SecurityContextHolder.getContext().authentication = auth
        }
        try { chain.doFilter(request, response) }
        finally { SecurityContextHolder.clearContext() }
    }
}

// 2. DynamicAuthorizationManager — DB/캐시 규칙으로 요청 평가
@Component
class DynamicAuthorizationManager(
    private val permissionCache: EndpointPermissionCacheService,
) : AuthorizationManager<RequestAuthorizationContext> {

    private val pathMatcher = AntPathMatcher()

    override fun check(
        authentication: Supplier<Authentication>,
        context: RequestAuthorizationContext,
    ): AuthorizationDecision {
        val request = context.request
        val matched = permissionCache.getPermissions()
            .filter { it.isActive }
            .sortedBy { it.priority }
            .firstOrNull { rule ->
                (rule.httpMethod == null || rule.httpMethod == request.method) &&
                pathMatcher.match(rule.pathPattern, request.requestURI)
            } ?: return AuthorizationDecision(false)

        if (matched.requiredRole == "PUBLIC") return AuthorizationDecision(true)

        val grantedRole = authentication.get()
            ?.authorities?.firstOrNull()?.authority
            ?: return AuthorizationDecision(false)

        return AuthorizationDecision(
            when (matched.requiredRole) {
                "ADMIN" -> grantedRole == "ROLE_ADMIN"
                "USER"  -> grantedRole == "ROLE_USER" || grantedRole == "ROLE_ADMIN"
                else    -> false
            }
        )
    }
}

// 3. SecurityConfig — Spring Boot 3.x (SecurityFilterChain)
@Configuration
@EnableWebSecurity
class SecurityConfig(
    private val dynamicAuthorizationManager: DynamicAuthorizationManager,
    private val headerAuthenticationFilter: HeaderAuthenticationFilter,
) {
    @Bean
    fun securityFilterChain(http: HttpSecurity): SecurityFilterChain {
        http
            .csrf { it.disable() }
            .sessionManagement { it.sessionCreationPolicy(STATELESS) }
            .authorizeHttpRequests { it.anyRequest().access(dynamicAuthorizationManager) }
            .addFilterBefore(headerAuthenticationFilter, UsernamePasswordAuthenticationFilter::class.java)
        return http.build()
    }
}

// 4. EndpointPermissionCacheService — Redis read-through 캐시
@Service
class EndpointPermissionCacheService(
    private val repository: EndpointPermissionRepository,
    private val redisTemplate: RedisTemplate<String, String>,
    private val objectMapper: ObjectMapper,
) {
    companion object {
        const val CACHE_KEY = "endpoint-permissions:all"
        val TTL = Duration.ofMinutes(10)
    }

    fun getPermissions(): List<EndpointPermissionDto> {
        val cached = redisTemplate.opsForValue().get(CACHE_KEY)
        if (cached != null) return objectMapper.readValue(cached)
        return loadAndCache()
    }

    fun evict() { redisTemplate.delete(CACHE_KEY) }

    @Transactional(readOnly = true)
    private fun loadAndCache(): List<EndpointPermissionDto> {
        val dtos = repository.findAllByIsActiveTrueOrderByPriorityAsc().map { it.toDto() }
        redisTemplate.opsForValue().set(CACHE_KEY, objectMapper.writeValueAsString(dtos), TTL)
        return dtos
    }
}
```

#### Admin API

권한 규칙을 런타임에 변경한다. 변경 즉시 캐시를 evict해 10분 TTL을 기다리지 않고 반영한다.

| Method | 경로 | 설명 |
|--------|------|------|
| `GET` | `/admin/endpoint-permissions` | 전체 규칙 조회 |
| `POST` | `/admin/endpoint-permissions` | 규칙 추가 |
| `PUT` | `/admin/endpoint-permissions/{id}` | 규칙 수정 |
| `DELETE` | `/admin/endpoint-permissions/{id}` | 규칙 비활성화 (soft delete) |
| `POST` | `/admin/endpoint-permissions/cache/evict` | 캐시 강제 갱신 |

> `/admin/**` 경로 자체는 DB에 `required_role = ADMIN` 규칙으로 등록한다.

#### 초기 데이터 (Flyway seed)

```sql
-- V2__seed_endpoint_permissions.sql
INSERT INTO endpoint_permission (http_method, path_pattern, required_role, description, priority) VALUES
-- PUBLIC
(NULL,   '/auth/sign-up',               'PUBLIC', '회원가입',         10),
(NULL,   '/auth/sign-in',               'PUBLIC', '로그인',           10),
(NULL,   '/auth/.well-known/jwks.json', 'PUBLIC', 'JWKS',             10),
(NULL,   '/actuator/health',            'PUBLIC', 'Health check',     10),
-- ADMIN
('GET',  '/users/{userId}',             'ADMIN',  '특정 유저 조회',   20),
('PUT',  '/users/{userId}/suspend',     'ADMIN',  '계정 정지',        20),
('PUT',  '/users/{userId}/activate',    'ADMIN',  '계정 활성화',      20),
(NULL,   '/admin/**',                   'ADMIN',  '관리자 API 전체',  20),
('POST', '/collect-tasks',              'ADMIN',  '수집 태스크 생성', 20),
('PUT',  '/collect-tasks/{id}',         'ADMIN',  '수집 태스크 수정', 20),
-- USER (와일드카드 — 가장 낮은 우선순위)
(NULL,   '/**',                         'USER',   '기본 인증 필요',  100);
```

---

## 6. Observability - 분산 트레이싱

> Outbox 패턴 상세 설계 (엔티티, Relay, DB 스키마, 서비스별 적용 범위)는
> [outbox-pattern.md](./outbox-pattern.md) 참조

### MDC 컨텍스트 전략

각 요청에 다음 식별자를 MDC에 주입하여 Observability를 강화한다.

| 식별자 | 타입 | 설명 | 설정 시점 |
|--------|------|------|-----------|
| `traceId` | W3C Trace (32자 hex) | 단일 요청 내 모든 Span을 연결 | Micrometer 자동 |
| `spanId` | W3C Span (16자 hex) | 개별 작업 단위 | Micrometer 자동 |
| `requestId` | UUID | 단일 HTTP 요청 식별 (API 레이어) | Gateway가 생성, 헤더로 전달 |
| `userId` | UUID | 인증된 사용자 식별 | Gateway가 X-User-Id 헤더에서 주입 |
| `globalTraceId` | UUID | 비즈니스 플로우 전체를 묶는 식별자 | 최초 진입점에서 생성, 하위 이벤트에 포함 |

```kotlin
// MDC Filter (서비스 공통)
class MdcContextFilter : OncePerRequestFilter() {
    override fun doFilterInternal(request: HttpServletRequest, ...) {
        MDC.put("requestId",     request.getHeader("X-Request-Id") ?: UUID.randomUUID().toString())
        MDC.put("userId",        request.getHeader("X-User-Id") ?: "anonymous")
        MDC.put("globalTraceId", request.getHeader("X-Global-Trace-Id") ?: UUID.randomUUID().toString())
        try { filterChain.doFilter(request, response) }
        finally { MDC.clear() }
    }
}
```

> `globalTraceId`는 예를 들어 "회원가입 → 로그인 → 전략 설정 → 백테스팅" 같은
> 비즈니스 플로우 전체를 하나로 묶어 Kibana/Grafana에서 사용자 여정 추적에 활용한다.

### TraceId 전파 규칙

| 구간 | 전파 방식 |
|------|-----------|
| HTTP 요청 → 서비스 | Spring Micrometer 자동 전파 |
| 서비스 → Kafka (직접 발행) | Micrometer + Kafka 자동 전파 |
| 서비스 → Outbox INSERT | 수동으로 `traceId` / `parentSpanId` 컬럼 저장 |
| Outbox Relay → Kafka | 수동으로 `traceparent` 헤더 구성 |
| Kafka Consumer → 서비스 | Micrometer + Kafka 자동 복원 |
| gRPC 호출 | gRPC Metadata로 `traceparent` 전달 |

---

## 7. 데이터베이스 전략

### Database per Service — 별도 인스턴스

각 서비스는 **물리적으로 분리된 PostgreSQL 인스턴스**를 보유한다.
다른 서비스의 DB에 직접 접근하는 것은 엄격히 금지한다.

> 단일 인스턴스 내 스키마 분리가 아닌 **별도 DB 인스턴스**를 사용한다.
> 서비스 장애 시 DB 레벨에서의 완전한 격리가 보장되며, 서비스별 독립적인 백업·스케일 아웃이 가능하다.

| 서비스 | DB 종류 | 비고 |
|--------|---------|------|
| User Service | PostgreSQL | 계정, 인증 정보 |
| Market Service | PostgreSQL (TimescaleDB) | 캔들 파티션 테이블 |
| Exchange Service | 없음 (Stateless) | 거래소 API 어댑터만 |
| Agent Service | PostgreSQL | 전략, 포트폴리오 |
| Simulation Service | PostgreSQL | 시뮬레이션 결과, 거래 내역 |
| VirtualTrade Service | PostgreSQL | 가상 계좌, 포지션 |
| Trade Service | PostgreSQL | 실계좌, 감사 로그 |
| Notification Service | PostgreSQL | 채널 설정, 발송 이력, 메시지 템플릿 |

### 서비스별 Redis 캐시

각 서비스는 **독립된 Redis 인스턴스**를 사용한다. 공유 Redis를 사용하지 않는다.

> **공유 Redis를 사용하지 않는 이유:**
> - 키 네임스페이스 오염 위험 (다른 서비스가 실수로 같은 키 사용)
> - 한 서비스의 캐시 메모리 폭증이 다른 서비스에 영향
> - 서비스별 독립적인 TTL 정책 / Eviction 정책 적용 불가
> - 서비스 독립 배포·스케일 아웃 원칙 위배

| 서비스 | Redis 용도 |
|--------|-----------|
| Market Service | 최근 캔들 데이터 캐시 (실시간 전략 실행용) |
| Simulation Service | 반복 조회 캔들 데이터 캐시 (백테스팅 성능 최적화) |
| Agent Service | 전략 설정 캐시, 계산된 기술적 지표 캐시 |
| User Service | (선택) 블랙리스트 AccessToken 캐시 |

> **백테스팅 캐시 전략 (Simulation Service):**
> 동일 심볼·기간의 캔들 데이터를 반복 조회하는 경우가 많으므로
> Simulation Service 측 Redis에 `candle:{symbol}:{interval}:{date}` 키로 캐시한다.
> TTL은 1시간. Market gRPC 조회 전 캐시 Hit 여부를 먼저 확인한다.

---

## 8. Exchange Service — Rate Limit 풀 분리

### Rate Limit 풀 분리

```
Exchange Service
│
├── PUBLIC_API 풀 (데이터 수집 전용)
│     Market Service ──▶ 심볼 목록 조회
│     Market Service ──▶ 캔들 데이터 조회
│     (거래소 Public API — 인증 불필요)
│
└── PRIVATE_API 풀 (주문 실행 전용)
      Trade Service ──▶ 실주문 실행 (POST /v1/orders)
      Trade Service ──▶ 주문 취소  (DELETE /v1/orders/{uuid})
      (거래소 Private API — API Key + HMAC 서명 필요)
```

| 풀 | 대상 API | Rate Limit 예시 (업비트) | 비고 |
|----|----------|------------------------|------|
| `PUBLIC_API` | 심볼 목록, 캔들 조회 | 10 req/s | 인증 불필요 |
| `PRIVATE_API` | 주문 실행, 취소, 잔액 조회 | 8 req/s | API Key 필요 |

각 풀은 독립적인 `RateLimiter` (Resilience4j) 인스턴스로 관리한다.

---

## 9. 실시간 데이터 전달 — Server-Sent Events (SSE)

클라이언트가 서버로부터 실시간으로 진행 상태를 수신해야 하는 경우 SSE를 사용한다.

| 기능 | 서비스 | SSE 엔드포인트 | 설명 |
|------|--------|----------------|------|
| 백테스팅 진행률 | Simulation Service | `GET /simulations/{id}/progress` | 진행 % 및 중간 결과 스트리밍 |

```kotlin
@GetMapping("/simulations/{id}/progress", produces = [MediaType.TEXT_EVENT_STREAM_VALUE])
fun streamProgress(
    @PathVariable id: UUID,
    @RequestHeader("X-User-Id") userId: UUID,
): SseEmitter {
    return simulationProgressService.subscribe(SimulationId.of(id), UserId.of(userId))
}
```

---

## 10. 기술 스택 요약

| 영역            | 기술                                        |
| ------------- | ----------------------------------------- |
| Language      | Kotlin 2.1.x                              |
| Framework     | Spring Boot 3.5.x                         |
| Architecture  | Microservice, DDD, Hexagonal Architecture |
| ORM           | Spring Data JPA + jOOQ                    |
| Messaging     | Apache Kafka (기본), gRPC (예외)              |
| Database      | PostgreSQL 17, TimescaleDB (시계열)          |
| Cache         | Redis (서비스별 독립 인스턴스)                      |
| Container     | Kubernetes (K3s)                          |
| CI/CD         | Jenkins + ArgoCD + Helm Chart             |
| Observability | OpenTelemetry SDK + Jaeger                |
| Metrics       | Prometheus + Grafana                      |
| Logging       | Grafana Loki + Grafana                    |
