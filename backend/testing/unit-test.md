# 테스트 피라미드 & 단위 테스트

> 원본: `backend/testing-strategy.md` Section 1~2

---

## 1. 테스트 피라미드

| 계층 | 비율 | 도구 | 범위 |
|------|------|------|------|
| Unit Test | 70% | JUnit 5, MockK | 도메인 모델, 도메인 서비스, Value Object |
| Integration Test | 20% | Testcontainers, Spring Boot Test | DB, Kafka, Redis, gRPC |
| E2E Test | 10% | REST Assured, Testcontainers | 서비스 간 전체 흐름 |

---

## 2. 단위 테스트 규칙

### 2.1 공통 규칙

- 모든 테스트는 **Given-When-Then** 패턴을 따른다.
- 테스트 데이터는 **Builder 패턴** 또는 **Fixture** 를 사용한다.
- 프로퍼티명은 **Identifier** 접미사를 사용한다 (예: `userIdentifier`, `agentIdentifier`).
- 외부 의존성은 MockK로 격리한다.

### 2.2 도메인 모델 테스트

각 Aggregate Root의 상태 전이를 검증하고, 불변식(Invariant) 위반 시 예외 발생을 확인한다.
Value Object의 유효성 검증도 포함한다.

#### User

```kotlin
@Test
fun `withdraw_정상상태_WITHDRAWN으로전이`() {
    // Given: ACTIVE 상태의 User
    // When: withdraw() 호출
    // Then: status == WITHDRAWN, updatedAt 갱신
}

@Test
fun `withdraw_이미탈퇴상태_AccountWithdrawnException`() {
    // Given: WITHDRAWN 상태의 User
    // When: withdraw() 호출
    // Then: AccountWithdrawnException 발생
}

@Test
fun `activate_WITHDRAWN상태에서시도_InvalidStateException`() {
    // Given: WITHDRAWN 상태의 User
    // When: activate() 호출
    // Then: InvalidStateException 발생 (종료 상태에서 복구 불가)
}
```

#### MarketCandleCollectTask

```kotlin
@Test
fun `collectStart_IDLE상태_COLLECTING으로전이`() {
    // Given: IDLE 상태, retryCount = 0
    // When: collectStart() 호출
    // Then: status == COLLECTING
}

@Test
fun `collectStart_COLLECTING상태_InvalidStateException`() {
    // Given: 이미 COLLECTING 상태
    // When: collectStart() 호출
    // Then: InvalidStateException 발생
}

@Test
fun `collectFail_retryCount초과_PAUSED상태전이`() {
    // Given: retryCount == MAX_RETRY_COUNT (3)
    // When: collectFail() 호출
    // Then: status == PAUSED, 자동 재시도 불가
}

@Test
fun `collectFail_retryCount미만_IDLE로복귀하고retryCount증가`() {
    // Given: retryCount < MAX_RETRY_COUNT
    // When: collectFail() 호출
    // Then: status == IDLE, retryCount += 1
}
```

#### Agent

```kotlin
@Test
fun `activate_INACTIVE상태_ACTIVE전이및Portfolio초기화`() {
    // Given: INACTIVE 상태의 Agent, initialCapital = 10,000,000
    // When: activate() 호출
    // Then: status == ACTIVE, Portfolio 생성 (cash = initialCapital, reservedCash = 0)
}

@Test
fun `terminate_ACTIVE상태_TERMINATED전이`() {
    // Given: ACTIVE 상태의 Agent
    // When: terminate() 호출
    // Then: status == TERMINATED
}

@Test
fun `activate_TERMINATED상태_InvalidStateException`() {
    // Given: TERMINATED 상태의 Agent
    // When: activate() 호출
    // Then: InvalidStateException 발생 (종료 상태에서 복구 불가)
}

@Test
fun `pause_ACTIVE상태_PAUSED전이`() {
    // Given: ACTIVE 상태의 Agent
    // When: pause() 호출
    // Then: status == PAUSED
}

@Test
fun `resume_PAUSED상태_ACTIVE전이`() {
    // Given: PAUSED 상태의 Agent
    // When: resume() 호출
    // Then: status == ACTIVE
}
```

#### Strategy

```kotlin
@Test
fun `validate_DRAFT상태_VALIDATED전이`() {
    // Given: DRAFT 상태의 Strategy
    // When: validate() 호출
    // Then: status == VALIDATED
}

@Test
fun `deprecate_VALIDATED상태_DEPRECATED전이`() {
    // Given: VALIDATED 상태의 Strategy
    // When: deprecate() 호출
    // Then: status == DEPRECATED
}

@Test
fun `Agent생성시_DEPRECATED전략할당_StrategyDeprecatedException`() {
    // Given: DEPRECATED 상태의 Strategy
    // When: Agent 생성 시 해당 Strategy 할당 시도
    // Then: StrategyDeprecatedException 발생
}

@Test
fun `Agent생성시_DRAFT전략할당_정상생성`() {
    // Given: DRAFT 상태의 Strategy
    // When: Agent 생성 시 해당 Strategy 할당
    // Then: Agent 정상 생성 (가상거래용)
}
```

#### Portfolio

```kotlin
@Test
fun `reserveCash_가용현금충분_reservedCash증가`() {
    // Given: cash = 10,000,000, reservedCash = 0
    // When: reserveCash(5,000,000) 호출
    // Then: reservedCash == 5,000,000
}

@Test
fun `reserveCash_가용현금부족_InsufficientCashException`() {
    // Given: cash = 1,000,000, reservedCash = 500,000
    // When: reserveCash(1,000,000) 호출
    // Then: InsufficientCashException 발생 (가용: 500,000 < 요청: 1,000,000)
}

@Test
fun `reserveQuantity_가용수량부족_InsufficientPositionException`() {
    // Given: position.quantity = 10, position.reservedQuantity = 8
    // When: reserveQuantity(5) 호출
    // Then: InsufficientPositionException 발생 (가용: 2 < 요청: 5)
}

@Test
fun `releaseReservation_점유해제후_reservedCash감소`() {
    // Given: reservedCash = 5,000,000
    // When: releaseReservation(3,000,000) 호출
    // Then: reservedCash == 2,000,000
}
```

#### Order (Trade Service)

```kotlin
@Test
fun `상태전이_PENDING에서SUBMITTED_정상전이`() {
    // Given: PENDING 상태의 Order
    // When: markSubmitted(exchangeOrderId) 호출
    // Then: status == SUBMITTED, exchangeOrderId 설정
}

@Test
fun `상태전이_SUBMITTED에서PARTIALLY_FILLED_Execution생성`() {
    // Given: SUBMITTED 상태, requestedQuantity = 100
    // When: addExecution(quantity=50, price=1000, fee=5) 호출
    // Then: status == PARTIALLY_FILLED, executedQuantity == 50, averageExecutedPrice 계산
}

@Test
fun `상태전이_PARTIALLY_FILLED에서FILLED_완전체결`() {
    // Given: PARTIALLY_FILLED 상태, executedQuantity = 50, requestedQuantity = 100
    // When: addExecution(quantity=50) 호출
    // Then: status == FILLED, executedQuantity == 100
}

@Test
fun `상태전이_PENDING에서REJECTED_종료상태`() {
    // Given: PENDING 상태의 Order
    // When: reject(reason) 호출
    // Then: status == REJECTED
}

@Test
fun `FILLED상태에서_추가상태전이시도_InvalidStateException`() {
    // Given: FILLED 상태의 Order (종료 상태)
    // When: cancel() 호출
    // Then: InvalidStateException 발생
}

@Test
fun `averageExecutedPrice_복수체결시_가중평균계산`() {
    // Given: 1차 체결 quantity=50, price=1000
    // When: 2차 체결 quantity=50, price=1200
    // Then: averageExecutedPrice == (50*1000 + 50*1200) / 100 == 1100
}
```

#### TradeRegistration

```kotlin
@Test
fun `emergencyStop_ACTIVE상태_emergencyStopped플래그설정`() {
    // Given: ACTIVE 상태, emergencyStopped = false
    // When: emergencyStop() 호출
    // Then: emergencyStopped == true, status == PAUSED
}

@Test
fun `emergencyResume_비상정지상태_PAUSED복귀`() {
    // Given: emergencyStopped = true
    // When: emergencyResume() 호출
    // Then: emergencyStopped == false, status == PAUSED (자동 ACTIVE 아님)
}
```

### 2.3 도메인 서비스 테스트

#### AgentRiskManager

```kotlin
@Test
fun `calculateBuyQuantity_가용현금기준_positionSizeRatio적용`() {
    // Given: cash=10,000,000, reservedCash=0, positionSizeRatio=0.5, currentPrice=50,000
    // When: calculateBuyQuantity() 호출
    // Then: suggestedQuantity == 10,000,000 * 0.5 / 50,000 == 100
}

@Test
fun `calculateBuyQuantity_maxConcurrentPositions도달_신규포지션HOLD전환`() {
    // Given: 현재 포지션 3개, maxConcurrentPositions = 3, 신규 심볼 BUY 신호
    // When: applySizing() 호출
    // Then: signalType == HOLD (포지션 수 제한)
}

@Test
fun `calculateBuyQuantity_기존포지션추가매수_maxConcurrentPositions무시`() {
    // Given: 현재 포지션 3개(BTC 포함), maxConcurrentPositions = 3, BTC BUY 신호
    // When: applySizing() 호출
    // Then: 정상 수량 계산 (추가 매수이므로 포지션 수 체크 안 함)
}

@Test
fun `checkStopCondition_손절조건충족_STOP_LOSS반환`() {
    // Given: averagePrice=50,000, stopLossPercent=0.05, currentPrice=47,000
    // When: checkStopCondition() 호출
    // Then: StopConditionResult.STOP_LOSS (47,000 <= 50,000 * 0.95 = 47,500)
}

@Test
fun `checkStopCondition_익절조건충족_TAKE_PROFIT반환`() {
    // Given: averagePrice=50,000, takeProfitPercent=0.10, currentPrice=56,000
    // When: checkStopCondition() 호출
    // Then: StopConditionResult.TAKE_PROFIT (56,000 >= 50,000 * 1.10 = 55,000)
}

@Test
fun `checkStopCondition_손절익절미설정_NONE반환`() {
    // Given: stopLossPercent=null, takeProfitPercent=null
    // When: checkStopCondition() 호출
    // Then: StopConditionResult.NONE (검사 건너뜀)
}

@Test
fun `checkLossLimits_일일손실한도초과_DAILY_EXCEEDED`() {
    // Given: initialCapital=10,000,000, 당일 periodLoss = -350,000 (-3.5%)
    // When: checkLossLimits() 호출
    // Then: LossLimitResult.DAILY_EXCEEDED (3.5% > 3% 한도)
}
```

#### PortfolioUpdater

```kotlin
@Test
fun `BUY체결반영_reservedCash해제및cash차감`() {
    // Given: reservedCash=100,000 (signalPrice=1,000, quantity=100)
    // When: ExecutionConfirmedEvent(side=BUY, quantity=100, price=1,050, fee=100) 수신
    // Then: reservedCash -= 100 * 1,000 = 100,000
    //       cash -= 100 * 1,050 + 100 = 105,100
    //       position 생성 (quantity=100, averagePrice=1,050)
}

@Test
fun `SELL체결반영_reservedQuantity해제및realizedPnl갱신`() {
    // Given: position(quantity=100, reservedQuantity=100, averagePrice=1,000)
    // When: ExecutionConfirmedEvent(side=SELL, quantity=100, price=1,200, fee=50) 수신
    // Then: reservedQuantity -= 100
    //       position.quantity -= 100
    //       cash += 100 * 1,200 - 50 = 119,950
    //       realizedPnl += (1,200 - 1,000) * 100 - 50 = 19,950
}

@Test
fun `부분체결후취소_미체결분점유해제`() {
    // Given: BUY 신호 suggestedQuantity=100, signalPrice=1,000 → reservedCash=100,000
    //        부분 체결 50개 완료 → reservedCash=50,000
    // When: OrderFailedEvent(remainingQuantity=50) 수신
    // Then: reservedCash -= 50 * 1,000 = 50,000 → reservedCash == 0
    //       cash는 변경 없음 (실제 자산이 아닌 점유만 해제)
}

@Test
fun `SELL실패_reservedQuantity만해제`() {
    // Given: position.reservedQuantity = 100
    // When: OrderFailedEvent(side=SELL, remainingQuantity=100) 수신
    // Then: position.reservedQuantity -= 100
    //       position.quantity는 변경 없음
}
```

#### MarketCandleIntervalCalculator

```kotlin
@Test
fun `캔들결합_1분캔들을5분캔들로결합`() {
    // Given: 5개의 1분 캔들
    // When: combine(candles, MINUTE_5) 호출
    // Then: 1개의 5분 캔들 (open=첫 캔들, close=마지막 캔들, high=최대, low=최소, volume=합산)
}

@Test
fun `FlatCandle생성_빈구간처리`() {
    // Given: 이전 캔들 close=50,000, 빈 구간 발생
    // When: fillGap() 호출
    // Then: open=high=low=close=50,000, volume=0
}

@Test
fun `빈구간처리_중간캔들누락시_이전종가로채움`() {
    // Given: 1분 캔들 [00:00, 00:01, (누락), 00:03, 00:04]
    // When: fillGaps() 호출
    // Then: 00:02 구간에 Flat Candle 삽입 (이전 종가 기준)
}
```

### 2.4 기술 지표 테스트

알려진 값(Known Values)으로 계산 결과를 검증한다. 소수점 오차 범위는 `SCALE=10` 기준으로 설정한다.

#### SMA (단순 이동평균)

```kotlin
@Test
fun `SMA_정상계산_알려진값검증`() {
    // Given: prices = [10, 20, 30, 40, 50], period = 5
    // When: sma(prices, 5) 호출
    // Then: result == 30.0
}

@Test
fun `SMA_데이터부족_IllegalArgumentException`() {
    // Given: prices = [10, 20], period = 5
    // When: sma(prices, 5) 호출
    // Then: IllegalArgumentException ("데이터 부족: 2 < 5")
}
```

#### EMA (지수 이동평균)

```kotlin
@Test
fun `EMA_정상계산_초기값은SMA`() {
    // Given: prices = [22, 24, 23, 25, 26, 28, 27, 29, 30, 31] (과거순), period = 5
    // When: ema(prices, 5) 호출
    // Then: 초기 SMA = (22+24+23+25+26)/5 = 24.0, 이후 지수 가중 적용
}

@Test
fun `EMA_모든값동일_입력값과동일`() {
    // Given: prices = [100, 100, 100, 100, 100], period = 3
    // When: ema(prices, 3) 호출
    // Then: result == 100.0
}
```

#### RSI (상대강도지수)

```kotlin
@Test
fun `RSI_정상계산_알려진값검증`() {
    // Given: 15개 이상의 종가 시계열 (period = 14)
    // When: rsi(prices, 14) 호출
    // Then: 0 <= result <= 100
}

@Test
fun `RSI_모든값상승_RSI100`() {
    // Given: 연속 상승 prices (모든 delta > 0)
    // When: rsi(prices, 14) 호출
    // Then: result == 100 (avgLoss == 0)
}

@Test
fun `RSI_모든값하락_RSI0에근접`() {
    // Given: 연속 하락 prices (모든 delta < 0)
    // When: rsi(prices, 14) 호출
    // Then: result 0에 근접
}

@Test
fun `RSI_데이터부족_IllegalArgumentException`() {
    // Given: prices 개수 < period + 1
    // When: rsi(prices, 14) 호출
    // Then: IllegalArgumentException
}
```

#### MACD (이동평균 수렴확산)

```kotlin
@Test
fun `MACD_정상계산_macdLine과signalLine산출`() {
    // Given: 35개 이상 종가 시계열 (longPeriod=26 + signalPeriod=9)
    // When: macd(prices) 호출
    // Then: MacdResult(macdLine, signalLine, histogram) 반환
    //       histogram == macdLine - signalLine
}

@Test
fun `MACD_데이터부족_IllegalArgumentException`() {
    // Given: prices 개수 < longPeriod + signalPeriod
    // When: macd(prices) 호출
    // Then: IllegalArgumentException
}
```

#### Bollinger Bands (볼린저 밴드)

```kotlin
@Test
fun `BollingerBands_정상계산_상하단밴드산출`() {
    // Given: prices = [동일 패턴 20개], period = 20, multiplier = 2.0
    // When: bollingerBands(prices, 20, 2.0) 호출
    // Then: middle == SMA(20), upper == middle + 2*stdDev, lower == middle - 2*stdDev
}

@Test
fun `BollingerBands_모든값동일_상하단밴드가middle과동일`() {
    // Given: prices = [100, 100, ..., 100] (20개)
    // When: bollingerBands(prices, 20, 2.0) 호출
    // Then: upper == middle == lower == 100 (stdDev == 0)
}

@Test
fun `BollingerBands_극단적변동_밴드폭확대`() {
    // Given: prices에 극단적 변동 포함 (예: [100, 200, 50, 300, ...])
    // When: bollingerBands(prices, 20, 2.0) 호출
    // Then: upper - lower 값이 안정적 데이터 대비 크게 산출
}
```

### 2.5 전략 신호 생성 테스트

#### MA Crossover (이동평균 크로스오버)

```kotlin
@Test
fun `MACrossover_GoldenCross_BUY신호`() {
    // Given: 이전 시점 shortMA <= longMA, 현재 시점 shortMA > longMA
    // When: analyze(candles) 호출
    // Then: type == SignalType.BUY
}

@Test
fun `MACrossover_DeadCross_SELL신호`() {
    // Given: 이전 시점 shortMA >= longMA, 현재 시점 shortMA < longMA
    // When: analyze(candles) 호출
    // Then: type == SignalType.SELL
}

@Test
fun `MACrossover_교차없음_HOLD`() {
    // Given: 이전과 현재 모두 shortMA > longMA (상승 추세 유지)
    // When: analyze(candles) 호출
    // Then: type == SignalType.HOLD
}

@Test
fun `MACrossover_confidence_괴리율비례`() {
    // Given: shortMA와 longMA의 차이가 큰 캔들 데이터
    // When: analyze(candles) 호출
    // Then: confidence == min(|shortMA - longMA| / longMA, 1.0)
}
```

#### RSI 과매수/과매도

```kotlin
@Test
fun `RSI_과매도구간_BUY신호`() {
    // Given: RSI < oversoldThreshold (30)
    // When: analyze(candles) 호출
    // Then: type == SignalType.BUY
}

@Test
fun `RSI_과매수구간_SELL신호`() {
    // Given: RSI > overboughtThreshold (70)
    // When: analyze(candles) 호출
    // Then: type == SignalType.SELL
}

@Test
fun `RSI_중립구간_HOLD`() {
    // Given: oversoldThreshold <= RSI <= overboughtThreshold
    // When: analyze(candles) 호출
    // Then: type == SignalType.HOLD
}
```

#### Bollinger Bands 브레이크아웃

```kotlin
@Test
fun `Bollinger_하단이탈_BUY신호`() {
    // Given: close < lowerBand
    // When: analyze(candles) 호출
    // Then: type == SignalType.BUY (평균 회귀 기대)
}

@Test
fun `Bollinger_상단이탈_SELL신호`() {
    // Given: close > upperBand
    // When: analyze(candles) 호출
    // Then: type == SignalType.SELL (과열 조정 기대)
}

@Test
fun `Bollinger_밴드내부_HOLD`() {
    // Given: lowerBand <= close <= upperBand
    // When: analyze(candles) 호출
    // Then: type == SignalType.HOLD
}

@Test
fun `Bollinger_confidence_밴드경계이탈비례`() {
    // Given: close가 상단 밴드를 크게 초과
    // When: analyze(candles) 호출
    // Then: confidence == min(|close - middle| / (upper - middle), 1.0)
}
```
