# Agent Service — 도메인 포트 및 서비스

> 이 문서는 `backend/agent/domain.md`에서 분할되었습니다.

---

## 4. 도메인 포트

```kotlin
// 신호 생성 조건만 평가 — 포트폴리오 무관
interface StrategyExecutor {
    fun requiredCandleCount(): Int          // 지표 계산에 필요한 최소 캔들 수
    fun analyze(candles: List<CandleData>): SignalConditionResult
}

data class SignalConditionResult(
    val type       : SignalType,
    val confidence : BigDecimal,
    val reason     : SignalReason,
)

// AgentRiskManager가 RiskConfig를 적용한 최종 결과
data class SignalResult(
    val symbolIdentifier          : UUID,
    val type              : SignalType,
    val confidence        : BigDecimal,
    val suggestedQuantity : BigDecimal,  // HOLD이면 0
    val reason            : SignalReason,
)

// 전략 유형에 따라 적절한 StrategyExecutor 구현체를 반환
interface StrategyExecutorFactory {
    fun create(strategy: Strategy): StrategyExecutor
}

// Market Service gRPC 어댑터용 Output Port
interface FindMarketCandleOutput {
    fun getRecentCandles(symbolIdentifier: UUID, interval: CandleInterval, limit: Int): List<CandleData>
}

interface FindSymbolMetadataOutput {
    fun getSymbol(symbolIdentifier: UUID): SymbolMetadata?
}

data class SymbolMetadata(
    val symbolIdentifier : UUID,
    val code     : String,       // KRW-BTC
    val name     : String,       // 비트코인
    val market   : MarketType,   // COIN
    val status   : SymbolStatus, // LISTED, WARNING, CAUTION, TRADING_HALTED, DELISTED
)

enum class SymbolStatus {
    LISTED, WARNING, CAUTION, TRADING_HALTED, DELISTED
}

// 백테스트 결과 저장/조회용 Output Port
interface SaveBacktestResultOutput {
    fun save(result: BacktestResult): BacktestResult
}

interface FindBacktestResultOutput {
    fun findById(backtestIdentifier: UUID): BacktestResult?
    fun findAllByAgentId(agentIdentifier: UUID): List<BacktestResult>
}

// 감사 로그 저장용 Output Port
interface SaveStrategyDecisionLogOutput {
    fun save(log: StrategyDecisionLog)
}
```

---

## 5. 도메인 서비스

### AgentRiskManager

Strategy가 반환한 `SignalConditionResult`에 Agent의 `RiskConfig`를 적용해 최종 `SignalResult`를 생성한다.
신호 생성 시점에 Portfolio의 **현금/포지션을 즉시 점유(Reserve)**하여,
다음 신호가 발생하기 전까지 동일 자산을 중복 사용하는 것을 방지한다.
실제 포트폴리오 차감·증가는 체결 확정(ExecutionConfirmedEvent) 수신 시 PortfolioUpdater가 처리한다.

#### 가용 잔고 계산

| 구분 | 계산식 |
|------|--------|
| 가용 현금 | `cash - reservedCash` |
| 가용 포지션 수량 | `position.quantity - position.reservedQuantity` |

#### 신호 평가 전 — 손절/익절 선행 검사

요청된 `symbolIdentifier`에 해당하는 보유 포지션이 있을 때 아래 조건을 확인하며,
조건 충족 시 전략 신호와 무관하게 SELL 신호로 강제 전환한다.
다른 심볼의 포지션은 해당 요청에서 `currentPrice`를 알 수 없으므로 체크하지 않는다.

- `stopLossPercent` 설정 시: `currentPrice ≤ averagePrice × (1 - stopLossPercent)` → 강제 SELL
- `takeProfitPercent` 설정 시: `currentPrice ≥ averagePrice × (1 + takeProfitPercent)` → 강제 SELL

#### 신호 처리 및 점유 로직

- **`BUY` 신호:**
  - 가용 현금(`cash - reservedCash`)을 기준으로 수량 계산
  - 해당 심볼 포지션이 **없는 경우 (신규 포지션)**: 현재 포지션 수 ≥ `maxConcurrentPositions`이면 HOLD로 전환. 미달이면 `positionSizeRatio × 가용현금 / currentPrice`로 수량 계산.
  - 해당 심볼 포지션이 **이미 있는 경우 (추가 매수)**: `maxConcurrentPositions` 체크 없이 `positionSizeRatio × 가용현금 / currentPrice`로 수량 계산.
  - 수량이 0보다 크면: `portfolio.reservedCash += suggestedQuantity × currentPrice` **(DB 즉시 저장)**
- **`SELL` 신호:**
  - 가용 수량(`position.quantity - position.reservedQuantity`)을 매도 수량으로 설정.
  - 가용 수량이 0 이하이면 HOLD로 전환.
  - 가용 수량이 0보다 크면: `position.reservedQuantity += suggestedQuantity` **(DB 즉시 저장)**
- **`HOLD` 신호:** 수량 0, 점유 없음. 그대로 반환.

> 신호 생성과 점유는 동일 트랜잭션에서 처리한다 (`@Transactional`).
> Portfolio/Position에 대해 `@Lock(PESSIMISTIC_WRITE)` 적용.

#### Lock 범위 명확화

동시 다중 신호(예: BTC + ETH 동시 수신) 시 `reservedCash` 초과를 방지하기 위해
Lock 범위를 명확히 한다.

```kotlin
@Transactional
fun analyzeAgent(command: AnalyzeAgentCommand): SignalResult {
    // 1. Lock 시작: Portfolio 조회 (PESSIMISTIC_WRITE)
    val portfolio = portfolioRepository.findByAgentIdForUpdate(command.agentIdentifier)

    // 2. 손절/익절 선행 검사 + 신호 생성 (Lock 유지)
    val condition = executor.analyze(candles)
    val result = agentRiskManager.applySizing(condition, portfolio, riskConfig, currentPrice)

    // 3. 점유 반영 및 DB 저장 (Lock 유지)
    portfolioRepository.save(portfolio)
    signalRepository.save(signal)

    // 4. Lock 종료: 트랜잭션 커밋
    return result
}
// 5. Kafka Reply 발행은 트랜잭션 커밋 후 (Lock 외부)
```

> Lock은 Portfolio 조회 시점부터 트랜잭션 커밋까지 유지된다.
> 동시에 수신된 다른 심볼의 신호는 Lock 해제 후 순차 처리되므로 가용 현금이 정확하다.

### PortfolioUpdater

VirtualTrade / Trade Service로부터 수신한 **`ExecutionConfirmedEvent`(체결 확정 이벤트)** 를 Portfolio에 반영하고, `PortfolioHistory`(SIGNAL 타입)를 기록한다.
또한, 주문 실패/취소 시 **점유된 자산을 해제(Rollback)**하는 보상 트랜잭션을 처리한다.

#### 1) 체결 반영 (Normal Flow)

각 `ExecutionConfirmedEvent`는 **이번 체결분(부분 또는 전체)**만을 나타낸다.
부분 체결이 여러 번 발생하면 체결 건마다 독립적으로 아래 로직을 실행한다.

- **`BUY` 체결:**
  1. `reservedCash -= quantity × signalPrice` (이번 체결분만큼 점유 해제)
  2. `cash -= price × quantity + fee` (실제 현금 차감 — 체결가 기준)
  3. 포지션이 없으면 신규 생성, 이미 있으면 수량을 더하고 평균 단가 재계산.
- **`SELL` 체결:**
  1. `position.reservedQuantity -= quantity` (이번 체결분만큼 점유 해제)
  2. `position.quantity -= quantity` (실제 수량 차감), `cash += price × quantity - fee`, `realizedPnl` 갱신.

> **핵심**: 점유 해제 금액은 `quantity × signalPrice`(신호 당시 가격)로 계산한다.
> 실제 체결가(`price`)와의 차이는 `cash` 차감/증가에서 반영되므로, 점유 해제는 항상 신호 당시 기준이다.

#### 2) 점유 해제 (Compensation/Rollback Flow)

주문이 거래소에서 거절(`REJECTED`)되거나 취소(`CANCELLED`)된 경우,
**`OrderFailedEvent`**를 수신하여 **미체결 잔여분에 대해서만** 점유를 해제한다.

```
OrderFailedEvent.remainingQuantity = 원래 신호 수량(suggestedQuantity) - 이미 체결된 누적 수량
```

- **`BUY` 실패:** `reservedCash -= remainingQuantity × signalPrice`
- **`SELL` 실패:** `position.reservedQuantity -= remainingQuantity`
- **주의**: 실제 자산(`cash`, `quantity`)은 건드리지 않고 점유(`reserved`) 필드만 차감한다.

> **부분 체결 후 취소 시나리오 예시:**
> 1. BUY 신호: suggestedQuantity=100, signalPrice=1,000 → reservedCash += 100,000
> 2. 부분 체결 50개: ExecutionConfirmedEvent(quantity=50) → reservedCash -= 50,000, cash -= 50×체결가+fee
> 3. 타임아웃 취소: OrderFailedEvent(remainingQuantity=50) → reservedCash -= 50,000
> 4. 최종: reservedCash 원래대로 복원 완료

> **Trade Service 책임**: `OrderFailedEvent.remainingQuantity`는
> `requestedQuantity - executedQuantity`로 계산하여 발행한다 (Section 6 참조).

---

## 5-1. Portfolio Reconciliation (데이터 대조)

### 개요
`Agent Service`의 포트폴리오 데이터와 `Exchange Service`의 실제 잔고를 비교하여 데이터 정합성을 검증한다.

### 대조 프로세스
1. **스케줄러**: 매일 자정(KST 00:00) 모든 `ACTIVE` 에이전트에 대해 실행.
2. **잔고 조회**: `Exchange Service`에 해당 계좌의 현재 잔고(`actualCash`, `actualPositions`) 요청.
3. **불일치 판단**:
   - **현금 오차**: `|cash - actualCash| > max(1000원, cash × 0.001)`
     - 절대값 1000원 또는 0.1% 중 큰 값 초과 시 불일치
   - **수량 오차**: `|position.quantity - actualQuantity| > quantity × 0.0001`
     - 0.01% (최소 거래 단위 고려)
4. **후속 조치**:
   - **불일치 발생 시**:
     - `PortfolioHistory(DAILY)`에 오차 금액(`discrepancy`) 기록.
     - 관리자 알림(Discord/Slack) 발송: `PORTFOLIO_RECONCILIATION_FAILED`
   - **자동 보정 조건** (선택적):
     - 현금 차이가 100원 미만이면 `actualCash`로 자동 보정
     - 수량 차이가 0.0001개 미만이면 `actualQuantity`로 자동 보정
     - 보정 시 `PortfolioHistory`에 `reconciliationType=AUTO_CORRECTED` 기록

---

## 5-2. Strategy Decision Logging (감사 로그)

신호 생성 요청(`AnalyzeAgentCommand`)이 처리될 때마다, 신호 결과(HOLD 포함)와 상관없이 **평가 시점의 모든 상태**를 기록한다.

- **목적**: "왜 이 시점에 매수 신호가 발생하지 않았는가?" 또는 "왜 잘못된 신호가 나갔는가?"를 사후 분석하기 위함.
- **기록 대상**:
  - `indicatorValues`: 전략 평가에 사용된 모든 기술적 지표의 당시 수치.
  - `signalType`: 최종 결정된 신호 (HOLD도 포함하여 기록).
  - `currentPrice`: 평가 당시의 가격.
- **저장소**: 메인 DB의 `strategy_decision_log` 테이블에 저장하며, 분석 성능을 위해 일정 기간(예: 3개월) 경과 후 빅데이터 저장소(BigQuery 등)로 오프로드하거나 삭제한다.

---

## 5-3. PortfolioHistoryRecorder (Daily 스케줄러)

매일 자정 ACTIVE 상태의 모든 Agent에 대해 `DAILY` 타입 스냅샷을 기록한다.

현재가 조회는 `FindMarketCandleOutput.getRecentCandles(limit=1)`로 가장 최근 캔들의 **종가(close)를 현재가로 대체**한다.
별도의 현재가 RPC를 추가하지 않고 기존 인터페이스를 재사용한다.

- 조회 실패 시 해당 포지션은 `averagePrice`로 대체하고 로그를 남긴다.
- 보유 포지션이 없더라도 현금 상태를 기록한다 (수익률 시계열 공백 방지).
