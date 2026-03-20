# Simulation Service — Domain 설계

## 1. Bounded Context

Simulation Service는 **과거 캔들 데이터를 기반으로 Agent의 전략을 백테스팅하는 흐름을 오케스트레이션**한다.

```
Simulation Service 책임
├── 과거 캔들 수집   Market Service에서 범위 기반 캔들 조회
├── 백테스팅 위임    Agent Service gRPC BacktestStrategy 호출
└── 결과 전달       스트리밍 응답을 클라이언트에게 실시간 전달 (SSE)
```

Simulation Service는 **자체 DB를 갖지 않는 얇은 오케스트레이션 레이어**다.
백테스팅 결과(`BacktestResult`)는 Agent Service가 자체 DB에 저장한다.
Simulation은 데이터를 영속하지 않고, 흐름을 연결하는 역할만 한다.

---

## 2. 헥사고날 아키텍처 레이어

```
domain/
  port/
    in/    RunBacktestUseCase
    out/   FindHistoricalCandlesOutput   (Market Service gRPC)
           StreamAgentBacktestOutput     (Agent Service gRPC)

application/
  usecase/ RunBacktestService   (implements RunBacktestUseCase)

infrastructure/
  grpc/    MarketCandleGrpcAdapter       (implements FindHistoricalCandlesOutput)
           AgentGrpcClient               (implements StreamAgentBacktestOutput)
  web/     BacktestController            (SSE 엔드포인트)
```

---

## 3. 도메인 포트

### Input Port

```kotlin
interface RunBacktestUseCase {
    // SSE 스트림으로 실시간 결과 전달
    fun runBacktest(command: RunBacktestCommand): Flow<BacktestSignalResult>
}

data class RunBacktestCommand(
    val agentIdentifier  : UUID,
    val symbolIdentifier : UUID,
    val from     : OffsetDateTime,
    val to       : OffsetDateTime,
    val interval : CandleInterval,
)
```

### Output Port

```kotlin
// Market Service에서 범위 기반 과거 캔들 조회
interface FindHistoricalCandlesOutput {
    fun getCandles(
        symbolIdentifier : UUID,
        interval : CandleInterval,
        from     : OffsetDateTime,
        to       : OffsetDateTime,
    ): List<CandleData>
}

// Agent Service gRPC BacktestStrategy 호출 및 스트리밍 수신
interface StreamAgentBacktestOutput {
    fun backtest(
        agentIdentifier  : UUID,
        symbolIdentifier : UUID,
        candles  : List<CandleData>,
    ): Flow<BacktestSignalResult>
}

data class BacktestSignalResult(
    val signalType        : SignalType,       // BUY | SELL | HOLD
    val confidence        : BigDecimal,
    val reason            : Map<String, Any>,
    val candleOpenTime    : OffsetDateTime,
    val suggestedQuantity : BigDecimal,
    val cashAfter         : BigDecimal,       // 신호 반영 후 잔여 현금
    val totalValueAfter   : BigDecimal,       // 신호 반영 후 총자산 평가액
)
```

---

## 4. 처리 흐름

```
1.  POST /backtests { agentIdentifier, symbolIdentifier, from, to, interval }
2.  RunBacktestCommand 생성
3.  FindHistoricalCandlesOutput.getCandles(symbolIdentifier, interval, from, to)
    └ Market Service gRPC GetHistoricalCandles 호출
4.  캔들 수 검증 (0건이면 S001 에러)
5.  StreamAgentBacktestOutput.backtest(agentIdentifier, symbolIdentifier, candles)
    └ Agent Service gRPC BacktestStrategy 호출 (candles 전달)
6.  Agent Service 내부 처리:
    └ Strategy 조회 → StrategyExecutor.analyze() 반복
    └ AgentRiskManager.applySizing() → 포지션/현금 반영
    └ BacktestSignalResponse 스트리밍
    └ 완료 후 BacktestResult DB 저장 (Agent Service 자체)
7.  BacktestSignalResult 스트리밍 → SSE로 클라이언트 전달
8.  스트림 완료 시 연결 종료
```

> Agent Service는 자체적으로 `BacktestResult`를 DB에 저장한다.
> 클라이언트는 백테스팅 완료 후 Agent Service REST API(`GET /agents/{id}/backtests`)로 결과를 조회할 수 있다.

### 스트림 실패 시 동작

| 실패 시점 | 동작 |
|-----------|------|
| Market gRPC 호출 실패 | S004 에러 즉시 반환 (SSE 시작 전) |
| Agent gRPC 스트리밍 도중 연결 끊김 | Simulation → SSE 에러 이벤트 발행 후 연결 종료 |
| 클라이언트 SSE 연결 끊김 | Simulation은 감지 후 Agent gRPC 스트림 cancel. Agent는 스트림 중단. |

> **BacktestResult 저장 정책**: Agent Service는 gRPC BacktestStrategy 스트림이 **정상 완료(onCompleted)**된 경우에만 `BacktestResult`를 DB에 저장한다.
> 스트림 도중 실패(onError)하면 `BacktestResult`는 **저장하지 않는다**.
> 백테스팅은 부작용 없는 읽기 전용 작업이므로 실패 시 단순히 재시도하면 된다.

---

## 5. gRPC 인터페이스

### Simulation → Market (과거 캔들 조회)

Market Service의 proto 파일에서 범위 기반 캔들 조회를 소비한다.

```
Market Service proto (market-service.proto)
────────────────────────────────────────────
service MarketCandle {
  rpc GetHistoricalCandles(GetHistoricalCandlesRequest) returns (GetHistoricalCandlesResponse);
}

message GetHistoricalCandlesRequest {
  string symbol_id  = 1;
  string interval   = 2;   // 예: MINUTE_15, HOUR_1
  string from       = 3;   // ISO-8601
  string to         = 4;   // ISO-8601
}

message GetHistoricalCandlesResponse {
  repeated CandleProto candles = 1;
}
```

> Agent Service가 사용하는 `GetRecentCandles`(최근 N개)와 별개로,
> Simulation은 `GetHistoricalCandles`(기간 기반)를 사용한다.
> Market Service proto에 두 메서드가 모두 존재한다.

```
FindHistoricalCandlesOutput (domain port)
        ▲
        │ implements
MarketCandleGrpcAdapter (infrastructure/grpc)
        │ uses generated stub
        ▼
MarketCandleGrpc.MarketCandleBlockingStub  ←  Market Service gRPC Server
```

### Simulation → Agent (백테스팅 위임)

Agent Service의 proto를 소비한다.

```
Agent Service proto (agent-service.proto)
─────────────────────────────────────────
service Agent {
  rpc BacktestStrategy(BacktestRequest) returns (stream BacktestSignalResponse);
}
```

```
StreamAgentBacktestOutput (domain port)
        ▲
        │ implements
AgentGrpcClient (infrastructure/grpc)
        │ uses generated stub
        ▼
AgentGrpc.AgentStub  ←  Agent Service gRPC Server
```

> 스트리밍이므로 비동기 스텁(`AgentGrpc.AgentStub`)을 사용한다.
> 블로킹 스텁(`AgentGrpc.AgentBlockingStub`)의 `backtest()` 반환 타입이 `Iterator<BacktestSignalResponse>`이므로,
> Kotlin Coroutine 기반 프로젝트라면 `grpc-kotlin`의 코루틴 스텁을 사용해 `Flow<BacktestSignalResponse>`로 변환한다.

---

## 6. Redis 캐시 전략

Simulation Service는 Market Service gRPC를 통해 대량의 과거 캔들 데이터를 반복 조회할 수 있다.
동일 심볼·구간·인터벌의 백테스팅 요청이 반복될 경우 Market gRPC 호출 비용을 줄이기 위해 Redis 캐시를 사용한다.

### 캐시 설계

| 캐시 키 | 형식 | TTL | 설명 |
|---------|------|-----|------|
| `candle:{symbolIdentifier}:{interval}:{fromDate}:{toDate}` | JSON 문자열 (캔들 배열) | 1시간 | 과거 캔들 데이터 (변경 없는 데이터) |

> 과거 캔들 데이터는 한번 수집되면 변경되지 않는다. TTL 1시간은 충분히 안전하다.
> 최신 캔들(현재 진행 중인 캔들)은 캐시 대상에서 제외한다.

### 캐시 적용 흐름

```
FindHistoricalCandlesOutput.getCandles() 호출 시:

1. Redis 조회: GET candle:{symbolIdentifier}:{interval}:{from}:{to}
   └─ Hit: 캐시된 캔들 배열 반환 (gRPC 호출 생략)
   └─ Miss: 다음 단계로
2. Market Service gRPC GetHistoricalCandles 호출
3. Redis 저장: SET candle:... {캔들 JSON} EX 3600
4. 캔들 배열 반환
```

### 캐시 어댑터 구현

```kotlin
@Component
class CachedMarketCandleGrpcAdapter(
    private val grpcAdapter: MarketCandleGrpcAdapter,
    private val redisTemplate: RedisTemplate<String, String>,
    private val objectMapper: ObjectMapper,
) : FindHistoricalCandlesOutput {

    companion object {
        val TTL = Duration.ofHours(1)
    }

    override fun getCandles(
        symbolIdentifier: UUID,
        interval: CandleInterval,
        from: OffsetDateTime,
        to: OffsetDateTime,
    ): List<CandleData> {
        val key = "candle:${symbolIdentifier}:${interval}:${from.toLocalDate()}:${to.toLocalDate()}"

        val cached = redisTemplate.opsForValue().get(key)
        if (cached != null) {
            return objectMapper.readValue(cached)
        }

        val candles = grpcAdapter.getCandles(symbolIdentifier, interval, from, to)
        redisTemplate.opsForValue().set(key, objectMapper.writeValueAsString(candles), TTL)
        return candles
    }
}
```

### Redis 인스턴스

Simulation Service는 **독립적인 Redis 인스턴스**를 사용한다. (architecture.md Section 7 참조)
다른 서비스의 캐시와 키 네임스페이스 충돌 없이 독립적인 Eviction 정책을 적용할 수 있다.

```yaml
# application.yml (Simulation Service)
spring:
  data:
    redis:
      host: simulation-redis
      port: 6379
```

---

## 7. API 엔드포인트

| Method | 경로 | Role | 설명 |
|--------|------|------|------|
| `POST` | `/backtests` | USER | 백테스팅 실행 — SSE 스트림으로 실시간 결과 전달 |

### 요청

```json
POST /backtests
Content-Type: application/json

{
  "agentIdentifier"  : "uuid",
  "symbolIdentifier" : "uuid",
  "from"     : "2024-01-01T00:00:00Z",
  "to"       : "2024-06-01T00:00:00Z",
  "interval" : "HOUR_1"
}
```

### 응답 (SSE)

```
Accept: text/event-stream

data: {"signalType":"BUY","confidence":0.85,"candleOpenTime":"2024-01-01T09:00:00Z","suggestedQuantity":0.05,"cashAfter":9500.0,"totalValueAfter":10200.0,"reason":{...}}
data: {"signalType":"HOLD","confidence":0.12,...}
data: {"signalType":"SELL","confidence":0.91,...}
...
event: done
data: {}
```

> 백테스팅 완료 후 Agent Service에 저장된 결과 전체 요약은
> `GET /agents/{id}/backtests/{backtestIdentifier}` (Agent Service REST)로 조회한다.

---

## 8. 에러 코드

| 코드 | 상수 | 설명 |
|------|------|------|
| `S001` | `CANDLE_DATA_EMPTY` | 조회된 캔들 데이터 없음 (기간/심볼 오류) |
| `S002` | `AGENT_NOT_FOUND` | Agent Service에서 Agent 없음 |
| `S003` | `BACKTEST_STREAM_ERROR` | Agent Service gRPC 스트리밍 중 오류 |
| `S004` | `MARKET_SERVICE_UNAVAILABLE` | Market Service gRPC 호출 실패 |
| `S005` | `INVALID_DATE_RANGE` | from ≥ to 또는 미래 날짜 |
