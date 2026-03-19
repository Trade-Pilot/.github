# Trade Service — Domain 설계

## 1. Bounded Context

Trade Service는 **Agent의 신호를 바탕으로 실제 거래소에 주문을 제출하고 체결을 추적**하는 역할을 담당한다.

```
Trade Service 책임
├── 등록 관리    Agent의 실거래 등록 및 거래소 계정 연결 관리
├── 트리거       스케줄러가 주기적으로 Kafka AnalyzeAgentCommand 발행
├── 주문 생성    AnalyzeAgentReply 수신 시 Order 엔티티 생성
├── 주문 제출    Exchange Service로 주문 전달 (Kafka)
├── 체결 추적    Exchange Service 체결 이벤트 수신 → Order/Execution 갱신
└── 타임아웃 처리 미체결 LIMIT 주문 자동 취소
```

### 책임 분리

| | Trade Service | Exchange Service | Agent Service |
|---|---|---|---|
| **실거래 등록/트리거** | ✅ | ❌ | ❌ |
| **전략 신호 생성** | ❌ | ❌ | ✅ |
| **주문 생성/추적** | ✅ | ❌ | ❌ |
| **거래소 API 연동** | ❌ | ✅ | ❌ |
| **실체결 기반 포트폴리오** | ❌ (이벤트 발행) | ❌ | ✅ (이벤트 수신 후 갱신) |
| **실제 체결 이력** | ✅ (Execution) | ❌ | ❌ |
| **현재가 조회** | ✅ (트리거 전) | ❌ | ✅ (stopLoss용) |

Trade Service는 체결이 확정될 때마다 `ExecutionConfirmedEvent`를 발행한다.
Agent Service는 이를 수신해 실제 체결가·수량·수수료 기준으로 포트폴리오를 갱신한다.

---

## 2. 헥사고날 아키텍처 레이어

```
domain/
  model/         TradeRegistration, OrderConfig
                 Order, Execution
                 OrderStatus, OrderType, OrderSide, RegistrationStatus
  port/
    in/          RegisterTradeUseCase
                 ActivateRegistrationUseCase
                 PauseRegistrationUseCase
                 StopRegistrationUseCase
                 HandleAgentReplyUseCase     (AnalyzeAgentReply 수신 → 주문 생성)
                 HandleOrderStatusUseCase    (Exchange 이벤트 → Order 상태 갱신)
                 CancelTimedOutOrdersUseCase (스케줄러: LIMIT 타임아웃 주문 취소)
    out/         FindRegistrationOutput, SaveRegistrationOutput
                 FindOrderOutput, SaveOrderOutput
                 FindCurrentPriceOutput             (Market Service gRPC)
                 PublishAnalyzeCommandOutput        (Kafka → Agent Service 신호 요청)
                 PublishExecutionConfirmedOutput    (Kafka → Agent Service 체결 확정)
                 SubmitOrderOutput                  (Kafka → Exchange Service)
                 CancelOrderOutput                  (Kafka → Exchange Service)

application/
  usecase/       RegisterTradeService
                 ActivateRegistrationService
                 PauseRegistrationService         (implements PauseRegistrationUseCase)
                 StopRegistrationService          (implements StopRegistrationUseCase)
                 HandleAgentReplyService
                 HandleOrderStatusService
                 TradeScheduler              (주기적 트리거)
                 OrderTimeoutScheduler       (LIMIT 주문 타임아웃 처리)

infrastructure/
  kafka/         AnalyzeAgentCommandProducer       (implements PublishAnalyzeCommandOutput)
                 AnalyzeAgentReplyConsumer          (reply.agent.trade.analyze-strategy 구독)
                 ExecutionConfirmedEventProducer    (implements PublishExecutionConfirmedOutput)
                 SubmitOrderCommandProducer         (implements SubmitOrderOutput)
                 CancelOrderCommandProducer         (implements CancelOrderOutput)
                 OrderStatusEventConsumer           (event.exchange.order-status 구독)
                 AgentTerminatedEventConsumer       (trade-pilot.agentservice.agent 구독)
                 UserWithdrawnEventConsumer         (trade-pilot.userservice.user 구독)
  grpc/          MarketCandleGrpcAdapter     (implements FindCurrentPriceOutput)
  persistence/   TradeRegistrationJpaAdapter
                   (implements FindRegistrationOutput, SaveRegistrationOutput)
                 OrderJpaAdapter
                   (implements FindOrderOutput, SaveOrderOutput)
  web/           TradeRegistrationController
                 OrderController
```

---

## 3. 도메인 모델

### Aggregate 구성

```
TradeRegistration (Aggregate Root)
├── registrationId       : UUID
├── agentId              : UUID              -- Agent Service 참조
├── userId               : UUID
├── exchangeAccountId    : UUID              -- Exchange Service 참조
├── symbolIds            : List<UUID>        -- 분석 대상 심볼 목록 (JSONB)
├── status               : RegistrationStatus
├── orderConfig          : OrderConfig       -- JSONB
├── emergencyStopped     : Boolean           -- 비상 정지 여부 (true이면 모든 신호 처리 차단)
├── createdAt            : OffsetDateTime
└── updatedAt            : OffsetDateTime

──────────────────────────────────────────

Order (Aggregate Root)
├── orderId              : UUID
├── registrationId       : UUID
├── agentId              : UUID
├── symbolId             : UUID
├── signalId             : UUID              -- Agent Service Signal 참조 (감사 목적)
├── side                 : OrderSide         -- BUY | SELL
├── type                 : OrderType         -- MARKET | LIMIT
├── requestedQuantity    : BigDecimal        -- Agent 신호 기준 요청 수량
├── requestedPrice       : BigDecimal?       -- LIMIT 주문 목표가 (MARKET이면 null)
├── executedQuantity     : BigDecimal        -- 누적 체결 수량 (기본값 0)
├── averageExecutedPrice : BigDecimal?       -- 평균 체결가 (미체결이면 null)
├── status               : OrderStatus
├── exchangeOrderId      : String?           -- 거래소가 부여한 주문 ID
├── timeoutAt            : OffsetDateTime?   -- LIMIT 주문 자동 취소 기준 시각 (null이면 무제한)
├── createdAt            : OffsetDateTime
└── updatedAt            : OffsetDateTime

Execution (Entity — Order 소속)
├── executionId          : UUID
├── orderId              : UUID
├── quantity             : BigDecimal        -- 이번 체결 수량
├── price                : BigDecimal        -- 실제 체결가
├── fee                  : BigDecimal        -- 수수료
└── executedAt           : OffsetDateTime
```

### Value Objects

```kotlin
enum class RegistrationStatus {
    ACTIVE,    // 스케줄러가 주기적으로 신호 요청 발행 중
    PAUSED,    // 일시 중지
    STOPPED,   // 종료 — 재활성화 불가
}

enum class OrderType  { MARKET, LIMIT }
enum class OrderSide  { BUY, SELL }

enum class OrderStatus {
    PENDING,           // Trade Service 생성, Exchange Service 미전달
    SUBMITTED,         // Exchange Service가 거래소에 제출 완료
    PARTIALLY_FILLED,  // 일부 체결 (잔여 수량 대기 중)
    FILLED,            // 완전 체결
    CANCELLED,         // 취소 완료 (타임아웃 또는 사용자 요청)
    REJECTED,          // 거래소 또는 Exchange Service가 거부
}

data class OrderConfig(
    val orderType                : OrderType,  // MARKET | LIMIT
    val limitOrderTimeoutMinutes : Int?,       // LIMIT 미체결 자동 취소 대기 시간, null이면 무제한
)
```

### Order 상태 전이

```
PENDING ──[Exchange 제출 확인]──▶ SUBMITTED ──[일부 체결]──▶ PARTIALLY_FILLED
                                      │                              │
                                      │                        [완전 체결]
                                      │                              │
                                      └─────────[완전 체결]──────────▼
                                                              FILLED (종료)
                                      │
                                [타임아웃/취소 요청]
                                      ▼
                                CANCELLED (종료)

PENDING ──[거래소 거부]──▶ REJECTED (종료)
```

> `FILLED` / `CANCELLED` / `REJECTED` 상태는 종료 상태다. 이후 상태 전이 없음.
>
> LIMIT 주문에서 `PARTIALLY_FILLED` 상태로 `timeoutAt`이 도래하면
> 잔여 수량에 대해 취소 요청을 보내고 최종적으로 `CANCELLED`로 전환된다.
> 이 시점까지 체결된 수량은 Execution에 유지된다.

### averageExecutedPrice 계산

여러 번에 걸쳐 부분 체결될 수 있으므로, Execution 추가 시마다 재계산한다.

```
새 averageExecutedPrice =
  (기존 executedQuantity × 기존 averageExecutedPrice + 새 quantity × 새 price)
  / (기존 executedQuantity + 새 quantity)
```

---

## 4. 도메인 포트

```kotlin
// Input Ports
interface RegisterTradeUseCase {
    fun register(command: RegisterTradeCommand): TradeRegistration
}

data class RegisterTradeCommand(
    val agentId           : UUID,
    val userId            : UUID,
    val exchangeAccountId : UUID,
    val symbolIds         : List<UUID>,
    val orderConfig       : OrderConfig,
)

interface HandleAgentReplyUseCase {
    fun handle(reply: AnalyzeAgentReply): Order?  // HOLD이면 null (주문 미생성)
}

interface HandleOrderStatusUseCase {
    fun handle(event: OrderStatusEvent)
}

interface CancelTimedOutOrdersUseCase {
    fun cancelTimedOut()  // OrderTimeoutScheduler가 주기적으로 호출
}

// Output Ports
interface FindRegistrationOutput {
    fun findById(registrationId: UUID): TradeRegistration?
    fun findAllByStatus(status: RegistrationStatus): List<TradeRegistration>
    fun findByAgentId(agentId: UUID): TradeRegistration?
}

interface SaveRegistrationOutput {
    fun save(registration: TradeRegistration): TradeRegistration
}

interface FindOrderOutput {
    fun findById(orderId: UUID): Order?
    fun findByExchangeOrderId(exchangeOrderId: String): Order?
    fun findTimedOutPendingOrders(now: OffsetDateTime): List<Order>
    fun findAllByAgentId(agentId: UUID, page: Int, size: Int): List<Order>
    // 중복 주문 방지: PENDING / SUBMITTED / PARTIALLY_FILLED 상태 주문 존재 여부 확인
    fun findActiveByAgentAndSymbol(agentId: UUID, symbolId: UUID): Order?
}

interface SaveOrderOutput {
    fun save(order: Order): Order
}

interface FindCurrentPriceOutput {
    fun getCurrentPrice(symbolId: UUID, interval: CandleInterval): BigDecimal
}

interface PublishAnalyzeCommandOutput {
    fun publish(topic: String, command: AnalyzeAgentCommand)
}

interface SubmitOrderOutput {
    fun submit(command: SubmitOrderCommand)
}

interface CancelOrderOutput {
    fun cancel(command: CancelOrderCommand)
}

// Agent Service에 실체결 완료 통보
interface PublishExecutionConfirmedOutput {
    fun publish(event: ExecutionConfirmedEvent)
}

data class ExecutionConfirmedEvent(
    val agentId    : UUID,
    val signalId   : UUID,           // 이 체결을 유발한 Signal ID
    val symbolId   : UUID,
    val side       : OrderSide,      // BUY | SELL
    val quantity   : BigDecimal,     // 이번 체결 수량 (부분 체결이면 부분 수량)
    val price      : BigDecimal,     // 실제 체결가
    val fee        : BigDecimal,     // 실제 수수료
    val executedAt : OffsetDateTime,
) : EventBaseMessage

data class SubmitOrderCommand(
    val orderId           : UUID,
    val exchangeAccountId : UUID,
    val symbolId          : UUID,
    val side              : OrderSide,
    val type              : OrderType,
    val quantity          : BigDecimal,
    val price             : BigDecimal?,   // LIMIT이면 지정가, MARKET이면 null
) : CommandBaseMessage

data class CancelOrderCommand(
    val orderId         : UUID,
    val exchangeOrderId : String,
) : CommandBaseMessage
```

---

## 5. 스케줄러

### TradeScheduler (신호 요청 트리거)

```
[매 1분 실행]
1. FindRegistrationOutput.findAllByStatus(ACTIVE)
2. 각 registration에 대해:
   각 symbolId에 대해:
     a. FindCurrentPriceOutput.getCurrentPrice(symbolId, interval=MINUTE_1)
     b. PublishAnalyzeCommandOutput.publish(
          topic   = "command.agent.trade.analyze-strategy",
          command = AnalyzeAgentCommand(agentId, symbolId, currentPrice)
        )
```

### OrderTimeoutScheduler (LIMIT 주문 타임아웃 처리)

```
[매 1분 실행]
1. FindOrderOutput.findTimedOutPendingOrders(now)
   └ status IN (SUBMITTED, PARTIALLY_FILLED) AND timeoutAt < now
2. 각 order에 대해:
   CancelOrderOutput.cancel(CancelOrderCommand(orderId, exchangeOrderId))
   └ Exchange Service가 취소 처리 후 OrderCancelledEvent 발행
```

> LIMIT 주문이 `SUBMITTED`된 이후 `timeoutAt` 이전까지는 Trade Service가 직접 취소하지 않는다.
> 타임아웃 초과 시에만 취소 요청을 보내고, 실제 `CANCELLED` 상태 전환은 Exchange Service의 이벤트를 기다린다.

---

## 6. Kafka 인터페이스

### 발행 — 신호 생성 요청

```kotlin
// 발행 토픽
// command.agent.trade.analyze-strategy

data class AnalyzeAgentCommand(
    val agentId      : UUID,
    val symbolId     : UUID,
    val currentPrice : BigDecimal,
) : CommandBaseMessage
```

### 수신 — 신호 생성 결과

```kotlin
// 구독 토픽
// reply.agent.trade.analyze-strategy

data class AnalyzeAgentReply(
    val agentId           : UUID,
    val signalId          : UUID?,        // BUY/SELL이면 Agent Service가 저장한 Signal ID, HOLD이면 null
    val strategyId        : UUID,
    val symbolId          : UUID,
    val signalType        : SignalType,
    val confidence        : BigDecimal,
    val suggestedQuantity : BigDecimal,
    val price             : BigDecimal,   // Agent가 사용한 currentPrice
    val reason            : Map<String, Any>,
) : CommandBaseMessage
```

**AnalyzeAgentReply 수신 후 처리:**

```
1. signalType 확인
   - HOLD  → 처리 없음 (단순 로그)
   - BUY / SELL →
       a. TradeRegistration 조회 (agentId 기준)
       b. OrderConfig 확인 (orderType, limitOrderTimeoutMinutes)
       b-1. 중복 주문 방지:
            FindOrderOutput.findActiveByAgentAndSymbol(agentId, symbolId)
            └ PENDING / SUBMITTED / PARTIALLY_FILLED 상태 주문이 이미 존재하면 → 처리 종료 (로그)
            └ 미체결 주문이 완료되지 않은 상태에서 중복 주문을 막기 위함
       c. Order 생성 (PENDING 상태)
            signalId          = reply.signalId
            side              = signalType (BUY → BUY, SELL → SELL)
            type              = orderConfig.orderType
            requestedQuantity = reply.suggestedQuantity
            requestedPrice    = reply.price (LIMIT이면 설정, MARKET이면 null)
            timeoutAt         = now + limitOrderTimeoutMinutes (LIMIT & 설정된 경우)
       d. Order DB 저장
       e. SubmitOrderOutput.submit(SubmitOrderCommand)
            └ Kafka command.exchange.submit-order 발행
```

### 발행 — 주문 제출

```kotlin
// 발행 토픽
// command.exchange.submit-order

data class SubmitOrderCommand(
    val orderId           : UUID,
    val exchangeAccountId : UUID,
    val symbolId          : UUID,
    val side              : OrderSide,
    val type              : OrderType,
    val quantity          : BigDecimal,
    val price             : BigDecimal?,
) : CommandBaseMessage
```

### 발행 — 체결 확정 (Agent Service 포트폴리오 갱신 트리거)

PARTIALLY_FILLED / FILLED 이벤트 수신 시 체결 건별로 발행한다.
부분 체결이 여러 번 발생하면 체결 건마다 이벤트가 독립적으로 발행된다.

```
발행 토픽 : event.trade.execution
메시지 구조: ExecutionConfirmedEvent (Section 4 도메인 포트 참조)
```

### 발행 — 주문 취소

```kotlin
// 발행 토픽
// command.exchange.cancel-order

data class CancelOrderCommand(
    val orderId         : UUID,
    val exchangeOrderId : String,
) : CommandBaseMessage
```

### 수신 — Exchange Service 주문 상태 이벤트

```kotlin
// 구독 토픽
// event.exchange.order-status

data class OrderStatusEvent(
    val orderId         : UUID,           // Trade Service Order ID
    val exchangeOrderId : String,         // 거래소 주문 ID
    val status          : ExchangeOrderStatus,
    val filledQuantity  : BigDecimal,     // 이번 이벤트의 체결 수량 (0이면 상태 변경만)
    val filledPrice     : BigDecimal?,    // 이번 체결가 (미체결이면 null)
    val fee             : BigDecimal?,    // 수수료 (체결 시만)
    val reason          : String?,        // REJECTED / CANCELLED 사유
) : EventBaseMessage

enum class ExchangeOrderStatus {
    SUBMITTED,        // 거래소 제출 완료
    PARTIALLY_FILLED, // 일부 체결
    FILLED,           // 완전 체결
    CANCELLED,        // 취소 완료
    REJECTED,         // 거부
}
```

**OrderStatusEvent 수신 후 처리:**

```
1. orderId로 Order 조회
2. ExchangeOrderStatus에 따라 분기:

   SUBMITTED:
     Order.status = SUBMITTED
     Order.exchangeOrderId = event.exchangeOrderId

   PARTIALLY_FILLED:
     Execution 생성 (filledQuantity, filledPrice, fee)
     Order.executedQuantity += filledQuantity
     Order.averageExecutedPrice 재계산
     Order.status = PARTIALLY_FILLED
     PublishExecutionConfirmedOutput.publish(ExecutionConfirmedEvent)
       └ agentId, signalId, symbolId, side
       └ quantity = filledQuantity, price = filledPrice, fee = fee
       └ 발행 토픽: event.trade.execution

   FILLED:
     Execution 생성 (filledQuantity, filledPrice, fee)
     Order.executedQuantity += filledQuantity
     Order.averageExecutedPrice 재계산
     Order.status = FILLED
     PublishExecutionConfirmedOutput.publish(ExecutionConfirmedEvent)
       └ agentId, signalId, symbolId, side
       └ quantity = filledQuantity, price = filledPrice, fee = fee
       └ 발행 토픽: event.trade.execution

   CANCELLED:
     Order.status = CANCELLED
     // 보상 트랜잭션: 미체결 잔여 수량에 대한 점유 해제 이벤트 발행
     PublishExecutionConfirmedOutput.publishOrderFailed(order)
       └ agentId, signalId, symbolId, side
       └ remainingQuantity = requestedQuantity - executedQuantity
       └ 발행 토픽: event.trade.execution-failed

   REJECTED:
     Order.status = REJECTED
     // 보상 트랜잭션: 요청 전체 수량에 대한 점유 해제 이벤트 발행
     PublishExecutionConfirmedOutput.publishOrderFailed(order)
       └ agentId, signalId, symbolId, side
       └ remainingQuantity = requestedQuantity
       └ 발행 토픽: event.trade.execution-failed
     로그 기록 (reason)
```

### Event 수신 — AgentTerminatedEvent

```
구독 토픽 : trade-pilot.agentservice.agent  (eventType: "agent-terminated")
처리      : agentId에 해당하는 TradeRegistration → STOPPED 처리
```

### Event 수신 — UserWithdrawnEvent

```
구독 토픽 : trade-pilot.userservice.user  (eventType: "user-withdrawn")
처리      : userId에 속한 모든 TradeRegistration → STOPPED 처리
            PENDING / SUBMITTED / PARTIALLY_FILLED 상태 Order → 취소 요청 발행
```

---

## 6-1. 비상 정지 (Emergency Stop) 메커니즘

### 개요

실거래 중 예기치 않은 시장 상황(급등락, 전략 오작동, 시스템 이상)이 감지될 때
사용자 또는 관리자가 즉각적으로 거래를 중단할 수 있는 메커니즘이다.

### 비상 정지 발동 조건

| 발동 주체 | 방법 | 범위 |
|-----------|------|------|
| 사용자 | `PUT /trade-registrations/{id}/emergency-stop` | 특정 Registration |
| 관리자 | `POST /admin/trade-registrations/emergency-stop-all` | 전체 ACTIVE Registration |

### 비상 정지 처리 흐름

```
PUT /trade-registrations/{id}/emergency-stop 요청

1. TradeRegistration.emergencyStopped = true
2. TradeRegistration.status = PAUSED         (스케줄러 트리거 중단)
3. 미체결 주문 취소:
   FindOrderOutput.findAllByRegistrationIdAndActiveStatus(registrationId)
     └ status IN (PENDING, SUBMITTED, PARTIALLY_FILLED)
     └ 각 주문에 대해 CancelOrderOutput.cancel(CancelOrderCommand)
4. Notification 발행: "비상 정지 완료, {n}건 주문 취소 요청됨"
```

### 신호 처리 시 비상 정지 검증

`AnalyzeAgentReply` 수신 시 (HandleAgentReplyService):

```
1. TradeRegistration 조회 (agentId 기준)
2. registration.emergencyStopped == true → 처리 중단 (TR012 로그) + 알림 발송
3. registration.status != ACTIVE → 처리 중단 (로그)
4. 이하 정상 처리 흐름
```

### 비상 정지 해제

비상 정지 해제(`PUT /trade-registrations/{id}/emergency-resume`) 시:
- `emergencyStopped = false`
- `status = PAUSED` (자동으로 ACTIVE가 되지 않음)
- 사용자가 상황을 확인하고 직접 `activate()` 호출해야 재개됨

### trade_registration 테이블 스키마 추가

`## 8. DB 스키마` 섹션의 `trade_registration` 테이블에 `emergency_stopped` 컬럼 추가가 필요합니다.

---

## 7. gRPC 인터페이스

### Trade → Market (현재가 조회)

스케줄러가 `AnalyzeAgentCommand`에 포함할 `currentPrice`를 조회한다.
VirtualTrade와 동일하게 `GetRecentCandles(limit=1).close`를 현재가로 사용한다.

```
Market Service proto (market-service.proto)
────────────────────────────────────────────
service MarketCandle {
  rpc GetRecentCandles(GetRecentCandlesRequest) returns (GetRecentCandlesResponse);
}
```

```
FindCurrentPriceOutput (domain port)
        ▲
        │ implements
MarketCandleGrpcAdapter (infrastructure/grpc)
        │ uses generated stub
        ▼
MarketCandleGrpc.MarketCandleBlockingStub  ←  Market Service gRPC Server
```

---

## 8. DB 스키마

```sql
CREATE TABLE trade_registration (
    id                   UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id             UUID         NOT NULL UNIQUE,
    user_id              UUID         NOT NULL,
    exchange_account_id  UUID         NOT NULL,
    symbol_ids           JSONB        NOT NULL DEFAULT '[]',
    status               VARCHAR(20)  NOT NULL DEFAULT 'ACTIVE',
    order_config         JSONB        NOT NULL DEFAULT '{}',
    emergency_stopped    BOOLEAN      NOT NULL DEFAULT FALSE,  -- 비상 정지 여부
    created_at           TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at           TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_tr_user   ON trade_registration (user_id);
CREATE INDEX idx_tr_status ON trade_registration (status);

CREATE TABLE trade_order (
    id                     UUID          PRIMARY KEY DEFAULT gen_random_uuid(),
    registration_id        UUID          NOT NULL REFERENCES trade_registration(id),
    agent_id               UUID          NOT NULL,
    symbol_id              UUID          NOT NULL,
    signal_id              UUID          NOT NULL,             -- Agent Service Signal 참조 (감사용)
    side                   VARCHAR(10)   NOT NULL,             -- BUY | SELL
    type                   VARCHAR(10)   NOT NULL,             -- MARKET | LIMIT
    requested_quantity     NUMERIC(30,8) NOT NULL,
    requested_price        NUMERIC(30,8),                      -- LIMIT이면 목표가, MARKET이면 null
    executed_quantity      NUMERIC(30,8) NOT NULL DEFAULT 0,
    average_executed_price NUMERIC(30,8),                      -- 평균 체결가 (미체결이면 null)
    status                 VARCHAR(20)   NOT NULL DEFAULT 'PENDING',
    exchange_order_id      VARCHAR(100),                       -- 거래소 주문 ID
    timeout_at             TIMESTAMPTZ,                        -- LIMIT 주문 자동 취소 기준 시각
    created_at             TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    updated_at             TIMESTAMPTZ   NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_order_agent       ON trade_order (agent_id,    created_at DESC);
CREATE INDEX idx_order_status      ON trade_order (status);
-- 중복 주문 방지: agentId + symbolId 기준 active 주문 조회
CREATE INDEX idx_order_active      ON trade_order (agent_id, symbol_id)
    WHERE status IN ('PENDING', 'SUBMITTED', 'PARTIALLY_FILLED');
-- 타임아웃 스케줄러 쿼리 최적화
CREATE INDEX idx_order_timeout     ON trade_order (timeout_at)
    WHERE status IN ('SUBMITTED', 'PARTIALLY_FILLED') AND timeout_at IS NOT NULL;
-- Exchange 이벤트 수신 시 exchangeOrderId로 Order 조회
CREATE INDEX idx_order_exchange_id ON trade_order (exchange_order_id)
    WHERE exchange_order_id IS NOT NULL;

CREATE TABLE execution (
    id           UUID          PRIMARY KEY DEFAULT gen_random_uuid(),
    order_id     UUID          NOT NULL REFERENCES trade_order(id),
    quantity     NUMERIC(30,8) NOT NULL,
    price        NUMERIC(30,8) NOT NULL,
    fee          NUMERIC(30,8) NOT NULL DEFAULT 0,
    executed_at  TIMESTAMPTZ   NOT NULL
);

CREATE INDEX idx_execution_order ON execution (order_id, executed_at ASC);

CREATE TABLE outbox (
    id             UUID    PRIMARY KEY DEFAULT gen_random_uuid(),
    aggregate_type VARCHAR NOT NULL,
    aggregate_id   VARCHAR NOT NULL,
    event_type     VARCHAR NOT NULL,
    payload        TEXT    NOT NULL,
    trace_id       VARCHAR,
    parent_span_id VARCHAR,
    status         VARCHAR NOT NULL DEFAULT 'PENDING',
    retry_count    INT     NOT NULL DEFAULT 0,
    created_at     TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    published_at   TIMESTAMP WITH TIME ZONE
);

CREATE INDEX outbox_relay_idx ON outbox (created_at)
    WHERE status IN ('PENDING', 'FAILED');
CREATE INDEX outbox_dead_idx ON outbox (created_at)
    WHERE status = 'DEAD';

CREATE TABLE processed_events (
    topic       VARCHAR(255) NOT NULL,
    partition   INT          NOT NULL,
    offset      BIGINT       NOT NULL,
    consumed_at TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    PRIMARY KEY (topic, partition, offset)
);
```

---

## 9. API 엔드포인트

### TradeRegistration

| Method | 경로 | Role | 설명 |
|--------|------|------|------|
| `POST` | `/trade-registrations` | USER | 실거래 등록 (agentId + exchangeAccountId + symbolIds + orderConfig) |
| `GET` | `/trade-registrations` | USER | 내 실거래 등록 목록 |
| `GET` | `/trade-registrations/{id}` | USER | 등록 상세 |
| `PUT` | `/trade-registrations/{id}/activate` | USER | ACTIVE 전환 |
| `PUT` | `/trade-registrations/{id}/pause` | USER | PAUSED 전환 |
| `PUT` | `/trade-registrations/{id}/stop` | USER | STOPPED 처리 |
| `PUT` | `/trade-registrations/{id}/symbols` | USER | 분석 대상 심볼 목록 수정 |
| `PUT` | `/trade-registrations/{id}/order-config` | USER | 주문 설정 수정 (PAUSED 상태만) |
| `PUT` | `/trade-registrations/{id}/emergency-stop` | USER | 비상 정지 (즉시 모든 신호 처리 차단 + 미체결 주문 취소) |
| `PUT` | `/trade-registrations/{id}/emergency-resume` | USER | 비상 정지 해제 (PAUSED 상태로 복귀 — 자동 재시작 안 함) |
| `POST` | `/admin/trade-registrations/emergency-stop-all` | ADMIN | 전체 실거래 비상 정지 |

### Order

| Method | 경로 | Role | 설명 |
|--------|------|------|------|
| `GET` | `/trade-registrations/{id}/orders` | USER | 주문 이력 (페이지네이션) |
| `GET` | `/trade-registrations/{id}/orders/{orderId}` | USER | 주문 상세 (Execution 포함) |
| `DELETE` | `/trade-registrations/{id}/orders/{orderId}` | USER | 미체결 주문 수동 취소 (SUBMITTED / PARTIALLY_FILLED만) |

---

## 10. 에러 코드

| 코드 | 상수 | 설명 |
|------|------|------|
| `TR001` | `REGISTRATION_NOT_FOUND` | 실거래 등록 없음 |
| `TR002` | `ALREADY_REGISTERED` | 해당 Agent는 이미 실거래에 등록됨 |
| `TR003` | `REGISTRATION_STOPPED` | STOPPED 상태는 재활성화 불가 |
| `TR004` | `REGISTRATION_NOT_ACTIVE` | ACTIVE 상태가 아니어서 일시정지 불가 |
| `TR005` | `REGISTRATION_NOT_PAUSED` | PAUSED 상태가 아니어서 재활성화 불가 |
| `TR006` | `SYMBOL_IDS_EMPTY` | symbolIds는 최소 1개 이상 필요 |
| `TR007` | `CURRENT_PRICE_UNAVAILABLE` | Market Service에서 현재가 조회 실패 |
| `TR008` | `ORDER_NOT_FOUND` | 주문 없음 |
| `TR009` | `ORDER_NOT_CANCELLABLE` | 취소 불가 상태의 주문 (FILLED / CANCELLED / REJECTED) |
| `TR010` | `EXCHANGE_ACCOUNT_NOT_FOUND` | Exchange Service에서 계정 없음 |
| `TR011` | `ORDER_SUBMIT_FAILED` | Exchange Service 주문 제출 실패 |
| `TR012` | `EMERGENCY_STOP_ACTIVE` | 비상 정지 상태이므로 주문 처리 불가 |
| `TR013` | `NOT_EMERGENCY_STOPPED` | 비상 정지 상태가 아님 |
