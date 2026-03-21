# Notification Service — Use Case, API, DB 스키마, 예외, 도메인 관계

> 이 문서는 `backend/notification/domain.md`에서 분할되었습니다.

---

## 10. Use Case

```kotlin
// 채널 관리
interface CreateNotificationChannelUseCase {
    fun create(userIdentifier: UserId, command: CreateChannelCommand): NotificationChannelId
}

interface UpdateNotificationChannelUseCase {
    fun activate(channelIdentifier: NotificationChannelId, userIdentifier: UserId)
    fun deactivate(channelIdentifier: NotificationChannelId, userIdentifier: UserId)
    fun updateConfig(channelIdentifier: NotificationChannelId, userIdentifier: UserId, config: ChannelConfig)
}

interface DeleteNotificationChannelUseCase {
    fun delete(channelIdentifier: NotificationChannelId, userIdentifier: UserId)   // 소프트 딜리트
}

interface GetNotificationChannelUseCase {
    fun getChannels(userIdentifier: UserId): List<NotificationChannel>
}

// 수신 설정 관리
interface UpdateNotificationPreferenceUseCase {
    fun updatePreference(
        userIdentifier: UserId,
        eventType: String,
        command: UpdatePreferenceCommand,
    )
}

interface GetNotificationPreferenceUseCase {
    fun getPreferences(userIdentifier: UserId): List<NotificationPreferenceResponse>
}

// 발송 이력
interface GetNotificationLogUseCase {
    fun getLogs(userIdentifier: UserId, pageable: Pageable): Page<NotificationLog>
}

// 템플릿 관리 (ADMIN)
interface ManageNotificationTemplateUseCase {
    fun createTemplate(command: CreateTemplateCommand): NotificationTemplateId
    fun updateTemplate(templateIdentifier: NotificationTemplateId, command: UpdateTemplateCommand)
    fun getTemplates(): List<NotificationTemplate>
}
```

---

## 11. API 엔드포인트

```http
# 채널 관리
POST /notification-channels
→ 채널 등록 (Discord)

GET /notification-channels
→ 내 채널 목록 조회 (isDeleted=false 필터)

PUT /notification-channels/{channelIdentifier}/activate
PUT /notification-channels/{channelIdentifier}/deactivate

DELETE /notification-channels/{channelIdentifier}
→ 채널 소프트 딜리트

# 수신 설정
GET /notification-preferences
→ 등록된 수신 설정 목록 조회 (없으면 isEnabled=false 기본값 포함)

PUT /notification-preferences/{eventType}
→ 특정 이벤트 수신 설정 변경
   Body: { isEnabled: true, channelIds: [uuid, uuid] }

# 발송 이력
GET /notification-logs?from=2024-01-01&to=2024-12-31
→ 발송 이력 조회 (페이징)

# 템플릿 관리 (ADMIN)
GET  /notification-templates
POST /notification-templates
PUT  /notification-templates/{templateIdentifier}
```

---

## 12. 데이터베이스 스키마

### notification_channel 테이블
```sql
CREATE TABLE notification_channel (
    identifier      UUID    PRIMARY KEY,
    user_identifier UUID    NOT NULL,
    type            VARCHAR NOT NULL,        -- DISCORD
    config          JSONB   NOT NULL,        -- ChannelConfig JSON
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    is_deleted      BOOLEAN NOT NULL DEFAULT FALSE,
    deleted_at      TIMESTAMP WITH TIME ZONE,
    created_date    TIMESTAMP WITH TIME ZONE NOT NULL,
    modified_date   TIMESTAMP WITH TIME ZONE NOT NULL
);

CREATE INDEX notification_channel_user_idx ON notification_channel (user_identifier)
    WHERE is_deleted = FALSE;
```

**config 컬럼 예시**:
```json
{ "webhookUrl": "https://discord.com/api/webhooks/..." }
```

### notification_preference 테이블
```sql
CREATE TABLE notification_preference (
    identifier          UUID    PRIMARY KEY,
    user_identifier     UUID    NOT NULL,
    event_type          VARCHAR NOT NULL,        -- String 이벤트 타입
    channel_identifiers UUID[]  NOT NULL,
    is_enabled          BOOLEAN NOT NULL DEFAULT FALSE,
    is_deleted          BOOLEAN NOT NULL DEFAULT FALSE,
    deleted_at          TIMESTAMP WITH TIME ZONE,
    created_date        TIMESTAMP WITH TIME ZONE NOT NULL,
    modified_date       TIMESTAMP WITH TIME ZONE NOT NULL,

    UNIQUE (user_identifier, event_type)         -- 삭제된 레코드 포함 unique 제약
);

CREATE INDEX notification_preference_user_idx ON notification_preference (user_identifier)
    WHERE is_deleted = FALSE;
```

### notification_log 테이블
```sql
CREATE TABLE notification_log (
    identifier          UUID    PRIMARY KEY,
    user_identifier     UUID    NOT NULL,
    channel_identifier  UUID    NOT NULL,
    event_type          VARCHAR NOT NULL,
    event_payload       TEXT    NOT NULL,
    message             TEXT    NOT NULL,
    status              VARCHAR NOT NULL,    -- SENT, FAILED
    failure_reason      TEXT,
    retry_count         INT     NOT NULL DEFAULT 0,
    created_at          TIMESTAMP WITH TIME ZONE NOT NULL,
    sent_at             TIMESTAMP WITH TIME ZONE
);

CREATE INDEX notification_log_user_idx   ON notification_log (user_identifier);
CREATE INDEX notification_log_time_idx   ON notification_log (created_at);
CREATE INDEX notification_log_failed_idx ON notification_log (created_at)
    WHERE status = 'FAILED';
```

### notification_template 테이블
```sql
CREATE TABLE notification_template (
    identifier      UUID    PRIMARY KEY,
    event_type      VARCHAR NOT NULL,
    channel_type    VARCHAR NOT NULL,       -- DISCORD
    title_template  VARCHAR NOT NULL,
    body_template   TEXT    NOT NULL,
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    created_date    TIMESTAMP WITH TIME ZONE NOT NULL,
    modified_date   TIMESTAMP WITH TIME ZONE NOT NULL,

    UNIQUE (event_type, channel_type)       -- 이벤트 타입 + 채널 타입 조합 unique
);

CREATE INDEX notification_template_event_idx ON notification_template (event_type, channel_type)
    WHERE is_active = TRUE;
```

### processed_events 테이블

```sql
CREATE TABLE processed_events (
    topic       VARCHAR(255) NOT NULL,
    partition   INT          NOT NULL,
    offset      BIGINT       NOT NULL,
    consumed_at TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    PRIMARY KEY (topic, partition, offset)
);
```

> `processed_events` 테이블은 Kafka Consumer의 멱등성 보장을 위해 사용된다.
> 동일 이벤트의 중복 소비를 방지하기 위해 처리된 (topic, partition, offset) 조합을 기록한다.

---

## 13. 예외

```kotlin
enum class NotificationErrorCode(
    override val code: String,
    override val message: String,
) : ErrorCode {
    CHANNEL_NOT_FOUND("N001", "Notification channel not found"),
    CHANNEL_NOT_OWNED("N002", "Notification channel not owned by user"),
    CHANNEL_ALREADY_INACTIVE("N003", "Channel is already inactive"),
    PREFERENCE_NOT_FOUND("N004", "Notification preference not found"),
    DISPATCH_FAILED("N005", "Notification dispatch failed"),
    TEMPLATE_NOT_FOUND("N006", "Notification template not found"),
}
```

---

## 14. 도메인 관계

```
User (UserId 참조)
  │
  ├─< (N) NotificationChannel       (채널 설정, 소프트 딜리트)
  │
  ├─< (N) NotificationPreference    (이벤트별 수신 설정, 소프트 딜리트)
  │          └── channelIdentifiers → NotificationChannel 참조
  │
  └─< (N) NotificationLog           (발송 이력, 영구 보존)

NotificationTemplate                 (eventType + channelType → 템플릿)
```

**생명주기**:
1. 사용자가 `NotificationChannel` 등록 (Discord Webhook URL)
2. `NotificationPreference`에서 원하는 이벤트 + 채널 연결 (opt-in)
3. 다른 서비스가 `NOTIFICATION_COMMAND_TOPIC`에 `SendNotificationCommand` 발행
4. `NotificationDispatcher`가 채널 설정 + 템플릿 조회 후 발송
5. `NotificationLog`에 결과 기록
6. 회원 탈퇴 시 Channel + Preference 소프트 딜리트, Log는 영구 보존
