# 예외 처리, 트랜잭션, 동시성, 로깅

> 원본: `backend/code-convention.md` Section 7~10

---

## 7. 예외 처리 규칙

### 7.1 도메인 예외 계층

```kotlin
// domain 레이어
abstract class BusinessException(
    val errorCode: ErrorCode,
) : RuntimeException(errorCode.message)

interface ErrorCode {
    val code: String
    val message: String
}
```

### 7.2 서비스별 에러 코드

```kotlin
enum class AgentErrorCode(
    override val code: String,
    override val message: String,
) : ErrorCode {
    STRATEGY_NOT_FOUND("A001", "Strategy not found"),
    STRATEGY_NOT_DRAFT("A002", "Strategy is not in DRAFT status"),
    STRATEGY_NOT_VALIDATED("A003", "DRAFT strategy cannot process trade signals"),
    STRATEGY_DEPRECATED("A004", "DEPRECATED strategy cannot be assigned to new agent"),
    AGENT_NOT_FOUND("A005", "Agent not found"),
    AGENT_NOT_ACTIVE("A006", "Agent is not active"),
    AGENT_NOT_INACTIVE("A007", "Agent is not in INACTIVE status"),
    AGENT_ALREADY_TERMINATED("A008", "Agent is already terminated"),
    PORTFOLIO_NOT_FOUND("A009", "Portfolio not found"),
    INSUFFICIENT_CASH("A010", "Insufficient cash for buy signal"),
    CANDLE_DATA_INSUFFICIENT("A011", "Insufficient candle data for indicator calculation"),
    UNSUPPORTED_STRATEGY_TYPE("A012", "Unsupported strategy type"),
    INVALID_RISK_CONFIG("A013", "Invalid risk configuration"),
}

class AgentNotFoundException : BusinessException(AgentErrorCode.AGENT_NOT_FOUND)
class InsufficientCashException : BusinessException(AgentErrorCode.INSUFFICIENT_CASH)
```

### 7.3 전역 예외 핸들러

```kotlin
@RestControllerAdvice
class GlobalExceptionHandler {

    @ExceptionHandler(BusinessException::class)
    fun handleBusiness(ex: BusinessException): ResponseEntity<ApiErrorResponse> {
        val status = errorCodeToHttpStatus(ex.errorCode)
        return ResponseEntity.status(status).body(
            ApiErrorResponse(
                code = ex.errorCode.code,
                message = ex.errorCode.message,
                timestamp = OffsetDateTime.now(),
                path = getCurrentRequestPath(),
            )
        )
    }

    @ExceptionHandler(MethodArgumentNotValidException::class)
    fun handleValidation(ex: MethodArgumentNotValidException): ResponseEntity<ApiErrorResponse> {
        val details = ex.bindingResult.fieldErrors.associate { it.field to (it.defaultMessage ?: "") }
        return ResponseEntity.badRequest().body(
            ApiErrorResponse(
                code = "VALIDATION_ERROR",
                message = "입력값 검증 실패",
                timestamp = OffsetDateTime.now(),
                path = getCurrentRequestPath(),
                details = details,
            )
        )
    }
}
```

### 7.4 에러 응답 포맷

```kotlin
data class ApiErrorResponse(
    val code: String,
    val message: String,
    val timestamp: OffsetDateTime,
    val path: String,
    val details: Map<String, String>? = null,
)
```

### 7.5 HTTP 상태 코드 매핑

| 도메인 에러 타입 | HTTP 상태 |
|-----------------|----------|
| NOT_FOUND | 404 |
| INVALID_STATE | 409 Conflict |
| VALIDATION_ERROR | 400 Bad Request |
| UNAUTHORIZED | 401 |
| FORBIDDEN | 403 |
| RATE_LIMIT_EXCEEDED | 429 |
| INTERNAL_ERROR | 500 |

---

## 8. 트랜잭션 규칙

- `@Transactional`은 **UseCase 구현체에만** 선언한다 (Controller, Repository에 선언 금지).
- 읽기 전용: `@Transactional(readOnly = true)`.
- Kafka 발행과 DB 변경이 동시에 필요하면 **Outbox 패턴**을 사용한다 (직접 Kafka 발행 금지).
- DB Lock은 최소 범위로 잡는다. `@Transactional` 범위를 최소화하여 Lock 보유 시간을 단축한다.

```kotlin
// 올바른 예
@Service
class AnalyzeAgentService : AnalyzeAgentUseCase {
    @Transactional
    override fun analyze(command: AnalyzeAgentCommand): SignalResult { ... }
}

// 금지 — Controller에 @Transactional
@RestController
class AgentController {
    @Transactional  // 금지
    @PostMapping
    fun create(...) { ... }
}
```

---

## 9. 동시성 제어 규칙

### 9.1 Lock 전략 선택 기준

```
보호 범위가 트랜잭션 내부인가?
  ├── YES → DB Pessimistic Lock (@Lock PESSIMISTIC_WRITE)
  └── NO  → 작업 시간이 짧고 예측 가능한가?
        ├── YES → Redis Distributed Lock (Redisson)
        └── NO  → DB-based Lock + 상태 머신
```

### 9.2 DB Pessimistic Lock

트랜잭션 내에서 레코드를 조회하고 즉시 업데이트하는 경우 사용한다.

```kotlin
@Lock(LockModeType.PESSIMISTIC_WRITE)
@Query("SELECT p FROM Portfolio p WHERE p.agentIdentifier = :agentId")
fun findByAgentIdForUpdate(@Param("agentId") agentId: UUID): Portfolio?
```

**적용 대상:**
- `Portfolio.reserveCash()` / `releaseReservation()` — 신호 생성 시 현금/포지션 점유
- `MarketCandleCollectTask.collectStart()` / `collectComplete()` — 수집 작업 상태 전이
- `User.withdraw()` — 회원 탈퇴 상태 전이

**Lock Timeout 설정:**

```yaml
spring:
  jpa:
    properties:
      jakarta.persistence.lock.timeout: 3000  # 3초
```

### 9.3 Redis Distributed Lock

스케줄러 중복 실행 방지 등 트랜잭션 외부에서 동작하는 작업에 사용한다.

```kotlin
@Component
class DistributedLockManager(
    private val redissonClient: RedissonClient,
) {
    fun <T> withLock(
        lockKey: String,
        waitTime: Long = 0,
        leaseTime: Long = 10,
        timeUnit: TimeUnit = TimeUnit.SECONDS,
        action: () -> T,
    ): T? {
        val lock = redissonClient.getLock(lockKey)
        if (!lock.tryLock(waitTime, leaseTime, timeUnit)) return null
        try {
            return action()
        } finally {
            if (lock.isHeldByCurrentThread) lock.unlock()
        }
    }
}
```

**적용 대상:**
- Outbox Relay Processor (100ms 폴링, 다중 Pod 중복 방지)
- Market 심볼별 수집 스케줄러

### 9.4 교착 상태 방지 원칙

1. **Lock 획득 순서 통일**: 여러 테이블에 Lock이 필요하면 항상 동일한 순서로 획득.
2. **최소 Lock 범위**: `@Transactional` 범위를 최소화하여 Lock 보유 시간 단축.
3. **타임아웃 설정**: DB Lock timeout 3초, Redis Lock leaseTime 10초 이하.

---

## 10. 로깅 규칙

### 10.1 Logger

SLF4J + Logback을 사용한다.

```kotlin
private val log = LoggerFactory.getLogger(this::class.java)
```

### 10.2 로그 레벨 기준

| 레벨 | 기준 | 예시 |
|------|------|------|
| ERROR | 시스템 장애, 데이터 손실 가능성 | DB 연결 끊김, DLQ 메시지 발생 |
| WARN | 복구 가능한 오류, Rate Limit 초과 | gRPC 타임아웃, 캔들 수집 실패 (재시도 가능) |
| INFO | 비즈니스 이벤트 | 주문 체결, 신호 생성, 에이전트 활성화 |
| DEBUG | 디버깅 정보 (프로덕션에서 비활성화) | 쿼리 파라미터, 캐시 Hit/Miss |

### 10.3 Structured Logging (JSON)

모든 로그에 `traceIdentifier`를 포함하여 분산 추적을 지원한다.

```json
{
  "timestamp": "2026-01-01T12:00:00Z",
  "level": "INFO",
  "traceIdentifier": "abc123",
  "service": "agent-service",
  "message": "Signal generated",
  "userIdentifier": "uuid",
  "agentIdentifier": "uuid",
  "signalType": "BUY"
}
```

### 10.4 민감 정보 마스킹

비밀번호, API Key, Secret Key는 로그에 출력하지 않는다. 부득이한 경우 마스킹 처리한다.

```kotlin
// 금지
log.info("API Key: $apiKey")

// 올바른 사용
log.info("API Key: ${apiKey.take(4)}****")
```

