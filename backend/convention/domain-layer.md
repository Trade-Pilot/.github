# 도메인 모델 규칙

> 원본: `backend/code-convention.md` Section 4

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
