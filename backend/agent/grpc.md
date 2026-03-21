# Agent Service — gRPC 인터페이스

> 이 문서는 `backend/agent/domain.md`에서 분할되었습니다.

---

## 7. gRPC 인터페이스

### Simulation → Agent (백테스팅)

Simulation은 Agent 단위로 백테스팅을 수행한다.
Agent Service는 Agent의 Strategy + RiskConfig를 기반으로 신호 조건 평가와 포지션 사이징을 모두 처리한다.
Agent의 `initialCapital`으로 임시 포트폴리오를 인메모리로 관리하며, 각 신호 시점의 포트폴리오 상태를 스트리밍으로 반환한다.
백테스팅 완료 후 결과 요약은 `BacktestResult`로 DB에 저장한다. 실제 Portfolio / PortfolioHistory에는 기록하지 않는다.
Agent 상태와 무관하게 백테스팅 요청을 수락한다.

```protobuf
service Agent {
  rpc BacktestStrategy(BacktestRequest) returns (stream BacktestSignalResponse);
}

message BacktestRequest {
  string           agent_id  = 1;
  string           symbol_id = 2;
  repeated CandleProto candles = 3;
}

message BacktestSignalResponse {
  string signal_type        = 1;  // BUY | SELL | HOLD
  double confidence         = 2;
  string reason_json        = 3;
  string candle_open_time   = 4;  // ISO-8601
  double suggested_quantity = 5;
  double cash_after         = 6;  // 신호 반영 후 잔여 현금
  double total_value_after  = 7;  // 신호 반영 후 총자산 평가액
}
```

### Agent → Market (캔들 조회)

Agent Service는 Market Service의 proto 계약을 **소비(consume)** 한다.
아래 정의는 Market Service가 제공하는 proto 파일의 일부이며, Agent Service는 빌드 시 생성된 클라이언트 스텁을 통해 호출한다.

```
Market Service proto (market-service.proto)
────────────────────────────────────────────
service MarketCandle {
  rpc GetRecentCandles(GetRecentCandlesRequest) returns (GetRecentCandlesResponse);
}

message GetRecentCandlesRequest {
  string symbol_id = 1;
  string interval  = 2;
  int32  limit     = 3;
}
```

Agent Service 인프라 레이어의 `MarketCandleGrpcAdapter`가 생성된 스텁(`MarketCandleGrpc.MarketCandleBlockingStub`)을 감싸고, 도메인 Output Port `FindMarketCandleOutput`을 구현한다.

```
FindMarketCandleOutput (domain port)
        ▲
        │ implements
MarketCandleGrpcAdapter (infrastructure/grpc)
        │ uses generated stub
        ▼
MarketCandleGrpc.MarketCandleBlockingStub  ←  Market Service gRPC Server
```

### Agent → Market (심볼 메타데이터 조회)

신호 생성 시 또는 화면 표시를 위해 심볼의 메타데이터(이름, 상태 등)가 필요할 수 있다.

```
Market Service proto (market-service.proto)
────────────────────────────────────────────
service MarketSymbol {
  rpc GetSymbol(GetSymbolRequest) returns (GetSymbolResponse);
}

message GetSymbolRequest {
  string symbol_id = 1;  // UUID
}

message GetSymbolResponse {
  SymbolProto symbol = 1;
}
```

Agent Service 인프라 레이어의 `MarketSymbolGrpcAdapter`가 생성된 스텁을 감싸고, 도메인 Output Port `FindSymbolMetadataOutput`을 구현한다.

```
FindSymbolMetadataOutput (domain port)
        ▲
        │ implements
MarketSymbolGrpcAdapter (infrastructure/grpc)
        │ uses generated stub
        │ + Redis caching
        ▼
MarketSymbolGrpc.MarketSymbolBlockingStub  ←  Market Service gRPC Server
```

**구현 예시**:
```kotlin
@Component
class MarketSymbolGrpcAdapter(
    private val marketSymbolStub: MarketSymbolGrpc.MarketSymbolBlockingStub,
    private val redisTemplate: RedisTemplate<String, String>,
    private val objectMapper: ObjectMapper,
) : FindSymbolMetadataOutput {

    companion object {
        val CACHE_TTL = Duration.ofMinutes(10)
    }

    override fun getSymbol(symbolIdentifier: UUID): SymbolMetadata? {
        val cacheKey = "symbol:$symbolIdentifier"

        // Redis 캐시 확인
        redisTemplate.opsForValue().get(cacheKey)?.let {
            return objectMapper.readValue(it, SymbolMetadata::class.java)
        }

        // gRPC 호출
        val request = GetSymbolRequest.newBuilder()
            .setSymbolId(symbolIdentifier.toString())  // proto field: symbol_id
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
                CACHE_TTL
            )

            metadata
        } catch (e: StatusRuntimeException) {
            when (e.status.code) {
                Status.Code.NOT_FOUND -> null
                Status.Code.DEADLINE_EXCEEDED -> {
                    log.error("Market Service timeout for symbolIdentifier=$symbolIdentifier")
                    null
                }
                else -> {
                    log.error("Market Service gRPC error", e)
                    null
                }
            }
        }
    }
}

private fun SymbolProto.toDomain(): SymbolMetadata =
    SymbolMetadata(
        symbolIdentifier = UUID.fromString(this.symbolIdentifier),
        code = this.code,
        name = this.name,
        market = MarketType.valueOf(this.market),
        status = SymbolStatus.valueOf(this.status),
    )
```
