# Agent Service — 도메인 모델

> 이 문서는 `backend/agent/domain.md`에서 분할되었습니다.

---

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
                 FindMarketCandleOutput, FindSymbolMetadataOutput
                 StrategyExecutorFactory
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
                 OrderFailedEventConsumer         (event.trade.execution-failed 구독 → 점유 해제)
                 AgentTerminatedEventProducer     (implements PublishAgentTerminatedOutput)
                 UserWithdrawnEventConsumer       (trade-pilot.userservice.user 구독)
  grpc/          MarketCandleGrpcAdapter       (implements FindMarketCandleOutput)
                 MarketSymbolGrpcAdapter       (implements FindSymbolMetadataOutput)
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
├── strategyIdentifier   : UUID
├── userIdentifier       : UUID
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
├── agentIdentifier        : UUID
├── userIdentifier         : UUID
├── name           : String
├── description    : String?
├── strategyIdentifier     : UUID              -- Strategy 참조 (DEPRECATED 불가)
├── status         : AgentStatus
├── riskConfig     : RiskConfig        -- JSONB
├── initialCapital : BigDecimal        -- 포트폴리오/백테스팅 초기 자본금
├── createdAt      : OffsetDateTime
└── updatedAt      : OffsetDateTime

Signal (Entity — Agent 소속)
├── signalIdentifier          : UUID
├── agentIdentifier           : UUID
├── strategyIdentifier        : UUID           -- 신호 생성 시점의 전략 추적용
├── symbolIdentifier          : UUID
├── type              : SignalType
├── confidence        : BigDecimal     -- 0.0 ~ 1.0
├── price             : BigDecimal
├── suggestedQuantity : BigDecimal     -- AgentRiskManager가 산출
├── reason            : SignalReason   -- JSONB
└── createdAt         : OffsetDateTime

──────────────────────────────────────────

Portfolio (Aggregate Root)
├── portfolioIdentifier     : UUID
├── agentIdentifier         : UUID             -- 1 Agent : 1 Portfolio (초기 자본금은 Agent.initialCapital 참조)
├── userIdentifier          : UUID
├── cash            : BigDecimal       -- 실제 보유 현금 (체결 완료 기준)
├── reservedCash    : BigDecimal       -- BUY 신호 발생 시 점유된 현금 (체결 전)
├── realizedPnl     : BigDecimal       -- 누적 실현손익 (매도 시 갱신)
├── createdAt       : OffsetDateTime
└── updatedAt       : OffsetDateTime

Position (Entity — Portfolio 소속)
├── positionIdentifier        : UUID
├── portfolioIdentifier       : UUID
├── symbolIdentifier          : UUID
├── quantity          : BigDecimal       -- 실제 보유 수량 (체결 완료 기준)
├── reservedQuantity  : BigDecimal       -- SELL 신호 발생 시 점유된 수량 (체결 전)
├── averagePrice      : BigDecimal       -- 평균 매입 단가
├── createdAt         : OffsetDateTime
└── updatedAt         : OffsetDateTime

BacktestResult (Entity — Agent 소속)
├── backtestIdentifier       : UUID
├── agentIdentifier          : UUID
├── symbolIdentifier         : UUID
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
├── logIdentifier             : UUID
├── agentIdentifier           : UUID
├── strategyIdentifier        : UUID
├── symbolIdentifier          : UUID
├── signalType        : SignalType        -- BUY | SELL | HOLD
├── currentPrice      : BigDecimal
├── evaluationStatus  : EvaluationStatus  -- SUCCESS | ERROR
├── indicatorValues   : JSONB             -- 평가 시점의 지표 수치 (예: {rsi: 28.4, ma20: 54000})
├── evaluationReason  : String?           -- 평가 실패 시 에러 메시지
└── createdAt         : OffsetDateTime

──────────────────────────────────────────

PortfolioHistory (Entity — Portfolio 소속)
├── historyIdentifier          : UUID
├── portfolioIdentifier        : UUID
├── snapshotType       : SnapshotType  -- SIGNAL | DAILY
├── cash               : BigDecimal
├── totalValue         : BigDecimal    -- cash + 포지션 평가액
├── realizedPnl        : BigDecimal    -- 이 시점까지의 누적 실현손익
├── unrealizedPnl      : BigDecimal    -- 보유 포지션 미실현 손익
├── positionsSnapshot  : JSONB         -- 시점 포지션 상태 (불변 기록)
├── triggerSignalIdentifier    : UUID?         -- SIGNAL 타입일 때 트리거 신호 ID
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
data class AiModelParameters(val modelIdentifier: String, val modelVersion: String, val featureConfig: Map<String, Any>, ...) : StrategyParameters
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
