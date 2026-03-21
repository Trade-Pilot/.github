# Mock 전략, 커버리지, 네이밍, CI, 데이터 관리

> 원본: `backend/testing-strategy.md` Section 5~9

---

## 5. Mock 전략

| 대상 | Mock 도구 | 이유 |
|------|-----------|------|
| 거래소 API (Upbit) | WireMock | 외부 API 의존성 제거, 응답 시나리오 제어 |
| 다른 MSA 서비스 | MockK / WireMock | 단위 테스트 시 서비스 격리 |
| Kafka | EmbeddedKafka (통합) / MockK (단위) | 통합 테스트에서 실제 동작 검증, 단위 테스트에서 속도 확보 |
| Redis | Testcontainers Redis (통합) / MockK (단위) | 통합 테스트에서 실제 캐시/Lock 동작 검증 |
| gRPC | InProcessServer (통합) / MockK (단위) | 네트워크 없이 gRPC 서버-클라이언트 테스트 |
| 시간 | `Clock` 주입 | 스케줄러, 타임아웃 테스트에서 시간 제어 |

### WireMock 활용 예시 (거래소 API)

```kotlin
@Test
fun `Exchange_주문제출_거래소API정상응답`() {
    // Given: WireMock으로 Upbit 주문 API 정상 응답 stub
    wireMock.stubFor(post("/v1/orders")
        .willReturn(okJson("""{"uuid": "upbit-order-123", "side": "bid"}""")))

    // When: SubmitOrderCommand 처리
    // Then: Order.exchangeOrderId == "upbit-order-123"
}

@Test
fun `Exchange_주문제출_거래소API타임아웃`() {
    // Given: WireMock에서 10초 지연 응답 설정
    wireMock.stubFor(post("/v1/orders")
        .willReturn(ok().withFixedDelay(10000)))

    // When: SubmitOrderCommand 처리
    // Then: 타임아웃 예외 발생, OrderStatusEvent(REJECTED) 발행
}
```

---

## 6. 테스트 커버리지 목표

| 계층 | 목표 | 측정 도구 |
|------|------|-----------|
| 도메인 모델 (`domain/model`) | 90% 이상 | JaCoCo |
| 도메인 서비스 (`domain/service`) | 85% 이상 | JaCoCo |
| Application 계층 (`application/usecase`) | 80% 이상 | JaCoCo |
| Infrastructure 계층 (`infrastructure`) | 60% 이상 | JaCoCo |
| 전체 | 75% 이상 | JaCoCo |

### JaCoCo 설정

```kotlin
// build.gradle.kts
plugins {
    id("jacoco")
}

tasks.jacocoTestReport {
    reports {
        xml.required.set(true)
        html.required.set(true)
    }
}

tasks.jacocoTestCoverageVerification {
    violationRules {
        rule {
            element = "BUNDLE"
            limit {
                counter = "LINE"
                value = "COVEREDRATIO"
                minimum = "0.75".toBigDecimal()
            }
        }
        rule {
            element = "PACKAGE"
            includes = listOf("*.domain.model.*")
            limit {
                counter = "LINE"
                value = "COVEREDRATIO"
                minimum = "0.90".toBigDecimal()
            }
        }
    }
}
```

### 커버리지 제외 대상

```kotlin
jacocoTestReport {
    afterEvaluate {
        classDirectories.setFrom(files(classDirectories.files.map {
            fileTree(it) {
                exclude(
                    "**/config/**",           // Spring 설정 클래스
                    "**/dto/**",              // 단순 DTO
                    "**/*Application*",       // main 클래스
                    "**/generated/**",        // gRPC/QueryDSL 생성 코드
                )
            }
        }))
    }
}
```

---

## 7. 테스트 네이밍 규칙

### 패턴

```
{메서드명}_{시나리오}_{기대결과}
```

### 예시

```kotlin
@Test
fun `withdraw_정상상태_WITHDRAWN으로전이`() { ... }

@Test
fun `withdraw_이미탈퇴상태_AccountWithdrawnException`() { ... }

@Test
fun `reserveCash_가용현금부족_InsufficientCashException`() { ... }

@Test
fun `activate_TERMINATED상태_InvalidStateException`() { ... }

@Test
fun `emergencyStop_ACTIVE상태_emergencyStopped설정및PAUSED전이`() { ... }

@Test
fun `calculateBuyQuantity_maxConcurrentPositions도달_HOLD전환`() { ... }

@Test
fun `sma_데이터부족_IllegalArgumentException`() { ... }
```

### Nested Class 활용

복잡한 도메인 모델은 `@Nested` 로 시나리오를 그룹화한다.

```kotlin
@DisplayName("Order 상태 전이")
class OrderStatusTransitionTest {

    @Nested
    @DisplayName("PENDING 상태에서")
    inner class FromPending {
        @Test fun `SUBMITTED로전이_정상`() { ... }
        @Test fun `REJECTED로전이_종료`() { ... }
        @Test fun `FILLED로직접전이_InvalidStateException`() { ... }
    }

    @Nested
    @DisplayName("SUBMITTED 상태에서")
    inner class FromSubmitted {
        @Test fun `PARTIALLY_FILLED로전이_부분체결`() { ... }
        @Test fun `FILLED로전이_완전체결`() { ... }
        @Test fun `CANCELLED로전이_타임아웃취소`() { ... }
    }
}
```

---

## 8. CI 연동

### 파이프라인 구성

```yaml
# .github/workflows/test.yml
name: Test Pipeline

on:
  pull_request:
    branches: [main, develop]

jobs:
  unit-and-integration:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-java@v4
        with:
          java-version: '21'
          distribution: 'temurin'
      - name: Run Unit & Integration Tests
        run: ./gradlew test integrationTest
      - name: Check Coverage
        run: ./gradlew jacocoTestCoverageVerification
      - name: Upload Coverage Report
        uses: actions/upload-artifact@v4
        with:
          name: coverage-report
          path: build/reports/jacoco/

  e2e:
    runs-on: ubuntu-latest
    if: github.event_name == 'schedule'  # Nightly만 실행
    steps:
      - uses: actions/checkout@v4
      - name: Start Services
        run: docker-compose -f docker-compose.e2e.yml up -d
      - name: Wait for Services
        run: ./scripts/wait-for-services.sh
      - name: Run E2E Tests
        run: ./gradlew e2eTest
      - name: Stop Services
        run: docker-compose -f docker-compose.e2e.yml down
```

### 실행 정책

| 트리거 | 테스트 범위 | 필수 통과 |
|--------|------------|-----------|
| PR 생성 / Push | Unit + Integration | 커버리지 75% 미만이면 실패 |
| 머지 전 (Branch Protection) | Unit + Integration | 전체 통과 필수 |
| Nightly (매일 03:00 KST) | E2E (전체 서비스 기동) | 실패 시 Slack 알림 |

### Gradle 태스크 분리

```kotlin
// build.gradle.kts
tasks.register<Test>("integrationTest") {
    description = "통합 테스트 실행"
    group = "verification"
    useJUnitPlatform {
        includeTags("integration")
    }
    shouldRunAfter(tasks.test)
}

tasks.register<Test>("e2eTest") {
    description = "E2E 테스트 실행"
    group = "verification"
    useJUnitPlatform {
        includeTags("e2e")
    }
}

tasks.test {
    useJUnitPlatform {
        excludeTags("integration", "e2e")
    }
}
```

### 태그 사용

```kotlin
@Tag("integration")
@SpringBootTest
class PortfolioRepositoryIntegrationTest { ... }

@Tag("e2e")
class VirtualTradeE2ETest { ... }
```

---

## 9. 테스트 데이터 관리

### Fixture 패턴

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

object PortfolioFixture {
    fun create(
        cash: BigDecimal = BigDecimal("10000000"),
        reservedCash: BigDecimal = BigDecimal.ZERO,
        positions: List<Position> = emptyList(),
    ): Portfolio = Portfolio(
        cash = cash,
        reservedCash = reservedCash,
        positions = positions,
    )
}

object CandleFixture {
    fun ascending(count: Int, basePrice: BigDecimal = BigDecimal("50000")): List<CandleData> {
        return (0 until count).map { i ->
            CandleData(
                open = basePrice + (i * 100).toBigDecimal(),
                high = basePrice + (i * 100 + 50).toBigDecimal(),
                low = basePrice + (i * 100 - 50).toBigDecimal(),
                close = basePrice + (i * 100 + 30).toBigDecimal(),
                volume = BigDecimal("100"),
            )
        }
    }
}
```

### 테스트 시간 제어

```kotlin
// Clock 주입으로 시간 의존 테스트 제어
@Test
fun `LIMIT주문_타임아웃도래_취소요청발행`() {
    // Given: 현재 시각 고정
    val fixedClock = Clock.fixed(Instant.parse("2026-01-01T12:00:00Z"), ZoneOffset.UTC)
    val scheduler = OrderTimeoutScheduler(clock = fixedClock, ...)

    // LIMIT 주문 (timeoutAt = 11:50:00)
    val order = OrderFixture.create(
        type = LIMIT,
        status = SUBMITTED,
        timeoutAt = OffsetDateTime.parse("2026-01-01T11:50:00Z"),
    )

    // When: cancelTimedOutOrders() 호출
    // Then: CancelOrderCommand 발행 확인 (12:00 > 11:50 → 타임아웃)
}
```
