# Market Service — Exception, 도메인 관계, Use Case

> 이 문서는 `backend/market/domain.md`에서 분할되었습니다.

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
