# Notification Service - 시퀀스 다이어그램

> Notification Service의 주요 시나리오별 상호작용 흐름

---

## 1. Kafka 이벤트 소비 및 발송 (메인 플로우)

### 1.1 정상 발송

```mermaid
sequenceDiagram
    participant Kafka as Kafka
    participant Listener as NotificationEventListener
    participant Dispatcher as NotificationDispatcher
    participant DB as Database
    participant Discord as Discord Webhook

    Kafka-->>Listener: NOTIFICATION_COMMAND_TOPIC
    Note over Kafka: userId, eventType=VIRTUAL_ORDER_FILLED, variables

    activate Listener
    Listener->>Dispatcher: dispatch(userId, VIRTUAL_ORDER_FILLED, variables)

    activate Dispatcher
    Dispatcher->>DB: SELECT preference
    Note over DB: WHERE user_id=? AND event_type=VIRTUAL_ORDER_FILLED AND is_enabled=true AND is_deleted=false

    alt Preference 없음 (opt-in 안 함)
        Dispatcher-->>Listener: 발송 스킵 (로그 없음)
    else Preference 있음
        Dispatcher->>DB: SELECT channel
        Note over DB: WHERE identifier IN (channelIds) AND is_active=true AND is_deleted=false

        Dispatcher->>DB: SELECT template
        Note over DB: WHERE event_type=VIRTUAL_ORDER_FILLED AND channel_type=DISCORD AND is_active=true

        Dispatcher->>Dispatcher: render(template, variables)
        Note over Dispatcher: title = "[가상거래] 주문 체결" 변수 치환

        loop 활성 채널별
            Dispatcher->>Discord: POST webhook (title + body)
            alt 발송 성공
                Discord-->>Dispatcher: 200 OK
                Dispatcher->>DB: INSERT notification_log (SENT, retryCount=0)
            else 발송 실패
                Note over Dispatcher: 상세 흐름은 Section 1.2 참조
            end
        end
    end
    deactivate Dispatcher
    deactivate Listener
```

### 1.2 발송 실패 재시도

```mermaid
sequenceDiagram
    participant Dispatcher as NotificationDispatcher
    participant Discord as Discord Webhook
    participant DB as Database

    Note over Dispatcher: 채널 발송 시도 (최대 3회, 1초 간격)

    Dispatcher->>Discord: Attempt 1
    Discord-->>Dispatcher: 503 Service Unavailable

    Note over Dispatcher: 1초 대기
    Dispatcher->>Discord: Attempt 2
    Discord-->>Dispatcher: 503 Service Unavailable

    Note over Dispatcher: 1초 대기
    Dispatcher->>Discord: Attempt 3
    Discord-->>Dispatcher: 503 Service Unavailable

    Note over Dispatcher: 3회 모두 실패
    Dispatcher->>DB: INSERT notification_log
    Note over DB: status=FAILED, failure_reason=503 after 3 retries, retry_count=3
```

> 발송 실패는 Kafka 메시지를 재큐잉하지 않는다. Notification은 종착점이므로
> 재시도는 인라인(동기)으로 처리하고 결과를 `notification_log`에 기록한다.

---

## 2. Market 오류 알림

Market Service에서 수집 오류 또는 파티션 실패 발생 시 `NOTIFICATION_COMMAND_TOPIC`에 발행한다.
Market 오류는 시스템 관리자(`ADMIN_USER_ID`)에게 발송한다.

```mermaid
sequenceDiagram
    participant Market as Market Service
    participant Kafka as Kafka
    participant Listener as NotificationEventListener
    participant Dispatcher as NotificationDispatcher
    participant DB as Database
    participant Discord as Discord Webhook

    Note over Market: retryCount >= MAX_RETRY_COUNT (3)
    Market->>Kafka: NOTIFICATION_COMMAND_TOPIC
    Note over Kafka: userId=ADMIN_USER_ID, eventType=MARKET_COLLECT_ERROR, variables

    Kafka-->>Listener: Consume
    Listener->>Dispatcher: dispatch(ADMIN_USER_ID, MARKET_COLLECT_ERROR, variables)

    Dispatcher->>DB: SELECT preference (ADMIN + MARKET_COLLECT_ERROR)
    Dispatcher->>DB: SELECT channel (ADMIN 활성 채널)
    Dispatcher->>DB: SELECT template (MARKET_COLLECT_ERROR + DISCORD)

    Dispatcher->>Dispatcher: render(template, variables)
    Note over Dispatcher: body = "KRW-BTC 수집 오류 — retryCount=3, errorMessage=..."

    Dispatcher->>Discord: POST webhook
    Discord-->>Dispatcher: 200 OK
    Dispatcher->>DB: INSERT notification_log (SENT)
```

---

## 3. 회원 탈퇴 이벤트 처리

```mermaid
sequenceDiagram
    participant Kafka as Kafka
    participant Listener as NotificationEventListener
    participant Handler as UserWithdrawnEventHandler
    participant DB as Database

    Kafka-->>Listener: USER_WITHDRAWN_EVENT_TOPIC
    Note over Kafka: userId, withdrawnAt

    activate Listener
    Listener->>Handler: handle(UserWithdrawnEvent)
    Note over Listener: consumeUserEvents()에서 위임 (Section 8 참조)

    activate Handler
    Handler->>DB: UPDATE notification_preference SET is_deleted=true, deleted_at=NOW()
    Note over DB: WHERE user_identifier = userId
    Handler->>DB: UPDATE notification_channel SET is_deleted=true, deleted_at=NOW()
    Note over DB: WHERE user_identifier = userId
    Note over Handler: NotificationLog는 감사 목적으로 영구 보존

    deactivate Handler
    deactivate Listener
```

---

## 4. 채널 등록 플로우

```mermaid
sequenceDiagram
    participant Client
    participant GW as API Gateway
    participant NS as NotificationChannelCommandService
    participant DB as Database

    Client->>GW: POST /notification-channels
    Note over Client: Body: type=DISCORD, webhookUrl=https://discord.com/api/webhooks/...
    Note over GW: JWT 검증 → X-User-Id 헤더

    GW->>NS: CreateChannelCommand(userId, DISCORD, DiscordConfig)

    activate NS
    NS->>NS: webhookUrl 형식 검증
    Note over NS: https://discord.com/api/webhooks/ 로 시작하는지 확인

    NS->>DB: BEGIN TRANSACTION
    NS->>NS: NotificationChannelFactory.create(userId, DISCORD, DiscordConfig)
    NS->>DB: INSERT notification_channel
    NS->>DB: COMMIT

    NS-->>GW: 201 Created (channelId)
    GW-->>Client: 201 Created
    deactivate NS
```

---

## 5. 수신 설정 변경 플로우

### 5.1 이벤트 타입별 설정 조회

```mermaid
sequenceDiagram
    participant Client
    participant GW as API Gateway
    participant NS as NotificationPreferenceQueryService
    participant DB as Database

    Client->>GW: GET /notification-preferences
    Note over GW: X-User-Id 헤더

    GW->>NS: GetPreferencesQuery(userId)
    NS->>DB: SELECT preference WHERE user_id=? AND is_deleted=false

    Note over NS: DB에 없는 eventType은 기본값(isEnabled=false, channels=[])으로 응답
    Note over NS: 등록된 템플릿 기반으로 전체 eventType 목록 구성

    NS-->>GW: List(NotificationPreferenceResponse)
    GW-->>Client: 200 OK
```

### 5.2 수신 설정 변경 (opt-in / opt-out)

```mermaid
sequenceDiagram
    participant Client
    participant GW as API Gateway
    participant NS as NotificationPreferenceCommandService
    participant DB as Database

    Client->>GW: PUT /notification-preferences/VIRTUAL_ORDER_FILLED
    Note over Client: Body: isEnabled=true, channelIds=[uuid1, uuid2]
    Note over GW: X-User-Id 헤더

    GW->>NS: UpdatePreferenceCommand(userId, VIRTUAL_ORDER_FILLED, isEnabled, channelIds)

    activate NS
    NS->>DB: SELECT channel WHERE identifier IN (channelIds) AND user_id=userId
    Note over NS: 본인 소유 채널인지 + is_deleted=false 검증

    alt 타인 채널 또는 삭제된 채널 포함
        NS-->>GW: 403 CHANNEL_NOT_OWNED
        GW-->>Client: 403 Forbidden
    else 검증 통과
        NS->>DB: SELECT preference (getOrCreate, is_deleted=false)

        NS->>DB: BEGIN TRANSACTION
        NS->>NS: preference.updateChannels(channelIds)
        NS->>NS: if isEnabled then enable() else disable()
        NS->>DB: UPSERT notification_preference
        NS->>DB: COMMIT

        NS-->>GW: 200 OK
        GW-->>Client: 200 OK
    end
    deactivate NS
```

---

## 6. 발송 이력 조회

```mermaid
sequenceDiagram
    participant Client
    participant GW as API Gateway
    participant NS as NotificationLogQueryService
    participant DB as Database

    Client->>GW: GET /notification-logs?from=2024-01-01&to=2024-01-31&page=0&size=20
    Note over GW: X-User-Id 헤더

    GW->>NS: GetLogsQuery(userId, from, to, pageable)
    NS->>DB: SELECT notification_log
    Note over DB: WHERE user_id=? AND created_at BETWEEN ? AND ?
    Note over DB: ORDER BY created_at DESC LIMIT 20 OFFSET 0

    NS-->>GW: Page(NotificationLogResponse)
    GW-->>Client: 200 OK
```

---

## 7. 템플릿 관리 (ADMIN)

```mermaid
sequenceDiagram
    participant Admin
    participant GW as API Gateway
    participant NS as NotificationTemplateCommandService
    participant DB as Database

    Admin->>GW: PUT /notification-templates/{templateId}
    Note over Admin: Body: titleTemplate, bodyTemplate
    Note over GW: X-User-Role = ADMIN 검증

    GW->>NS: UpdateTemplateCommand(templateId, titleTemplate, bodyTemplate)
    NS->>DB: UPDATE notification_template
    NS-->>GW: 200 OK
    GW-->>Admin: 200 OK
```

> 코드 배포 없이 메시지 형식을 수정할 수 있다.
> 새 이벤트 타입 추가 시: DB에 템플릿 레코드 INSERT만 하면 된다.

---

## 8. 트랜잭션 범위

| 작업 | 트랜잭션 범위 | 외부 I/O |
|------|--------------|----------|
| 채널 등록 | INSERT channel | 없음 |
| 수신 설정 변경 | UPSERT preference | 없음 |
| 이벤트 발송 | INSERT notification_log | Discord Webhook (트랜잭션 외부) |
| 회원 탈퇴 처리 | UPDATE preference(soft) + UPDATE channel(soft) | 없음 |
| 템플릿 수정 | UPDATE template | 없음 |

> 발송(Discord) 후 DB 기록 실패 시: 발송은 됐지만 로그가 없는 상태가 된다.
> 이는 허용 가능한 불일치다 (반대 방향보다 덜 위험).

---

## 9. Kafka Consumer 설정

```kotlin
// 단일 NOTIFICATION_COMMAND_TOPIC에서 모든 알림 커맨드 소비
@KafkaListener(
    topics = [NOTIFICATION_COMMAND_TOPIC],
    groupId = "notification-command-consumer",
    concurrency = 5,   // userId 파티션 키 → 동일 사용자 순서 보장
)
fun consumeNotificationCommands(record: ConsumerRecord<String, String>) {
    val command = objectMapper.readValue(record.value(), SendNotificationCommand::class.java)
    notificationDispatcher.dispatch(command.userId, command.eventType, command.variables)
}

// 회원 탈퇴 이벤트 (도메인 이벤트, 별도 그룹)
@KafkaListener(
    topics = [USER_WITHDRAWN_EVENT_TOPIC],
    groupId = "notification-user-consumer",
    concurrency = 3,
)
fun consumeUserEvents(record: ConsumerRecord<String, String>) {
    val event = objectMapper.readValue(record.value(), UserWithdrawnEvent::class.java)
    userWithdrawnEventHandler.handle(event)
}
```

> 파티션 키 = `userId`이므로 동일 사용자의 이벤트는 순서가 보장되며 동시에 처리되지 않는다.

---

## 참고

- **발송 채널**: Discord Webhook (향후 앱 푸시 등으로 확장)
- **발송 재시도**: 인라인 3회 (1초 간격), Outbox 패턴 미적용
- **이벤트 타입**: String 기반, Notification Service에 enum 없음
- **메시지 템플릿**: DB 관리, ADMIN API로 수정 가능
- **opt-in 정책**: Preference 레코드가 없으면 발송 스킵
- **Market 오류**: ADMIN 역할 사용자에게만 발송
- **회원 탈퇴**: channel + preference 소프트 딜리트, log는 영구 보존
