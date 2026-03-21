# Notification Service — Notification Command, Domain Service, Preference 초기화

> 이 문서는 `backend/notification/domain.md`에서 분할되었습니다.

---

## 6. Notification Command

각 서비스가 `NOTIFICATION_COMMAND_TOPIC`에 발행하는 커맨드 구조.

```kotlin
// 각 서비스가 Notification 발행 시 사용하는 커맨드
data class SendNotificationCommand(
    val userIdentifier: UserId,
    val eventType: String,                      // 이벤트 타입 식별자 (자유 문자열)
    val variables: Map<String, String>,         // 템플릿 변수 (모든 값은 String)
)
```

> `variables`는 `Map<String, String>`이지만, **발행 서비스 측에서 타입이 보장된 DTO를 통해 생성**한다.
> Notification Service는 변수를 템플릿에 치환하기만 하므로 String으로 충분하다.

**발행 예시 (VirtualTrade Service 측):**

```kotlin
// VirtualTrade Service가 정의하는 타입화된 변수 빌더
data class OrderFilledNotificationVariables(
    val symbol: String,
    val side: OrderSide,
    val quantity: BigDecimal,
    val price: BigDecimal,
) {
    fun toVariables(): Map<String, String> = mapOf(
        "symbol"   to symbol,
        "side"     to side.name,
        "quantity" to quantity.toPlainString(),
        "price"    to price.toPlainString(),
    )
}

// 발행
val command = SendNotificationCommand(
    userIdentifier = userIdentifier,
    eventType = "VIRTUAL_ORDER_FILLED",
    variables = OrderFilledNotificationVariables(symbol, side, qty, price).toVariables(),
)
kafkaTemplate.send(NOTIFICATION_COMMAND_TOPIC, userIdentifier.value.toString(), command)
```

**주요 이벤트 타입 및 변수 목록:**

| eventType | 발행 서비스 | 주요 variables |
|-----------|-----------|---------------|
| `VIRTUAL_ORDER_FILLED` | VirtualTrade | symbol, side, quantity, price |
| `VIRTUAL_STOP_LOSS` | VirtualTrade | symbol, loss |
| `VIRTUAL_TAKE_PROFIT` | VirtualTrade | symbol, profit |
| `VIRTUAL_DAILY_LOSS_LIMIT` | VirtualTrade | lossAmount, limitAmount |
| `VIRTUAL_DAILY_REPORT` | VirtualTrade | totalPnl, winRate |
| `REAL_ORDER_FILLED` | Trade | symbol, side, quantity, price |
| `REAL_STOP_LOSS` | Trade | symbol, loss |
| `REAL_TAKE_PROFIT` | Trade | symbol, profit |
| `REAL_DAILY_LOSS_LIMIT` | Trade | lossAmount, limitAmount |
| `REAL_WEEKLY_LOSS_LIMIT` | Trade | lossAmount, limitAmount |
| `REAL_MONTHLY_LOSS_LIMIT` | Trade | lossAmount, limitAmount |
| `REAL_DAILY_REPORT` | Trade | totalPnl, winRate |
| `REAL_EMERGENCY_STOP` | Trade | reason |
| `MARKET_COLLECT_ERROR` | Market | symbol, retryCount, errorMessage |
| `MARKET_PARTITION_ERROR` | Market | errorMessage |

> 이벤트 타입 문자열은 각 서비스의 코드에서 상수로 관리한다.
> Notification Service에는 별도 enum이 없으며, 알 수 없는 eventType은 fallback 템플릿으로 처리한다.

---

## 7. Domain Service

### 7.1 NotificationDispatcher

```kotlin
interface NotificationDispatcher {
    fun dispatch(
        userIdentifier: UserId,
        eventType: String,
        variables: Map<String, String>,
    )
}
```

**알고리즘**:
1. `NotificationPreference` 조회 (`userIdentifier` + `eventType`, `isEnabled == true`, `isDeleted == false`)
   - Preference가 없으면 → 발송 스킵
2. 설정된 채널 목록의 `NotificationChannel` 조회 (`isActive == true`, `isDeleted == false`)
3. 채널 타입에 맞는 `NotificationTemplate` 조회 → 변수 치환으로 `NotificationMessage` 생성
4. 채널 타입별 발송 (`DiscordSender`) — **최대 3회 재시도 (1초 간격)**
5. `NotificationLog` 저장 (성공: SENT, retryCount=0 / 실패: FAILED, retryCount=3)

**발송 재시도 정책**:
```kotlin
const val MAX_DISPATCH_RETRY = 3
const val RETRY_DELAY_MS = 1_000L

fun sendWithRetry(channel: NotificationChannel, message: NotificationMessage): Boolean {
    repeat(MAX_DISPATCH_RETRY) { attempt ->
        runCatching { sender.send(channel, message) }
            .onSuccess { return true }
            .onFailure { if (attempt < MAX_DISPATCH_RETRY - 1) Thread.sleep(RETRY_DELAY_MS) }
    }
    return false
}
```

> Outbox 패턴을 적용하지 않는 이유: Notification Service는 Kafka 이벤트를 소비하는 종착점이다.
> 발송 실패 시 DB 상태 불일치가 발생하지 않으며, `NotificationLog`의 FAILED 기록이 감사 역할을 대신한다.

### 7.2 NotificationTemplateRenderer

```kotlin
object NotificationTemplateRenderer {
    fun render(template: NotificationTemplate, variables: Map<String, String>): NotificationMessage {
        var title = template.titleTemplate
        var body  = template.bodyTemplate
        variables.forEach { (key, value) ->
            title = title.replace("\${$key}", value)
            body  = body.replace("\${$key}", value)
        }
        return NotificationMessage(title = title, body = body)
    }
}

data class NotificationMessage(
    val title: String,
    val body: String,
)
```

**Fallback 처리**:
```kotlin
// DB에 템플릿이 없는 eventType → 기본 포맷 사용
fun fallback(eventType: String, variables: Map<String, String>): NotificationMessage =
    NotificationMessage(
        title = "[Trade Pilot] $eventType",
        body  = variables.entries.joinToString(", ") { "${it.key}=${it.value}" },
    )
```

### 7.3 UserWithdrawnEventHandler

```kotlin
// consumeUserEvents(@KafkaListener) → UserWithdrawnEventHandler.handle() 위임
// @KafkaListener는 Section 8의 중앙 리스너에서 일괄 관리
class UserWithdrawnEventHandler(
    private val channelRepository: NotificationChannelRepository,
    private val preferenceRepository: NotificationPreferenceRepository,
) {
    fun handle(event: UserWithdrawnEvent) {
        val userIdentifier = UserId.of(event.userId)
        // 소프트 딜리트 — 감사 목적으로 데이터 보존, 발송 대상에서만 제외
        channelRepository.softDeleteAllByUserId(userIdentifier)
        preferenceRepository.softDeleteAllByUserId(userIdentifier)
        // NotificationLog는 삭제하지 않음 (감사 목적)
    }
}
```

---

## 8. NotificationPreference 초기화 정책

사용자가 명시적으로 opt-in한 이벤트에만 알림을 발송한다 (기본 off).

```kotlin
fun getOrCreate(userIdentifier: UserId, eventType: String): NotificationPreference =
    preferenceRepository.findByUserIdAndEventType(userIdentifier, eventType)
        ?: NotificationPreferenceFactory.create(userIdentifier, eventType)
```
