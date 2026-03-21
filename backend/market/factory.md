# Market Service — Factory

> 이 문서는 `backend/market/domain.md`에서 분할되었습니다.

---

## 7. Factory

### 7.1 MarketSymbolFactory

```kotlin
object MarketSymbolFactory {
    fun create(
        code: MarketSymbolCode,
        name: String,
        market: MarketType,
        status: MarketSymbolStatus = MarketSymbolStatus.LISTED,
    ): MarketSymbol {
        return MarketSymbol(
            identifier = MarketSymbolId.generate(),
            code = code,
            name = name,
            market = market,
            status = status,
            createdDate = OffsetDateTime.now(),
            modifiedDate = OffsetDateTime.now(),
        )
    }
}
```

### 7.2 MarketCandleCollectTaskFactory

```kotlin
object MarketCandleCollectTaskFactory {
    fun create(
        symbolIdentifier: MarketSymbolId,
        interval: MarketCandleInterval,
    ): MarketCandleCollectTask {
        return MarketCandleCollectTask(
            identifier = MarketCandleCollectTaskId.generate(),
            symbolIdentifier = symbolIdentifier,
            interval = interval,
            createdDate = OffsetDateTime.now(),
            lastCollectedTime = null,
            lastCollectedPrice = null,
            status = MarketCandleCollectStatus.CREATED,
        )
    }
}
```

### 7.3 MarketCandleFactory

```kotlin
object MarketCandleFactory {
    fun create(
        symbolIdentifier: MarketSymbolId,
        interval: MarketCandleInterval,
        time: OffsetDateTime,
        open: BigDecimal,
        high: BigDecimal,
        low: BigDecimal,
        close: BigDecimal,
        volume: BigDecimal,
        amount: BigDecimal,
    ): MarketCandle {
        require(high >= low) { "High must be >= Low" }
        require(high >= open) { "High must be >= Open" }
        require(high >= close) { "High must be >= Close" }
        require(low <= open) { "Low must be <= Open" }
        require(low <= close) { "Low must be <= Close" }
        require(volume >= BigDecimal.ZERO) { "Volume must be >= 0" }
        require(amount >= BigDecimal.ZERO) { "Amount must be >= 0" }

        return MarketCandle(
            symbolIdentifier = symbolIdentifier,
            interval = interval,
            time = time,
            open = open,
            high = high,
            low = low,
            close = close,
            volume = volume,
            amount = amount,
        )
    }
}
```
