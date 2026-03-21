# 성과 지표 계산 (Performance Metrics)

> 원본: `backend/business-logic.md` Section 4 + 부록

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
