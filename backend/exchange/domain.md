# Exchange Service — Domain 설계

## 1. Bounded Context

Exchange Service는 **거래소 API 어댑터**로서 다른 서비스가 거래소와 상호작용하는 진입점 역할을 담당한다.
거래소 API의 복잡성(인증, Rate Limit, 재시도, 에러 정규화)을 캡슐화하고, 내부 서비스에게 표준화된 인터페이스를 제공한다.

```
Exchange Service 책임
├── ExchangeAccount  거래소 API Key 등록 및 암호화 관리
├── 심볼/캔들 조회    Market Service 요청에 따라 거래소 Public API 호출
├── 주문 제출         Trade Service 요청에 따라 거래소 Private API 주문 실행
├── 주문 취소         미체결 주문 취소 요청 처리
├── Rate Limit 관리  Public/Private API 풀 분리 관리 (Resilience4j)
└── 에러 정규화       거래소별 에러 코드를 내부 표준 에러로 변환
```

### 핵심 원칙

- Exchange Service는 **상태를 최소화**한다. 거래소 API 호출 결과를 내부 서비스로 전달하는 어댑터 역할에 집중한다.
- **거래소 API Key**는 AES-256-GCM으로 암호화하여 DB에 저장한다. 메모리 상에서만 복호화하여 사용한다.
- Rate Limit 초과 시 요청을 거부(빠른 실패)하며, 재시도는 요청 서비스(Market/Trade)의 책임이다.

---

## 2. 헥사고날 아키텍처 레이어

```
domain/
  model/         ExchangeAccount, ApiKeyStatus
  port/
    in/          RegisterExchangeAccountUseCase
                 DeleteExchangeAccountUseCase
                 HandleSymbolQueryUseCase     (Market Kafka Command 수신)
                 HandleCandleQueryUseCase     (Market Kafka Command 수신)
                 HandleOrderSubmitUseCase     (Trade Kafka Command 수신)
                 HandleOrderCancelUseCase     (Trade Kafka Command 수신)
    out/         FindExchangeAccountOutput, SaveExchangeAccountOutput
                 UpbitPublicApiOutput         (심볼/캔들 조회 — Public API)
                 UpbitPrivateApiOutput        (주문 실행/취소 — Private API)
                 PublishSymbolReplyOutput     (Kafka → Market)
                 PublishCandleReplyOutput     (Kafka → Market)
                 PublishOrderStatusOutput     (Kafka → Trade)

application/
  usecase/       RegisterExchangeAccountService
                 HandleSymbolQueryService
                 HandleCandleQueryService
                 HandleOrderSubmitService
                 HandleOrderCancelService

infrastructure/
  kafka/         SymbolQueryCommandConsumer    (command.exchange.market.find-all-symbol 구독)
                 CandleQueryCommandConsumer    (command.exchange.market.find-all-candle 구독)
                 OrderSubmitCommandConsumer    (command.exchange.trade.submit-order 구독)
                 OrderCancelCommandConsumer    (command.exchange.trade.cancel-order 구독)
                 SymbolReplyProducer           (implements PublishSymbolReplyOutput)
                 CandleReplyProducer           (implements PublishCandleReplyOutput)
                 OrderStatusEventProducer      (implements PublishOrderStatusOutput)
                 UserWithdrawnEventConsumer    (trade-pilot.userservice.user 구독 → ExchangeAccount REVOKED)
  upbit/         UpbitPublicApiAdapter         (implements UpbitPublicApiOutput)
                 UpbitPrivateApiAdapter        (implements UpbitPrivateApiOutput)
  crypto/        ApiKeyCryptoService           (AES-256-GCM 암복호화)
  persistence/   ExchangeAccountJpaAdapter
                   (implements FindExchangeAccountOutput, SaveExchangeAccountOutput)
  web/           ExchangeAccountController
```

---

## 3. 도메인 모델

```
ExchangeAccount (Aggregate Root)
├── accountIdentifier          : UUID
├── userIdentifier             : UUID
├── exchange           : ExchangeType       -- UPBIT | BINANCE (현재: UPBIT만)
├── encryptedAccessKey : String             -- AES-256-GCM 암호화된 Access Key
├── encryptedSecretKey : String             -- AES-256-GCM 암호화된 Secret Key
├── status             : ApiKeyStatus
├── createdAt          : OffsetDateTime
└── updatedAt          : OffsetDateTime
```

### Value Objects

```kotlin
enum class ExchangeType { UPBIT }

enum class ApiKeyStatus {
    ACTIVE,    // 정상 사용 중
    REVOKED,   // 사용자가 삭제 요청 (소프트 딜리트)
    INVALID,   // 거래소 API 호출 실패로 자동 비활성화
}
```

### API Key 암호화 전략

API Key는 DB에 평문으로 저장하지 않는다. AES-256-GCM을 사용해 암호화한다.

```kotlin
@Service
class ApiKeyCryptoService(
    @Value("\${crypto.aes.key}") private val rawKey: String,  // 32바이트 Base64
) {
    private val secretKey: SecretKey by lazy {
        val decoded = Base64.getDecoder().decode(rawKey)
        SecretKeySpec(decoded, "AES")
    }

    fun encrypt(plaintext: String): String {
        val cipher = Cipher.getInstance("AES/GCM/NoPadding")
        val iv = ByteArray(12).also { SecureRandom().nextBytes(it) }
        cipher.init(Cipher.ENCRYPT_MODE, secretKey, GCMParameterSpec(128, iv))
        val encrypted = cipher.doFinal(plaintext.toByteArray(Charsets.UTF_8))
        // IV(12) + Ciphertext 를 Base64로 저장
        return Base64.getEncoder().encodeToString(iv + encrypted)
    }

    /**
     * API Key를 CharArray로 복호화한다.
     * 사용 후 반드시 Arrays.fill(result, '\0')으로 메모리에서 폐기해야 한다.
     * String은 immutable이라 GC 전까지 힙에 잔류하므로, 민감 데이터는 CharArray로 취급한다.
     */
    fun decrypt(ciphertext: String): CharArray {
        val data = Base64.getDecoder().decode(ciphertext)
        val iv = data.copyOfRange(0, 12)
        val encrypted = data.copyOfRange(12, data.size)
        val cipher = Cipher.getInstance("AES/GCM/NoPadding")
        cipher.init(Cipher.DECRYPT_MODE, secretKey, GCMParameterSpec(128, iv))
        val decrypted = cipher.doFinal(encrypted)
        val result = String(decrypted, Charsets.UTF_8).toCharArray()
        Arrays.fill(decrypted, 0)  // 중간 ByteArray 즉시 폐기
        return result
    }
}
```

**사용 패턴**:
```kotlin
val apiKey = cryptoService.decrypt(account.encryptedAccessKey)
try {
    upbitApi.call(apiKey)
} finally {
    Arrays.fill(apiKey, '\0')  // API 호출 완료 후 즉시 메모리 폐기
}
```

> JVM Heap Dump 분석으로 API Key가 노출되는 것을 방지한다.
> String 대신 CharArray를 사용하면 사용 후 명시적으로 제로화할 수 있다.

> 암호화 키(`crypto.aes.key`)는 Kubernetes Secret으로 주입한다. 코드·설정 파일에 평문으로 포함하지 않는다.

---

## 4. Rate Limit 전략

거래소 API의 Rate Limit을 초과하면 거래소가 요청을 거부하거나 계정을 일시 차단한다.
Exchange Service는 Resilience4j RateLimiter를 사용해 **Public API 풀**과 **Private API 풀**을 분리 관리한다.

```
Exchange Service
│
├── PUBLIC_API 풀 (데이터 수집 전용)
│     Market Service ──▶ 심볼 목록 조회
│     Market Service ──▶ 캔들 데이터 조회
│     Rate Limit: 10 req/s (업비트 기준)
│
└── PRIVATE_API 풀 (주문 실행 전용)
      Trade Service ──▶ 주문 제출
      Trade Service ──▶ 주문 취소
      Rate Limit: 8 req/s (업비트 기준)
```

```kotlin
@Configuration
class RateLimiterConfig {

    @Bean
    fun publicApiRateLimiter(registry: RateLimiterRegistry): RateLimiter =
        registry.rateLimiter("upbit-public", RateLimiterConfig.custom()
            .limitForPeriod(10)
            .limitRefreshPeriod(Duration.ofSeconds(1))
            .timeoutDuration(Duration.ofMillis(500))  // Rate Limit 초과 시 500ms 대기 후 실패
            .build()
        )

    @Bean
    fun privateApiRateLimiter(registry: RateLimiterRegistry): RateLimiter =
        registry.rateLimiter("upbit-private", RateLimiterConfig.custom()
            .limitForPeriod(8)
            .limitRefreshPeriod(Duration.ofSeconds(1))
            .timeoutDuration(Duration.ofMillis(500))
            .build()
        )
}
```

Rate Limit 초과(`RequestNotPermitted`) 시 즉시 실패 처리하고, reply-failure 또는 에러 이벤트로 호출 서비스에 알린다.

---

## 5. Kafka 인터페이스

### 수신 — Market Service 심볼 조회 (Command/Reply)

```kotlin
// 구독 토픽
// command.exchange.market.find-all-symbol

data class FindAllMarketSymbolCommand(
    val requestIdentifier : UUID,
    val market    : String,   // "KRW"
) : CommandBaseMessage

// 발행 토픽 — Envelope.callback으로 결정
// reply.market.exchange.find-all-symbol

data class FindAllMarketSymbolReply(
    val requestIdentifier : UUID,
    val symbols   : List<SymbolDto>,
) : CommandBaseMessage

data class SymbolDto(
    val market     : String,  // "KRW-BTC"
    val baseAsset  : String,  // "BTC"
    val quoteAsset : String,  // "KRW"
)
```

### 수신 — Market Service 캔들 조회 (Command/Reply)

```kotlin
// 구독 토픽
// command.exchange.market.find-all-candle

data class FindAllMarketCandleCommand(
    val requestIdentifier : UUID,
    val market    : String,     // "KRW-BTC"
    val interval  : String,     // "minutes", "days" 등 업비트 규격
    val count     : Int,        // 최대 200
    val to        : String?,    // ISO-8601, null이면 최신
) : CommandBaseMessage

// 발행 토픽 (성공)
// reply.market.exchange.find-all-candle

data class FindAllMarketCandleReply(
    val requestIdentifier : UUID,
    val candles   : List<CandleDto>,
) : CommandBaseMessage

// 발행 토픽 (실패)
// reply-failure.market.exchange.find-all-candle

data class FindAllMarketCandleReplyFailure(
    val requestIdentifier : UUID,
    val errorCode : String,
    val message   : String,
) : CommandBaseMessage
```

### 수신 — Trade Service 주문 제출 (단방향 Command)

```kotlin
// 구독 토픽
// command.exchange.trade.submit-order

data class SubmitOrderCommand(
    val orderIdentifier           : UUID,
    val exchangeAccountIdentifier : UUID,
    val symbolIdentifier          : UUID,
    val side              : OrderSide,
    val type              : OrderType,
    val quantity          : BigDecimal,
    val price             : BigDecimal?,   // LIMIT이면 지정가, MARKET이면 null
) : CommandBaseMessage
```

**처리 흐름:**
```
1. ExchangeAccount 조회 (exchangeAccountIdentifier 기준, ACTIVE 검증)
2. API Key 복호화
3. Private API Rate Limiter 획득 (초과 시 ORDER_STATUS 이벤트로 REJECTED 발행)
4. 업비트 POST /v1/orders 호출
5. 성공: OrderStatusEvent(SUBMITTED, exchangeOrderId) 발행
6. 실패: OrderStatusEvent(REJECTED, reason) 발행
```

### 수신 — Trade Service 주문 취소 (단방향 Command)

```kotlin
// 구독 토픽
// command.exchange.trade.cancel-order

data class CancelOrderCommand(
    val orderIdentifier            : UUID,
    val exchangeAccountIdentifier  : UUID,        // API Key 조회에 필요
    val exchangeOrderId    : String,
) : CommandBaseMessage
```

**처리 흐름:**
```
1. ExchangeAccount 조회 (exchangeAccountIdentifier 기준, ACTIVE 검증)
2. API Key 복호화
3. Private API Rate Limiter 획득
4. 업비트 DELETE /v1/orders?identifier={exchangeOrderId} 호출
5. 성공: OrderStatusEvent(CANCELLED) 발행
6. 실패: 로그 기록 (Trade Service가 다음 사이클에 재시도)
```

### 발행 — 주문 상태 이벤트 (단방향 Event)

```kotlin
// 발행 토픽
// event.exchange.order-status

data class OrderStatusEvent(
    val orderIdentifier         : UUID,
    val exchangeOrderId : String?,
    val status          : ExchangeOrderStatus,
    val filledQuantity  : BigDecimal,
    val filledPrice     : BigDecimal?,
    val fee             : BigDecimal?,
    val reason          : String?,
) : EventBaseMessage

enum class ExchangeOrderStatus {
    SUBMITTED,
    PARTIALLY_FILLED,
    FILLED,
    CANCELLED,
    REJECTED,
}
```

> 업비트는 WebSocket으로 실시간 체결 알림을 제공한다. Exchange Service는 WebSocket을 구독해 체결 이벤트를 수신하고, 이를 `event.exchange.order-status`로 Kafka에 발행한다. 미체결 상태 추적은 WebSocket 연결 유지로 처리한다.

---

## 6. DB 스키마

Exchange Service는 거래소 계정 정보만 영속화한다.

```sql
CREATE TABLE exchange_account (
    id                  UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id             UUID        NOT NULL,
    exchange            VARCHAR(20) NOT NULL DEFAULT 'UPBIT',
    encrypted_access_key TEXT       NOT NULL,
    encrypted_secret_key TEXT       NOT NULL,
    status              VARCHAR(20) NOT NULL DEFAULT 'ACTIVE',
    created_date        TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    modified_date       TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_ea_user   ON exchange_account (user_id);
CREATE INDEX idx_ea_status ON exchange_account (status);

-- 사용자당 거래소별 활성 계정은 1개로 제한
CREATE UNIQUE INDEX idx_ea_user_exchange_active
    ON exchange_account (user_id, exchange)
    WHERE status = 'ACTIVE';
```

> Exchange Service는 **Stateless에 가깝다.** 주문 이력·체결 내역은 Trade Service가 관리한다. Exchange Service는 거래소 API Key 정보만 저장한다.

---

## 7. API 엔드포인트

### ExchangeAccount (거래소 계정 관리)

| Method | 경로 | Role | 설명 |
|--------|------|------|------|
| `POST` | `/exchange-accounts` | USER | 거래소 API Key 등록 |
| `GET` | `/exchange-accounts` | USER | 내 거래소 계정 목록 (Key 평문 미노출) |
| `GET` | `/exchange-accounts/{id}` | USER | 계정 상세 (Key 평문 미노출) |
| `DELETE` | `/exchange-accounts/{id}` | USER | API Key 삭제 (REVOKED 처리) |
| `POST` | `/exchange-accounts/{id}/validate` | USER | API Key 유효성 검증 (거래소 API 호출) |

> API Key 조회 API는 암호화된 값이나 마스킹된 형태(`****xxxx`)만 반환한다. 평문 Key는 절대 응답에 포함하지 않는다.

---

## 8. 에러 코드

| 코드 | 상수 | 설명 |
|------|------|------|
| `EX001` | `EXCHANGE_ACCOUNT_NOT_FOUND` | 거래소 계정 없음 |
| `EX002` | `EXCHANGE_ACCOUNT_REVOKED` | 삭제된 계정 |
| `EX003` | `EXCHANGE_ACCOUNT_INVALID` | 유효하지 않은 API Key |
| `EX004` | `RATE_LIMIT_EXCEEDED` | Rate Limit 초과 |
| `EX005` | `EXCHANGE_API_ERROR` | 거래소 API 오류 (4xx/5xx) |
| `EX006` | `DUPLICATE_ACTIVE_ACCOUNT` | 해당 거래소 활성 계정 이미 존재 |
| `EX007` | `ORDER_SUBMIT_FAILED` | 주문 제출 실패 (거래소 거부) |
| `EX008` | `ORDER_CANCEL_FAILED` | 주문 취소 실패 |

---

## 9. Event 수신 — UserWithdrawnEvent

```
구독 토픽 : trade-pilot.userservice.user  (eventType: "user-withdrawn")
처리      : userIdentifier에 속한 모든 ExchangeAccount → REVOKED 처리
보존      : 감사 목적으로 레코드 보존 (status=REVOKED, 복호화 불가 상태)
```

> 회원 탈퇴 시 암호화된 API Key가 활성 상태로 남아있으면 보안 리스크다.
> REVOKED 상태의 계정은 주문 제출/취소 요청 시 즉시 거부된다.
