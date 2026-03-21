# Market Service — 도메인 모델 (Aggregate, Entity, Value Object, Enum)

> 이 문서는 `backend/market/domain.md`에서 분할되었습니다.

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
