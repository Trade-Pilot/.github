# 백엔드 코드 컨벤션 — Trade Pilot

> 모든 백엔드 서비스가 준수해야 하는 코드 작성 규칙, 네이밍 표준, 계층별 패턴 정의

---

## 1. 기술 스택 요약

| 분류 | 기술 | 버전 |
|------|------|------|
| 언어 | Kotlin | 2.0.21 |
| 프레임워크 | Spring Boot | 3.4.0 |
| JDK | Eclipse Temurin | 21 |
| ORM | JPA, QueryDSL | - |
| 빌드 | Gradle (Kotlin DSL) | 8.x |
| 데이터베이스 | PostgreSQL | 16 |
| 시계열 DB | TimescaleDB (Market Service) | - |
| 캐시 | Redis | 7 |
| 메시징 | Apache Kafka (KRaft) | 7.6.0 |
| 동기 통신 | gRPC | - |
| 컨테이너 | Kubernetes (K3s) | - |

---

## 2. 프로젝트 구조 — 헥사고날 아키텍처

### 2.1 패키지 구조

각 서비스는 아래의 표준 패키지 구조를 따른다.

```
com.tradepilot.{서비스명}/
├── domain/
│   ├── model/         # Aggregate Root, Entity, Value Object, Enum
│   ├── service/       # 도메인 서비스 (AgentRiskManager, PortfolioUpdater 등)
│   └── port/
│       ├── in/        # Input Port (UseCase 인터페이스, Command 객체)
│       └── out/       # Output Port (Repository, 외부 서비스 인터페이스)
├── application/
│   └── usecase/       # UseCase 구현체 (Input Port implements)
└── infrastructure/
    ├── persistence/   # JPA Entity, JPA Repository, Entity ↔ Domain Mapper
    ├── kafka/         # Producer, Consumer
    ├── grpc/          # gRPC Server, Client Adapter
    ├── redis/         # Redis 캐시 어댑터
    └── web/           # REST Controller, Request/Response DTO
```

### 2.2 계층 간 의존성 규칙

```
domain  ← 외부 의존성 없음 (Spring, JPA, Jackson 어노테이션 금지)
application ← domain만 의존
infrastructure ← domain + application + 외부 라이브러리 (Spring, JPA, Kafka, gRPC 등)
```

- **domain 레이어**: 순수 Kotlin 코드만 허용. `@Entity`, `@Service`, `@Transactional` 등 프레임워크 어노테이션 사용 금지.
- **application 레이어**: `@Service`, `@Transactional` 허용. infrastructure 레이어에 직접 의존하지 않고 Output Port를 통해 접근.
- **infrastructure 레이어**: 프레임워크 어노테이션 자유롭게 사용. Output Port를 구현하여 domain/application에 주입.

---

## 3. 네이밍 규칙

### 3.1 패키지

소문자, 단수형을 사용한다.

```
com.tradepilot.agentservice.domain.model
com.tradepilot.marketservice.infrastructure.persistence
com.tradepilot.tradeservice.application.usecase
```

### 3.2 클래스

| 역할 | 네이밍 규칙 | 예시 |
|------|-------------|------|
| Aggregate Root | 도메인 이름 그대로 | `User`, `Agent`, `Strategy`, `Portfolio` |
| Entity | 도메인 이름 그대로 | `Signal`, `Position`, `Execution` |
| Value Object | `@JvmInline value class` + 도메인 타입 | `UserId`, `MarketSymbolCode` |
| Enum | 도메인 의미 반영 | `AgentStatus`, `SignalType`, `OrderSide` |
| UseCase 인터페이스 | `{동사}{도메인}UseCase` | `CreateAgentUseCase`, `AnalyzeAgentUseCase` |
| UseCase 구현체 | `{동사}{도메인}Service` | `CreateAgentService`, `AnalyzeAgentService` |
| Controller | `{도메인}Controller` | `AgentController`, `StrategyController` |
| Repository Port (Output) | `{동사}{도메인}Output` | `FindAgentOutput`, `SaveAgentOutput` |
| JPA Adapter | `{도메인}JpaAdapter` | `AgentJpaAdapter`, `PortfolioJpaAdapter` |
| JPA Entity | `{도메인}JpaEntity` | `AgentJpaEntity`, `StrategyJpaEntity` |
| Kafka Consumer | `{메시지명}Consumer` | `AnalyzeAgentCommandConsumer`, `UserWithdrawnEventConsumer` |
| Kafka Producer | `{메시지명}Producer` | `AnalyzeAgentReplyProducer`, `AgentTerminatedEventProducer` |
| gRPC Server | `{서비스명}GrpcServer` | `MarketCandleGrpcServer`, `AgentGrpcServer` |
| gRPC Client Adapter | `{서비스명}GrpcAdapter` | `MarketCandleGrpcAdapter`, `MarketSymbolGrpcAdapter` |
| 도메인 서비스 | 비즈니스 의미 반영 | `AgentRiskManager`, `PortfolioUpdater` |
| 도메인 예외 | `{도메인}{상황}Exception` | `AgentNotFoundException`, `InsufficientCashException` |
| 에러 코드 Enum | `{서비스명}ErrorCode` | `AgentErrorCode`, `TradeErrorCode` |
| Fixture (테스트) | `{도메인}Fixture` | `AgentFixture`, `PortfolioFixture` |

### 3.3 프로퍼티 / 필드

| 분류 | 규칙 | 올바른 예시 | 금지 예시 |
|------|------|-------------|-----------|
| PK 식별자 | `identifier` | `identifier: UUID` | `id` |
| FK 참조 | `{참조도메인}Identifier` | `userIdentifier`, `agentIdentifier` | `userId`, `agentId` |
| 생성일 | `createdDate` | `createdDate: OffsetDateTime` | `createdAt`, `created_at` |
| 수정일 | `modifiedDate` | `modifiedDate: OffsetDateTime` | `updatedAt`, `updated_at` |
| Boolean | `is{상태}` | `isRevoked`, `isDeleted`, `isActive` | `revoked`, `deleted` |
| 금액/수량 | `BigDecimal` 필수 | `cash: BigDecimal`, `quantity: BigDecimal` | `Double`, `Float` |

> **메서드 이름에서는 `Id`를 사용할 수 있다** (프로퍼티와 구분).
> 예: `findById()`, `findByAgentId()` — 메서드 파라미터나 반환 필드는 `Identifier` 접미사.

### 3.4 메서드

| 유형 | 네이밍 규칙 | 예시 |
|------|-------------|------|
| 단건 조회 | `findBy{조건}` | `findByIdentifier()`, `findByAgentIdForUpdate()` |
| 다건 조회 | `findAllBy{조건}` | `findAllByStatus()`, `findAllByUserId()` |
| 조회 (존재 보장) | `getBy{조건}` | `getByIdentifier()` — 없으면 예외 |
| 저장 | `save` | `save(agent)` |
| 상태 변경 | 도메인 동사 사용 | `activate()`, `withdraw()`, `collectStart()`, `emergencyStop()` |
| 검증 | `validate`, `require` | `validate()`, `require(condition) { message }` |

### 3.5 Kafka 토픽

**패턴**: `{type}.{수신자/발행자}.{발신자}.{액션}`

| 메시지 타입 | 패턴 | 설명 |
|------------|------|------|
| `command` | `command.{수신자}.{발신자}.{액션}` | 요청 전달 |
| `reply` | `reply.{수신자}.{발신자}.{액션}` | 응답 전달 (command의 발신자가 수신) |
| `reply-failure` | `reply-failure.{수신자}.{발신자}.{액션}` | 실패 응답 |
| `event` | `event.{발행자}.{액션}` | 단방향 이벤트 |

**토픽 상수 정의** — `SCREAMING_SNAKE_CASE`:

```kotlin
object KafkaTopics {
    // Command: VirtualTrade(발신) → Agent(수신)
    const val COMMAND_AGENT_VIRTUAL_TRADE_ANALYZE = "command.agent.virtual-trade.analyze-strategy"

    // Reply: Agent(발신) → VirtualTrade(수신)
    const val REPLY_VIRTUAL_TRADE_AGENT_ANALYZE = "reply.virtual-trade.agent.analyze-strategy"

    // Event: 단방향
    const val EVENT_VIRTUAL_TRADE_EXECUTION = "event.virtual-trade.execution"
    const val EVENT_TRADE_EXECUTION = "event.trade.execution"
    const val EVENT_AGENT_TERMINATED = "trade-pilot.agentservice.agent"

    // DLQ
    // dlq.{원본토픽명} — 예: dlq.command.agent.trade.analyze-strategy

    // 전역
    const val NOTIFICATION_COMMAND = "trade-pilot.notification.command"
}
```

### 3.6 에러 코드

**형식**: `{서비스코드}{3자리번호}`

| 서비스 | 코드 범위 |
|--------|----------|
| User Service | `U001` ~ `U999` |
| Exchange Service | `EX001` ~ `EX999` |
| Market Service | `MS001` ~ `MS999` |
| Agent Service | `A001` ~ `A999` |
| Simulation Service | `S001` ~ `S999` |
| VirtualTrade Service | `VT001` ~ `VT999` |
| Trade Service | `T001` ~ `T999` |
| Notification Service | `N001` ~ `N999` |

### 3.7 Redis Lock Key

**패턴**: `{domain}:{operation}:{identifier}`

```
outbox:relay:market
collect:symbol:KRW-BTC
virtual-trade:close-position:{accountIdentifier}
```

### 3.8 Flyway 마이그레이션 파일

**패턴**: `V{YYYYMMDD}_{순번}__{설명}.sql`

```
V20260320_001__create_user_table.sql
V20260320_002__create_refresh_token_table.sql
V20260321_001__add_nickname_to_user.sql
```

---

## 4. 도메인 모델 규칙

### 4.1 Aggregate Root

도메인 레이어에 프레임워크 어노테이션을 사용하지 않는다. 상태 변경은 반드시 메서드를 통해 수행하며, 외부에서 직접 setter를 호출하지 않는다.

```kotlin
class Agent(
    val identifier: UUID,
    val userIdentifier: UUID,
    val strategyIdentifier: UUID,
    var status: AgentStatus,
    val riskConfig: RiskConfig,
    val initialCapital: BigDecimal,
    val createdDate: OffsetDateTime,
    var modifiedDate: OffsetDateTime,
) {
    fun activate() {
        require(status == AgentStatus.INACTIVE) { "INACTIVE 상태에서만 활성화 가능" }
        status = AgentStatus.ACTIVE
        modifiedDate = OffsetDateTime.now()
    }

    fun terminate() {
        require(status != AgentStatus.TERMINATED) { "이미 종료된 에이전트" }
        status = AgentStatus.TERMINATED
        modifiedDate = OffsetDateTime.now()
    }

    fun pause() {
        require(status == AgentStatus.ACTIVE) { "ACTIVE 상태에서만 일시정지 가능" }
        status = AgentStatus.PAUSED
        modifiedDate = OffsetDateTime.now()
    }

    fun resume() {
        require(status == AgentStatus.PAUSED) { "PAUSED 상태에서만 재개 가능" }
        status = AgentStatus.ACTIVE
        modifiedDate = OffsetDateTime.now()
    }
}
```

### 4.2 Value Object

Kotlin의 `@JvmInline value class`를 활용하여 타입 안전성을 확보한다.

```kotlin
@JvmInline
value class UserId(val value: UUID) {
    companion object {
        fun of(value: UUID) = UserId(value)
        fun generate() = UserId(UUID.randomUUID())
    }
}
```

### 4.3 불변식 검증

| 시점 | 방법 |
|------|------|
| 객체 생성 시 | Factory 또는 생성자에서 `require`로 검증 |
| 상태 전이 시 | Aggregate Root 메서드 내에서 `require`로 검증 |
| 외부 입력 | DTO에 `@Valid`, JSR-303 어노테이션 적용 |

```kotlin
// Factory 패턴
object AgentFactory {
    fun create(command: CreateAgentCommand): Agent {
        require(command.initialCapital > BigDecimal.ZERO) { "초기 자본금은 0보다 커야 합니다" }
        require(command.riskConfig.positionSizeRatio in BigDecimal("0.01")..BigDecimal.ONE) {
            "포지션 사이즈 비율은 1%~100% 사이여야 합니다"
        }
        return Agent(
            identifier = UUID.randomUUID(),
            userIdentifier = command.userIdentifier,
            // ...
        )
    }
}
```

### 4.4 금액 계산

금액과 수량은 반드시 `BigDecimal`을 사용한다. `Double`, `Float` 사용을 절대 금지한다.

```kotlin
// 올바른 사용
val cash: BigDecimal = BigDecimal("10000000")
val price: BigDecimal = BigDecimal("50000.12345678")

// 금지
val cash: Double = 10000000.0
```

---

## 5. Application 계층 규칙

### 5.1 UseCase 인터페이스 (Input Port)

`domain/port/in/` 패키지에 정의한다. Command 객체도 같은 패키지에 위치한다.

```kotlin
interface CreateAgentUseCase {
    fun create(command: CreateAgentCommand): Agent
}

data class CreateAgentCommand(
    val userIdentifier: UUID,
    val name: String,
    val strategyIdentifier: UUID,
    val riskConfig: RiskConfig,
    val initialCapital: BigDecimal,
)
```

### 5.2 UseCase 구현체

`application/usecase/` 패키지에 정의한다. Output Port를 통해 인프라에 접근한다.

```kotlin
@Service
class CreateAgentService(
    private val findAgent: FindAgentOutput,
    private val saveAgent: SaveAgentOutput,
    private val findStrategy: FindStrategyOutput,
) : CreateAgentUseCase {

    @Transactional
    override fun create(command: CreateAgentCommand): Agent {
        val strategy = findStrategy.findById(command.strategyIdentifier)
            ?: throw StrategyNotFoundException()
        require(strategy.status != StrategyStatus.DEPRECATED) { "DEPRECATED 전략 할당 불가" }

        val agent = AgentFactory.create(command)
        return saveAgent.save(agent)
    }
}
```

**규칙:**
- UseCase 구현체에 `@Transactional`을 선언한다 (Controller, Repository에 선언 금지).
- 읽기 전용 UseCase는 `@Transactional(readOnly = true)`를 사용한다.
- 하나의 UseCase 구현체는 하나의 비즈니스 작업만 담당한다.

---

## 6. Infrastructure 계층 규칙

### 6.1 JPA Entity ↔ Domain Model 분리

JPA Entity와 Domain Model을 반드시 분리한다. `toDomain()` / `fromDomain()` 메서드로 변환한다.

```kotlin
@Entity
@Table(name = "agent")
class AgentJpaEntity(
    @Id
    val id: UUID,

    @Column(name = "user_id")
    val userId: UUID,

    @Column(name = "strategy_id")
    val strategyId: UUID,

    @Column(name = "status")
    @Enumerated(EnumType.STRING)
    var status: String,

    @Column(name = "risk_config", columnDefinition = "jsonb")
    val riskConfig: String,

    @Column(name = "initial_capital")
    val initialCapital: BigDecimal,

    @Column(name = "created_date")
    val createdDate: OffsetDateTime,

    @Column(name = "modified_date")
    var modifiedDate: OffsetDateTime,
) {
    fun toDomain(): Agent = Agent(
        identifier = id,
        userIdentifier = userId,
        strategyIdentifier = strategyId,
        status = AgentStatus.valueOf(status),
        // ...
    )

    companion object {
        fun fromDomain(agent: Agent): AgentJpaEntity = AgentJpaEntity(
            id = agent.identifier,
            userId = agent.userIdentifier,
            strategyId = agent.strategyIdentifier,
            status = agent.status.name,
            // ...
        )
    }
}
```

### 6.2 JPA Adapter (Output Port 구현)

```kotlin
@Repository
class AgentJpaAdapter(
    private val jpaRepository: AgentJpaRepository,
) : FindAgentOutput, SaveAgentOutput {

    override fun findById(identifier: UUID): Agent? =
        jpaRepository.findById(identifier)?.toDomain()

    override fun save(agent: Agent): Agent {
        val entity = AgentJpaEntity.fromDomain(agent)
        return jpaRepository.save(entity).toDomain()
    }
}
```

### 6.3 Controller 규칙

```kotlin
@RestController
@RequestMapping("/agents")
class AgentController(
    private val createAgent: CreateAgentUseCase,
) {
    @PostMapping
    fun create(
        @RequestHeader("X-User-Id") userIdentifier: UUID,
        @Valid @RequestBody request: CreateAgentRequest,
    ): ResponseEntity<ApiResponse<AgentResponse>> {
        val command = request.toCommand(userIdentifier)
        val agent = createAgent.create(command)
        return ResponseEntity.status(201).body(ApiResponse.of(AgentResponse.from(agent)))
    }
}
```

**규칙:**
- 사용자 식별은 `X-User-Id` 헤더에서 추출한다 (API Gateway가 JWT 검증 후 주입).
- 요청 DTO에 `@Valid`를 적용하여 입력을 검증한다.
- Controller에서 비즈니스 로직을 수행하지 않는다. UseCase에 위임만 한다.
- Controller에 `@Transactional`을 선언하지 않는다.

### 6.4 공통 응답 래퍼

모든 REST API 성공 응답은 `ApiResponse`로 래핑한다.

```kotlin
data class ApiResponse<T>(val data: T) {
    companion object {
        fun <T> of(data: T) = ApiResponse(data)
    }
}

data class PagedResponse<T>(
    val data: List<T>,
    val page: PageInfo,
)

data class PageInfo(
    val number: Int,
    val size: Int,
    val totalElements: Long,
    val totalPages: Int,
)
```

### 6.5 Kafka Envelope

모든 Kafka 메시지는 공통 Envelope로 래핑한다.

```kotlin
data class KafkaEnvelope<T>(
    val messageIdentifier: UUID,
    val timestamp: OffsetDateTime,
    val traceIdentifier: String,
    val callback: String?,
    val payload: T,
)
```

### 6.6 Kafka Consumer 규칙

멱등성을 보장하기 위해 `processed_events` 테이블로 중복 처리를 방지한다.

```kotlin
@KafkaListener(topics = [KafkaTopics.COMMAND_AGENT_VIRTUAL_TRADE_ANALYZE], groupId = "agent-consumer")
fun consume(record: ConsumerRecord<String, String>) {
    val key = ProcessedEventKey(record.topic(), record.partition(), record.offset())
    if (processedEventRepository.existsById(key)) return

    transactionTemplate.execute {
        processedEventRepository.save(ProcessedEvent(key))
        handleMessage(record)
    }
}
```

**규칙:**
- 모든 Consumer는 `processed_events` 테이블로 멱등성을 보장한다.
- 비즈니스 로직과 멱등성 레코드 INSERT를 동일 트랜잭션으로 묶는다.
- 3회 재시도 실패 시 DLQ(`dlq.{원본토픽명}`)로 이동한다.
- DLQ 메시지 발생 시 관리자 알림을 발송한다.

### 6.7 Outbox 패턴

DB 트랜잭션과 Kafka 발행의 원자성이 필요한 경우 Outbox 패턴을 적용한다.

```kotlin
@Transactional
fun withdraw(command: WithdrawCommand) {
    val user = userRepository.findByIdForUpdate(command.userIdentifier)
        ?: throw UserNotFoundException()

    user.withdraw()
    userRepository.save(user)

    // 동일 트랜잭션 내에서 Outbox INSERT
    outboxRepository.save(OutboxEvent(
        id = UUID.randomUUID(),
        aggregateType = "User",
        aggregateIdentifier = user.identifier.toString(),
        eventType = "USER_WITHDRAWN",
        payload = objectMapper.writeValueAsString(UserWithdrawnPayload(user.identifier)),
        traceIdentifier = tracer.currentSpan()?.context()?.traceId(),
        parentSpanIdentifier = tracer.currentSpan()?.context()?.spanId(),
        status = OutboxStatus.PENDING,
        createdAt = OffsetDateTime.now(),
        publishedAt = null,
    ))
}
```

**적용 대상:**
- User Service: `withdraw()` → `UserWithdrawnEvent`
- Market Service: `collectStart()` → COMMAND, `collectComplete()` → EVENT
- Agent Service: `terminate()` → `AgentTerminatedEvent`
- Trade Service: 주문 실행/체결/실패 이벤트
- VirtualTrade Service: 가상 체결 이벤트

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

---

## 11. 테스트 규칙

### 11.1 테스트 피라미드

| 계층 | 비율 | 도구 | 범위 |
|------|------|------|------|
| Unit Test | 70% | JUnit 5, MockK | 도메인 모델, 도메인 서비스, Value Object |
| Integration Test | 20% | Testcontainers, Spring Boot Test | DB, Kafka, Redis, gRPC |
| E2E Test | 10% | REST Assured, Testcontainers | 서비스 간 전체 흐름 |

### 11.2 네이밍 규칙

**패턴**: `` `{메서드명}_{시나리오}_{기대결과}` ``

```kotlin
@Test
fun `withdraw_정상상태_WITHDRAWN으로전이`() { ... }

@Test
fun `reserveCash_가용현금부족_InsufficientCashException`() { ... }

@Test
fun `activate_TERMINATED상태_InvalidStateException`() { ... }
```

### 11.3 Given-When-Then 패턴

모든 테스트는 Given-When-Then 패턴을 따른다.

```kotlin
@Test
fun `activate_INACTIVE상태_ACTIVE전이및Portfolio초기화`() {
    // Given: INACTIVE 상태의 Agent, initialCapital = 10,000,000
    val agent = AgentFixture.create(status = AgentStatus.INACTIVE)

    // When: activate() 호출
    agent.activate()

    // Then: status == ACTIVE
    assertThat(agent.status).isEqualTo(AgentStatus.ACTIVE)
}
```

### 11.4 Fixture 패턴

테스트 데이터는 Builder 패턴 또는 Fixture를 사용한다. 프로퍼티명은 `Identifier` 접미사를 사용한다.

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
```

### 11.5 통합 테스트 격리

`@DirtiesContext` 대신 **테이블 TRUNCATE**를 사용하여 테스트를 격리한다.

```kotlin
@TestInstance(TestInstance.Lifecycle.PER_CLASS)
@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT)
abstract class IntegrationTestBase {

    @Autowired
    lateinit var jdbcTemplate: JdbcTemplate

    @BeforeEach
    fun cleanUp() {
        jdbcTemplate.execute("TRUNCATE TABLE outbox, processed_events CASCADE")
    }
}
```

### 11.6 태그 분리

```kotlin
@Tag("integration")
@SpringBootTest
class PortfolioRepositoryIntegrationTest { ... }

@Tag("e2e")
class VirtualTradeE2ETest { ... }
```

### 11.7 커버리지 목표

| 계층 | 목표 |
|------|------|
| 도메인 모델 (`domain/model`) | 90% 이상 |
| 도메인 서비스 (`domain/service`) | 85% 이상 |
| Application (`application/usecase`) | 80% 이상 |
| Infrastructure (`infrastructure`) | 60% 이상 |
| 전체 | 75% 이상 |

### 11.8 Mock 전략

| 대상 | Mock 도구 | 이유 |
|------|-----------|------|
| 거래소 API | WireMock | 외부 API 의존성 제거 |
| 다른 MSA 서비스 | MockK / WireMock | 서비스 격리 |
| Kafka | EmbeddedKafka (통합) / MockK (단위) | 실제 동작 검증 / 속도 확보 |
| Redis | Testcontainers (통합) / MockK (단위) | 캐시/Lock 동작 검증 |
| gRPC | InProcessServer (통합) / MockK (단위) | 네트워크 없이 테스트 |
| 시간 | `Clock` 주입 | 스케줄러, 타임아웃 테스트 시간 제어 |

---

## 12. 코드 스타일

### 12.1 정적 분석 도구

| 도구 | 용도 |
|------|------|
| ktlint | Kotlin 공식 스타일 가이드 준수 |
| detekt | 정적 분석 (코드 복잡도, 잠재적 버그) |
| JaCoCo | 테스트 커버리지 측정 |

### 12.2 포맷 규칙

- 최대 라인 길이: **120자**
- 들여쓰기: **4 spaces** (탭 금지)
- trailing comma 사용

```kotlin
data class CreateAgentCommand(
    val userIdentifier: UUID,
    val name: String,
    val strategyIdentifier: UUID,
    val riskConfig: RiskConfig,
    val initialCapital: BigDecimal,  // trailing comma
)
```

### 12.3 주석 규칙

- **사소한 주석 금지**: 코드 동작을 번역하는 주석을 작성하지 않는다.
- **"Why" over "What"**: 복잡한 비즈니스 로직의 이유만 문서화한다.
- **레거시 코드 삭제**: 사용하지 않는 코드를 주석 처리하지 않고 즉시 삭제한다.

```kotlin
// 금지 — 코드를 번역하는 주석
val user = userRepository.findById(id) // 유저를 조회한다

// 올바른 사용 — 비즈니스 의사결정 근거
// DEPRECATED 전략은 기존 Active Agent의 신호 생성은 허용하되 신규 할당만 차단한다.
// 운영 중인 에이전트의 중단을 방지하기 위함.
require(strategy.status != StrategyStatus.DEPRECATED) { "DEPRECATED 전략 할당 불가" }
```

---

## 13. 공통 모듈 (shared-kernel)

서비스 간 공유되는 코드는 `shared-kernel` 모듈에 정의한다.

```
shared-kernel/
├── KafkaEnvelope.kt           # Kafka 공통 Envelope
├── KafkaTopics.kt             # 토픽 상수
├── ApiResponse.kt             # 공통 성공 응답
├── ApiErrorResponse.kt        # 공통 에러 응답
├── PagedResponse.kt           # 페이지네이션 응답
├── BusinessException.kt       # 도메인 예외 기반 클래스
├── ErrorCode.kt               # 에러 코드 인터페이스
├── ProcessedEvent.kt          # 멱등성 보장 엔티티
└── OutboxEvent.kt             # Outbox 패턴 엔티티
```

---

## 부록: 체크리스트

새 코드를 작성하거나 리뷰할 때 아래 항목을 확인한다.

### 도메인 모델
- [ ] domain 레이어에 Spring/JPA 어노테이션이 없는가?
- [ ] 상태 변경이 Aggregate Root 메서드를 통해 이루어지는가?
- [ ] 금액/수량에 `BigDecimal`을 사용하는가?
- [ ] 프로퍼티명이 `Identifier` 접미사를 사용하는가 (`Id` 금지)?

### Application 계층
- [ ] `@Transactional`이 UseCase 구현체에만 선언되어 있는가?
- [ ] Output Port를 통해 인프라에 접근하는가 (직접 의존 금지)?

### Infrastructure 계층
- [ ] JPA Entity와 Domain Model이 분리되어 있는가?
- [ ] Kafka Consumer에 멱등성 처리가 적용되어 있는가?
- [ ] DB + Kafka 원자성이 필요한 곳에 Outbox 패턴을 사용하는가?

### 보안
- [ ] 외부 입력에 `@Valid` 검증이 적용되어 있는가?
- [ ] 민감 정보가 로그에 노출되지 않는가?
- [ ] 환경 변수로 시크릿을 관리하는가 (하드코딩 금지)?

### 테스트
- [ ] Given-When-Then 패턴을 따르는가?
- [ ] Happy Path와 Edge Case를 모두 테스트하는가?
- [ ] 네이밍이 `{메서드명}_{시나리오}_{기대결과}` 패턴인가?
