# Agent Service 설계

## 개요

Agent Service는 거래 전략을 정의하고 실행하는 서비스입니다.

- **언어**: Kotlin 2.0.21
- **프레임워크**: Spring Boot 3.4.0
- **아키텍처**: Hexagonal Architecture (Ports & Adapters)
- **데이터베이스**: PostgreSQL
- **메시징**: Apache Kafka

## 핵심 개념

### Agent란?
Agent는 시장 데이터를 분석하고 매수/매도 의사결정을 내리는 **자율적인 거래 주체**입니다.

```
Agent = Strategy + Portfolio Management + Risk Management
```

## 도메인 정의

### Strategy (전략)

거래 의사결정 로직을 정의하는 도메인 객체입니다.

**생명 주기**:
- 사용자가 전략을 생성하면 `DRAFT` 상태로 시작합니다.
- 백테스팅을 통과하면 `VALIDATED` 상태로 변경됩니다.
- 가상거래나 실거래에 배포되면 `DEPLOYED` 상태가 됩니다.

**상태 정의**:
- `DRAFT`: 작성 중인 전략
- `VALIDATED`: 백테스팅 통과한 전략
- `DEPLOYED`: 배포된 전략 (가상거래 또는 실거래)
- `PAUSED`: 일시 중지된 전략
- `ARCHIVED`: 보관된 전략 (더 이상 사용하지 않음)

| **프로퍼티 (한글)** | **프로퍼티 (영문)** | **개념**                                     | **필수** | **불변** |
|:--------------------|:--------------------|:--------------------------------------------|:---------|:---------|
| 식별자              | identifier          | 전략을 식별하기 위한 UUID                    | O        | O        |
| 이름                | name                | 전략의 이름                                  | O        | X        |
| 설명                | description         | 전략에 대한 설명                             | X        | X        |
| 타입                | type                | 전략 타입 (MANUAL, AI)                       | O        | O        |
| 시장                | market              | 적용 시장 (COIN, STOCK)                      | O        | O        |
| 상태                | status              | 전략의 현재 상태                             | O        | X        |
| 파라미터            | parameters          | 전략 파라미터 (JSON)                         | X        | X        |
| 생성자              | creator             | 전략을 생성한 사용자                         | O        | O        |
| 생성일              | created_date        | 전략이 생성된 시각                           | O        | O        |
| 수정일              | modified_date       | 전략이 마지막으로 수정된 시각                | O        | X        |

**비즈니스 메서드**:
- `validate()`: 백테스팅 통과 시 상태를 `VALIDATED`로 변경
- `deploy()`: 전략을 배포 (상태를 `DEPLOYED`로 변경)
- `pause()`: 전략 일시 중지
- `resume()`: 전략 재개
- `archive()`: 전략 보관

**전략 타입**:

#### 1. MANUAL (수동 전략)
사용자가 직접 정의한 기술적 지표 기반 전략

**예시**:
- 이동평균 크로스오버
- RSI 과매수/과매도
- 볼린저 밴드 브레이크아웃

**파라미터 예시** (이동평균 크로스오버):
```json
{
  "shortPeriod": 5,
  "longPeriod": 20,
  "entryCondition": "GOLDEN_CROSS",
  "exitCondition": "DEAD_CROSS"
}
```

#### 2. AI (AI 기반 전략)
강화학습 또는 머신러닝 모델을 사용하는 전략 (Phase 5)

---

### Signal (신호)

전략이 생성한 매수/매도/관망 신호를 나타내는 값 객체(Value Object)입니다.

| **프로퍼티 (한글)** | **프로퍼티 (영문)** | **개념**                                     | **필수** | **불변** |
|:--------------------|:--------------------|:--------------------------------------------|:---------|:---------|
| 전략식별자          | strategy_identifier | 신호를 생성한 전략의 식별자                  | O        | O        |
| 심볼식별자          | symbol_identifier   | 거래 대상 심볼의 식별자                      | O        | O        |
| 시각                | time                | 신호가 생성된 시각                           | O        | O        |
| 타입                | type                | 신호 타입 (BUY, SELL, HOLD)                  | O        | O        |
| 신뢰도              | confidence          | 신호의 신뢰도 (0.0 ~ 1.0)                    | O        | O        |
| 가격                | price               | 신호 생성 시점의 가격                        | O        | O        |
| 이유                | reason              | 신호 생성 이유 (JSON)                        | X        | O        |

**신호 타입**:
- `BUY`: 매수 신호
- `SELL`: 매도 신호
- `HOLD`: 관망 (아무 행동도 하지 않음)

**이유 예시** (이동평균 크로스오버):
```json
{
  "indicator": "MA_CROSSOVER",
  "shortMA": 51234.56,
  "longMA": 50123.45,
  "crossType": "GOLDEN_CROSS"
}
```

---

### Portfolio (포트폴리오)

Agent가 보유한 자산 현황을 나타내는 도메인 객체입니다.

| **프로퍼티 (한글)** | **프로퍼티 (영문)** | **개념**                                     | **필수** | **불변** |
|:--------------------|:--------------------|:--------------------------------------------|:---------|:---------|
| 식별자              | identifier          | 포트폴리오를 식별하기 위한 UUID              | O        | O        |
| 전략식별자          | strategy_identifier | 포트폴리오를 소유한 전략의 식별자            | O        | O        |
| 초기자본            | initial_capital     | 시작 시 투입된 자본                          | O        | O        |
| 현금                | cash                | 현재 보유 현금                               | O        | X        |
| 총자산가치          | total_value         | 현금 + 보유 포지션 가치의 합                 | O        | X        |
| 생성일              | created_date        | 포트폴리오가 생성된 시각                     | O        | O        |
| 수정일              | modified_date       | 포트폴리오가 마지막으로 수정된 시각          | O        | X        |

**비즈니스 메서드**:
- `buy(symbol, quantity, price)`: 자산 매수
- `sell(symbol, quantity, price)`: 자산 매도
- `calculateTotalValue(currentPrices)`: 총 자산 가치 계산
- `getReturnRate()`: 수익률 계산 `(totalValue - initialCapital) / initialCapital`

---

### Position (포지션)

특정 심볼에 대한 보유 현황을 나타내는 도메인 객체입니다.

| **프로퍼티 (한글)** | **프로퍼티 (영문)** | **개념**                                     | **필수** | **불변** |
|:--------------------|:--------------------|:--------------------------------------------|:---------|:---------|
| 식별자              | identifier          | 포지션을 식별하기 위한 UUID                  | O        | O        |
| 포트폴리오식별자    | portfolio_identifier| 포지션이 속한 포트폴리오의 식별자            | O        | O        |
| 심볼식별자          | symbol_identifier   | 보유 자산의 심볼 식별자                      | O        | O        |
| 수량                | quantity            | 보유 수량                                    | O        | X        |
| 평균단가            | average_price       | 평균 매수 가격                               | O        | X        |
| 생성일              | created_date        | 포지션이 생성된 시각 (최초 매수 시각)        | O        | O        |
| 수정일              | modified_date       | 포지션이 마지막으로 수정된 시각              | O        | X        |

**비즈니스 메서드**:
- `addQuantity(quantity, price)`: 추가 매수 (평균단가 재계산)
- `reduceQuantity(quantity)`: 매도 (수량 감소)
- `getTotalCost()`: 총 매수 비용 계산 `quantity * average_price`
- `getCurrentValue(currentPrice)`: 현재 가치 계산 `quantity * currentPrice`
- `getUnrealizedPnL(currentPrice)`: 미실현 손익 계산

**평균단가 계산 로직**:
```kotlin
fun addQuantity(newQuantity: BigDecimal, newPrice: BigDecimal) {
    val totalCost = (quantity * averagePrice) + (newQuantity * newPrice)
    quantity += newQuantity
    averagePrice = totalCost / quantity
}
```

---

### Trade (거래 내역)

실제 실행된 거래 내역을 기록하는 불변 값 객체입니다.

| **프로퍼티 (한글)** | **프로퍼티 (영문)** | **개념**                                     | **필수** | **불변** |
|:--------------------|:--------------------|:--------------------------------------------|:---------|:---------|
| 식별자              | identifier          | 거래 내역을 식별하기 위한 UUID               | O        | O        |
| 포트폴리오식별자    | portfolio_identifier| 거래가 발생한 포트폴리오의 식별자            | O        | O        |
| 심볼식별자          | symbol_identifier   | 거래 대상 심볼의 식별자                      | O        | O        |
| 시각                | time                | 거래가 체결된 시각                           | O        | O        |
| 타입                | type                | 거래 타입 (BUY, SELL)                        | O        | O        |
| 수량                | quantity            | 거래 수량                                    | O        | O        |
| 가격                | price               | 체결 가격                                    | O        | O        |
| 수수료              | fee                 | 거래 수수료                                  | O        | O        |
| 총금액              | total_amount        | 거래 총 금액 (수량 * 가격 ± 수수료)          | O        | O        |

**거래 타입**:
- `BUY`: 매수
- `SELL`: 매도

---

## 기술적 지표 라이브러리

Agent가 전략을 실행할 때 사용하는 기술적 지표 계산 유틸리티입니다.

### 지원 지표

#### 1. MA (Moving Average, 이동평균)
```kotlin
fun calculateMA(candles: List<MarketCandle>, period: Int): BigDecimal {
    return candles.takeLast(period).map { it.close }.average()
}
```

#### 2. EMA (Exponential Moving Average, 지수 이동평균)
```kotlin
fun calculateEMA(candles: List<MarketCandle>, period: Int): BigDecimal {
    val multiplier = 2.0 / (period + 1)
    var ema = candles.first().close
    candles.drop(1).forEach { candle ->
        ema = (candle.close * multiplier) + (ema * (1 - multiplier))
    }
    return ema
}
```

#### 3. RSI (Relative Strength Index, 상대강도지수)
```kotlin
fun calculateRSI(candles: List<MarketCandle>, period: Int = 14): BigDecimal {
    val gains = mutableListOf<BigDecimal>()
    val losses = mutableListOf<BigDecimal>()

    for (i in 1 until candles.size) {
        val change = candles[i].close - candles[i - 1].close
        if (change > 0) {
            gains.add(change)
            losses.add(BigDecimal.ZERO)
        } else {
            gains.add(BigDecimal.ZERO)
            losses.add(change.abs())
        }
    }

    val avgGain = gains.takeLast(period).average()
    val avgLoss = losses.takeLast(period).average()

    if (avgLoss == BigDecimal.ZERO) return BigDecimal(100)

    val rs = avgGain / avgLoss
    return 100 - (100 / (1 + rs))
}
```

#### 4. MACD (Moving Average Convergence Divergence)
```kotlin
data class MACD(
    val macd: BigDecimal,
    val signal: BigDecimal,
    val histogram: BigDecimal
)

fun calculateMACD(
    candles: List<MarketCandle>,
    fastPeriod: Int = 12,
    slowPeriod: Int = 26,
    signalPeriod: Int = 9
): MACD {
    val fastEMA = calculateEMA(candles, fastPeriod)
    val slowEMA = calculateEMA(candles, slowPeriod)
    val macdLine = fastEMA - slowEMA
    val signalLine = calculateEMA(candles, signalPeriod) // simplified
    val histogram = macdLine - signalLine

    return MACD(macdLine, signalLine, histogram)
}
```

#### 5. Bollinger Bands (볼린저 밴드)
```kotlin
data class BollingerBands(
    val upper: BigDecimal,
    val middle: BigDecimal,
    val lower: BigDecimal
)

fun calculateBollingerBands(
    candles: List<MarketCandle>,
    period: Int = 20,
    stdDev: Double = 2.0
): BollingerBands {
    val middle = calculateMA(candles, period)
    val variance = candles.takeLast(period)
        .map { (it.close - middle).pow(2) }
        .average()
    val standardDeviation = sqrt(variance)

    val upper = middle + (standardDeviation * stdDev)
    val lower = middle - (standardDeviation * stdDev)

    return BollingerBands(upper, middle, lower)
}
```

---

## 전략 인터페이스

모든 전략은 다음 인터페이스를 구현해야 합니다:

```kotlin
interface TradingStrategy {
    /**
     * 전략 식별자
     */
    val strategyIdentifier: UUID

    /**
     * 시장 데이터를 분석하여 신호를 생성합니다.
     *
     * @param symbol 분석 대상 심볼
     * @param candles 최근 캔들 데이터
     * @param portfolio 현재 포트폴리오 상태
     * @return 생성된 신호 (BUY, SELL, HOLD)
     */
    fun analyze(
        symbol: MarketSymbol,
        candles: List<MarketCandle>,
        portfolio: Portfolio
    ): Signal

    /**
     * 신호를 기반으로 주문 크기를 결정합니다.
     *
     * @param signal 생성된 신호
     * @param portfolio 현재 포트폴리오 상태
     * @param currentPrice 현재 가격
     * @return 주문 수량
     */
    fun calculateOrderSize(
        signal: Signal,
        portfolio: Portfolio,
        currentPrice: BigDecimal
    ): BigDecimal

    /**
     * 전략 파라미터를 반환합니다.
     */
    fun getParameters(): Map<String, Any>
}
```

---

## 수동 전략 예시

### 1. 이동평균 크로스오버 전략

```kotlin
class MovingAverageCrossoverStrategy(
    override val strategyIdentifier: UUID,
    private val shortPeriod: Int = 5,
    private val longPeriod: Int = 20
) : TradingStrategy {

    override fun analyze(
        symbol: MarketSymbol,
        candles: List<MarketCandle>,
        portfolio: Portfolio
    ): Signal {
        require(candles.size >= longPeriod) {
            "Not enough candles for analysis"
        }

        val shortMA = calculateMA(candles, shortPeriod)
        val longMA = calculateMA(candles, longPeriod)

        val prevShortMA = calculateMA(candles.dropLast(1), shortPeriod)
        val prevLongMA = calculateMA(candles.dropLast(1), longPeriod)

        val currentPrice = candles.last().close

        return when {
            // Golden Cross: 매수 신호
            prevShortMA <= prevLongMA && shortMA > longMA -> {
                Signal(
                    strategyIdentifier = strategyIdentifier,
                    symbolIdentifier = symbol.identifier,
                    time = candles.last().time,
                    type = SignalType.BUY,
                    confidence = 0.8,
                    price = currentPrice,
                    reason = mapOf(
                        "indicator" to "MA_CROSSOVER",
                        "shortMA" to shortMA,
                        "longMA" to longMA,
                        "crossType" to "GOLDEN_CROSS"
                    )
                )
            }
            // Dead Cross: 매도 신호
            prevShortMA >= prevLongMA && shortMA < longMA -> {
                Signal(
                    strategyIdentifier = strategyIdentifier,
                    symbolIdentifier = symbol.identifier,
                    time = candles.last().time,
                    type = SignalType.SELL,
                    confidence = 0.8,
                    price = currentPrice,
                    reason = mapOf(
                        "indicator" to "MA_CROSSOVER",
                        "shortMA" to shortMA,
                        "longMA" to longMA,
                        "crossType" to "DEAD_CROSS"
                    )
                )
            }
            else -> {
                // 관망
                Signal(
                    strategyIdentifier = strategyIdentifier,
                    symbolIdentifier = symbol.identifier,
                    time = candles.last().time,
                    type = SignalType.HOLD,
                    confidence = 1.0,
                    price = currentPrice,
                    reason = mapOf("indicator" to "MA_CROSSOVER")
                )
            }
        }
    }

    override fun calculateOrderSize(
        signal: Signal,
        portfolio: Portfolio,
        currentPrice: BigDecimal
    ): BigDecimal {
        return when (signal.type) {
            SignalType.BUY -> {
                // 보유 현금의 50%를 사용
                val budget = portfolio.cash * BigDecimal("0.5")
                budget / currentPrice
            }
            SignalType.SELL -> {
                // 보유 수량의 100%를 매도
                val position = portfolio.getPosition(signal.symbolIdentifier)
                position?.quantity ?: BigDecimal.ZERO
            }
            SignalType.HOLD -> BigDecimal.ZERO
        }
    }

    override fun getParameters(): Map<String, Any> {
        return mapOf(
            "shortPeriod" to shortPeriod,
            "longPeriod" to longPeriod
        )
    }
}
```

### 2. RSI 과매수/과매도 전략

```kotlin
class RSIStrategy(
    override val strategyIdentifier: UUID,
    private val period: Int = 14,
    private val oversoldThreshold: Int = 30,
    private val overboughtThreshold: Int = 70
) : TradingStrategy {

    override fun analyze(
        symbol: MarketSymbol,
        candles: List<MarketCandle>,
        portfolio: Portfolio
    ): Signal {
        require(candles.size >= period + 1) {
            "Not enough candles for RSI calculation"
        }

        val rsi = calculateRSI(candles, period)
        val currentPrice = candles.last().close

        return when {
            rsi < oversoldThreshold -> {
                // 과매도: 매수 신호
                Signal(
                    strategyIdentifier = strategyIdentifier,
                    symbolIdentifier = symbol.identifier,
                    time = candles.last().time,
                    type = SignalType.BUY,
                    confidence = (oversoldThreshold - rsi) / oversoldThreshold,
                    price = currentPrice,
                    reason = mapOf(
                        "indicator" to "RSI",
                        "rsi" to rsi,
                        "condition" to "OVERSOLD"
                    )
                )
            }
            rsi > overboughtThreshold -> {
                // 과매수: 매도 신호
                Signal(
                    strategyIdentifier = strategyIdentifier,
                    symbolIdentifier = symbol.identifier,
                    time = candles.last().time,
                    type = SignalType.SELL,
                    confidence = (rsi - overboughtThreshold) / (100 - overboughtThreshold),
                    price = currentPrice,
                    reason = mapOf(
                        "indicator" to "RSI",
                        "rsi" to rsi,
                        "condition" to "OVERBOUGHT"
                    )
                )
            }
            else -> {
                // 관망
                Signal(
                    strategyIdentifier = strategyIdentifier,
                    symbolIdentifier = symbol.identifier,
                    time = candles.last().time,
                    type = SignalType.HOLD,
                    confidence = 1.0,
                    price = currentPrice,
                    reason = mapOf(
                        "indicator" to "RSI",
                        "rsi" to rsi
                    )
                )
            }
        }
    }

    override fun calculateOrderSize(
        signal: Signal,
        portfolio: Portfolio,
        currentPrice: BigDecimal
    ): BigDecimal {
        return when (signal.type) {
            SignalType.BUY -> {
                // 신뢰도에 비례하여 주문 크기 결정 (최대 현금의 50%)
                val maxBudget = portfolio.cash * BigDecimal("0.5")
                val budget = maxBudget * signal.confidence
                budget / currentPrice
            }
            SignalType.SELL -> {
                // 보유 수량의 100%를 매도
                val position = portfolio.getPosition(signal.symbolIdentifier)
                position?.quantity ?: BigDecimal.ZERO
            }
            SignalType.HOLD -> BigDecimal.ZERO
        }
    }

    override fun getParameters(): Map<String, Any> {
        return mapOf(
            "period" to period,
            "oversoldThreshold" to oversoldThreshold,
            "overboughtThreshold" to overboughtThreshold
        )
    }
}
```

---

## API 엔드포인트

### 전략 관리 API

#### POST /strategies
새로운 전략을 생성합니다.

**요청 예시**:
```json
{
  "name": "MA Crossover 5-20",
  "description": "5일선과 20일선 크로스오버 전략",
  "type": "MANUAL",
  "market": "COIN",
  "parameters": {
    "shortPeriod": 5,
    "longPeriod": 20
  }
}
```

#### GET /strategies
전략 목록을 조회합니다.

**요청 파라미터**:
- `status` (optional): 전략 상태 필터
- `type` (optional): 전략 타입 필터
- `market` (optional): 시장 타입 필터

#### GET /strategies/{strategyIdentifier}
특정 전략의 상세 정보를 조회합니다.

#### PUT /strategies/{strategyIdentifier}
전략을 수정합니다.

#### DELETE /strategies/{strategyIdentifier}
전략을 삭제합니다.

#### PUT /strategies/{strategyIdentifier}/validate
백테스팅 통과 후 전략을 검증 상태로 변경합니다.

#### PUT /strategies/{strategyIdentifier}/deploy
전략을 배포합니다.

#### PUT /strategies/{strategyIdentifier}/pause
전략을 일시 중지합니다.

---

## 데이터베이스 스키마

### strategy 테이블
```sql
CREATE TABLE IF NOT EXISTS strategy (
    identifier    UUID                     NOT NULL,
    name          VARCHAR                  NOT NULL,
    description   TEXT,
    type          VARCHAR                  NOT NULL,
    market        VARCHAR                  NOT NULL,
    status        VARCHAR                  NOT NULL,
    parameters    JSONB,
    creator       UUID                     NOT NULL,
    created_date  TIMESTAMP WITH TIME ZONE NOT NULL,
    modified_date TIMESTAMP WITH TIME ZONE NOT NULL,
    PRIMARY KEY (identifier)
);

CREATE INDEX IF NOT EXISTS strategy_creator_idx ON strategy (creator);
CREATE INDEX IF NOT EXISTS strategy_status_idx ON strategy (status);
```

### portfolio 테이블
```sql
CREATE TABLE IF NOT EXISTS portfolio (
    identifier          UUID                     NOT NULL,
    strategy_identifier UUID                     NOT NULL,
    initial_capital     DECIMAL                  NOT NULL,
    cash                DECIMAL                  NOT NULL,
    total_value         DECIMAL                  NOT NULL,
    created_date        TIMESTAMP WITH TIME ZONE NOT NULL,
    modified_date       TIMESTAMP WITH TIME ZONE NOT NULL,
    PRIMARY KEY (identifier)
);

CREATE INDEX IF NOT EXISTS portfolio_strategy_idx ON portfolio (strategy_identifier);
```

### position 테이블
```sql
CREATE TABLE IF NOT EXISTS position (
    identifier           UUID                     NOT NULL,
    portfolio_identifier UUID                     NOT NULL,
    symbol_identifier    UUID                     NOT NULL,
    quantity             DECIMAL                  NOT NULL,
    average_price        DECIMAL                  NOT NULL,
    created_date         TIMESTAMP WITH TIME ZONE NOT NULL,
    modified_date        TIMESTAMP WITH TIME ZONE NOT NULL,
    PRIMARY KEY (identifier)
);

CREATE INDEX IF NOT EXISTS position_portfolio_idx ON position (portfolio_identifier);
CREATE UNIQUE INDEX IF NOT EXISTS position_portfolio_symbol_idx
    ON position (portfolio_identifier, symbol_identifier);
```

### trade 테이블
```sql
CREATE TABLE IF NOT EXISTS trade (
    identifier           UUID                     NOT NULL,
    portfolio_identifier UUID                     NOT NULL,
    symbol_identifier    UUID                     NOT NULL,
    time                 TIMESTAMP WITH TIME ZONE NOT NULL,
    type                 VARCHAR                  NOT NULL,
    quantity             DECIMAL                  NOT NULL,
    price                DECIMAL                  NOT NULL,
    fee                  DECIMAL                  NOT NULL,
    total_amount         DECIMAL                  NOT NULL,
    PRIMARY KEY (identifier)
);

CREATE INDEX IF NOT EXISTS trade_portfolio_idx ON trade (portfolio_identifier);
CREATE INDEX IF NOT EXISTS trade_time_idx ON trade (time);
```

---

## 다음 단계

- Simulation Service와 연동하여 백테스팅 수행
- VirtualTrade Service와 연동하여 가상거래 실행
- Trade Service와 연동하여 실거래 실행
