# Market Service — gRPC 클라이언트 예시, 보안, Use Case 추가

> 이 문서는 `backend/market/domain.md`에서 분할되었습니다.

---

## 12.4 클라이언트 사용 예시

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
