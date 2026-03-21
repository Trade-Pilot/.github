# Trade Service — 도메인 포트, 스케줄러, Account Reconciliation

> 이 문서는 `backend/trade/domain.md`에서 분할되었습니다.

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
