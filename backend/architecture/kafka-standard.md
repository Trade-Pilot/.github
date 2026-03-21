# Trade Pilot — Kafka 토픽 명명/메시지 표준

> 이 문서는 `backend/architecture.md`에서 분할되었습니다.

---

## 6. Kafka 토픽 명명 규칙 및 메시지 표준

### 6.1 토픽 명명 규칙

**패턴**:

| 메시지 타입 | 패턴 | 설명 |
|------------|------|------|
| `command` | `command.{수신자}.{발신자}.{액션}` | 요청 전달 — 수신자가 처리 |
| `reply` | `reply.{수신자}.{발신자}.{액션}` | 응답 전달 — command의 발신자가 수신 |
| `reply-failure` | `reply-failure.{수신자}.{발신자}.{액션}` | 실패 응답 |
| `event` | `event.{발행자}.{액션}` | 단방향 이벤트 (발행 후 잊기) |

> **핵심**: `command`의 발신자가 `reply`의 수신자가 된다.
> 예: VirtualTrade → Agent로 command 발행 시, reply는 Agent → VirtualTrade로 돌아온다.

**예시**:
```
# Command: VirtualTrade(발신) → Agent(수신)
command.agent.virtual-trade.analyze-strategy

# Reply: Agent(발신) → VirtualTrade(수신) — command의 발신/수신이 뒤바뀜
reply.virtual-trade.agent.analyze-strategy

# Event: 발행자만 명시
event.virtual-trade.execution
event.agent.agent-terminated

# Exchange Service
command.exchange.market.find-all-symbol       # Market(발신) → Exchange(수신)
reply.market.exchange.find-all-symbol         # Exchange(발신) → Market(수신)
command.exchange.trade.submit-order           # Trade(발신) → Exchange(수신)
command.exchange.trade.cancel-order

# 도메인 이벤트 (CDC 스타일)
trade-pilot.agentservice.agent       (eventType: agent-terminated)
trade-pilot.userservice.user         (eventType: user-withdrawn)
```

**전역 토픽**:
```
trade-pilot.notification.command     (NOTIFICATION_COMMAND_TOPIC)
```

### 6.2 메시지 Envelope

모든 Kafka 메시지는 공통 Envelope로 래핑:

```kotlin
data class KafkaEnvelope<T>(
    val messageIdentifier: UUID,      // 메시지 고유 ID (멱등성 보장)
    val timestamp: OffsetDateTime,
    val traceIdentifier: String,      // 분산 추적용
    val callback: String?,            // Reply 토픽 (Command 전용)
    val payload: T,                   // 실제 메시지
)
```

### 6.3 Command/Reply 패턴

```kotlin
// Command 발행 시 callback 지정
KafkaEnvelope(
    messageIdentifier = UUID.randomUUID(),
    timestamp = now,
    traceIdentifier = currentTraceId,
    callback = "reply.agent.virtual-trade.analyze-strategy",
    payload = AnalyzeAgentCommand(...)
)

// Consumer는 callback 토픽으로 Reply 발행
kafkaTemplate.send(envelope.callback!!, reply)
```

### 6.4 멱등성 보장

모든 Consumer는 `processed_events` 테이블로 중복 처리 방지:

```sql
CREATE TABLE processed_events (
    topic       VARCHAR(255) NOT NULL,
    partition   INT          NOT NULL,
    offset      BIGINT       NOT NULL,
    consumed_at TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    PRIMARY KEY (topic, partition, offset)
);
```

```kotlin
@Transactional
fun consume(record: ConsumerRecord<String, KafkaEnvelope<T>>) {
    val key = ProcessedEventKey(record.topic(), record.partition(), record.offset())

    if (processedEventRepository.existsById(key)) {
        log.debug("Already processed: $key")
        return
    }

    // 비즈니스 로직 처리
    handleMessage(record.value().payload)

    // 처리 완료 기록
    processedEventRepository.save(ProcessedEvent(key, now()))
}
```
