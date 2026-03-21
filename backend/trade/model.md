# Trade Service — 도메인 모델

> 이 문서는 `backend/trade/domain.md`에서 분할되었습니다.

---

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
