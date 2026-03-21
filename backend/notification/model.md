# Notification Service — 서비스 책임, Aggregate, Entity, Value Object, Enum

> 이 문서는 `backend/notification/domain.md`에서 분할되었습니다.

---

## 1. 서비스 책임

**담당**:
- 사용자별 알림 채널 설정 관리 (Discord Webhook URL 등)
- 알림 수신 여부 설정 (어떤 이벤트를 어느 채널로 받을지)
- `NOTIFICATION_COMMAND_TOPIC` 소비 → 실제 메시지 발송
- 메시지 템플릿 관리 (DB에서 관리, 변수 치환 방식)
- 발송 이력 저장

**담당하지 않음**:
- 사용자 계정/인증 → User Service 담당
- "어떤 이벤트가 발생했는가"의 판단 → 각 발행 서비스 담당

**핵심 설계 원칙 — 의존성 역전**

기존 Notification Service가 다른 도메인의 이벤트 타입을 알아야 했던 구조를 역전한다.
각 서비스(VirtualTrade, Trade, Market 등)가 알림이 필요할 때 `NOTIFICATION_COMMAND_TOPIC`에 발행하며,
Notification Service는 도메인을 알 필요 없이 커맨드를 처리한다.

```
기존 (잘못된 방향):
  Notification Service ← VirtualTrade, Trade, Market 이벤트 타입 enum 의존

개선 (올바른 방향):
  VirtualTrade ──▶ NOTIFICATION_COMMAND_TOPIC ──▶ Notification Service
  Trade        ──▶ NOTIFICATION_COMMAND_TOPIC ──▶ Notification Service
  Market       ──▶ NOTIFICATION_COMMAND_TOPIC ──▶ Notification Service
```

---

## 2. Aggregate Root

### 2.1 NotificationChannel (알림 채널)

**목적**: 사용자가 등록한 알림 발송 채널(Discord 등)을 관리한다.

**속성**:
```kotlin
class NotificationChannel(
    val identifier: NotificationChannelId,  // 고유 식별자 (UUID)
    val userIdentifier: UserId,             // 소유자
    val type: ChannelType,                  // 채널 타입 (DISCORD)
    val config: ChannelConfig,              // 채널 설정 (Sealed class)
    var isActive: Boolean,                  // 활성화 여부
    var isDeleted: Boolean = false,         // 소프트 딜리트
    var deletedAt: OffsetDateTime? = null,
    val createdDate: OffsetDateTime,
    var modifiedDate: OffsetDateTime,
)
```

**ChannelConfig (Sealed class)**:
```kotlin
sealed class ChannelConfig {
    data class DiscordConfig(
        val webhookUrl: String,     // Discord Incoming Webhook URL
    ) : ChannelConfig()
    // 향후 추가: AppPushConfig 등
}
```

**비즈니스 로직**:
```kotlin
fun activate()
fun deactivate()
fun updateConfig(config: ChannelConfig)
fun softDelete()    // isDeleted = true, deletedAt = now
```

**불변 조건 (Invariants)**:
- `userIdentifier`는 변경 불가
- `type`은 변경 불가
- `isDeleted == true`인 채널로는 발송하지 않음
- `isActive == false`인 채널로는 발송하지 않음

---

### 2.2 NotificationPreference (알림 수신 설정)

**목적**: 사용자별로 어떤 이벤트를 어느 채널로 수신할지 설정한다.

**속성**:
```kotlin
class NotificationPreference(
    val identifier: NotificationPreferenceId,
    val userIdentifier: UserId,
    val eventType: String,                              // String 기반 이벤트 타입 (enum 미사용)
    val channelIdentifiers: List<NotificationChannelId>,
    var isEnabled: Boolean,
    var isDeleted: Boolean = false,
    var deletedAt: OffsetDateTime? = null,
    val createdDate: OffsetDateTime,
    var modifiedDate: OffsetDateTime,
)
```

**비즈니스 로직**:
```kotlin
fun enable()
fun disable()
fun updateChannels(channelIdentifiers: List<NotificationChannelId>)
fun softDelete()
```

**불변 조건 (Invariants)**:
- `(userIdentifier, eventType)` 조합은 unique (삭제된 레코드 제외)
- `channelIdentifiers`의 각 채널은 동일 `userIdentifier` 소유여야 함

---

## 3. Entity

### 3.1 NotificationLog (발송 이력)

```kotlin
class NotificationLog(
    val identifier: NotificationLogId,
    val userIdentifier: UserId,
    val channelIdentifier: NotificationChannelId,
    val eventType: String,
    val eventPayload: String,                   // 원본 커맨드 JSON
    val message: String,                        // 실제 발송된 메시지 내용
    var status: NotificationStatus,             // SENT / FAILED
    var failureReason: String?,
    var retryCount: Int = 0,                    // 발송 시도 횟수 (성공=0, 실패=3)
    val createdAt: OffsetDateTime,
    var sentAt: OffsetDateTime?,
)
```

### 3.2 NotificationTemplate (메시지 템플릿)

**목적**: 이벤트 타입별 메시지 형식을 DB에서 관리한다. 코드 변경 없이 템플릿 수정 가능.

```kotlin
class NotificationTemplate(
    val identifier: NotificationTemplateId,
    val eventType: String,                  // 이벤트 타입 (String)
    val channelType: ChannelType,           // 채널 타입별 다른 템플릿 가능
    var titleTemplate: String,              // 제목 템플릿 (변수: ${변수명})
    var bodyTemplate: String,               // 본문 템플릿 (변수: ${변수명})
    var isActive: Boolean = true,
    val createdDate: OffsetDateTime,
    var modifiedDate: OffsetDateTime,
)
```

**템플릿 예시:**
```
eventType: "VIRTUAL_ORDER_FILLED"
channelType: DISCORD
titleTemplate: "[가상거래] 주문 체결"
bodyTemplate:  "${symbol} ${side} ${quantity}개 @ ${price}원"
```

---

## 4. Value Object

### 4.1 NotificationChannelId
```kotlin
@JvmInline
value class NotificationChannelId(val value: UUID) {
    companion object {
        fun of(value: UUID) = NotificationChannelId(value)
        fun generate() = NotificationChannelId(UUID.randomUUID())
    }
}
```

### 4.2 NotificationPreferenceId
```kotlin
@JvmInline
value class NotificationPreferenceId(val value: UUID) {
    companion object {
        fun of(value: UUID) = NotificationPreferenceId(value)
        fun generate() = NotificationPreferenceId(UUID.randomUUID())
    }
}
```

### 4.3 NotificationLogId
```kotlin
@JvmInline
value class NotificationLogId(val value: UUID) {
    companion object {
        fun of(value: UUID) = NotificationLogId(value)
        fun generate() = NotificationLogId(UUID.randomUUID())
    }
}
```

### 4.4 NotificationTemplateId
```kotlin
@JvmInline
value class NotificationTemplateId(val value: UUID) {
    companion object {
        fun of(value: UUID) = NotificationTemplateId(value)
        fun generate() = NotificationTemplateId(UUID.randomUUID())
    }
}
```

---

## 5. Enum

### 5.1 ChannelType (채널 타입)
```kotlin
enum class ChannelType {
    DISCORD,    // Discord Incoming Webhook
    // 향후 추가: APP_PUSH, TELEGRAM 등
}
```

### 5.2 NotificationStatus (발송 상태)
```kotlin
enum class NotificationStatus {
    SENT,   // 발송 성공
    FAILED, // 발송 실패 (3회 재시도 후)
}
```

> **이벤트 타입은 enum이 아닌 String으로 관리한다.**
> Notification Service가 다른 도메인의 이벤트 타입 enum을 알 필요가 없도록 의존성을 역전한다.
> 각 서비스는 자유롭게 이벤트 타입 문자열을 정의하고 `SendNotificationCommand`에 포함한다.
