# 네이밍 규칙

> 원본: `backend/code-convention.md` Section 3

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
