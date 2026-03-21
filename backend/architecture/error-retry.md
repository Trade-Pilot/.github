# Trade Pilot — 재시도/에러 처리, Circuit Breaker

> 이 문서는 `backend/architecture.md`에서 분할되었습니다.

---

## 8. 재시도 및 에러 처리 전략

### 8.1 재시도 정책

**Kafka Consumer**:
```yaml
재시도 횟수: 3회
백오프: 지수 백오프 (1s, 2s, 4s)
DLQ: 3회 실패 시 Dead Letter Queue로 이동
```

**DLQ (Dead Letter Queue) 정책**:

```yaml
토픽 네이밍: dlq.{원본토픽명}
  예시:
    dlq.command.agent.trade.analyze-strategy
    dlq.event.trade.execution
    dlq.event.virtual-trade.execution

보관 기간: 7일 (retention.ms = 604800000)
파티션 수: 원본 토픽과 동일
```

```kotlin
// 각 서비스의 DLQ Consumer 구현 패턴
@KafkaListener(topicPattern = "dlq\\..*", groupId = "{service-name}-dlq-consumer")
fun handleDLQ(record: ConsumerRecord<String, String>) {
    logger.error("DLQ 메시지 수신: topic=${record.topic()}, key=${record.key()}")
    // 1. 관리자 알림 발송 (NOTIFICATION_COMMAND_TOPIC)
    // 2. DLQ 메트릭 증가
    // 3. DB에 DLQ 레코드 저장 (수동 분석용, 선택적)
}
```

**gRPC Client**:
```yaml
재시도 횟수: 3회 (GET 계열), 0회 (POST/PUT)
타임아웃: 5초 (조회), 30초 (대용량 조회)
재시도 가능 코드: UNAVAILABLE, DEADLINE_EXCEEDED
```

**HTTP 외부 API** (거래소 등):
```yaml
재시도 횟수: 2회
타임아웃: 10초
재시도 간격: 1초
```

**스케줄러 작업**:
```yaml
Market Candle 수집:
  자동 재시도: 3회 (retryCount < MAX_RETRY_COUNT)
  재시도 간격: 다음 스케줄 사이클 (1분)
  3회 초과 시: PAUSED 상태, 수동 복구 필요
```

### 8.2 Circuit Breaker

**적용 대상**:
- Exchange Service → 거래소 API
- 모든 gRPC 클라이언트

**설정** (Resilience4j):
```yaml
failureRateThreshold: 50%        # 실패율 50% 초과 시 Open
slowCallRateThreshold: 50%       # 느린 호출 50% 초과 시 Open
slowCallDurationThreshold: 5s    # 5초 이상이면 느린 호출
waitDurationInOpenState: 60s     # Open 상태 유지 시간
permittedNumberOfCallsInHalfOpenState: 10
```

### 8.3 에러 코드 체계

**형식**: `{서비스코드}{일련번호}`

```
User Service:         U001~U999
Exchange Service:     EX001~EX999
Market Service:       MS001~MS999
Agent Service:        A001~A999
Simulation Service:   S001~S999
VirtualTrade Service: VT001~VT999
Trade Service:        T001~T999
Notification Service: N001~N999
```

**HTTP 상태 코드 매핑**:
```
도메인 에러 타입     → HTTP 상태
NOT_FOUND          → 404
INVALID_STATE      → 409 Conflict
VALIDATION_ERROR   → 400 Bad Request
UNAUTHORIZED       → 401
FORBIDDEN          → 403
RATE_LIMIT_EXCEEDED → 429
INTERNAL_ERROR     → 500
```
