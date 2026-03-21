# Application / Infrastructure 계층 규칙

> 원본: `backend/code-convention.md` Section 5~6

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

