# 리스크 관리 (Risk Management)

> 원본: `backend/business-logic.md` Section 3

---

## 3. 리스크 관리 (Risk Management)

`AgentRiskManager`가 `SignalConditionResult`에 `RiskConfig`를 적용하여 최종 `SignalResult`를 산출한다.

---

### 3.1 포지션 사이징 (Position Sizing)

**알고리즘:**
```
availableCash = portfolio.cash - portfolio.reservedCash
investAmount  = availableCash * riskConfig.positionSizeRatio
quantity      = floor(investAmount / currentPrice, 거래소 최소 단위)
```

**제약 조건:**

| 조건 | 처리 |
|------|------|
| 해당 심볼 포지션 없음 + 현재 포지션 수 >= `maxConcurrentPositions` | HOLD로 전환 |
| 해당 심볼 포지션 있음 (추가 매수) | `maxConcurrentPositions` 체크 없이 수량 계산 |
| 계산된 수량이 거래소 최소 주문 수량 미만 | HOLD로 전환 |
| 가용 현금 부족 (`availableCash <= 0`) | HOLD로 전환 |

**Kotlin pseudo-code:**
```kotlin
fun calculateBuyQuantity(
    portfolio: Portfolio,
    riskConfig: RiskConfig,
    currentPrice: BigDecimal,
    symbolIdentifier: UUID,
    existingPosition: Position?,
): BigDecimal {
    val availableCash = portfolio.cash - portfolio.reservedCash
    if (availableCash <= BigDecimal.ZERO) return BigDecimal.ZERO

    // 신규 포지션인 경우 동시 보유 제한 확인
    if (existingPosition == null) {
        val currentPositionCount = portfolio.positions.count { it.quantity > BigDecimal.ZERO }
        if (currentPositionCount >= riskConfig.maxConcurrentPositions) return BigDecimal.ZERO
    }

    val investAmount = availableCash * riskConfig.positionSizeRatio
    return investAmount.divide(currentPrice, QUANTITY_SCALE, RoundingMode.DOWN)
}
```

---

### 3.2 손절/익절 (Stop Loss / Take Profit)

전략 신호 평가 전에 보유 포지션에 대해 손절/익절 조건을 선행 검사한다.
조건 충족 시 전략 신호와 무관하게 강제 SELL 신호를 생성한다.

**알고리즘:**
```
손절 조건: currentPrice <= averagePrice * (1 - stopLossPercent)
익절 조건: currentPrice >= averagePrice * (1 + takeProfitPercent)
```

| 설정 | 기본값 | 설명 |
|------|--------|------|
| `stopLossPercent` | `null` (미사용) | 평균 매입가 대비 하락 비율 |
| `takeProfitPercent` | `null` (미사용) | 평균 매입가 대비 상승 비율 |

> `stopLossPercent`와 `takeProfitPercent`가 모두 `null`이면 손절/익절 검사를 건너뛴다.

**Kotlin pseudo-code:**
```kotlin
fun checkStopCondition(
    position: Position,
    riskConfig: RiskConfig,
    currentPrice: BigDecimal,
): StopConditionResult {
    val avgPrice = position.averagePrice

    // 손절 검사
    riskConfig.stopLossPercent?.let { slPercent ->
        val stopPrice = avgPrice * (BigDecimal.ONE - slPercent)
        if (currentPrice <= stopPrice) {
            return StopConditionResult.STOP_LOSS
        }
    }

    // 익절 검사
    riskConfig.takeProfitPercent?.let { tpPercent ->
        val targetPrice = avgPrice * (BigDecimal.ONE + tpPercent)
        if (currentPrice >= targetPrice) {
            return StopConditionResult.TAKE_PROFIT
        }
    }

    return StopConditionResult.NONE
}

enum class StopConditionResult { NONE, STOP_LOSS, TAKE_PROFIT }
```

**향후 확장 — 추적 손절 (Trailing Stop):**
```
trailingStopPrice = peakPrice * (1 - trailingStopPercent)
peakPrice: 포지션 보유 기간 중 최고가 (PortfolioHistory에서 추적)
currentPrice <= trailingStopPrice이면 강제 SELL
```

---

### 3.3 일일/주간/월간 손실 한도

포트폴리오의 누적 손실이 초기 자본 대비 임계값을 초과하면 Agent를 자동 일시 정지(PAUSED)한다.

**한도 설정:**

| 구분 | 임계값 | 계산 기준 |
|------|--------|-----------|
| 일일 | 초기 자본 대비 -3% | 당일 00:00 KST부터 현재까지 |
| 주간 | 초기 자본 대비 -7% | 해당 주 월요일 00:00 KST부터 |
| 월간 | 초기 자본 대비 -15% | 해당 월 1일 00:00 KST부터 |

**손실 계산:**
```
periodLoss = realizedPnl(현재) - realizedPnl(기간시작) + unrealizedPnl(현재)
lossPercent = periodLoss / initialCapital
```

> `realizedPnl`은 누적값이므로 기간별 변화분을 계산한다.
> `unrealizedPnl`은 현재 보유 포지션의 미실현 손익이다.

**초과 시 처리:**
1. Agent 상태를 `PAUSED`로 전환
2. `NOTIFICATION_COMMAND_TOPIC`에 알림 발행 (`VIRTUAL_DAILY_LOSS_LIMIT`, `REAL_WEEKLY_LOSS_LIMIT` 등)
3. 관리자 알림 전송

**Kotlin pseudo-code:**
```kotlin
fun checkLossLimits(
    agent: Agent,
    portfolio: Portfolio,
    periodStartPnl: BigDecimal,  // 기간 시작 시점의 누적 realizedPnl
    currentUnrealizedPnl: BigDecimal,
): LossLimitResult {
    val periodLoss = (portfolio.realizedPnl - periodStartPnl) + currentUnrealizedPnl
    val lossPercent = periodLoss.divide(agent.initialCapital, SCALE, RoundingMode.HALF_UP)

    return when {
        lossPercent <= DAILY_LOSS_LIMIT -> LossLimitResult.DAILY_EXCEEDED
        lossPercent <= WEEKLY_LOSS_LIMIT -> LossLimitResult.WEEKLY_EXCEEDED
        lossPercent <= MONTHLY_LOSS_LIMIT -> LossLimitResult.MONTHLY_EXCEEDED
        else -> LossLimitResult.WITHIN_LIMIT
    }
}

companion object {
    val DAILY_LOSS_LIMIT = BigDecimal("-0.03")   // -3%
    val WEEKLY_LOSS_LIMIT = BigDecimal("-0.07")  // -7%
    val MONTHLY_LOSS_LIMIT = BigDecimal("-0.15") // -15%
}
```

