# Trade Pilot — 옵저빌리티 (Health, Metrics, Tracing, Logging, 알람)

> 이 문서는 `backend/architecture.md`에서 분할되었습니다.

---

## 7. 옵저빌리티 (Observability)

### 7.1 Health Check

모든 서비스는 다음 엔드포인트 제공:

```
GET /actuator/health
GET /actuator/health/liveness
GET /actuator/health/readiness
```

**Custom Health Indicators**:
- Database 연결
- Kafka 연결
- Redis 연결
- 외부 의존 서비스 (gRPC)

### 7.2 Metrics (Prometheus)

**필수 메트릭**:
```
# HTTP 요청
http_server_requests_seconds_count{uri, method, status}
http_server_requests_seconds_sum

# Kafka Consumer
kafka_consumer_records_consumed_total{topic}
kafka_consumer_lag{topic, partition}

# gRPC
grpc_server_handled_total{service, method, code}
grpc_server_handling_seconds

# 비즈니스 메트릭 (서비스별)
agent_signal_generated_total{signal_type}
market_candle_collected_total{symbol, interval}
trade_order_submitted_total{side, type, status}
```

### 7.3 Distributed Tracing

**구현**: OpenTelemetry + Jaeger/Tempo

**Trace ID 전파**:
```
HTTP → X-Trace-Id 헤더
Kafka → KafkaEnvelope.traceId
gRPC → grpc-trace-bin 메타데이터
```

**Span 분류**:
- HTTP: `http.method`, `http.url`, `http.status_code`
- Kafka: `messaging.system=kafka`, `messaging.destination=topic`
- gRPC: `rpc.system=grpc`, `rpc.service`, `rpc.method`
- DB: `db.system=postgresql`, `db.statement`

### 7.4 Logging

**로그 레벨 기준**:
```
ERROR: 시스템 장애, 데이터 손실 가능성
WARN:  복구 가능한 오류, Rate Limit 초과
INFO:  비즈니스 이벤트 (주문 체결, 신호 생성)
DEBUG: 디버깅 정보 (프로덕션에서 비활성화)
```

**Structured Logging** (JSON):
```json
{
  "timestamp": "2024-01-01T12:00:00Z",
  "level": "INFO",
  "traceIdentifier": "abc123",
  "service": "agent-service",
  "message": "Signal generated",
  "userIdentifier": "uuid",
  "agentIdentifier": "uuid",
  "signalType": "BUY"
}
```

### 7.5 알람 정책

**Severity 분류**:

**P0 (Critical - 즉시 대응)**:
- 서비스 Health Check 실패 (5분 이상)
- DB 연결 끊김
- DLQ 메시지 발생 (어떤 서비스든)
- Kafka Consumer Lag 서비스별 임계값 초과:

| 서비스 | P0 Lag | P1 Lag | 근거 |
|--------|--------|--------|------|
| Trade Service | > 5,000 | > 1,000 | 실거래 지연은 직접적 손실 |
| Agent Service | > 3,000 | > 500 | 신호 생성 지연 → 체결 타이밍 이탈 |
| VirtualTrade Service | > 5,000 | > 1,000 | 가상거래 지연은 학습 데이터 왜곡 |
| Exchange Service | > 3,000 | > 500 | 주문 제출 지연 → 가격 이탈 |
| Market Service | > 10,000 | > 3,000 | 수집 지연은 허용 범위 넓음 |
| Notification Service | > 30,000 | > 10,000 | 알림 지연은 심각도 낮음 |

**P1 (High - 30분 내 대응)**:
- API 에러율 > 5%
- 주문 제출 실패율 > 10%
- 캔들 수집 실패 연속 3회 이상
- 미체결 LIMIT 주문 3개 이상 && 각 1시간 이상 대기

**P2 (Medium - 업무시간 내 대응)**:
- 디스크 사용률 > 80%
- Memory 사용률 > 85%
- Portfolio Reconciliation 불일치
- Account Reconciliation 불일치
