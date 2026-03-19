# Agent Service — Domain 설계

## 1. Bounded Context

Agent Service는 **전략 기반 매매 신호 생성과 에이전트별 자산 관리**를 담당한다.

```
Agent Service 책임
├── Strategy   신호 생성 조건 정의 (어떤 조건에서 BUY/SELL/HOLD인가)
├── Agent      전략 참조 + 포지션 사이징 + 리스크 관리 (어떻게 자산을 굴릴 것인가)
└── Portfolio  에이전트별 가상 자산 현황 (현금 + 포지션)
```

### Strategy와 Agent의 책임 분리

| | Strategy | Agent |
|---|---|---|
| **관심사** | 신호 생성 조건 | 자산 관리 방식 |
| **포트폴리오 의존** | ❌ 없음 | ✅ 있음 |
| **재사용** | 여러 Agent가 동일 Strategy 참조 가능 | 1 Agent : 1 Strategy |
| **포지션 사이징** | ❌ 결정 안 함 | ✅ RiskConfig 기반 결정 |

이 분리의 핵심은 **Strategy가 포트폴리오를 모른다**는 것이다.
Strategy는 캔들 데이터만 보고 신호 조건을 평가하는 순수 함수에 가깝다.
"얼마를 살 것인가"는 Agent의 `RiskConfig` 기반으로 결정된다.

### 기술적 지표의 위치

기술적 지표(MA, RSI 등)는 **Agent Service 인프라 레이어(`infrastructure/indicator`)** 에 둔다.
Market Service의 bounded context는 원시 데이터 수집·저장이다.
지표 종류와 파라미터는 전략에 종속되므로, Market이 미리 계산하려면 Agent의 전략 파라미터를 알아야 하는 경계 침범이 발생한다.
**도메인 레이어는 지표 계산에 의존하지 않는다.**

---

## 2. 헥사고날 아키텍처 레이어

```
domain/
  model/         Strategy, Agent, Portfolio, Position, Signal
                 BacktestResult, PortfolioHistory, StrategyDecisionLog
                 SignalConditionResult, SignalResult, RiskConfig ...
  port/
    in/          AnalyzeAgentUseCase, BacktestStrategyUseCase,
                 CreateStrategyUseCase, CreateAgentUseCase,
                 ActivateAgentUseCase ...
                 HandleExecutionUseCase   (ExecutionConfirmedEvent 수신 → Portfolio 갱신)
    out/         FindStrategyOutput, SaveStrategyOutput
                 FindAgentOutput, SaveAgentOutput
                 FindPortfolioOutput, SavePortfolioOutput
                 FindPortfolioHistoryOutput, SavePortfolioHistoryOutput
                 SaveSignalOutput, FindSignalOutput
                 SaveStrategyDecisionLogOutput
                 FindMarketCandleOutput, StrategyExecutorFactory
                 SaveBacktestResultOutput, FindBacktestResultOutput
                 PublishAgentTerminatedOutput
                 PublishAnalyzeReplyOutput

application/
  usecase/       AnalyzeAgentService      (implements AnalyzeAgentUseCase)
                 BacktestStrategyService  (implements BacktestStrategyUseCase)
                 HandleExecutionService   (implements HandleExecutionUseCase)
                 CreateStrategyService, CreateAgentService ...

infrastructure/
  kafka/         AnalyzeAgentCommandConsumer
                 AnalyzeAgentReplyProducer        (implements PublishAnalyzeReplyOutput)
                 ExecutionConfirmedEventConsumer  (event.virtual-trade.execution, event.trade.execution 구독)
                 AgentTerminatedEventProducer     (implements PublishAgentTerminatedOutput)
                 UserWithdrawnEventConsumer       (trade-pilot.userservice.user 구독)
  grpc/          MarketCandleGrpcAdapter       (implements FindMarketCandleOutput)
                 AgentGrpcServer         (BacktestStrategy gRPC 서버 — generated from service Agent)
  persistence/   StrategyJpaAdapter      (implements FindStrategyOutput, SaveStrategyOutput)
                 AgentJpaAdapter         (implements FindAgentOutput, SaveAgentOutput)
                 PortfolioJpaAdapter     (implements FindPortfolioOutput, SavePortfolioOutput,
                                          FindPortfolioHistoryOutput, SavePortfolioHistoryOutput)
                 SignalJpaAdapter        (implements SaveSignalOutput, FindSignalOutput)
                 StrategyDecisionLogJpaAdapter (implements SaveStrategyDecisionLogOutput)
                 BacktestResultJpaAdapter (implements SaveBacktestResultOutput, FindBacktestResultOutput)
  indicator/     TechnicalIndicators     (MA, EMA, RSI, MACD, Bollinger, Stochastic)
  strategy/      MovingAverageCrossoverExecutor, RsiExecutor, BollingerBreakoutExecutor
                 AiStrategyAdapter       (미래 확장)
                 StrategyExecutorFactoryImpl
```

---

## 3. 도메인 모델

### Aggregate 구성

```
Strategy (Aggregate Root)
├── strategyId   : UUID
├── userId       : UUID
├── name         : String
├── description  : String?
├── type         : StrategyType        -- MANUAL | AI
├── market       : MarketType          -- COIN
├── status       : StrategyStatus
├── parameters   : StrategyParameters  -- JSONB (open interface)
├── createdAt    : OffsetDateTime
└── updatedAt    : OffsetDateTime

──────────────────────────────────────────

Agent (Aggregate Root)
├── agentId        : UUID
├── userId         : UUID
├── name           : String
├── description    : String?
├── strategyId     : UUID              -- Strategy 참조 (DEPRECATED 불가)
├── status         : AgentStatus
├── riskConfig     : RiskConfig        -- JSONB
├── initialCapital : BigDecimal        -- 포트폴리오/백테스팅 초기 자본금
├── createdAt      : OffsetDateTime
└── updatedAt      : OffsetDateTime

Signal (Entity — Agent 소속)
├── signalId          : UUID
├── agentId           : UUID
├── strategyId        : UUID           -- 신호 생성 시점의 전략 추적용
├── symbolId          : UUID
├── type              : SignalType
├── confidence        : BigDecimal     -- 0.0 ~ 1.0
├── price             : BigDecimal
├── suggestedQuantity : BigDecimal     -- AgentRiskManager가 산출
├── reason            : SignalReason   -- JSONB
└── createdAt         : OffsetDateTime

──────────────────────────────────────────

Portfolio (Aggregate Root)
├── portfolioId     : UUID
├── agentId         : UUID             -- 1 Agent : 1 Portfolio (초기 자본금은 Agent.initialCapital 참조)
├── userId          : UUID
├── cash            : BigDecimal       -- 실제 보유 현금 (체결 완료 기준)
├── reservedCash    : BigDecimal       -- BUY 신호 발생 시 점유된 현금 (체결 전)
├── realizedPnl     : BigDecimal       -- 누적 실현손익 (매도 시 갱신)
├── createdAt       : OffsetDateTime
└── updatedAt       : OffsetDateTime

Position (Entity — Portfolio 소속)
├── positionId        : UUID
├── portfolioId       : UUID
├── symbolId          : UUID
├── quantity          : BigDecimal       -- 실제 보유 수량 (체결 완료 기준)
├── reservedQuantity  : BigDecimal       -- SELL 신호 발생 시 점유된 수량 (체결 전)
├── averagePrice      : BigDecimal       -- 평균 매입 단가
├── createdAt         : OffsetDateTime
└── updatedAt         : OffsetDateTime

BacktestResult (Entity — Agent 소속)
├── backtestId       : UUID
├── agentId          : UUID
├── symbolId         : UUID
├── candleFrom       : OffsetDateTime  -- 백테스팅 캔들 시작 시점
├── candleTo         : OffsetDateTime  -- 백테스팅 캔들 종료 시점
├── initialCapital   : BigDecimal
├── finalValue       : BigDecimal      -- cash + 마지막 시점 포지션 평가액
├── realizedPnl      : BigDecimal      -- 청산된 포지션의 누적 실현손익
├── unrealizedPnl    : BigDecimal      -- 마지막 시점 보유 포지션 미실현 손익
├── totalSignals     : Int             -- BUY/SELL 신호만 카운트 (HOLD 제외)
├── signalSnapshots  : JSONB           -- 각 신호 시점의 포트폴리오 상태
└── createdAt         : OffsetDateTime

──────────────────────────────────────────

StrategyDecisionLog (Entity — 감사 분석용)
├── logId             : UUID
├── agentId           : UUID
├── strategyId        : UUID
├── symbolId          : UUID
├── signalType        : SignalType        -- BUY | SELL | HOLD
├── currentPrice      : BigDecimal
├── evaluationStatus  : EvaluationStatus  -- SUCCESS | ERROR
├── indicatorValues   : JSONB             -- 평가 시점의 지표 수치 (예: {rsi: 28.4, ma20: 54000})
├── evaluationReason  : String?           -- 평가 실패 시 에러 메시지
└── createdAt         : OffsetDateTime

──────────────────────────────────────────

PortfolioHistory (Entity — Portfolio 소속)
├── historyId          : UUID
├── portfolioId        : UUID
├── snapshotType       : SnapshotType  -- SIGNAL | DAILY
├── cash               : BigDecimal
├── totalValue         : BigDecimal    -- cash + 포지션 평가액
├── realizedPnl        : BigDecimal    -- 이 시점까지의 누적 실현손익
├── unrealizedPnl      : BigDecimal    -- 보유 포지션 미실현 손익
├── positionsSnapshot  : JSONB         -- 시점 포지션 상태 (불변 기록)
├── triggerSignalId    : UUID?         -- SIGNAL 타입일 때 트리거 신호 ID
└── recordedAt         : OffsetDateTime
```

### Value Objects

```kotlin
enum class StrategyType   { MANUAL, AI }
enum class MarketType     { COIN }
enum class SignalType     { BUY, SELL, HOLD }
enum class EvaluationStatus { SUCCESS, ERROR }

enum class SnapshotType {
    SIGNAL,  // BUY/SELL 신호 실행 직후 자동 기록
    DAILY,   // 매일 자정 스케줄러 기록 (보유 포지션 현재가 조회 필요)
}

enum class StrategyStatus {
    DRAFT,       // 작성 중, 파라미터 수정 가능
    VALIDATED,   // 검증됨, 실거래 Agent 할당 가능
    DEPRECATED   // 신규 Agent 할당 불가 (기존 Active Agent는 계속 사용 가능)
}

enum class AgentStatus {
    INACTIVE,    // 생성됨, 미활성
    ACTIVE,      // 신호 생성 중
    PAUSED,      // 일시 중지
    TERMINATED   // 종료, 복구 불가
}

data class RiskConfig(
    val positionSizeRatio     : BigDecimal,  // 신호당 현금 투자 비율 (예: 0.5 = 50%)
    val maxConcurrentPositions: Int,          // 최대 동시 보유 포지션 수
    val stopLossPercent       : BigDecimal?,  // 손절 기준, null이면 미사용
    val takeProfitPercent     : BigDecimal?,  // 익절 기준, null이면 미사용
)

data class SignalReason(
    val indicator : String,           // 예: "MA_CROSSOVER", "RSI", "AI_MODEL"
    val details   : Map<String, Any>, // 지표 수치, 근거 등
)
```

### StrategyParameters

`sealed class` 대신 **open interface**로 설계해 AI 등 미래 전략 타입을 제약 없이 추가한다.
JSONB로 저장하고 역직렬화 시 `strategyKind` 필드를 기준으로 분기한다.

```kotlin
interface StrategyParameters {
    val strategyKind: String     // 역직렬화 식별자, 예: "MA_CROSSOVER"
    val interval    : CandleInterval  // 분석에 사용할 캔들 주기, 예: MINUTE_15, HOUR_1
}

// MANUAL
data class MovingAverageCrossoverParameters(val shortPeriod: Int, val longPeriod: Int, override val interval: CandleInterval, ...) : StrategyParameters
data class RsiParameters(val period: Int, val oversoldThreshold: Int, val overboughtThreshold: Int, override val interval: CandleInterval, ...) : StrategyParameters
data class BollingerBreakoutParameters(val period: Int, val multiplier: Double, override val interval: CandleInterval, ...) : StrategyParameters

// AI (미래 확장)
data class AiModelParameters(val modelId: String, val modelVersion: String, val featureConfig: Map<String, Any>, ...) : StrategyParameters
```

### 생명주기

**Strategy**
```
DRAFT ──validate()──▶ VALIDATED ──deprecate()──▶ DEPRECATED
  └ 파라미터 수정 가능     └ 실거래 Agent 할당 가능      └ 신규 할당 불가
  └ 가상거래 Agent
    할당 가능
```

Agent 생성 시 전략 할당 조건: DEPRECATED 전략은 할당 불가. DRAFT / VALIDATED는 모두 허용.

신호 요청 시 허용 조건 (Kafka `AnalyzeAgentCommand` 기준):

| Strategy 상태 | VirtualTrade | Trade (실거래) |
|---|---|---|
| DRAFT | ✅ 허용 | ❌ 불가 (A003) |
| VALIDATED | ✅ 허용 | ✅ 허용 |
| DEPRECATED | ✅ 허용 (기존 Active Agent) | ✅ 허용 (기존 Active Agent) |

> Simulation은 Kafka 토픽을 사용하지 않고 gRPC `BacktestStrategy`로 직접 통신한다. Section 7 참조.

> 구독 토픽이 `command.agent.trade.analyze-strategy`인 요청은 실거래이므로
> Agent Service는 전략 상태가 `VALIDATED`인지 검증한다. DRAFT면 A003 에러를 반환한다.

**Agent**
```
INACTIVE ──activate()──▶ ACTIVE ◀──resume()──┐
                           │                  │
                         pause()              │
                           ▼                  │
                         PAUSED ─────────────┘
                           │
                       terminate()
                           ▼
                       TERMINATED
```

> Agent를 `activate()`할 때 Portfolio가 초기화된다.
> `ACTIVE` 상태의 Agent만 Kafka AnalyzeAgent 요청을 처리한다.

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
    val symbolId          : UUID,
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
    fun getRecentCandles(symbolId: UUID, interval: CandleInterval, limit: Int): List<CandleData>
}

// 백테스트 결과 저장/조회용 Output Port
interface SaveBacktestResultOutput {
    fun save(result: BacktestResult): BacktestResult
}

interface FindBacktestResultOutput {
    fun findById(backtestId: UUID): BacktestResult?
    fun findAllByAgentId(agentId: UUID): List<BacktestResult>
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

요청된 `symbolId`에 해당하는 보유 포지션이 있을 때 아래 조건을 확인하며,
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

### PortfolioUpdater

VirtualTrade / Trade Service로부터 수신한 **`ExecutionConfirmedEvent`(체결 확정 이벤트)** 를 Portfolio에 반영하고, `PortfolioHistory`(SIGNAL 타입)를 기록한다.
또한, 주문 실패/취소 시 **점유된 자산을 해제(Rollback)**하는 보상 트랜잭션을 처리한다.

#### 1) 체결 반영 (Normal Flow)
- **`BUY` 체결:**
  1. `reservedCash -= suggestedQuantity × signalPrice` (점유 해제)
  2. `cash -= price × quantity + fee` (실제 현금 차감)
  3. 포지션이 없으면 신규 생성, 이미 있으면 수량을 더하고 평균 단가 재계산.
- **`SELL` 체결:**
  1. `position.reservedQuantity -= quantity` (점유 해제)
  2. `position.quantity -= quantity` (실제 수량 차감), `cash += price × quantity - fee`, `realizedPnl` 갱신.

#### 2) 점유 해제 (Compensation/Rollback Flow)
주문이 거래소에서 거절(`REJECTED`)되거나 사용자에 의해 취소(`CANCELLED`)된 경우, `ExecutionConfirmedEvent`와 유사한 규격의 **`OrderFailedEvent`**를 수신하여 점유를 해제한다.

- **`BUY` 실패:** `reservedCash -= suggestedQuantity × signalPrice`
- **`SELL` 실패:** `position.reservedQuantity -= suggestedQuantity`
- **주의**: 실제 자산(`cash`, `quantity`)은 건드리지 않고 점유(`reserved`) 필드만 차감한다.

---

## 5-1. Portfolio Reconciliation (데이터 대조)

### 개요
`Agent Service`의 포트폴리오 데이터와 `Exchange Service`의 실제 잔고를 비교하여 데이터 정합성을 검증한다.

### 대조 프로세스
1. **스케줄러**: 매일 자정 모든 `ACTIVE` 에이전트에 대해 실행.
2. **잔고 조회**: `Exchange Service`에 해당 계좌의 현재 잔고(`actualCash`, `actualPositions`) 요청.
3. **불일치 판단**:
   - `|cash - actualCash| > Threshold` (오차 범위 밖)
   - `|position.quantity - actualQuantity| > Threshold`
4. **후속 조치**:
   - 불일치 발생 시 `PortfolioHistory(DAILY)`에 오차 금액 기록.
   - 관리자 알림(Discord/Slack) 발송.
   - (옵션) 차이가 미세할 경우 `actual` 데이터로 자동 보정.

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

---

## 6. Kafka 인터페이스

### Command 수신 — 신호 생성 요청

VirtualTrade / Trade가 `agentId`를 기준으로 요청한다.
Agent Service가 내부에서 전략을 조회하고 신호를 생성한다.

```kotlin
// 구독 토픽
// - command.agent.virtual-trade.analyze-strategy
// - command.agent.trade.analyze-strategy

data class AnalyzeAgentCommand(
    val agentId      : UUID,
    val symbolId     : UUID,
    val currentPrice : BigDecimal,
) : CommandBaseMessage

// 발행 토픽 — Envelope.callback으로 동적 결정
data class AnalyzeAgentReply(
    val agentId           : UUID,
    val signalId          : UUID?,        -- BUY/SELL이면 저장된 Signal ID, HOLD이면 null
    val strategyId        : UUID,
    val symbolId          : UUID,
    val signalType        : SignalType,
    val confidence        : BigDecimal,
    val suggestedQuantity : BigDecimal,
    val price             : BigDecimal,
    val reason            : Map<String, Any>,
) : CommandBaseMessage
```

**처리 흐름:**
```
1.  AnalyzeAgentCommand 수신 (멱등성 확인)
2.  Agent 조회 (Redis 캐시 → DB), ACTIVE 검증
3.  Strategy 조회 (Redis 캐시 → DB)
    └ 토픽이 trade.analyze-strategy이면 VALIDATED 상태 검증 (DRAFT면 A003)
4.  StrategyExecutorFactory.create(strategy) → executor
5.  FindMarketCandleOutput.getRecentCandles(symbolId, strategy.parameters.interval, executor.requiredCandleCount())
6.  executor.analyze(candles) → SignalConditionResult
7.  StrategyDecisionLog 생성 및 비동기 저장 (도메인 이벤트 발행 또는 직접 호출)
8.  Portfolio 조회 + @Lock(PESSIMISTIC_WRITE) (가용 현금/포지션 정확히 읽기 위해 락 필요)
9.  AgentRiskManager.applySizing(symbolId, condition, portfolio, riskConfig, currentPrice) → SignalResult
    └ BUY: portfolio.reservedCash += suggestedQuantity × currentPrice (즉시 점유)
    └ SELL: position.reservedQuantity += suggestedQuantity (즉시 점유)
10. BUY/SELL 신호만 Signal DB 저장 (HOLD는 저장 안 함)
11. Portfolio/Position 점유 상태 DB 저장 (9번의 reservation 반영)
12. AnalyzeAgentReply 발행 (HOLD 포함 모든 신호 유형 발행)

> 신호 생성과 점유(9~11번)는 동일 트랜잭션에서 처리한다.
> 실제 포트폴리오 반영(cash 차감·증가, position 갱신)은
> VirtualTrade / Trade Service의 체결 완료 후 ExecutionConfirmedEvent를 수신할 때
> PortfolioUpdater가 처리한다. (Section 6 아래 참조)
```

### Event 수신 — ExecutionConfirmedEvent

VirtualTrade / Trade Service가 체결을 완료한 후 발행하는 이벤트다.
Agent Service는 이 이벤트를 기준으로 Portfolio를 갱신한다.

```kotlin
// 구독 토픽
// - event.virtual-trade.execution  (VirtualTrade Service 발행 — 가상 체결)
// - event.trade.execution          (Trade Service 발행 — 실제 체결)

data class ExecutionConfirmedEvent(
    val agentId    : UUID,
    val signalId   : UUID,           // 이 체결을 유발한 Signal ID
    val symbolId   : UUID,
    val side       : OrderSide,      // BUY | SELL
    val quantity   : BigDecimal,     // 체결 수량
    val price      : BigDecimal,     // 실제 체결가
    val fee        : BigDecimal,     // 수수료 (가상 체결이면 0)
    val executedAt : OffsetDateTime,
) : EventBaseMessage
```

**처리 흐름:**
```
1. Portfolio 조회 (agentId 기준)
2. PortfolioUpdater.apply(portfolio, event)
   └ BUY : 현금 차감 (price × quantity + fee), 포지션 갱신 (평균단가 재계산)
   └ SELL: 포지션 청산, 현금 증가 (price × quantity - fee), realizedPnl 갱신
3. Portfolio DB 저장
4. PortfolioHistory(SIGNAL 타입, triggerSignalId = event.signalId) 기록
```

> 부분 체결(Trade의 PARTIALLY_FILLED)이 발생하면 체결 건별로 이벤트가 도착한다.
> 각 이벤트마다 위 흐름을 독립적으로 처리한다.

### Event 발행 — AgentTerminatedEvent

Agent가 TERMINATED 상태로 전환될 때 발행한다.
VirtualTrade Service / Trade Service가 구독해 관련 Registration을 STOPPED 처리한다.

```
발행 토픽 : trade-pilot.agentservice.agent  (eventType: "agent-terminated")
트리거    : Agent.status → TERMINATED (사용자 요청 또는 UserWithdrawnEvent 처리)
페이로드  : { agentId, userId }
```

### Event 수신 — UserWithdrawnEvent

```
구독 토픽 : trade-pilot.userservice.user  (eventType: "user-withdrawn")
처리      : userId에 속한 모든 Agent → TERMINATED → AgentTerminatedEvent 발행
보존      : Portfolio / Signal / Position (감사 목적)
```

---

## 7. gRPC 인터페이스

### Simulation → Agent (백테스팅)

Simulation은 Agent 단위로 백테스팅을 수행한다.
Agent Service는 Agent의 Strategy + RiskConfig를 기반으로 신호 조건 평가와 포지션 사이징을 모두 처리한다.
Agent의 `initialCapital`으로 임시 포트폴리오를 인메모리로 관리하며, 각 신호 시점의 포트폴리오 상태를 스트리밍으로 반환한다.
백테스팅 완료 후 결과 요약은 `BacktestResult`로 DB에 저장한다. 실제 Portfolio / PortfolioHistory에는 기록하지 않는다.
Agent 상태와 무관하게 백테스팅 요청을 수락한다.

```protobuf
service Agent {
  rpc BacktestStrategy(BacktestRequest) returns (stream BacktestSignalResponse);
}

message BacktestRequest {
  string           agent_id  = 1;
  string           symbol_id = 2;
  repeated CandleProto candles = 3;
}

message BacktestSignalResponse {
  string signal_type        = 1;  // BUY | SELL | HOLD
  double confidence         = 2;
  string reason_json        = 3;
  string candle_open_time   = 4;  // ISO-8601
  double suggested_quantity = 5;
  double cash_after         = 6;  // 신호 반영 후 잔여 현금
  double total_value_after  = 7;  // 신호 반영 후 총자산 평가액
}
```

### Agent → Market (캔들 조회)

Agent Service는 Market Service의 proto 계약을 **소비(consume)** 한다.
아래 정의는 Market Service가 제공하는 proto 파일의 일부이며, Agent Service는 빌드 시 생성된 클라이언트 스텁을 통해 호출한다.

```
Market Service proto (market-service.proto)
────────────────────────────────────────────
service MarketCandle {
  rpc GetRecentCandles(GetRecentCandlesRequest) returns (GetRecentCandlesResponse);
}

message GetRecentCandlesRequest {
  string symbol_id = 1;
  string interval  = 2;
  int32  limit     = 3;
}
```

Agent Service 인프라 레이어의 `MarketCandleGrpcAdapter`가 생성된 스텁(`MarketCandleGrpc.MarketCandleBlockingStub`)을 감싸고, 도메인 Output Port `FindMarketCandleOutput`을 구현한다.

```
FindMarketCandleOutput (domain port)
        ▲
        │ implements
MarketCandleGrpcAdapter (infrastructure/grpc)
        │ uses generated stub
        ▼
MarketCandleGrpc.MarketCandleBlockingStub  ←  Market Service gRPC Server
```

---

## 8. 캐시 전략 (Redis)

| 캐시 키 | 값 | TTL | 갱신 조건 |
|---------|-----|-----|----------|
| `strategy:{strategyId}` | `StrategyDto` (JSON) | 10분 | 수정/상태 변경 시 evict |
| `agent:{agentId}` | `AgentDto` (JSON) | 10분 | 수정/상태 변경 시 evict |

---

## 9. DB 스키마

```sql
CREATE TABLE strategy (
    id          UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID         NOT NULL,
    name        VARCHAR(100) NOT NULL,
    description TEXT,
    type        VARCHAR(20)  NOT NULL DEFAULT 'MANUAL',
    market      VARCHAR(20)  NOT NULL DEFAULT 'COIN',
    status      VARCHAR(20)  NOT NULL DEFAULT 'DRAFT',
    parameters  JSONB        NOT NULL DEFAULT '{}',
    created_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_strategy_user   ON strategy (user_id);
CREATE INDEX idx_strategy_status ON strategy (status);
CREATE INDEX idx_strategy_params ON strategy USING GIN (parameters);

CREATE TABLE agent (
    id          UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID         NOT NULL,
    name        VARCHAR(100) NOT NULL,
    description TEXT,
    strategy_id     UUID          NOT NULL REFERENCES strategy(id),
    status          VARCHAR(20)   NOT NULL DEFAULT 'INACTIVE',
    risk_config     JSONB         NOT NULL DEFAULT '{}',
    initial_capital NUMERIC(30,8) NOT NULL,
    created_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_agent_user     ON agent (user_id);
CREATE INDEX idx_agent_strategy ON agent (strategy_id);
CREATE INDEX idx_agent_status   ON agent (status);

CREATE TABLE signal (
    id                 UUID          PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id           UUID          NOT NULL REFERENCES agent(id),
    strategy_id        UUID          NOT NULL REFERENCES strategy(id),
    symbol_id          UUID          NOT NULL,
    type               VARCHAR(10)   NOT NULL,
    confidence         NUMERIC(5,4)  NOT NULL,
    price              NUMERIC(30,8) NOT NULL,
    suggested_quantity NUMERIC(30,8) NOT NULL,
    reason             JSONB         NOT NULL DEFAULT '{}',
    created_at         TIMESTAMPTZ   NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_signal_agent    ON signal (agent_id,    created_at DESC);
CREATE INDEX idx_signal_strategy ON signal (strategy_id, created_at DESC);

CREATE TABLE portfolio (
    id              UUID          PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id        UUID          NOT NULL UNIQUE REFERENCES agent(id),
    user_id         UUID          NOT NULL,
    cash            NUMERIC(30,8) NOT NULL,          -- 실제 보유 현금 (체결 완료 기준)
    reserved_cash   NUMERIC(30,8) NOT NULL DEFAULT 0, -- BUY 신호 점유 현금 (체결 전)
    realized_pnl    NUMERIC(30,8) NOT NULL DEFAULT 0, -- 누적 실현손익
    created_at      TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ   NOT NULL DEFAULT NOW()
);

CREATE TABLE portfolio_history (
    id                  UUID          PRIMARY KEY DEFAULT gen_random_uuid(),
    portfolio_id        UUID          NOT NULL REFERENCES portfolio(id),
    snapshot_type       VARCHAR(10)   NOT NULL,          -- SIGNAL | DAILY
    cash                NUMERIC(30,8) NOT NULL,
    total_value         NUMERIC(30,8) NOT NULL,          -- cash + 포지션 평가액
    realized_pnl        NUMERIC(30,8) NOT NULL,          -- 이 시점까지 누적 실현손익
    unrealized_pnl      NUMERIC(30,8) NOT NULL,          -- 보유 포지션 미실현 손익
    positions_snapshot  JSONB         NOT NULL,          -- 시점 포지션 상태 (불변)
    trigger_signal_id   UUID,                            -- SIGNAL 타입 전용
    recorded_at         TIMESTAMPTZ   NOT NULL DEFAULT NOW()
);

-- 시계열 조회 최적화 (포트폴리오별 시간순)
CREATE INDEX idx_portfolio_history_portfolio ON portfolio_history (portfolio_id, recorded_at DESC);
-- 일별 중복 방지 (DAILY 타입은 하루 1건)
CREATE UNIQUE INDEX idx_portfolio_history_daily
    ON portfolio_history (portfolio_id, DATE(recorded_at))
    WHERE snapshot_type = 'DAILY';

CREATE TABLE position (
    id                UUID          PRIMARY KEY DEFAULT gen_random_uuid(),
    portfolio_id      UUID          NOT NULL REFERENCES portfolio(id),
    symbol_id         UUID          NOT NULL,
    quantity          NUMERIC(30,8) NOT NULL,           -- 실제 보유 수량 (체결 완료 기준)
    reserved_quantity NUMERIC(30,8) NOT NULL DEFAULT 0, -- SELL 신호 점유 수량 (체결 전)
    average_price     NUMERIC(30,8) NOT NULL,
    created_at        TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    updated_at        TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    UNIQUE (portfolio_id, symbol_id)
);

CREATE TABLE backtest_result (
    id                UUID          PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id          UUID          NOT NULL REFERENCES agent(id),
    symbol_id         UUID          NOT NULL,
    candle_from       TIMESTAMPTZ   NOT NULL,
    candle_to         TIMESTAMPTZ   NOT NULL,
    initial_capital   NUMERIC(30,8) NOT NULL,
    final_value       NUMERIC(30,8) NOT NULL,
    realized_pnl      NUMERIC(30,8) NOT NULL,
    unrealized_pnl    NUMERIC(30,8) NOT NULL,
    total_signals     INT           NOT NULL DEFAULT 0,
    signal_snapshots  JSONB         NOT NULL DEFAULT '[]',
    created_at        TIMESTAMPTZ   NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_backtest_result_agent ON backtest_result (agent_id, created_at DESC);

CREATE TABLE strategy_decision_log (
    id               UUID          PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id         UUID          NOT NULL REFERENCES agent(id),
    strategy_id      UUID          NOT NULL REFERENCES strategy(id),
    symbol_id        UUID          NOT NULL,
    signal_type      VARCHAR(10)   NOT NULL,
    current_price    NUMERIC(30,8) NOT NULL,
    indicator_values JSONB         NOT NULL DEFAULT '{}',
    evaluation_status VARCHAR(20)  NOT NULL,
    evaluation_reason TEXT,
    created_at       TIMESTAMPTZ   NOT NULL DEFAULT NOW()
);

-- 최신 로그 조회 및 특정 기간 데이터 삭제 최적화
CREATE INDEX idx_decision_log_agent_time ON strategy_decision_log (agent_id, created_at DESC);

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

## 10. API 엔드포인트

### Strategy

| Method | 경로 | Role | 설명 |
|--------|------|------|------|
| `POST` | `/strategies` | USER | 전략 생성 (DRAFT) |
| `GET` | `/strategies` | USER | 내 전략 목록 |
| `GET` | `/strategies/{id}` | USER | 전략 상세 |
| `PUT` | `/strategies/{id}` | USER | 파라미터 수정 (DRAFT만) |
| `DELETE` | `/strategies/{id}` | USER | 삭제 (DRAFT, Agent 미할당) |
| `PUT` | `/strategies/{id}/validate` | USER | VALIDATED 전환 |
| `PUT` | `/strategies/{id}/deprecate` | USER | DEPRECATED 처리 |

### Agent

| Method | 경로 | Role | 설명 |
|--------|------|------|------|
| `POST` | `/agents` | USER | 에이전트 생성 (strategyId 지정) |
| `GET` | `/agents` | USER | 내 에이전트 목록 |
| `GET` | `/agents/{id}` | USER | 에이전트 상세 |
| `PUT` | `/agents/{id}` | USER | 설정 수정 (INACTIVE만) |
| `PUT` | `/agents/{id}/activate` | USER | ACTIVE 전환 + 포트폴리오 초기화 |
| `PUT` | `/agents/{id}/pause` | USER | PAUSED 전환 |
| `PUT` | `/agents/{id}/resume` | USER | ACTIVE 복귀 |
| `PUT` | `/agents/{id}/terminate` | USER | TERMINATED 처리 |
| `GET` | `/agents/{id}/signals` | USER | 신호 이력 (페이지네이션) |
| `GET` | `/agents/{id}/portfolio` | USER | 포트폴리오 현황 (현금, 총자산, 실현손익) |
| `GET` | `/agents/{id}/portfolio/positions` | USER | 현재 보유 포지션 목록 |
| `GET` | `/agents/{id}/portfolio/history` | USER | 시간별 포트폴리오 이력 (`?from=&to=&type=SIGNAL\|DAILY`) |
| `GET` | `/agents/{id}/decision-logs` | USER | 전략 결정 감사 로그 (페이지네이션) |
| `GET` | `/agents/{id}/backtests` | USER | 백테스트 결과 목록 |
| `GET` | `/agents/{id}/backtests/{backtestId}` | USER | 백테스트 결과 상세 (신호 스냅샷 포함) |

---

## 11. 에러 코드

| 코드 | 상수 | 설명 |
|------|------|------|
| `A001` | `STRATEGY_NOT_FOUND` | 전략 없음 |
| `A002` | `STRATEGY_NOT_DRAFT` | DRAFT 상태가 아니어서 수정 불가 |
| `A003` | `STRATEGY_NOT_VALIDATED` | DRAFT 전략은 실거래(TRADE) 신호 요청 불가 |
| `A004` | `STRATEGY_DEPRECATED` | DEPRECATED 전략은 신규 Agent에 할당 불가 |
| `A005` | `AGENT_NOT_FOUND` | 에이전트 없음 |
| `A006` | `AGENT_NOT_ACTIVE` | ACTIVE 상태가 아니어서 신호 생성 불가 |
| `A007` | `AGENT_NOT_INACTIVE` | INACTIVE 상태가 아니어서 설정 수정 불가 |
| `A008` | `AGENT_ALREADY_TERMINATED` | TERMINATED 에이전트는 상태 전환 불가 |
| `A009` | `PORTFOLIO_NOT_FOUND` | 포트폴리오 없음 |
| `A010` | `INSUFFICIENT_CASH` | 매수 시 현금 부족 |
| `A011` | `CANDLE_DATA_INSUFFICIENT` | 지표 계산에 필요한 캔들 수 부족 |
| `A012` | `UNSUPPORTED_STRATEGY_TYPE` | 지원하지 않는 전략 타입 |
| `A013` | `INVALID_RISK_CONFIG` | RiskConfig 유효성 오류 |
