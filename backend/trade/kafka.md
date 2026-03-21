# Trade Service — Kafka 인터페이스

> 이 문서는 `backend/trade/domain.md`에서 분할되었습니다.

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
