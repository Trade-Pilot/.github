# Market Service — Domain Service, Domain Event

> 이 문서는 `backend/market/domain.md`에서 분할되었습니다.

---

## 5. Domain Service

### 5.1 MarketCandleIntervalCalculator

**목적**: 기준 간격의 캔들을 결합하여 다른 간격의 캔들을 계산합니다.

**메서드**:
```kotlin
object MarketCandleIntervalCalculator {
    fun calculate(
        lastCollectTime: OffsetDateTime?,      // 마지막 수집 시각
        lastCollectedPrice: BigDecimal?,       // 마지막 수집 종가
        symbolIdentifier: MarketSymbolId,
        interval: MarketCandleInterval,
        candles: List<MarketCandle>,           // 기준 간격 캔들 목록
    ): List<MarketCandle>
}
```

**알고리즘**:
1. **시간 범위 계산**: `lastCollectTime + interval` ~ `max(candles.time)`
2. **캔들 그룹화**: `time.floor(interval.timeSpan)`로 그룹화
3. **시간 순회**: 각 시점마다 캔들 생성
   - **실제 데이터 있음**: `combineCandles()` - OHLC 결합
   - **데이터 없음 + 이전 종가 있음**: `createFlatCandle()` - Flat Candle 생성
   - **데이터 없음 + 이전 종가 없음**: 스킵 (최초 수집)

**Flat Candle 생성 규칙**:
```kotlin
MarketCandle(
    open = previousClosePrice,
    high = previousClosePrice,
    low = previousClosePrice,
    close = previousClosePrice,
    volume = BigDecimal.ZERO,
    amount = BigDecimal.ZERO,
)
```

**캔들 결합 규칙**:
```kotlin
MarketCandle(
    time = candles.first().time.floor(interval.timeSpan),
    open = sortedCandles.first().open,
    high = sortedCandles.maxOf { it.high },
    low = sortedCandles.minOf { it.low },
    close = sortedCandles.last().close,
    volume = sortedCandles.sumOf { it.volume },
    amount = sortedCandles.sumOf { it.amount },
)
```

---

## 6. Domain Event

### 6.1 MarketSymbol 이벤트

```kotlin
// 추상 기본 이벤트
abstract class AbstractMarketSymbolEvent(
    open val identifier: MarketSymbolId,
    open val code: MarketSymbolCode,
    open val name: String,
    open val market: MarketType,
    open val status: MarketSymbolStatus,
    open val createdDate: OffsetDateTime,
    open val modifiedDate: OffsetDateTime,
)

// 구체적 이벤트
data class MarketSymbolListedEvent(...)
data class MarketSymbolWarningEvent(...)
data class MarketSymbolCautionEvent(...)
data class MarketSymbolTradingHaltedEvent(...)
data class MarketSymbolDelistedEvent(...)
```

### 6.2 MarketCandleCollectTask 이벤트

```kotlin
// 수집 완료 이벤트 (간격 계산 트리거)
data class MarketCandleCollectTaskCollectedEvent(
    val identifier: MarketCandleCollectTaskId,
    val symbolIdentifier: MarketSymbolId,
    val interval: MarketCandleInterval,
    val createdDate: OffsetDateTime,
    val lastCollectedTime: OffsetDateTime?,
    val lastCollectedPrice: BigDecimal?,
    val status: MarketCandleCollectStatus,
) : AbstractMarketCandleCollectTaskEvent
```
