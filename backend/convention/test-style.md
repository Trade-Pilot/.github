# 테스트, 코드 스타일, 공통 모듈, 체크리스트

> 원본: `backend/code-convention.md` Section 11~부록

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
