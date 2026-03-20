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
├── registrationIdentifier       : UUID
├── agentIdentifier              : UUID              -- Agent Service 참조
├── userIdentifier               : UUID
├── exchangeAccountIdentifier    : UUID              -- Exchange Service 참조
├── symbolIdentifiers            : List<UUID>        -- 분석 대상 심볼 목록 (JSONB)
├── allocatedCapital     : BigDecimal        -- 이 Registration에 할당된 자본금 (Account Reconciliation용)
├── status               : RegistrationStatus
├── orderConfig          : OrderConfig       -- JSONB
├── emergencyStopped     : Boolean           -- 비상 정지 여부 (true이면 모든 신호 처리 차단)
├── createdAt            : OffsetDateTime
└── updatedAt            : OffsetDateTime

──────────────────────────────────────────

Order (Aggregate Root)
├── orderIdentifier              : UUID
├── registrationIdentifier       : UUID
├── agentIdentifier              : UUID
├── symbolIdentifier             : UUID
├── signalIdentifier             : UUID              -- Agent Service Signal 참조 (감사 목적)
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
├── executionIdentifier          : UUID
├── orderIdentifier              : UUID
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
    val agentIdentifier           : UUID,
    val userIdentifier            : UUID,
    val exchangeAccountIdentifier : UUID,
    val symbolIdentifiers         : List<UUID>,
    val allocatedCapital  : BigDecimal,   // 이 Registration에 할당할 자본금
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
    fun findById(registrationIdentifier: UUID): TradeRegistration?
    fun findAllByStatus(status: RegistrationStatus): List<TradeRegistration>
    fun findByAgentId(agentIdentifier: UUID): TradeRegistration?
}

interface SaveRegistrationOutput {
    fun save(registration: TradeRegistration): TradeRegistration
}

interface FindOrderOutput {
    fun findById(orderIdentifier: UUID): Order?
    fun findByExchangeOrderId(exchangeOrderId: String): Order?
    fun findTimedOutPendingOrders(now: OffsetDateTime): List<Order>
    fun findAllByAgentId(agentIdentifier: UUID, page: Int, size: Int): List<Order>
    // 중복 주문 방지: PENDING / SUBMITTED / PARTIALLY_FILLED 상태 주문 존재 여부 확인
    fun findActiveByAgentAndSymbol(agentIdentifier: UUID, symbolIdentifier: UUID): Order?
}

interface SaveOrderOutput {
    fun save(order: Order): Order
}

interface FindCurrentPriceOutput {
    fun getCurrentPrice(symbolIdentifier: UUID, interval: CandleInterval): BigDecimal
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
    val agentIdentifier    : UUID,
    val signalIdentifier   : UUID,           // 이 체결을 유발한 Signal ID
    val symbolIdentifier   : UUID,
    val side       : OrderSide,      // BUY | SELL
    val quantity   : BigDecimal,     // 이번 체결 수량 (부분 체결이면 부분 수량)
    val price      : BigDecimal,     // 실제 체결가
    val fee        : BigDecimal,     // 실제 수수료
    val executedAt : OffsetDateTime,
) : EventBaseMessage

data class SubmitOrderCommand(
    val orderIdentifier           : UUID,
    val exchangeAccountIdentifier : UUID,
    val symbolIdentifier          : UUID,
    val side              : OrderSide,
    val type              : OrderType,
    val quantity          : BigDecimal,
    val price             : BigDecimal?,   // LIMIT이면 지정가, MARKET이면 null
) : CommandBaseMessage

data class CancelOrderCommand(
    val orderIdentifier            : UUID,
    val exchangeAccountIdentifier  : UUID,        // Exchange Service가 API Key를 조회하기 위해 필요
    val exchangeOrderId    : String,
) : CommandBaseMessage
```

---

## 5. 스케줄러

### TradeScheduler (신호 요청 트리거)

**설정 가능한 실행 주기 (기본: 1분)**:

```yaml
# application.yml
scheduler:
  trade:
    interval: 60000  # 밀리초
```

```kotlin
@Component
class TradeScheduler(
    @Value("\${scheduler.trade.interval:60000}")
    private val schedulerInterval: Long,
    // ...
) {
    @Scheduled(fixedDelayString = "\${scheduler.trade.interval:60000}")
    fun triggerAnalysis() {
        // ...
    }
}
```

**실행 흐름**:
```
[설정된 주기마다 실행]
1. FindRegistrationOutput.findAllByStatus(ACTIVE)
2. 각 registration에 대해:
   각 symbolIdentifier에 대해:
     a. FindCurrentPriceOutput.getCurrentPrice(symbolIdentifier, interval=MINUTE_1)
     b. PublishAnalyzeCommandOutput.publish(
          topic   = "command.agent.trade.analyze-strategy",
          command = AnalyzeAgentCommand(agentIdentifier, symbolIdentifier, currentPrice)
        )
```

### OrderTimeoutScheduler (LIMIT 주문 타임아웃 처리)

**설정 가능한 실행 주기 (기본: 1분)**:

```yaml
# application.yml
scheduler:
  trade:
    timeout-check-interval: 60000  # 밀리초
```

```kotlin
@Component
class OrderTimeoutScheduler(
    @Value("\${scheduler.trade.timeout-check-interval:60000}")
    private val checkInterval: Long,
    // ...
) {
    @Scheduled(fixedDelayString = "\${scheduler.trade.timeout-check-interval:60000}")
    fun cancelTimedOutOrders() {
        // ...
    }
}
```

**실행 흐름**:
```
[설정된 주기마다 실행]
1. FindOrderOutput.findTimedOutPendingOrders(now)
   └ WHERE status IN ('SUBMITTED', 'PARTIALLY_FILLED')
         AND timeout_at < now
         AND timeout_at IS NOT NULL
         AND exchange_order_id IS NOT NULL
   └ exchange_order_id IS NOT NULL: 거래소에 제출되지 않은 PENDING 주문은 제외

2. 각 order에 대해:
   CancelOrderOutput.cancel(CancelOrderCommand(
       orderIdentifier, exchangeAccountIdentifier, exchangeOrderId))
   └ Exchange Service가 취소 처리 후 OrderStatusEvent(CANCELLED) 발행
```

> LIMIT 주문이 `SUBMITTED`된 이후 `timeoutAt` 이전까지는 Trade Service가 직접 취소하지 않는다.
> 타임아웃 초과 시에만 취소 요청을 보내고, 실제 `CANCELLED` 상태 전환은 Exchange Service의 이벤트를 기다린다.

**멱등성 보장**:
- 스케줄러가 동일 주문을 중복 취소 요청할 수 있다 (이전 사이클의 Cancel이 아직 처리되지 않은 경우).
- Exchange Service의 `CancelOrderCommand` 핸들러는 이미 FILLED/CANCELLED인 주문의 취소 요청을 무시(로그만 남김)한다.

**부분 체결 후 타임아웃 취소 시나리오**:
```
1. LIMIT 주문 제출 (requestedQuantity=100)
2. 50개 부분 체결 → PARTIALLY_FILLED, executedQuantity=50
3. timeoutAt 도래 → 스케줄러가 CancelOrderCommand 발행
4. Exchange에서 나머지 50개 취소 → OrderStatusEvent(CANCELLED) 수신
5. Trade Service:
   - Order.status = CANCELLED
   - OrderFailedEvent 발행 (remainingQuantity = 100-50 = 50, signalPrice = 원래 신호가)
   - 이미 체결된 50개의 Execution 레코드는 유지
6. Agent Service: reservedCash -= 50 × signalPrice (미체결분만 점유 해제)
```

---

## 5-1. Global Account Reconciliation (계좌 대조)

### 개요

하나의 거래소 계정을 여러 Agent가 공유하므로, **계좌 전체 차원의 자산 정합성**을 검증한다.
Agent Service의 Portfolio Reconciliation이 에이전트별 가상 장부를 실계좌와 비교한다면,
Trade Service의 Global Account Reconciliation은 **모든 에이전트의 할당 자산 합계**가 실계좌를 초과하지 않는지 검증한다.

### 검증 대상

1. **계좌별 총 할당 자본 검증**:
   ```
   Σ(TradeRegistration.allocatedCapital | exchangeAccountIdentifier = X)
     ≤ Exchange Service 실계좌 총 잔고
   ```

2. **미할당 잔고 계산**:
   ```
   UnallocatedBalance = 실계좌 총 잔고 - Σ(allocatedCapital)
   ```

### 대조 프로세스

**스케줄러**: **6시간 간격** 실행 (기본). 일 1회로는 할당 초과 집행을 감지하기에 부족하다.

```kotlin
@Component
class AccountReconciliationScheduler(
    @Value("\${scheduler.trade.reconciliation-interval:21600000}")  // 기본: 6시간
    private val reconciliationInterval: Long,
    // ...
) {
    @Scheduled(fixedDelayString = "\${scheduler.trade.reconciliation-interval:21600000}")
    fun reconcileAccounts() {
        // ...
    }
}
```

### Soft Limit (안전 마진)

할당 자본의 **90%**까지만 실제 신호 발행에 사용하여, 체결가 오차·수수료 누적으로 인한 초과를 예방한다.

```
usableCapital = allocatedCapital × 0.9
```

> TradeScheduler가 AnalyzeAgentCommand를 발행하기 전에, 해당 Registration의 Agent Portfolio의
> `cash + reservedCash`가 `usableCapital`을 초과하지 않는지 사전 검증한다.
> 초과 시 해당 Registration의 트리거를 건너뛰고 경고 로그를 남긴다.

**실행 흐름**:
```
1. 모든 고유한 exchangeAccountIdentifier 추출 (ACTIVE Registration 기준)
2. 각 계정에 대해:
   a. Exchange Service에 실계좌 잔고 조회 (gRPC 또는 Kafka)
      └ ActualBalance { cash, positions }
   b. Trade Service에서 해당 계정의 총 할당 자본 합산
      └ SELECT SUM(allocated_capital) FROM trade_registration
          WHERE exchange_account_id = ? AND status = 'ACTIVE'
   c. 불일치 판단:
      - 현금 부족: actualCash < Σ(allocatedCapital) - Threshold
      - Threshold = max(10000원, Σ(allocatedCapital) × 0.01) (1%)
   d. 불일치 발생 시 후속 조치:
      - 관리자 알림 발송 (ACCOUNT_RECONCILIATION_FAILED)
      - 로그 기록 (reconciliation_log 테이블)
      - 선택: 부족분이 임계치(5%) 이상이면 해당 계정의 모든 Registration → PAUSED
3. 정상이면 다음 계정으로
```

### 불일치 원인

- 사용자가 거래소에서 직접 출금
- Exchange Service 미집계 수수료
- 체결 이벤트 누락 (Kafka Consumer 장애)
- 포트폴리오 갱신 로직 버그

### 복구 방법

1. **관리자 개입**:
   - 원인 파악 (출금 이력, 체결 이벤트 로그 확인)
   - 필요 시 `allocatedCapital` 수동 조정 (API 제공)
   - Registration 재활성화

2. **자동 보정** (선택적):
   - 차이가 미미(1% 미만)하고 실계좌 잔고가 더 클 경우
   - 미할당 잔고를 각 Registration에 비례 배분하여 조정

### DB 스키마 추가 (선택)

계좌 대조 이력을 저장하려면:

```sql
CREATE TABLE account_reconciliation_log (
    id                      UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    exchange_account_id     UUID         NOT NULL,
    actual_cash             NUMERIC(30,8) NOT NULL,
    total_allocated_capital NUMERIC(30,8) NOT NULL,
    discrepancy             NUMERIC(30,8) NOT NULL,  -- actualCash - totalAllocated
    threshold               NUMERIC(30,8) NOT NULL,
    status                  VARCHAR(20)  NOT NULL,   -- OK | WARNING | CRITICAL
    action_taken            TEXT,                     -- PAUSED_ALL | NOTIFIED_ADMIN
    reconciled_at           TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_reconciliation_account ON account_reconciliation_log
    (exchange_account_id, reconciled_at DESC);
```

### allocatedCapital 수동 조정 API

```
PUT /admin/trade-registrations/{id}/allocated-capital
Body: { newAllocatedCapital: 10000000 }
Role: ADMIN
```

---

## 6. Kafka 인터페이스

### 발행 — 신호 생성 요청

```kotlin
// 발행 토픽
// command.agent.trade.analyze-strategy

data class AnalyzeAgentCommand(
    val agentIdentifier      : UUID,
    val symbolIdentifier     : UUID,
    val currentPrice : BigDecimal,
) : CommandBaseMessage
```

### 수신 — 신호 생성 결과

```kotlin
// 구독 토픽
// reply.agent.trade.analyze-strategy

data class AnalyzeAgentReply(
    val agentIdentifier           : UUID,
    val signalIdentifier          : UUID?,        // BUY/SELL이면 Agent Service가 저장한 Signal ID, HOLD이면 null
    val strategyIdentifier : UUID,
    val symbolIdentifier          : UUID,
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
       a. TradeRegistration 조회 (agentIdentifier 기준)
       b. OrderConfig 확인 (orderType, limitOrderTimeoutMinutes)
       b-1. 중복 주문 방지:
            FindOrderOutput.findActiveByAgentAndSymbol(agentIdentifier, symbolIdentifier)
            └ PENDING / SUBMITTED / PARTIALLY_FILLED 상태 주문이 이미 존재하면 → 처리 종료 (로그)
            └ 미체결 주문이 완료되지 않은 상태에서 중복 주문을 막기 위함
       c. Order 생성 (PENDING 상태)
            signalIdentifier          = reply.signalIdentifier
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
// command.exchange.trade.submit-order

data class SubmitOrderCommand(
    val orderIdentifier           : UUID,
    val exchangeAccountIdentifier : UUID,
    val symbolIdentifier          : UUID,
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
발행 토픽      : event.trade.execution
Partition Key : signalIdentifier (동일 신호의 부분 체결 순서 보장)
메시지 구조    : ExecutionConfirmedEvent (Section 4 도메인 포트 참조)
```

> **Partition Key = signalIdentifier**: 동일 신호에서 발생한 부분 체결 이벤트가
> 같은 Kafka 파티션에 순서대로 적재되어, Agent Service가 역순 수신하지 않도록 보장한다.
> 서로 다른 신호의 체결은 독립 파티션에서 병렬 처리된다.

### 발행 — 주문 취소

```kotlin
// 발행 토픽
// command.exchange.trade.cancel-order

data class CancelOrderCommand(
    val orderIdentifier            : UUID,
    val exchangeAccountIdentifier  : UUID,        // Exchange Service가 API Key를 조회하기 위해 필요
    val exchangeOrderId    : String,
) : CommandBaseMessage
```

### 수신 — Exchange Service 주문 상태 이벤트

```kotlin
// 구독 토픽
// event.exchange.order-status

data class OrderStatusEvent(
    val orderIdentifier         : UUID,           // Trade Service Order ID
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
1. orderIdentifier로 Order 조회
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
       └ agentIdentifier, signalIdentifier, symbolIdentifier, side
       └ quantity = filledQuantity, price = filledPrice, fee = fee
       └ 발행 토픽: event.trade.execution

   FILLED:
     Execution 생성 (filledQuantity, filledPrice, fee)
     Order.executedQuantity += filledQuantity
     Order.averageExecutedPrice 재계산
     Order.status = FILLED
     PublishExecutionConfirmedOutput.publish(ExecutionConfirmedEvent)
       └ agentIdentifier, signalIdentifier, symbolIdentifier, side
       └ quantity = filledQuantity, price = filledPrice, fee = fee
       └ 발행 토픽: event.trade.execution

   CANCELLED:
     Order.status = CANCELLED
     // 보상 트랜잭션: 미체결 잔여 수량에 대한 점유 해제 이벤트 발행
     PublishExecutionConfirmedOutput.publishOrderFailed(order)
       └ agentIdentifier, signalIdentifier, symbolIdentifier, side
       └ remainingQuantity = requestedQuantity - executedQuantity
       └ 발행 토픽: event.trade.execution-failed

   REJECTED:
     Order.status = REJECTED
     // 보상 트랜잭션: 요청 전체 수량에 대한 점유 해제 이벤트 발행
     PublishExecutionConfirmedOutput.publishOrderFailed(order)
       └ agentIdentifier, signalIdentifier, symbolIdentifier, side
       └ remainingQuantity = requestedQuantity
       └ 발행 토픽: event.trade.execution-failed
     로그 기록 (reason)
```

### Event 수신 — AgentTerminatedEvent

```
구독 토픽 : trade-pilot.agentservice.agent  (eventType: "agent-terminated")
처리      : agentIdentifier에 해당하는 TradeRegistration → STOPPED 처리
```

### Event 수신 — UserWithdrawnEvent

```
구독 토픽 : trade-pilot.userservice.user  (eventType: "user-withdrawn")
처리      : userIdentifier에 속한 모든 TradeRegistration → STOPPED 처리
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
   FindOrderOutput.findAllByRegistrationIdAndActiveStatus(registrationIdentifier)
     └ status IN (PENDING, SUBMITTED, PARTIALLY_FILLED)
     └ 각 주문에 대해 CancelOrderOutput.cancel(CancelOrderCommand)
4. Notification 발행: "비상 정지 완료, {n}건 주문 취소 요청됨"
```

### 신호 처리 시 비상 정지 검증

`AnalyzeAgentReply` 수신 시 (HandleAgentReplyService):

```
1. TradeRegistration 조회 (agentIdentifier 기준)
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

## 6-2. 주문 미체결 모니터링

### 필수 메트릭

```
# 상태별 주문 수
trade_order_count{status}                           -- PENDING, SUBMITTED, PARTIALLY_FILLED 등

# 미체결 대기 시간 (SUBMITTED/PARTIALLY_FILLED 상태 주문의 경과 시간)
trade_order_pending_seconds{side, type, symbol}     -- Histogram

# 타임아웃 취소 건수
trade_order_timeout_cancelled_total{symbol}
```

### 알람 규칙

```
P1: 미체결 LIMIT 주문이 3개 이상 && 각 1시간 이상 미체결
P2: SUBMITTED 상태 주문 누적 20개 이상
P2: 타임아웃 취소 연속 5건 이상 (동일 심볼) → 전략 문제 가능성
```

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
    id                   UUID          PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id             UUID          NOT NULL UNIQUE,
    user_id              UUID          NOT NULL,
    exchange_account_id  UUID          NOT NULL,
    symbol_ids           JSONB         NOT NULL DEFAULT '[]',
    allocated_capital    NUMERIC(30,8) NOT NULL,                -- 할당 자본금 (Account Reconciliation용)
    status               VARCHAR(20)   NOT NULL DEFAULT 'ACTIVE',
    order_config         JSONB         NOT NULL DEFAULT '{}',
    emergency_stopped    BOOLEAN       NOT NULL DEFAULT FALSE,  -- 비상 정지 여부
    created_at           TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    updated_at           TIMESTAMPTZ   NOT NULL DEFAULT NOW()
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
-- 중복 주문 방지: agentIdentifier + symbolIdentifier 기준 active 주문 조회
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
| `POST` | `/trade-registrations` | USER | 실거래 등록 (agentIdentifier + exchangeAccountIdentifier + symbolIdentifiers + orderConfig) |
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
| `PUT` | `/admin/trade-registrations/{id}/allocated-capital` | ADMIN | 할당 자본 수동 조정 (Account Reconciliation 불일치 해결) |

### Order

| Method | 경로 | Role | 설명 |
|--------|------|------|------|
| `GET` | `/trade-registrations/{id}/orders` | USER | 주문 이력 (페이지네이션) |
| `GET` | `/trade-registrations/{id}/orders/{orderIdentifier}` | USER | 주문 상세 (Execution 포함) |
| `DELETE` | `/trade-registrations/{id}/orders/{orderIdentifier}` | USER | 미체결 주문 수동 취소 (SUBMITTED / PARTIALLY_FILLED만) |

### 리소스 소유권 검증 규칙

모든 USER 엔드포인트는 `X-User-Id` 헤더와 리소스 소유권 일치를 검증한다.

```kotlin
// 공통 패턴: TradeRegistration 기반 리소스 접근 시
fun validateOwnership(registrationIdentifier: UUID, userIdentifier: UUID) {
    val registration = findById(registrationIdentifier)
        ?: throw RegistrationNotFoundException()
    if (registration.userIdentifier != userIdentifier) {
        throw ForbiddenException("TR016")  // RESOURCE_NOT_OWNED
    }
}

// Order 접근 시: Registration → Order 계층 검증
fun validateOrderOwnership(registrationIdentifier: UUID, orderIdentifier: UUID, userIdentifier: UUID) {
    validateOwnership(registrationIdentifier, userIdentifier)
    val order = findById(orderIdentifier)
        ?: throw OrderNotFoundException()
    if (order.registrationIdentifier != registrationIdentifier) {
        throw ForbiddenException("TR016")
    }
}
```

> **미검증 시 위험**: 다른 사용자의 주문을 취소하거나 거래 설정을 변경할 수 있다.
> 모든 Controller에서 `@RequestHeader("X-User-Id")` 기반 소유권 검증을 수행해야 한다.

---

## 10. 에러 코드

| 코드 | 상수 | 설명 |
|------|------|------|
| `TR001` | `REGISTRATION_NOT_FOUND` | 실거래 등록 없음 |
| `TR002` | `ALREADY_REGISTERED` | 해당 Agent는 이미 실거래에 등록됨 |
| `TR003` | `REGISTRATION_STOPPED` | STOPPED 상태는 재활성화 불가 |
| `TR004` | `REGISTRATION_NOT_ACTIVE` | ACTIVE 상태가 아니어서 일시정지 불가 |
| `TR005` | `REGISTRATION_NOT_PAUSED` | PAUSED 상태가 아니어서 재활성화 불가 |
| `TR006` | `SYMBOL_IDS_EMPTY` | symbolIdentifiers는 최소 1개 이상 필요 |
| `TR007` | `CURRENT_PRICE_UNAVAILABLE` | Market Service에서 현재가 조회 실패 |
| `TR008` | `ORDER_NOT_FOUND` | 주문 없음 |
| `TR009` | `ORDER_NOT_CANCELLABLE` | 취소 불가 상태의 주문 (FILLED / CANCELLED / REJECTED) |
| `TR010` | `EXCHANGE_ACCOUNT_NOT_FOUND` | Exchange Service에서 계정 없음 |
| `TR011` | `ORDER_SUBMIT_FAILED` | Exchange Service 주문 제출 실패 |
| `TR012` | `EMERGENCY_STOP_ACTIVE` | 비상 정지 상태이므로 주문 처리 불가 |
| `TR013` | `NOT_EMERGENCY_STOPPED` | 비상 정지 상태가 아님 |
| `TR014` | `ACCOUNT_BALANCE_INSUFFICIENT` | 거래소 계정 실제 잔고 부족 (Reconciliation 실패) |
| `TR015` | `ALLOCATED_CAPITAL_INVALID` | allocatedCapital 값이 잘못됨 (음수 또는 실계좌 초과) |
| `TR016` | `RESOURCE_NOT_OWNED` | 리소스가 요청 사용자 소유가 아님 (403 Forbidden) |
