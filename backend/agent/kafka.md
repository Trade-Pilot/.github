# Agent Service — Kafka 인터페이스

> 이 문서는 `backend/agent/domain.md`에서 분할되었습니다.

---

## 6. Kafka 인터페이스

### Command 수신 — 신호 생성 요청

VirtualTrade / Trade가 `agentIdentifier`를 기준으로 요청한다.
Agent Service가 내부에서 전략을 조회하고 신호를 생성한다.

```kotlin
// 구독 토픽
// - command.agent.virtual-trade.analyze-strategy
// - command.agent.trade.analyze-strategy

data class AnalyzeAgentCommand(
    val agentIdentifier      : UUID,
    val symbolIdentifier     : UUID,
    val currentPrice : BigDecimal,
) : CommandBaseMessage

// 발행 토픽 — Envelope.callback으로 동적 결정
data class AnalyzeAgentReply(
    val agentIdentifier           : UUID,
    val signalIdentifier          : UUID?,        -- BUY/SELL이면 저장된 Signal ID, HOLD이면 null
    val strategyIdentifier        : UUID,
    val symbolIdentifier          : UUID,
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
5.  FindMarketCandleOutput.getRecentCandles(symbolIdentifier, strategy.parameters.interval, executor.requiredCandleCount())
6.  executor.analyze(candles) → SignalConditionResult
7.  StrategyDecisionLog 생성 및 비동기 저장 (도메인 이벤트 발행 또는 직접 호출)
8.  Portfolio 조회 + @Lock(PESSIMISTIC_WRITE) (가용 현금/포지션 정확히 읽기 위해 락 필요)
9.  AgentRiskManager.applySizing(symbolIdentifier, condition, portfolio, riskConfig, currentPrice) → SignalResult
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
    val agentIdentifier    : UUID,
    val signalIdentifier   : UUID,           // 이 체결을 유발한 Signal ID
    val symbolIdentifier   : UUID,
    val side       : OrderSide,      // BUY | SELL
    val quantity   : BigDecimal,     // 체결 수량
    val price      : BigDecimal,     // 실제 체결가
    val fee        : BigDecimal,     // 수수료 (가상 체결이면 0)
    val executedAt : OffsetDateTime,
) : EventBaseMessage
```

**처리 흐름:**
```
1. Portfolio 조회 (agentIdentifier 기준)
2. PortfolioUpdater.apply(portfolio, event)
   └ BUY : 현금 차감 (price × quantity + fee), 포지션 갱신 (평균단가 재계산)
   └ SELL: 포지션 청산, 현금 증가 (price × quantity - fee), realizedPnl 갱신
3. Portfolio DB 저장
4. PortfolioHistory(SIGNAL 타입, triggerSignalIdentifier = event.signalIdentifier) 기록
```

> 부분 체결(Trade의 PARTIALLY_FILLED)이 발생하면 체결 건별로 이벤트가 도착한다.
> 각 이벤트마다 위 흐름을 독립적으로 처리한다.

### Event 발행 — AgentTerminatedEvent

Agent가 TERMINATED 상태로 전환될 때 발행한다.
VirtualTrade Service / Trade Service가 구독해 관련 Registration을 STOPPED 처리한다.

```
발행 토픽 : trade-pilot.agentservice.agent  (eventType: "agent-terminated")
트리거    : Agent.status → TERMINATED (사용자 요청 또는 UserWithdrawnEvent 처리)
페이로드  : { agentIdentifier, userIdentifier }
```

### Event 수신 — OrderFailedEvent (점유 해제)

VirtualTrade / Trade Service에서 주문이 거절(`REJECTED`)되거나 취소(`CANCELLED`)된 경우 발행하는 이벤트다.
Agent Service는 이 이벤트를 수신하여 점유된 자산(`reservedCash` / `reservedQuantity`)을 해제한다.

```kotlin
// 구독 토픽
// - event.virtual-trade.execution-failed  (VirtualTrade Service 발행 — 가상 주문 실패)
// - event.trade.execution-failed          (Trade Service 발행 — 실주문 실패/취소)

data class OrderFailedEvent(
    val agentIdentifier              : UUID,
    val signalIdentifier             : UUID,
    val symbolIdentifier             : UUID,
    val side                 : OrderSide,      // BUY | SELL
    val remainingQuantity    : BigDecimal,     // 미체결 잔여 수량
    val signalPrice          : BigDecimal,     // 원래 신호 가격 (BUY 점유 해제 계산용)
) : EventBaseMessage
```

**처리 흐름:**
```
1. Portfolio 조회 (agentIdentifier 기준)
2. PortfolioUpdater.rollback(portfolio, event)
   └ BUY 실패: reservedCash -= remainingQuantity × signalPrice
   └ SELL 실패: position.reservedQuantity -= remainingQuantity
3. Portfolio DB 저장
```

### Event 수신 — UserWithdrawnEvent

```
구독 토픽 : trade-pilot.userservice.user  (eventType: "user-withdrawn")
처리      : userIdentifier에 속한 모든 Agent → TERMINATED → AgentTerminatedEvent 발행
보존      : Portfolio / Signal / Position (감사 목적)
```
