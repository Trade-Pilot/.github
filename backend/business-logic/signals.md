# 전략 신호 생성 로직 (Strategy Signal Generation)

> 원본: `backend/business-logic.md` Section 2

---

## 2. 전략 신호 생성 로직 (Strategy Signal Generation)

각 전략은 `StrategyExecutor` 인터페이스를 구현하며, 캔들 데이터만으로 `SignalConditionResult`를 반환한다.
포지션 사이징, 손절/익절은 `AgentRiskManager`가 별도 처리한다.

### strategyKind ↔ Executor 매핑

| `strategyKind` (StrategyParameters) | Executor 클래스 | 필수 파라미터 |
|-------------------------------------|-----------------|-------------|
| `MA_CROSSOVER` | `MovingAverageCrossoverExecutor` | shortPeriod, longPeriod, interval |
| `RSI` | `RsiExecutor` | period, oversoldThreshold, overboughtThreshold, interval |
| `BOLLINGER_BREAKOUT` | `BollingerBreakoutExecutor` | period, multiplier, interval |

> `StrategyExecutorFactory.create(strategy)`는 `strategy.parameters.strategyKind`를 기준으로
> 적절한 Executor 구현체를 반환한다.

---

### 2.1 이동평균 크로스오버 (MA Crossover)

`MovingAverageCrossoverExecutor` — `StrategyParameters: MovingAverageCrossoverParameters`

**신호 조건:**

| 신호 | 조건 | 설명 |
|------|------|------|
| `BUY` | `shortMA[현재] > longMA[현재]` AND `shortMA[이전] <= longMA[이전]` | Golden Cross — 단기선이 장기선을 상향 돌파 |
| `SELL` | `shortMA[현재] < longMA[현재]` AND `shortMA[이전] >= longMA[이전]` | Dead Cross — 단기선이 장기선을 하향 돌파 |
| `HOLD` | 교차 없음 | 기존 상태 유지 |

**confidence 계산:**
```
confidence = |shortMA - longMA| / longMA
```
두 이동평균의 괴리율이 클수록 신호 강도가 높다고 판단한다.

**Kotlin pseudo-code:**
```kotlin
class MovingAverageCrossoverExecutor(
    private val params: MovingAverageCrossoverParameters,
) : StrategyExecutor {

    override fun requiredCandleCount(): Int = params.longPeriod + 1

    override fun analyze(candles: List<CandleData>): SignalConditionResult {
        val closes = candles.map { it.close }

        // 현재 시점
        val shortMaCurrent = sma(closes, params.shortPeriod)
        val longMaCurrent = sma(closes, params.longPeriod)

        // 이전 시점 (한 캔들 전)
        val prevCloses = closes.drop(1)
        val shortMaPrev = sma(prevCloses, params.shortPeriod)
        val longMaPrev = sma(prevCloses, params.longPeriod)

        val type = when {
            shortMaCurrent > longMaCurrent && shortMaPrev <= longMaPrev -> SignalType.BUY
            shortMaCurrent < longMaCurrent && shortMaPrev >= longMaPrev -> SignalType.SELL
            else -> SignalType.HOLD
        }

        val confidence = (shortMaCurrent - longMaCurrent).abs()
            .divide(longMaCurrent, SCALE, RoundingMode.HALF_UP)

        return SignalConditionResult(
            type = type,
            confidence = confidence.min(BigDecimal.ONE),
            reason = SignalReason(
                indicator = "MA_CROSSOVER",
                details = mapOf(
                    "shortMA" to shortMaCurrent,
                    "longMA" to longMaCurrent,
                    "shortPeriod" to params.shortPeriod,
                    "longPeriod" to params.longPeriod,
                ),
            ),
        )
    }
}
```

---

### 2.2 RSI 과매수/과매도

`RsiExecutor` — `StrategyParameters: RsiParameters`

**신호 조건:**

| 신호 | 조건 | 설명 |
|------|------|------|
| `BUY` | `RSI < oversoldThreshold` (기본 30) | 과매도 구간 — 반등 기대 |
| `SELL` | `RSI > overboughtThreshold` (기본 70) | 과매수 구간 — 조정 기대 |
| `HOLD` | `oversoldThreshold <= RSI <= overboughtThreshold` | 중립 구간 |

**confidence 계산:**
```
confidence = |RSI - 50| / 50
```
RSI가 극단값(0 또는 100)에 가까울수록 confidence가 높다.

**Kotlin pseudo-code:**
```kotlin
class RsiExecutor(
    private val params: RsiParameters,
) : StrategyExecutor {

    override fun requiredCandleCount(): Int = params.period + 1

    override fun analyze(candles: List<CandleData>): SignalConditionResult {
        val closes = candles.map { it.close }
        val rsiValue = rsi(closes, params.period)

        val type = when {
            rsiValue < params.oversoldThreshold.toBigDecimal() -> SignalType.BUY
            rsiValue > params.overboughtThreshold.toBigDecimal() -> SignalType.SELL
            else -> SignalType.HOLD
        }

        val confidence = (rsiValue - BigDecimal(50)).abs()
            .divide(BigDecimal(50), SCALE, RoundingMode.HALF_UP)

        return SignalConditionResult(
            type = type,
            confidence = confidence.min(BigDecimal.ONE),
            reason = SignalReason(
                indicator = "RSI",
                details = mapOf(
                    "rsi" to rsiValue,
                    "period" to params.period,
                    "oversoldThreshold" to params.oversoldThreshold,
                    "overboughtThreshold" to params.overboughtThreshold,
                ),
            ),
        )
    }
}
```

---

### 2.3 볼린저 밴드 브레이크아웃

`BollingerBreakoutExecutor` — `StrategyParameters: BollingerBreakoutParameters`

**신호 조건:**

| 신호 | 조건 | 설명 |
|------|------|------|
| `BUY` | `close < lowerBand` | 하단 밴드 이탈 — 평균 회귀 기대 |
| `SELL` | `close > upperBand` | 상단 밴드 이탈 — 과열 조정 기대 |
| `HOLD` | `lowerBand <= close <= upperBand` | 밴드 내부 |

> 기본 전략은 평균 회귀(Mean Reversion) 방식이다. 추세 추종 방식은 향후 파라미터로 분리 가능.

**confidence 계산:**
```
confidence = |close - middle| / (upper - middle)
```
종가가 밴드 경계에서 벗어난 정도를 정규화한다. 1.0을 초과하면 1.0으로 clamp한다.

**Kotlin pseudo-code:**
```kotlin
class BollingerBreakoutExecutor(
    private val params: BollingerBreakoutParameters,
) : StrategyExecutor {

    override fun requiredCandleCount(): Int = params.period

    override fun analyze(candles: List<CandleData>): SignalConditionResult {
        val closes = candles.map { it.close }
        val currentClose = closes.first()

        val bands = bollingerBands(closes, params.period, params.multiplier)

        val type = when {
            currentClose < bands.lower -> SignalType.BUY
            currentClose > bands.upper -> SignalType.SELL
            else -> SignalType.HOLD
        }

        val halfBandWidth = bands.upper - bands.middle
        val confidence = if (halfBandWidth > BigDecimal.ZERO) {
            (currentClose - bands.middle).abs()
                .divide(halfBandWidth, SCALE, RoundingMode.HALF_UP)
                .min(BigDecimal.ONE)
        } else {
            BigDecimal.ZERO
        }

        return SignalConditionResult(
            type = type,
            confidence = confidence,
            reason = SignalReason(
                indicator = "BOLLINGER_BREAKOUT",
                details = mapOf(
                    "close" to currentClose,
                    "upper" to bands.upper,
                    "middle" to bands.middle,
                    "lower" to bands.lower,
                    "period" to params.period,
                    "multiplier" to params.multiplier,
                ),
            ),
        )
    }
}
```

