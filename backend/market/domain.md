# Market Service - 도메인 설계

> 시장 데이터 수집 및 관리를 담당하는 Market Service의 도메인 모델 정의

---

## 1. Aggregate Root

### 1.1 MarketSymbol (시장 심볼)

**목적**: 거래 가능한 심볼의 상태를 관리합니다.

**속성**:
```kotlin
class MarketSymbol(
    val identifier: MarketSymbolId,        // 고유 식별자 (UUID)
    val code: MarketSymbolCode,            // 심볼 코드 (예: KRW-BTC)
    val name: String,                       // 심볼 이름 (예: 비트코인)
    val market: MarketType,                 // 시장 타입 (COIN, STOCK)
    var status: MarketSymbolStatus,         // 심볼 상태
    val createdDate: OffsetDateTime,        // 생성 시각
    var modifiedDate: OffsetDateTime,       // 수정 시각
)
```

**비즈니스 로직**:
```kotlin
fun list()          // 정상 거래 가능 상태로 변경 (LISTED)
fun warning()       // 경고 상태로 변경 (WARNING)
fun caution()       // 주의 상태로 변경 (CAUTION)
fun tradingHalt()   // 거래 중지 상태로 변경 (TRADING_HALTED)
fun delist()        // 상장 폐지 상태로 변경 (DELISTED)
```

**상태 전이**:
```
LISTED ↔ WARNING ↔ CAUTION ↔ TRADING_HALTED → DELISTED
```

**불변 조건 (Invariants)**:
- `code`는 변경 불가
- `market`은 변경 불가
- 상태 변경 시 `modifiedDate` 자동 업데이트

**도메인 이벤트**:
- `MarketSymbolListedEvent`: 심볼이 정상 거래 가능 상태가 됨
- `MarketSymbolWarningEvent`: 심볼이 경고 상태가 됨
- `MarketSymbolCautionEvent`: 심볼이 주의 상태가 됨
- `MarketSymbolTradingHaltedEvent`: 심볼이 거래 중지 상태가 됨
- `MarketSymbolDelistedEvent`: 심볼이 상장 폐지됨

---

### 1.2 MarketCandleCollectTask (캔들 수집 작업)

**목적**: 심볼별 캔들 데이터 수집 작업의 상태와 이력을 관리합니다.

**속성**:
```kotlin
class MarketCandleCollectTask(
    val identifier: MarketCandleCollectTaskId,  // 고유 식별자 (UUID)
    val symbolIdentifier: MarketSymbolId,        // 심볼 참조
    val interval: MarketCandleInterval,          // 캔들 간격
    val createdDate: OffsetDateTime,             // 생성 시각
    var lastCollectedTime: OffsetDateTime?,      // 마지막 수집 시각
    var lastCollectedPrice: BigDecimal?,         // 마지막 수집 종가
    var status: MarketCandleCollectStatus,       // 수집 상태
    var retryCount: Int = 0,                    // 연속 실패 횟수 (MAX_RETRY_COUNT 초과 시 수동 복구 필요)
)
```

**비즈니스 로직**:
```kotlin
// 상태 관리
fun list()                                      // 정상 상태로 복구 (COLLECTED)
fun delist()                                    // 상장 폐지 처리 (DELISTED)

// 수집 프로세스
fun collectStart()                              // 수집 시작 (COLLECTING): STARTABLE_STATUS 또는 AUTO_RETRYABLE_STATUS(retryCount < MAX_RETRY_COUNT) 조건 검증
fun collectComplete(candles: List<MarketCandle>) // 수집 완료 (COLLECTED), retryCount 초기화
fun collectComplete()                            // 수집 완료 (데이터 없음), retryCount 초기화
fun collectFail()                                // 수집 실패: retryCount++, ERROR 상태 유지
fun collectPause()                               // 수집 일시정지 (PAUSED)
```

**상태 전이**:
```
CREATED ──→ COLLECTING ──→ COLLECTED
              ↓              ↑
            ERROR ←──────────┤
              ↓              ↓
            PAUSED ←─────────┘
              ↓
          DELISTED (종료 상태)
```

**상태별 전이 가능 조건**:
```kotlin
companion object {
    const val MAX_RETRY_COUNT = 3                        // 자동 재시도 최대 횟수 (초과 시 수동 복구 필요)
    val STARTABLE_STATUS = setOf(CREATED, COLLECTED)     // 수집 시작 가능 (기본)
    val AUTO_RETRYABLE_STATUS = setOf(ERROR)             // 자동 재시도 가능 (retryCount < MAX_RETRY_COUNT 조건 포함)
    val PAUSABLE_STATUS = setOf(CREATED, COLLECTING, COLLECTED, ERROR) // 일시정지 가능
}
```

**불변 조건 (Invariants)**:
- `symbolIdentifier`와 `interval` 조합은 unique
- `collectStart()` 호출 시 `STARTABLE_STATUS` 또는 (`AUTO_RETRYABLE_STATUS`이면서 `retryCount < MAX_RETRY_COUNT`)에 포함되어야 함
- `collectComplete()` 호출 시 `COLLECTING` 또는 `PAUSED` 상태여야 함, `retryCount` 초기화
  > PAUSED 허용 이유: `collectStart()` 후 Kafka Command가 이미 발행된 상태에서 pause가 걸릴 수 있다.
  > Exchange Reply는 이미 in-flight이므로 응답이 도착하면 `collectComplete()`가 정상 호출된다.
  > 이 경우 PAUSED → COLLECTED로 전이하여 수집된 데이터는 유효하게 저장된다.
- `collectFail()` 호출 시 `COLLECTING` 또는 `PAUSED` 상태여야 함, `retryCount` 증가
- `collectPause()` 호출 시 `PAUSABLE_STATUS`에 포함되어야 함
- `COLLECTING` 상태에서만 `ERROR`로 전이 가능 (PAUSED 상태에서는 유지)
- `lastCollectedTime`은 수집 완료 시 자동 업데이트

**도메인 이벤트**:
- `MarketCandleCollectTaskCollectedEvent`: 캔들 수집 완료 (간격 계산 트리거)

---

## 2. Entity

### 2.1 MarketCandle (시장 캔들)

**목적**: 특정 시점의 가격 및 거래량 데이터를 저장합니다.

**속성**:
```kotlin
class MarketCandle(
    val symbolIdentifier: MarketSymbolId,    // 심볼 참조
    val interval: MarketCandleInterval,      // 캔들 간격
    val time: OffsetDateTime,                // 캔들 시각 (간격의 시작 시각)
    val open: BigDecimal,                    // 시가
    val high: BigDecimal,                    // 고가
    val low: BigDecimal,                     // 저가
    val close: BigDecimal,                   // 종가
    val volume: BigDecimal,                  // 거래량
    val amount: BigDecimal,                  // 거래대금
)
```

**불변 조건 (Invariants)**:
- `high >= low`
- `high >= open`
- `high >= close`
- `low <= open`
- `low <= close`
- `volume >= 0`
- `amount >= 0`
- Flat Candle 판별: `volume == 0` && `open == high == low == close`

**식별자**:
- Composite Key: `(symbolIdentifier, interval, time)`

---

## 3. Value Object

### 3.1 MarketSymbolId

```kotlin
@JvmInline
value class MarketSymbolId(val value: UUID) {
    companion object {
        fun of(value: UUID) = MarketSymbolId(value)
        fun generate() = MarketSymbolId(UUID.randomUUID())
    }
}
```

### 3.2 MarketSymbolCode

```kotlin
@JvmInline
value class MarketSymbolCode(val value: String) {
    init {
        require(value.isNotBlank()) { "Code cannot be blank" }
        require(value.matches(Regex("^[A-Z]+-[A-Z]+$"))) {
            "Code must be in format: BASE-QUOTE (e.g., KRW-BTC)"
        }
    }

    companion object {
        fun of(value: String) = MarketSymbolCode(value)
    }
}
```

### 3.3 MarketCandleCollectTaskId

```kotlin
@JvmInline
value class MarketCandleCollectTaskId(val value: UUID) {
    companion object {
        fun of(value: UUID) = MarketCandleCollectTaskId(value)
        fun generate() = MarketCandleCollectTaskId(UUID.randomUUID())
    }
}
```

---

## 4. Enum

### 4.1 MarketType (시장 타입)

```kotlin
enum class MarketType {
    COIN,   // 암호화폐
    STOCK,  // 주식
}
```

### 4.2 MarketSymbolStatus (심볼 상태)

```kotlin
enum class MarketSymbolStatus {
    LISTED,          // 정상 거래 가능
    WARNING,         // 경고
    CAUTION,         // 주의
    TRADING_HALTED,  // 거래 중지
    DELISTED,        // 상장 폐지
}
```

### 4.3 MarketCandleCollectStatus (수집 상태)

```kotlin
enum class MarketCandleCollectStatus {
    CREATED,     // 생성됨 (수집 전)
    COLLECTING,  // 수집 중
    COLLECTED,   // 수집 완료
    ERROR,       // 수집 실패
    PAUSED,      // 일시정지
    DELISTED,    // 상장 폐지 (수집 중단)
}
```

### 4.4 MarketCandleInterval (캔들 간격)

```kotlin
enum class MarketCandleInterval(
    val value: Int,               // 간격 값
    val baseIntervalValue: Int,   // 기준 간격 값
    val timeSpan: TimeSpan,       // 시간 범위
) {
    MIN_1(1, 1, TimeSpan.ofMinutes(1)),      // 1분봉 (기준)
    MIN_3(2, 1, TimeSpan.ofMinutes(3)),      // 3분봉 ← MIN_1
    MIN_5(3, 1, TimeSpan.ofMinutes(5)),      // 5분봉 ← MIN_1
    MIN_10(4, 3, TimeSpan.ofMinutes(10)),    // 10분봉 ← MIN_5
    MIN_15(5, 3, TimeSpan.ofMinutes(15)),    // 15분봉 ← MIN_5
    MIN_30(6, 3, TimeSpan.ofMinutes(30)),    // 30분봉 ← MIN_5
    MIN_60(7, 6, TimeSpan.ofMinutes(60)),    // 60분봉 ← MIN_30
    MIN_120(8, 7, TimeSpan.ofMinutes(120)),  // 120분봉 ← MIN_60
    MIN_180(9, 7, TimeSpan.ofMinutes(180)),  // 180분봉 ← MIN_60
    DAY(10, 9, TimeSpan.ofDays(1)),          // 일봉 ← MIN_180
    WEEK(11, 10, TimeSpan.ofWeeks()),        // 주봉 ← DAY
    MONTH(12, 10, TimeSpan.ofMonths(1)),     // 월봉 ← DAY
    ;

    val baseInterval: MarketCandleInterval
        get() = entries.first { this.baseIntervalValue == it.value }

    val isBaseInterval: Boolean
        get() = this.baseIntervalValue == this.value
}
```

**간격 계산 관계**:
```
MIN_1 (외부 수집)
├─ MIN_3 (3개 결합)
├─ MIN_5 (5개 결합)
│  ├─ MIN_10 (2개 결합)
│  ├─ MIN_15 (3개 결합)
│  └─ MIN_30 (6개 결합)
│     └─ MIN_60 (2개 결합)
│        ├─ MIN_120 (2개 결합)
│        └─ MIN_180 (3개 결합)
│           └─ DAY (8개 결합)
│              ├─ WEEK (7개 결합)
│              └─ MONTH (월별 결합)
```

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

---

## 8. Exception

### 8.1 MarketSymbol 예외

```kotlin
enum class MarketSymbolErrorCode(
    override val code: String,
    override val message: String,
) : ErrorCode {
    MARKET_SYMBOL_NOT_FOUND("MS001", "Market symbol not found"),
}

class MarketSymbolNotFoundException(
    val symbolIdentifier: MarketSymbolId,
) : BusinessException(MarketSymbolErrorCode.MARKET_SYMBOL_NOT_FOUND)
```

### 8.2 MarketCandleCollectTask 예외

```kotlin
enum class MarketCandleCollectTaskErrorCode(
    override val code: String,
    override val message: String,
) : ErrorCode {
    TASK_NOT_FOUND("MCT001", "Market candle collect task not found"),
    INVALID_STATUS_FOR_START("MCT002", "Invalid status for start"),
    INVALID_STATUS_FOR_COMPLETE("MCT003", "Invalid status for complete"),
    INVALID_STATUS_FOR_FAIL("MCT004", "Invalid status for fail"),
    INVALID_STATUS_FOR_PAUSE("MCT005", "Invalid status for pause"),
}

class MarketCandleCollectTaskNotFoundException(...)
class MarketCandleCollectTaskInvalidStatusForStartException(...)
class MarketCandleCollectTaskInvalidStatusForCompleteException(...)
class MarketCandleCollectTaskInvalidStatusForFailException(...)
class MarketCandleCollectTaskInvalidStatusForPauseException(...)
```

---

## 9. 도메인 관계

```
MarketSymbol (1) ──< (N) MarketCandleCollectTask
                │
                │ (1)
                ↓
                │ (N)
              MarketCandle
```

**생명주기**:
1. **MarketSymbol** 생성 → **MarketSymbolListedEvent** 발행
2. **MarketSymbolListedEvent** 수신 → 12개 **MarketCandleCollectTask** 생성
3. **MarketSymbol** 상장 폐지 → **MarketSymbolDelistedEvent** 발행
4. **MarketSymbolDelistedEvent** 수신 → 모든 **MarketCandleCollectTask** DELISTED 처리

---

## 10. 주요 Use Case

### 10.1 심볼 수집

```kotlin
interface CollectMarketSymbolUseCase {
    fun collectStart(market: MarketType)
    fun collectMarketSymbol(symbols: List<CollectedMarketSymbolDto>)
}
```

### 10.2 캔들 수집

```kotlin
interface CollectMarketCandleUseCase {
    fun collectStart(market: MarketType)
    fun collectMarketCandle(
        taskIdentifier: MarketCandleCollectTaskId,
        candles: List<CollectedMarketCandleDto>,
    )
    fun collectFail(
        taskIdentifier: MarketCandleCollectTaskId,
        message: String,
    )
    fun calculateInterval(
        symbolIdentifier: MarketSymbolId,
        interval: MarketCandleInterval,
        maxTime: OffsetDateTime,
    )
}
```

### 10.3 수집 작업 관리

```kotlin
interface UpdateMarketCandleCollectTaskUseCase {
    fun resume(identifier: MarketCandleCollectTaskId)
    fun pause(identifier: MarketCandleCollectTaskId)
    fun resumeAll(): List<MarketCandleCollectTask>
    fun pauseAll(): List<MarketCandleCollectTask>
}
```

### 10.5 수집 샤딩 및 스케줄링 (Worker Sharding)

수많은 심볼의 캔들을 효율적으로 수집하기 위해 **Consistency Hashing** 기반의 샤딩을 적용한다.

- **샤딩 알고리즘**: `hash(symbolIdentifier) % totalWorkerCount`
- **동적 노드 관리**: Kubernetes Pod 리스트를 감시하여 `totalWorkerCount` 변화 시 샤딩을 재계산한다 (Rebalancing).
- **작업 할당**:
  - 각 워커(Pod)는 자신의 `workerIndex`를 알고 있다.
  - 스케줄러 실행 시 `hash(task.symbolIdentifier) % totalWorkerCount == myWorkerIndex`인 태스크만 추출하여 실행한다.
  - 이 방식은 별도의 마스터 노드 없이도 각 워커가 독립적으로 자신의 할 일을 결정할 수 있게 한다.

**구현 세부사항**:

```kotlin
@Component
class WorkerShardingConfig(
    @Value("\${worker.index:0}") val myWorkerIndex: Int,
    private val kubernetesClient: KubernetesClient,
) {
    // Kubernetes StatefulSet ordinal 기반 자동 할당
    // 환경 변수: WORKER_INDEX = ${HOSTNAME##*-} (예: market-service-2 → 2)

    fun getTotalWorkerCount(): Int =
        kubernetesClient.apps().statefulSets()
            .withName("market-service")
            .get()?.spec?.replicas ?: 1

    fun isMyTask(symbolIdentifier: MarketSymbolId): Boolean =
        abs(symbolIdentifier.value.hashCode()) % getTotalWorkerCount() == myWorkerIndex
}
```

**스케줄러 적용**:
```kotlin
@Scheduled(fixedDelayString = "\${scheduler.market.candle-collect-interval:60000}")
fun collectCandles() {
    val allTasks = taskRepository.findAllCollectable()
    val myTasks = allTasks.filter { shardingConfig.isMyTask(it.symbolIdentifier) }
    myTasks.forEach { task -> collectCandle(task) }
}
```

**병렬 수집**: 할당받은 태스크를 `CompletableFuture`로 최대 10개 동시 실행한다 (Upbit Public API Rate Limit 10 req/s 이내).

```kotlin
val executor = Executors.newFixedThreadPool(10)
myTasks.map { task ->
    CompletableFuture.runAsync({ collectCandle(task) }, executor)
}.forEach { it.join() }
```

---

## 11. 핵심 비즈니스 규칙

### 11.0 "최신 캔들" 정의

`GetRecentCandles(limit=1)`이 반환하는 캔들은 **가장 최근 종료된 캔들**이다.

```
MarketCandle.time = 캔들 시작 시각 (예: 13:59:00)
MarketCandle.close = 해당 봉의 마지막 거래가 (13:59:59까지의 종가)
```

- 현재 진행 중인 캔들(아직 종료되지 않은 봉)은 **반환하지 않는다**.
- 따라서 `GetRecentCandles(limit=1).close`를 현재가로 사용하면, 실제 최신 가격과 최대 1분(MIN_1 기준)의 차이가 발생할 수 있다.
- VirtualTrade / Trade 스케줄러가 이 값을 `currentPrice`로 사용할 때 이 지연을 인지해야 한다.

### 11.1 Flat Candle 생성 규칙
- 이전 종가가 있는 경우에만 생성
- `volume = 0`, `amount = 0`
- `open = high = low = close = 이전 종가`

### 11.2 간격 계산 순서
- MIN_1 수집 완료 후 이벤트 발행
- 모든 파생 간격(MIN_3 ~ MONTH)을 순차적으로 계산
- 각 간격은 `baseInterval` 기준으로 계산

### 11.3 수집 실패 처리
- 상태를 ERROR로 변경, `retryCount` 1 증가
- 다음 스케줄 사이클(기본: 1분)에 자동 재시도 (`retryCount < MAX_RETRY_COUNT = 3` 조건 충족 시)
- 3회 초과 시 자동 재시도 중단 → 수동 복구 필요 (`PUT /tasks/{id}/resume`)

**스케줄러 설정 예시**:
```yaml
# application.yml
scheduler:
  market:
    candle-collect-interval: 60000  # 밀리초 (기본: 1분)
```

```kotlin
// MarketCandleCollectScheduler.kt
@Component
class MarketCandleCollectScheduler(
    @Value("\${scheduler.market.candle-collect-interval:60000}")
    private val collectInterval: Long,
    // ...
) {
    @Scheduled(fixedDelayString = "\${scheduler.market.candle-collect-interval:60000}")
    fun collectCandles() {
        // MIN_1 간격 수집 작업 처리
        // ...
    }
}
```

### 11.4 데이터 검증
- OHLC 관계 검증 (Factory에서 수행)
- 가격 급등락 감지 (추가 구현 필요)
- Flat Candle 비율 모니터링 (< 5%)

---

## 12. gRPC 인터페이스

Market Service는 다른 서비스에 캔들 데이터 및 심볼 메타데이터를 제공하는 gRPC 서버를 운영한다.

### 12.1 Proto 정의 (market-service.proto)

```protobuf
syntax = "proto3";

package market;

option java_package = "com.tradepilot.market.grpc";
option java_multiple_files = true;

// ============================================
// Market Candle Service
// ============================================
service MarketCandle {
  // 최근 N개 캔들 조회 (Agent Service, VirtualTrade Service, Trade Service 사용)
  rpc GetRecentCandles(GetRecentCandlesRequest) returns (GetRecentCandlesResponse);

  // 기간 기반 과거 캔들 조회 (Simulation Service 사용)
  rpc GetHistoricalCandles(GetHistoricalCandlesRequest) returns (GetHistoricalCandlesResponse);
}

// 최근 캔들 조회
message GetRecentCandlesRequest {
  string symbol_id = 1;  // UUID
  string interval  = 2;  // MIN_1, MIN_5, MIN_60, DAY 등 (MarketCandleInterval enum 값)
  int32  limit     = 3;  // 최대 1000개
}

message GetRecentCandlesResponse {
  repeated CandleProto candles = 1;
}

// 과거 캔들 조회 (기간 기반)
message GetHistoricalCandlesRequest {
  string symbol_id = 1;  // UUID
  string interval  = 2;  // MIN_1, MIN_5, MIN_60, DAY 등 (MarketCandleInterval enum 값)
  string from      = 3;  // ISO-8601 (예: 2024-01-01T00:00:00Z)
  string to        = 4;  // ISO-8601
}

message GetHistoricalCandlesResponse {
  repeated CandleProto candles = 1;
}

message CandleProto {
  string symbol_id = 1;
  string interval  = 2;
  string time      = 3;  // ISO-8601
  string open      = 4;  // BigDecimal → String
  string high      = 5;
  string low       = 6;
  string close     = 7;
  string volume    = 8;
  string amount    = 9;
}

// ============================================
// Market Symbol Service
// ============================================
service MarketSymbol {
  // 심볼 메타데이터 조회 (Agent Service, Trade Service 사용)
  rpc GetSymbol(GetSymbolRequest) returns (GetSymbolResponse);

  // 여러 심볼 일괄 조회
  rpc GetSymbols(GetSymbolsRequest) returns (GetSymbolsResponse);

  // 거래 가능한 심볼 목록 조회
  rpc ListSymbols(ListSymbolsRequest) returns (ListSymbolsResponse);
}

message GetSymbolRequest {
  string symbol_id = 1;  // UUID
}

message GetSymbolResponse {
  SymbolProto symbol = 1;
}

message GetSymbolsRequest {
  repeated string symbol_ids = 1;  // UUID 배열
}

message GetSymbolsResponse {
  repeated SymbolProto symbols = 1;
}

message ListSymbolsRequest {
  string market = 1;     // COIN, STOCK
  string status = 2;     // LISTED (optional, 기본값: LISTED만 조회)
  int32  page   = 3;     // 페이지 번호 (0부터 시작)
  int32  size   = 4;     // 페이지 크기 (기본 100, 최대 1000)
}

message ListSymbolsResponse {
  repeated SymbolProto symbols = 1;
  int32 total_count = 2;
}

message SymbolProto {
  string symbol_id = 1;  // UUID
  string code      = 2;  // KRW-BTC
  string name      = 3;  // 비트코인
  string market    = 4;  // COIN
  string status    = 5;  // LISTED, WARNING, CAUTION, TRADING_HALTED, DELISTED
}
```

### 12.2 gRPC 서버 구현

**Infrastructure Layer**:
```
infrastructure/
  grpc/
    MarketCandleGrpcServer    (implements MarketCandleGrpc.MarketCandleImplBase)
    MarketSymbolGrpcServer    (implements MarketSymbolGrpc.MarketSymbolImplBase)
    GrpcExceptionHandler      (gRPC 에러 변환)
```

**에러 매핑**:
```kotlin
도메인 예외                         → gRPC Status
MarketSymbolNotFoundException      → NOT_FOUND
MarketCandleCollectTaskNotFoundException → NOT_FOUND
ValidationException                 → INVALID_ARGUMENT
InternalError                       → INTERNAL
TimeoutException                    → DEADLINE_EXCEEDED
```

### 12.3 타임아웃 및 성능

**타임아웃 설정**:
```yaml
GetRecentCandles:       5초
GetHistoricalCandles:   30초 (대용량 데이터)
GetSymbol:              3초
GetSymbols:             10초
ListSymbols:            10초
```

**캐싱 전략**:
- `GetSymbol`: Redis 캐싱 (TTL 10분)
  - Key: `symbol:{symbolIdentifier}`
  - Value: `SymbolProto` JSON

- `GetRecentCandles`: 최신 캔들(limit=1)만 Redis 캐싱 (TTL 10초)
  - Key: `candle:recent:{symbolIdentifier}:{interval}`
  - 이유: 현재가 조회 용도로 자주 호출됨

**페이징**:
- `ListSymbols`: 최대 1000개까지 한 번에 조회 가능
- 기본 페이지 크기: 100개

### 12.4 클라이언트 사용 예시

**Agent Service (캔들 조회)**:
```kotlin
// infrastructure/grpc/MarketCandleGrpcAdapter.kt
@Component
class MarketCandleGrpcAdapter(
    private val marketCandleStub: MarketCandleGrpc.MarketCandleBlockingStub,
) : FindMarketCandleOutput {

    override fun getRecentCandles(
        symbolIdentifier: UUID,
        interval: CandleInterval,
        limit: Int,
    ): List<CandleData> {
        val request = GetRecentCandlesRequest.newBuilder()
            .setSymbolId(symbolIdentifier.toString())
            .setInterval(interval.name)
            .setLimit(limit)
            .build()

        return try {
            val response = marketCandleStub
                .withDeadlineAfter(5, TimeUnit.SECONDS)
                .getRecentCandles(request)

            response.candlesList.map { it.toDomain() }
        } catch (e: StatusRuntimeException) {
            when (e.status.code) {
                Status.Code.NOT_FOUND -> emptyList()
                Status.Code.DEADLINE_EXCEEDED -> throw CandleDataUnavailableException(symbolIdentifier)
                else -> throw MarketServiceUnavailableException(e)
            }
        }
    }
}
```

**Agent Service (심볼 메타데이터 조회)**:
```kotlin
// infrastructure/grpc/MarketSymbolGrpcAdapter.kt
@Component
class MarketSymbolGrpcAdapter(
    private val marketSymbolStub: MarketSymbolGrpc.MarketSymbolBlockingStub,
    private val redisTemplate: RedisTemplate<String, String>,
) : FindSymbolMetadataOutput {

    override fun getSymbol(symbolId: UUID): SymbolMetadata? {
        // Redis 캐시 확인
        val cacheKey = "symbol:$symbolId"
        redisTemplate.opsForValue().get(cacheKey)?.let {
            return objectMapper.readValue(it, SymbolMetadata::class.java)
        }

        // gRPC 호출
        val request = GetSymbolRequest.newBuilder()
            .setSymbolId(symbolIdentifier.toString())
            .build()

        return try {
            val response = marketSymbolStub
                .withDeadlineAfter(3, TimeUnit.SECONDS)
                .getSymbol(request)

            val metadata = response.symbol.toDomain()

            // Redis 캐싱
            redisTemplate.opsForValue().set(
                cacheKey,
                objectMapper.writeValueAsString(metadata),
                Duration.ofMinutes(10)
            )

            metadata
        } catch (e: StatusRuntimeException) {
            when (e.status.code) {
                Status.Code.NOT_FOUND -> null
                else -> throw MarketServiceUnavailableException(e)
            }
        }
    }
}
```

### 12.5 보안

**mTLS 적용**:
```yaml
grpc:
  server:
    port: 9090
    security:
      enabled: true
      cert-chain: /etc/certs/server-cert.pem
      private-key: /etc/certs/server-key.pem
      trust-cert-collection: /etc/certs/ca-cert.pem
      client-auth: REQUIRE
```

**Internal API Key** (추가 검증):
```kotlin
class InternalApiKeyInterceptor : ServerInterceptor {
    override fun <ReqT, RespT> interceptCall(
        call: ServerCall<ReqT, RespT>,
        headers: Metadata,
        next: ServerCallHandler<ReqT, RespT>,
    ): ServerCall.Listener<ReqT> {
        val apiKey = headers.get(Metadata.Key.of("X-Internal-Secret", ASCII_STRING_MARSHALLER))

        if (apiKey != expectedApiKey) {
            call.close(Status.UNAUTHENTICATED.withDescription("Invalid API key"), Metadata())
            return object : ServerCall.Listener<ReqT>() {}
        }

        return next.startCall(call, headers)
    }
}
```

---

## 13. Use Case 추가 (심볼 조회)

```kotlin
// domain/port/in/
interface GetSymbolMetadataUseCase {
    fun getSymbol(symbolIdentifier: MarketSymbolId): MarketSymbol?
    fun getSymbols(symbolIdentifiers: List<MarketSymbolId>): List<MarketSymbol>
    fun listSymbols(market: MarketType, status: MarketSymbolStatus?, pageable: Pageable): Page<MarketSymbol>
}

// domain/port/out/
interface FindSymbolOutput {
    fun findById(symbolIdentifier: MarketSymbolId): MarketSymbol?
    fun findAllByIds(symbolIdentifiers: List<MarketSymbolId>): List<MarketSymbol>
    fun findAllByMarketAndStatus(
        market: MarketType,
        status: MarketSymbolStatus?,
        pageable: Pageable,
    ): Page<MarketSymbol>
}
```
