# 기술적 지표 (Technical Indicators)

> 원본: `backend/business-logic.md` Section 1

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

