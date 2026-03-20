# Trade Pilot — 테스트 전략

> 테스트 피라미드, 계층별 테스트 규칙, Mock 전략, CI 연동 기준

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

---

## 3. 통합 테스트 규칙

### 3.1 도구 및 환경

- **Testcontainers**: PostgreSQL, Kafka, Redis 실제 컨테이너를 사용한다.
- **Spring Boot Test**: `@SpringBootTest(webEnvironment = RANDOM_PORT)` 로 애플리케이션 컨텍스트를 로드한다.
- **테스트 격리**: `@DirtiesContext` 대신 **트랜잭션 롤백** 또는 **테이블 TRUNCATE** 를 사용한다. 컨텍스트 재생성 비용이 크므로 TRUNCATE 방식을 권장한다.

```kotlin
@TestInstance(TestInstance.Lifecycle.PER_CLASS)
@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT)
abstract class IntegrationTestBase {

    @Autowired
    lateinit var jdbcTemplate: JdbcTemplate

    @BeforeEach
    fun cleanUp() {
        jdbcTemplate.execute("TRUNCATE TABLE outbox, processed_events CASCADE")
        // 서비스별 테이블 추가
    }
}
```

### 3.2 DB 통합 테스트

#### Repository 테스트

```kotlin
@Test
fun `findAllByStatus_ACTIVE등록만조회`() {
    // Given: ACTIVE 2건, PAUSED 1건, STOPPED 1건 INSERT
    // When: findAllByStatus(ACTIVE) 호출
    // Then: 2건만 반환
}

@Test
fun `findTimedOutPendingOrders_타임아웃초과주문만조회`() {
    // Given: timeoutAt이 과거인 SUBMITTED 주문 1건, 미래인 주문 1건
    // When: findTimedOutPendingOrders(now) 호출
    // Then: 1건만 반환
}

@Test
fun `findActiveByAgentAndSymbol_중복주문방지인덱스확인`() {
    // Given: agentIdentifier + symbolIdentifier 조합으로 PENDING 주문 존재
    // When: findActiveByAgentAndSymbol(agentIdentifier, symbolIdentifier) 호출
    // Then: 기존 주문 반환 (부분 인덱스 idx_order_active 적중)
}
```

#### Pessimistic Lock 테스트

```kotlin
@Test
fun `PessimisticLock_동시Portfolio접근_순차처리`() {
    // Given: Portfolio (cash=10,000,000)
    // When: 2개 스레드가 동시에 findByAgentIdForUpdate() + reserveCash(6,000,000) 시도
    // Then: 첫 번째 스레드 성공 (reservedCash=6,000,000)
    //       두 번째 스레드 InsufficientCashException (가용: 4,000,000 < 요청: 6,000,000)
}

@Test
fun `PessimisticLock_lockTimeout초과_LockTimeoutException`() {
    // Given: 3초 lock timeout 설정
    // When: 첫 번째 트랜잭션이 5초간 Lock 점유, 두 번째 트랜잭션 대기
    // Then: 두 번째 트랜잭션 LockTimeoutException 발생
}
```

#### Outbox 통합 테스트

```kotlin
@Test
fun `Outbox_트랜잭션내INSERT_Relay가Kafka발행`() {
    // Given: 도메인 상태 변경 + Outbox INSERT (동일 트랜잭션)
    // When: 트랜잭션 커밋
    // Then: Outbox status == PENDING
    //       Relay 실행 후 status == PUBLISHED
    //       Kafka Consumer에서 메시지 수신 확인
}

@Test
fun `Outbox_Kafka발행실패_retryCount증가후재시도`() {
    // Given: Kafka 브로커 일시 중단
    // When: Relay 실행
    // Then: status == FAILED, retryCount += 1
    //       Kafka 브로커 복구 후 다음 Relay 사이클에서 PUBLISHED
}

@Test
fun `Outbox_3회실패_DEAD상태전환`() {
    // Given: retryCount == 2, Kafka 발행 실패
    // When: Relay 실행
    // Then: status == DEAD, retryCount == 3
    //       관리자 알림 발행 확인
}

@Test
fun `Outbox_traceId전파_KafkaConsumer에서동일traceId확인`() {
    // Given: HTTP 요청 traceId = "abc-123"
    // When: Outbox INSERT → Relay → Kafka 발행
    // Then: Kafka Consumer가 수신한 traceparent 헤더에 "abc-123" 포함
}
```

### 3.3 Kafka 통합 테스트

```kotlin
@Test
fun `Kafka_메시지발행후Consumer수신확인`() {
    // Given: AnalyzeAgentCommand 메시지
    // When: Producer가 command.agent.trade.analyze-strategy 토픽에 발행
    // Then: Consumer에서 동일 메시지 수신 (Awaitility 5초 대기)
}

@Test
fun `Kafka_멱등성_동일메시지2회소비시1회만처리`() {
    // Given: 동일 (topic, partition, offset)의 메시지
    // When: Consumer가 2회 소비 시도
    // Then: processed_events 테이블 확인 → 1회만 비즈니스 로직 실행
    //       2회차는 skip (이미 처리됨)
}

@Test
fun `Kafka_DLQ_3회실패후DeadLetterQueue이동`() {
    // Given: 처리 시 항상 예외 발생하는 Consumer
    // When: 메시지 소비 시도 (3회 재시도)
    // Then: dlq.{원본토픽명} 토픽에 메시지 존재 확인
}

@Test
fun `Kafka_CommandReply_callback토픽으로응답발행`() {
    // Given: Command에 callback = "reply.virtual-trade.agent.analyze-strategy" 설정
    // When: Agent Service Consumer가 Command 처리 완료
    // Then: callback 토픽에 Reply 메시지 발행 확인
}

@Test
fun `Kafka_KafkaEnvelope_messageIdentifier기반멱등성`() {
    // Given: 동일 messageIdentifier를 가진 KafkaEnvelope 2개
    // When: Consumer가 순차 소비
    // Then: 첫 번째만 처리, 두 번째는 중복으로 skip
}
```

### 3.4 gRPC 통합 테스트

```kotlin
@Test
fun `gRPC_GetRecentCandles_정상응답`() {
    // Given: Market Service gRPC 서버 기동, DB에 캔들 데이터 INSERT
    // When: GetRecentCandles(symbolIdentifier, interval=MINUTE_1, limit=10) 호출
    // Then: 10개 캔들 응답, 최신순 정렬
}

@Test
fun `gRPC_BacktestStrategy_스트리밍신호순서검증`() {
    // Given: Agent Service gRPC 서버 기동, 100개 캔들 데이터
    // When: BacktestStrategy 스트리밍 호출
    // Then: 시간순으로 신호 수신, 각 신호에 portfolioSnapshot 포함
}

@Test
fun `gRPC_deadline초과_DEADLINE_EXCEEDED`() {
    // Given: 의도적으로 느린 gRPC 서버 (5초 지연)
    // When: deadline 3초로 설정하고 호출
    // Then: StatusRuntimeException(DEADLINE_EXCEEDED) 발생
}

@Test
fun `gRPC_서버미기동_UNAVAILABLE`() {
    // Given: gRPC 서버 미기동 상태
    // When: GetRecentCandles 호출
    // Then: StatusRuntimeException(UNAVAILABLE) 발생
}
```

### 3.5 Redis 통합 테스트

```kotlin
@Test
fun `Redis_캐시Hit_DB조회생략`() {
    // Given: Redis에 캔들 데이터 캐싱 완료
    // When: 동일 키로 조회
    // Then: DB 쿼리 실행 없음, 캐시에서 반환
}

@Test
fun `Redis_캐시Miss_DB조회후캐싱`() {
    // Given: Redis에 해당 키 없음
    // When: 조회 요청
    // Then: DB에서 조회 → Redis에 캐싱 → 다음 조회 시 캐시 Hit
}

@Test
fun `Redis_DistributedLock_동시실행방지`() {
    // Given: Outbox Relay Lock Key = "outbox:relay:market"
    // When: 2개 인스턴스가 동시에 tryLock 시도
    // Then: 1개만 Lock 획득, 나머지는 skip (null 반환)
}

@Test
fun `Redis_TTL만료후_캐시재조회`() {
    // Given: TTL 1초로 캐싱
    // When: 2초 후 조회
    // Then: 캐시 Miss → DB 재조회 → 새 데이터 캐싱
}

@Test
fun `Redis_Lock_leaseTime초과시_자동해제`() {
    // Given: leaseTime = 5초로 Lock 획득
    // When: 6초 경과
    // Then: 다른 인스턴스가 Lock 획득 가능
}
```

---

## 4. E2E 테스트

### 4.1 주요 시나리오

#### 시나리오 1: 가상거래 전체 흐름

```
회원가입 → 로그인 → 전략 생성(MA Crossover)
→ 에이전트 생성 → 에이전트 활성화(Portfolio 초기화)
→ 가상거래 등록 → 스케줄러 트리거(AnalyzeAgentCommand 발행)
→ Agent Service 신호 생성(BUY) → VirtualTrade Service 가상 체결
→ Portfolio 갱신(cash 차감, Position 생성) 확인
```

#### 시나리오 2: 회원 탈퇴 — Eventually Consistent 데이터 정리

```
회원 탈퇴 요청 → User.status == WITHDRAWN
→ UserWithdrawnEvent Kafka 발행
→ 각 서비스 Consumer 수신:
  - Agent Service: 해당 유저의 ACTIVE Agent → TERMINATED
  - Trade Service: ACTIVE Registration → STOPPED, 미체결 주문 취소
  - VirtualTrade Service: ACTIVE VirtualTrade → STOPPED
  - Notification Service: 알림 채널/설정 soft delete
→ 최종 확인: 모든 서비스에서 해당 유저 리소스 비활성화
```

#### 시나리오 3: 비상 정지

```
실거래 중 비상 정지 요청
→ TradeRegistration.emergencyStopped = true, status = PAUSED
→ 미체결 주문(SUBMITTED, PARTIALLY_FILLED) 취소 요청 발행
→ Exchange Service 취소 처리 → OrderStatusEvent(CANCELLED) 수신
→ 포트폴리오 점유 해제 확인 (reservedCash, reservedQuantity 복원)
```

### 4.2 구성

```yaml
# docker-compose.e2e.yml
services:
  postgres:
    image: postgres:16-alpine
  kafka:
    image: confluentinc/cp-kafka:7.6.0
  redis:
    image: redis:7-alpine
  user-service:
    build: ./user-service
  exchange-service:
    build: ./exchange-service
  market-service:
    build: ./market-service
  agent-service:
    build: ./agent-service
  virtual-trade-service:
    build: ./virtual-trade-service
  trade-service:
    build: ./trade-service
  notification-service:
    build: ./notification-service
```

- **REST Assured**: API 호출 및 응답 검증
- **Awaitility**: 비동기 이벤트 처리 대기 (Kafka 이벤트 전파, Eventually Consistent 상태 수렴)

```kotlin
@Test
fun `E2E_가상거래전체흐름`() {
    // Given: 회원가입 + 로그인 (JWT 발급)
    val token = signUpAndSignIn()

    // When: 전략 → 에이전트 → 가상거래 등록
    val strategyId = createStrategy(token, maCrossoverParams)
    val agentId = createAndActivateAgent(token, strategyId)
    val virtualTradeId = registerVirtualTrade(token, agentId)

    // Then: 신호 생성 및 가상 체결 대기 (최대 60초)
    await().atMost(60, SECONDS).untilAsserted {
        val portfolio = getPortfolio(token, agentId)
        assertThat(portfolio.positions).isNotEmpty()
    }
}
```

---

## 5. Mock 전략

| 대상 | Mock 도구 | 이유 |
|------|-----------|------|
| 거래소 API (Upbit) | WireMock | 외부 API 의존성 제거, 응답 시나리오 제어 |
| 다른 MSA 서비스 | MockK / WireMock | 단위 테스트 시 서비스 격리 |
| Kafka | EmbeddedKafka (통합) / MockK (단위) | 통합 테스트에서 실제 동작 검증, 단위 테스트에서 속도 확보 |
| Redis | Testcontainers Redis (통합) / MockK (단위) | 통합 테스트에서 실제 캐시/Lock 동작 검증 |
| gRPC | InProcessServer (통합) / MockK (단위) | 네트워크 없이 gRPC 서버-클라이언트 테스트 |
| 시간 | `Clock` 주입 | 스케줄러, 타임아웃 테스트에서 시간 제어 |

### WireMock 활용 예시 (거래소 API)

```kotlin
@Test
fun `Exchange_주문제출_거래소API정상응답`() {
    // Given: WireMock으로 Upbit 주문 API 정상 응답 stub
    wireMock.stubFor(post("/v1/orders")
        .willReturn(okJson("""{"uuid": "upbit-order-123", "side": "bid"}""")))

    // When: SubmitOrderCommand 처리
    // Then: Order.exchangeOrderId == "upbit-order-123"
}

@Test
fun `Exchange_주문제출_거래소API타임아웃`() {
    // Given: WireMock에서 10초 지연 응답 설정
    wireMock.stubFor(post("/v1/orders")
        .willReturn(ok().withFixedDelay(10000)))

    // When: SubmitOrderCommand 처리
    // Then: 타임아웃 예외 발생, OrderStatusEvent(REJECTED) 발행
}
```

---

## 6. 테스트 커버리지 목표

| 계층 | 목표 | 측정 도구 |
|------|------|-----------|
| 도메인 모델 (`domain/model`) | 90% 이상 | JaCoCo |
| 도메인 서비스 (`domain/service`) | 85% 이상 | JaCoCo |
| Application 계층 (`application/usecase`) | 80% 이상 | JaCoCo |
| Infrastructure 계층 (`infrastructure`) | 60% 이상 | JaCoCo |
| 전체 | 75% 이상 | JaCoCo |

### JaCoCo 설정

```kotlin
// build.gradle.kts
plugins {
    id("jacoco")
}

tasks.jacocoTestReport {
    reports {
        xml.required.set(true)
        html.required.set(true)
    }
}

tasks.jacocoTestCoverageVerification {
    violationRules {
        rule {
            element = "BUNDLE"
            limit {
                counter = "LINE"
                value = "COVEREDRATIO"
                minimum = "0.75".toBigDecimal()
            }
        }
        rule {
            element = "PACKAGE"
            includes = listOf("*.domain.model.*")
            limit {
                counter = "LINE"
                value = "COVEREDRATIO"
                minimum = "0.90".toBigDecimal()
            }
        }
    }
}
```

### 커버리지 제외 대상

```kotlin
jacocoTestReport {
    afterEvaluate {
        classDirectories.setFrom(files(classDirectories.files.map {
            fileTree(it) {
                exclude(
                    "**/config/**",           // Spring 설정 클래스
                    "**/dto/**",              // 단순 DTO
                    "**/*Application*",       // main 클래스
                    "**/generated/**",        // gRPC/QueryDSL 생성 코드
                )
            }
        }))
    }
}
```

---

## 7. 테스트 네이밍 규칙

### 패턴

```
{메서드명}_{시나리오}_{기대결과}
```

### 예시

```kotlin
@Test
fun `withdraw_정상상태_WITHDRAWN으로전이`() { ... }

@Test
fun `withdraw_이미탈퇴상태_AccountWithdrawnException`() { ... }

@Test
fun `reserveCash_가용현금부족_InsufficientCashException`() { ... }

@Test
fun `activate_TERMINATED상태_InvalidStateException`() { ... }

@Test
fun `emergencyStop_ACTIVE상태_emergencyStopped설정및PAUSED전이`() { ... }

@Test
fun `calculateBuyQuantity_maxConcurrentPositions도달_HOLD전환`() { ... }

@Test
fun `sma_데이터부족_IllegalArgumentException`() { ... }
```

### Nested Class 활용

복잡한 도메인 모델은 `@Nested` 로 시나리오를 그룹화한다.

```kotlin
@DisplayName("Order 상태 전이")
class OrderStatusTransitionTest {

    @Nested
    @DisplayName("PENDING 상태에서")
    inner class FromPending {
        @Test fun `SUBMITTED로전이_정상`() { ... }
        @Test fun `REJECTED로전이_종료`() { ... }
        @Test fun `FILLED로직접전이_InvalidStateException`() { ... }
    }

    @Nested
    @DisplayName("SUBMITTED 상태에서")
    inner class FromSubmitted {
        @Test fun `PARTIALLY_FILLED로전이_부분체결`() { ... }
        @Test fun `FILLED로전이_완전체결`() { ... }
        @Test fun `CANCELLED로전이_타임아웃취소`() { ... }
    }
}
```

---

## 8. CI 연동

### 파이프라인 구성

```yaml
# .github/workflows/test.yml
name: Test Pipeline

on:
  pull_request:
    branches: [main, develop]

jobs:
  unit-and-integration:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-java@v4
        with:
          java-version: '21'
          distribution: 'temurin'
      - name: Run Unit & Integration Tests
        run: ./gradlew test integrationTest
      - name: Check Coverage
        run: ./gradlew jacocoTestCoverageVerification
      - name: Upload Coverage Report
        uses: actions/upload-artifact@v4
        with:
          name: coverage-report
          path: build/reports/jacoco/

  e2e:
    runs-on: ubuntu-latest
    if: github.event_name == 'schedule'  # Nightly만 실행
    steps:
      - uses: actions/checkout@v4
      - name: Start Services
        run: docker-compose -f docker-compose.e2e.yml up -d
      - name: Wait for Services
        run: ./scripts/wait-for-services.sh
      - name: Run E2E Tests
        run: ./gradlew e2eTest
      - name: Stop Services
        run: docker-compose -f docker-compose.e2e.yml down
```

### 실행 정책

| 트리거 | 테스트 범위 | 필수 통과 |
|--------|------------|-----------|
| PR 생성 / Push | Unit + Integration | 커버리지 75% 미만이면 실패 |
| 머지 전 (Branch Protection) | Unit + Integration | 전체 통과 필수 |
| Nightly (매일 03:00 KST) | E2E (전체 서비스 기동) | 실패 시 Slack 알림 |

### Gradle 태스크 분리

```kotlin
// build.gradle.kts
tasks.register<Test>("integrationTest") {
    description = "통합 테스트 실행"
    group = "verification"
    useJUnitPlatform {
        includeTags("integration")
    }
    shouldRunAfter(tasks.test)
}

tasks.register<Test>("e2eTest") {
    description = "E2E 테스트 실행"
    group = "verification"
    useJUnitPlatform {
        includeTags("e2e")
    }
}

tasks.test {
    useJUnitPlatform {
        excludeTags("integration", "e2e")
    }
}
```

### 태그 사용

```kotlin
@Tag("integration")
@SpringBootTest
class PortfolioRepositoryIntegrationTest { ... }

@Tag("e2e")
class VirtualTradeE2ETest { ... }
```

---

## 9. 테스트 데이터 관리

### Fixture 패턴

```kotlin
object AgentFixture {
    fun create(
        agentIdentifier: UUID = UUID.randomUUID(),
        userIdentifier: UUID = UUID.randomUUID(),
        strategyIdentifier: UUID = UUID.randomUUID(),
        status: AgentStatus = AgentStatus.INACTIVE,
        initialCapital: BigDecimal = BigDecimal("10000000"),
        riskConfig: RiskConfig = RiskConfig(
            positionSizeRatio = BigDecimal("0.5"),
            maxConcurrentPositions = 3,
            stopLossPercent = BigDecimal("0.05"),
            takeProfitPercent = BigDecimal("0.10"),
        ),
    ): Agent = Agent(
        agentIdentifier = agentIdentifier,
        userIdentifier = userIdentifier,
        strategyIdentifier = strategyIdentifier,
        status = status,
        initialCapital = initialCapital,
        riskConfig = riskConfig,
    )
}

object PortfolioFixture {
    fun create(
        cash: BigDecimal = BigDecimal("10000000"),
        reservedCash: BigDecimal = BigDecimal.ZERO,
        positions: List<Position> = emptyList(),
    ): Portfolio = Portfolio(
        cash = cash,
        reservedCash = reservedCash,
        positions = positions,
    )
}

object CandleFixture {
    fun ascending(count: Int, basePrice: BigDecimal = BigDecimal("50000")): List<CandleData> {
        return (0 until count).map { i ->
            CandleData(
                open = basePrice + (i * 100).toBigDecimal(),
                high = basePrice + (i * 100 + 50).toBigDecimal(),
                low = basePrice + (i * 100 - 50).toBigDecimal(),
                close = basePrice + (i * 100 + 30).toBigDecimal(),
                volume = BigDecimal("100"),
            )
        }
    }
}
```

### 테스트 시간 제어

```kotlin
// Clock 주입으로 시간 의존 테스트 제어
@Test
fun `LIMIT주문_타임아웃도래_취소요청발행`() {
    // Given: 현재 시각 고정
    val fixedClock = Clock.fixed(Instant.parse("2026-01-01T12:00:00Z"), ZoneOffset.UTC)
    val scheduler = OrderTimeoutScheduler(clock = fixedClock, ...)

    // LIMIT 주문 (timeoutAt = 11:50:00)
    val order = OrderFixture.create(
        type = LIMIT,
        status = SUBMITTED,
        timeoutAt = OffsetDateTime.parse("2026-01-01T11:50:00Z"),
    )

    // When: cancelTimedOutOrders() 호출
    // Then: CancelOrderCommand 발행 확인 (12:00 > 11:50 → 타임아웃)
}
```
