# 비즈니스 로직 알고리즘 설계

> Trade Pilot 프로젝트의 핵심 비즈니스 로직에 대한 수학적 정의, 알고리즘, Kotlin pseudo-code

---

## 1. 기술적 지표 (Technical Indicators)

Agent Service 인프라 레이어(`infrastructure/indicator/TechnicalIndicators`)에 구현한다.
도메인 레이어는 지표 계산에 의존하지 않으며, 전략 실행기(StrategyExecutor)가 인프라 레이어를 통해 지표를 계산한다.

---

### 1.1 MA (이동평균, Moving Average)

#### SMA (Simple Moving Average, 단순 이동평균)

**수학 공식:**
```
SMA(period) = (close[0] + close[1] + ... + close[period-1]) / period
```

**입력 파라미터:**

| 파라미터 | 타입 | 설명 |
|----------|------|------|
| `prices` | `List<BigDecimal>` | 종가 시계열 (최신순) |
| `period` | `Int` | 이동평균 기간 |

**출력:** `BigDecimal` — 해당 기간의 단순 이동평균 값

**Kotlin pseudo-code:**
```kotlin
fun sma(prices: List<BigDecimal>, period: Int): BigDecimal {
    require(prices.size >= period) { "데이터 부족: ${prices.size} < $period" }
    return prices.take(period)
        .fold(BigDecimal.ZERO) { acc, price -> acc + price }
        .divide(period.toBigDecimal(), SCALE, RoundingMode.HALF_UP)
}
```

#### EMA (Exponential Moving Average, 지수 이동평균)

**수학 공식:**
```
k = 2 / (period + 1)
EMA[0] = SMA(period)                        -- 초기값은 SMA
EMA[i] = close[i] * k + EMA[i-1] * (1 - k) -- 이후 지수 가중
```

**입력 파라미터:**

| 파라미터 | 타입 | 설명 |
|----------|------|------|
| `prices` | `List<BigDecimal>` | 종가 시계열 (과거순 — 오래된 데이터가 앞) |
| `period` | `Int` | EMA 기간 |

**출력:** `BigDecimal` — 최신 시점의 EMA 값

**Kotlin pseudo-code:**
```kotlin
fun ema(prices: List<BigDecimal>, period: Int): BigDecimal {
    require(prices.size >= period) { "데이터 부족: ${prices.size} < $period" }
    val k = BigDecimal(2).divide((period + 1).toBigDecimal(), SCALE, RoundingMode.HALF_UP)
    val oneMinusK = BigDecimal.ONE - k

    // 초기 EMA = 첫 period개의 SMA
    var ema = prices.subList(0, period)
        .fold(BigDecimal.ZERO) { acc, p -> acc + p }
        .divide(period.toBigDecimal(), SCALE, RoundingMode.HALF_UP)

    // period 이후부터 EMA 계산
    for (i in period until prices.size) {
        ema = prices[i] * k + ema * oneMinusK
    }
    return ema.setScale(SCALE, RoundingMode.HALF_UP)
}
```

---

### 1.2 RSI (상대강도지수, Relative Strength Index)

**수학 공식:**
```
변화량: delta[i] = close[i] - close[i-1]
상승분: gain[i]  = max(delta[i], 0)
하락분: loss[i]  = abs(min(delta[i], 0))

초기 평균 (SMA 방식, 첫 period 구간):
  avgGain = sum(gain[1..period]) / period
  avgLoss = sum(loss[1..period]) / period

이후 Wilder's Smoothing:
  avgGain = (avgGain * (period - 1) + gain[i]) / period
  avgLoss = (avgLoss * (period - 1) + loss[i]) / period

RS  = avgGain / avgLoss
RSI = 100 - 100 / (1 + RS)

예외: avgLoss == 0이면 RSI = 100 (하락 없음)
```

**입력 파라미터:**

| 파라미터 | 타입 | 설명 |
|----------|------|------|
| `prices` | `List<BigDecimal>` | 종가 시계열 (과거순) |
| `period` | `Int` | RSI 기간 (기본 14) |

**출력:** `BigDecimal` — RSI 값 (0 ~ 100)

**Kotlin pseudo-code:**
```kotlin
fun rsi(prices: List<BigDecimal>, period: Int = 14): BigDecimal {
    require(prices.size > period) { "데이터 부족: 최소 ${period + 1}개 필요" }

    val deltas = (1 until prices.size).map { prices[it] - prices[it - 1] }

    // 초기 avgGain, avgLoss (SMA)
    var avgGain = deltas.take(period)
        .filter { it > BigDecimal.ZERO }
        .fold(BigDecimal.ZERO) { acc, d -> acc + d }
        .divide(period.toBigDecimal(), SCALE, RoundingMode.HALF_UP)

    var avgLoss = deltas.take(period)
        .filter { it < BigDecimal.ZERO }
        .fold(BigDecimal.ZERO) { acc, d -> acc + d.abs() }
        .divide(period.toBigDecimal(), SCALE, RoundingMode.HALF_UP)

    // Wilder's Smoothing
    for (i in period until deltas.size) {
        val gain = if (deltas[i] > BigDecimal.ZERO) deltas[i] else BigDecimal.ZERO
        val loss = if (deltas[i] < BigDecimal.ZERO) deltas[i].abs() else BigDecimal.ZERO

        avgGain = (avgGain * (period - 1).toBigDecimal() + gain)
            .divide(period.toBigDecimal(), SCALE, RoundingMode.HALF_UP)
        avgLoss = (avgLoss * (period - 1).toBigDecimal() + loss)
            .divide(period.toBigDecimal(), SCALE, RoundingMode.HALF_UP)
    }

    if (avgLoss == BigDecimal.ZERO) return BigDecimal(100)

    val rs = avgGain.divide(avgLoss, SCALE, RoundingMode.HALF_UP)
    return BigDecimal(100) - BigDecimal(100).divide(
        BigDecimal.ONE + rs, SCALE, RoundingMode.HALF_UP
    )
}
```

---

### 1.3 MACD (이동평균 수렴확산)

**수학 공식:**
```
MACD Line   = EMA(close, 12) - EMA(close, 26)
Signal Line = EMA(MACD Line, 9)
Histogram   = MACD Line - Signal Line
```

**입력 파라미터:**

| 파라미터 | 타입 | 설명 |
|----------|------|------|
| `prices` | `List<BigDecimal>` | 종가 시계열 (과거순) |
| `shortPeriod` | `Int` | 단기 EMA 기간 (기본 12) |
| `longPeriod` | `Int` | 장기 EMA 기간 (기본 26) |
| `signalPeriod` | `Int` | Signal EMA 기간 (기본 9) |

**출력:**

| 필드 | 타입 | 설명 |
|------|------|------|
| `macdLine` | `BigDecimal` | MACD 라인 값 |
| `signalLine` | `BigDecimal` | Signal 라인 값 |
| `histogram` | `BigDecimal` | 히스토그램 (MACD - Signal) |

**Kotlin pseudo-code:**
```kotlin
data class MacdResult(
    val macdLine: BigDecimal,
    val signalLine: BigDecimal,
    val histogram: BigDecimal,
)

fun macd(
    prices: List<BigDecimal>,
    shortPeriod: Int = 12,
    longPeriod: Int = 26,
    signalPeriod: Int = 9,
): MacdResult {
    require(prices.size >= longPeriod + signalPeriod) {
        "데이터 부족: 최소 ${longPeriod + signalPeriod}개 필요"
    }

    // 각 시점의 MACD Line 시계열 생성
    val macdSeries = mutableListOf<BigDecimal>()
    for (i in longPeriod..prices.size) {
        val subPrices = prices.subList(0, i)
        val shortEma = ema(subPrices, shortPeriod)
        val longEma = ema(subPrices, longPeriod)
        macdSeries.add(shortEma - longEma)
    }

    val macdLine = macdSeries.last()
    val signalLine = ema(macdSeries, signalPeriod)
    val histogram = macdLine - signalLine

    return MacdResult(macdLine, signalLine, histogram)
}
```

---

### 1.4 볼린저 밴드 (Bollinger Bands)

**수학 공식:**
```
Middle Band = SMA(close, period)
σ (표준편차) = sqrt(Σ(close[i] - SMA)^2 / period)
Upper Band  = Middle + multiplier * σ
Lower Band  = Middle - multiplier * σ
```

**입력 파라미터:**

| 파라미터 | 타입 | 설명 |
|----------|------|------|
| `prices` | `List<BigDecimal>` | 종가 시계열 (최신순) |
| `period` | `Int` | SMA 기간 (기본 20) |
| `multiplier` | `Double` | 표준편차 배수 (기본 2.0) |

**출력:**

| 필드 | 타입 | 설명 |
|------|------|------|
| `upper` | `BigDecimal` | 상단 밴드 |
| `middle` | `BigDecimal` | 중간 밴드 (SMA) |
| `lower` | `BigDecimal` | 하단 밴드 |

**Kotlin pseudo-code:**
```kotlin
data class BollingerResult(
    val upper: BigDecimal,
    val middle: BigDecimal,
    val lower: BigDecimal,
)

fun bollingerBands(
    prices: List<BigDecimal>,
    period: Int = 20,
    multiplier: Double = 2.0,
): BollingerResult {
    require(prices.size >= period) { "데이터 부족: ${prices.size} < $period" }

    val middle = sma(prices, period)

    // 표준편차 계산
    val variance = prices.take(period)
        .map { price -> (price - middle).pow(2) }
        .fold(BigDecimal.ZERO) { acc, v -> acc + v }
        .divide(period.toBigDecimal(), SCALE, RoundingMode.HALF_UP)

    val stdDev = variance.sqrt(MathContext(SCALE))
    val band = stdDev * multiplier.toBigDecimal()

    return BollingerResult(
        upper = middle + band,
        middle = middle,
        lower = middle - band,
    )
}
```

---

### 1.5 스토캐스틱 오실레이터 (Stochastic Oscillator)

**수학 공식:**
```
%K = (close - lowest(low, period)) / (highest(high, period) - lowest(low, period)) * 100
%D = SMA(%K, smoothPeriod)

lowest(low, period)  = period 기간 내 최저가
highest(high, period) = period 기간 내 최고가
```

**입력 파라미터:**

| 파라미터 | 타입 | 설명 |
|----------|------|------|
| `highs` | `List<BigDecimal>` | 고가 시계열 (최신순) |
| `lows` | `List<BigDecimal>` | 저가 시계열 (최신순) |
| `closes` | `List<BigDecimal>` | 종가 시계열 (최신순) |
| `period` | `Int` | 룩백 기간 (기본 14) |
| `smoothPeriod` | `Int` | %D SMA 기간 (기본 3) |

**출력:**

| 필드 | 타입 | 설명 |
|------|------|------|
| `percentK` | `BigDecimal` | %K 값 (0 ~ 100) |
| `percentD` | `BigDecimal` | %D 값 (0 ~ 100) |

**Kotlin pseudo-code:**
```kotlin
data class StochasticResult(
    val percentK: BigDecimal,
    val percentD: BigDecimal,
)

fun stochastic(
    highs: List<BigDecimal>,
    lows: List<BigDecimal>,
    closes: List<BigDecimal>,
    period: Int = 14,
    smoothPeriod: Int = 3,
): StochasticResult {
    require(highs.size >= period + smoothPeriod - 1) { "데이터 부족" }

    // %K 시계열 생성 (%D 계산을 위해 smoothPeriod만큼 필요)
    val kSeries = (0 until smoothPeriod).map { offset ->
        val highSlice = highs.subList(offset, offset + period)
        val lowSlice = lows.subList(offset, offset + period)
        val close = closes[offset]

        val highest = highSlice.max()
        val lowest = lowSlice.min()
        val range = highest - lowest

        if (range == BigDecimal.ZERO) BigDecimal(50) // 변동 없으면 중립
        else (close - lowest)
            .divide(range, SCALE, RoundingMode.HALF_UP) * BigDecimal(100)
    }

    val percentK = kSeries.first()
    val percentD = kSeries
        .fold(BigDecimal.ZERO) { acc, k -> acc + k }
        .divide(smoothPeriod.toBigDecimal(), SCALE, RoundingMode.HALF_UP)

    return StochasticResult(percentK, percentD)
}
```

---

## 2. 전략 신호 생성 로직 (Strategy Signal Generation)

각 전략은 `StrategyExecutor` 인터페이스를 구현하며, 캔들 데이터만으로 `SignalConditionResult`를 반환한다.
포지션 사이징, 손절/익절은 `AgentRiskManager`가 별도 처리한다.

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

---

## 4. 성과 지표 계산 (Performance Metrics)

`PortfolioHistory` 시계열 데이터를 기반으로 Agent/백테스팅 성과를 정량 평가한다.

---

### 4.1 수익률 (Return)

#### 단순 수익률
```
simpleReturn = (finalValue - initialCapital) / initialCapital * 100
```

#### 로그 수익률
```
logReturn = ln(finalValue / initialCapital) * 100
```

> 로그 수익률은 시간 가산성을 가지므로 기간별 수익률 합산에 적합하다.

**Kotlin pseudo-code:**
```kotlin
fun simpleReturn(initialCapital: BigDecimal, finalValue: BigDecimal): BigDecimal {
    return (finalValue - initialCapital)
        .divide(initialCapital, SCALE, RoundingMode.HALF_UP) * BigDecimal(100)
}

fun logReturn(initialCapital: BigDecimal, finalValue: BigDecimal): BigDecimal {
    val ratio = finalValue.divide(initialCapital, SCALE, RoundingMode.HALF_UP)
    return ln(ratio.toDouble()).toBigDecimal() * BigDecimal(100)
}
```

---

### 4.2 최대 낙폭 (MDD, Maximum Drawdown)

**수학 공식:**
```
MDD = max((peak - trough) / peak) * 100

peak: 시계열 상의 역대 최고 포트폴리오 가치
trough: peak 이후의 최저 포트폴리오 가치
```

**알고리즘:** 전체 포트폴리오 가치 시계열을 순회하며 고점 대비 최대 하락폭을 추적한다.

**Kotlin pseudo-code:**
```kotlin
fun maxDrawdown(portfolioValues: List<BigDecimal>): BigDecimal {
    if (portfolioValues.size < 2) return BigDecimal.ZERO

    var peak = portfolioValues.first()
    var maxDd = BigDecimal.ZERO

    for (value in portfolioValues) {
        if (value > peak) {
            peak = value
        }
        val drawdown = (peak - value).divide(peak, SCALE, RoundingMode.HALF_UP)
        if (drawdown > maxDd) {
            maxDd = drawdown
        }
    }

    return maxDd * BigDecimal(100)
}
```

---

### 4.3 샤프 비율 (Sharpe Ratio)

**수학 공식:**
```
Sharpe = (Rp - Rf) / σp

Rp: 포트폴리오 수익률 (일별 평균)
Rf: 무위험 수익률 (연 3.5% → 일 3.5%/252 또는 3.5%/365)
σp: 일별 수익률의 표준편차

연환산: Sharpe_annual = Sharpe_daily * sqrt(N)
  N = 252 (주식, 거래일 기준)
  N = 365 (암호화폐, 24/7 운영)
```

**Kotlin pseudo-code:**
```kotlin
fun sharpeRatio(
    dailyReturns: List<BigDecimal>,
    annualRiskFreeRate: BigDecimal = BigDecimal("0.035"),
    tradingDaysPerYear: Int = 365,  // 암호화폐 기준
): BigDecimal {
    if (dailyReturns.size < 2) return BigDecimal.ZERO

    val dailyRf = annualRiskFreeRate
        .divide(tradingDaysPerYear.toBigDecimal(), SCALE, RoundingMode.HALF_UP)

    // 일별 초과수익률
    val excessReturns = dailyReturns.map { it - dailyRf }

    val mean = excessReturns
        .fold(BigDecimal.ZERO) { acc, r -> acc + r }
        .divide(excessReturns.size.toBigDecimal(), SCALE, RoundingMode.HALF_UP)

    // 표준편차
    val variance = excessReturns
        .map { r -> (r - mean).pow(2) }
        .fold(BigDecimal.ZERO) { acc, v -> acc + v }
        .divide((excessReturns.size - 1).toBigDecimal(), SCALE, RoundingMode.HALF_UP)

    val stdDev = variance.sqrt(MathContext(SCALE))
    if (stdDev == BigDecimal.ZERO) return BigDecimal.ZERO

    val dailySharpe = mean.divide(stdDev, SCALE, RoundingMode.HALF_UP)

    // 연환산
    val annualizationFactor = sqrt(tradingDaysPerYear.toDouble()).toBigDecimal()
    return dailySharpe * annualizationFactor
}
```

---

### 4.4 소티노 비율 (Sortino Ratio)

**수학 공식:**
```
Sortino = (Rp - Rf) / σd

σd (하방 편차): sqrt(Σ(min(Ri - Rf, 0))^2 / N)
```

샤프 비율과 달리 하락 변동성만 고려하므로, 상승 변동성이 큰 전략에 유리한 평가가 가능하다.

**Kotlin pseudo-code:**
```kotlin
fun sortinoRatio(
    dailyReturns: List<BigDecimal>,
    annualRiskFreeRate: BigDecimal = BigDecimal("0.035"),
    tradingDaysPerYear: Int = 365,
): BigDecimal {
    if (dailyReturns.size < 2) return BigDecimal.ZERO

    val dailyRf = annualRiskFreeRate
        .divide(tradingDaysPerYear.toBigDecimal(), SCALE, RoundingMode.HALF_UP)

    val excessReturns = dailyReturns.map { it - dailyRf }

    val mean = excessReturns
        .fold(BigDecimal.ZERO) { acc, r -> acc + r }
        .divide(excessReturns.size.toBigDecimal(), SCALE, RoundingMode.HALF_UP)

    // 하방 편차: 음수 초과수익률만 사용
    val downsideVariance = excessReturns
        .filter { it < BigDecimal.ZERO }
        .map { r -> r.pow(2) }
        .fold(BigDecimal.ZERO) { acc, v -> acc + v }
        .divide(excessReturns.size.toBigDecimal(), SCALE, RoundingMode.HALF_UP)

    val downsideDev = downsideVariance.sqrt(MathContext(SCALE))
    if (downsideDev == BigDecimal.ZERO) return BigDecimal.ZERO

    val dailySortino = mean.divide(downsideDev, SCALE, RoundingMode.HALF_UP)

    val annualizationFactor = sqrt(tradingDaysPerYear.toDouble()).toBigDecimal()
    return dailySortino * annualizationFactor
}
```

---

### 4.5 승률 및 손익비

#### 승률 (Win Rate)
```
winRate = 수익 거래 수 / 전체 거래 수 * 100
```

> 전체 거래 수: SELL 체결 건수 기준 (포지션 청산 완료된 거래)

#### 손익비 (Profit/Loss Ratio)
```
profitLossRatio = 평균 수익 / 평균 손실

평균 수익 = 수익 거래들의 실현손익 합 / 수익 거래 수
평균 손실 = |손실 거래들의 실현손익 합| / 손실 거래 수
```

**Kotlin pseudo-code:**
```kotlin
data class TradeStatistics(
    val winRate: BigDecimal,
    val profitLossRatio: BigDecimal,
    val totalTrades: Int,
    val winningTrades: Int,
    val losingTrades: Int,
)

fun calculateTradeStatistics(tradePnls: List<BigDecimal>): TradeStatistics {
    if (tradePnls.isEmpty()) {
        return TradeStatistics(
            winRate = BigDecimal.ZERO,
            profitLossRatio = BigDecimal.ZERO,
            totalTrades = 0,
            winningTrades = 0,
            losingTrades = 0,
        )
    }

    val wins = tradePnls.filter { it > BigDecimal.ZERO }
    val losses = tradePnls.filter { it < BigDecimal.ZERO }

    val winRate = wins.size.toBigDecimal()
        .divide(tradePnls.size.toBigDecimal(), SCALE, RoundingMode.HALF_UP) * BigDecimal(100)

    val avgProfit = if (wins.isNotEmpty()) {
        wins.fold(BigDecimal.ZERO) { acc, p -> acc + p }
            .divide(wins.size.toBigDecimal(), SCALE, RoundingMode.HALF_UP)
    } else BigDecimal.ZERO

    val avgLoss = if (losses.isNotEmpty()) {
        losses.fold(BigDecimal.ZERO) { acc, l -> acc + l.abs() }
            .divide(losses.size.toBigDecimal(), SCALE, RoundingMode.HALF_UP)
    } else BigDecimal.ZERO

    val profitLossRatio = if (avgLoss > BigDecimal.ZERO) {
        avgProfit.divide(avgLoss, SCALE, RoundingMode.HALF_UP)
    } else BigDecimal.ZERO

    return TradeStatistics(
        winRate = winRate,
        profitLossRatio = profitLossRatio,
        totalTrades = tradePnls.size,
        winningTrades = wins.size,
        losingTrades = losses.size,
    )
}
```

---

## 부록: 공통 상수

```kotlin
const val SCALE = 10           // BigDecimal 연산 소수점 자릿수
const val QUANTITY_SCALE = 8   // 수량 소수점 자릿수 (암호화폐)
```
