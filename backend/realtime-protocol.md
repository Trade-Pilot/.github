# Trade Pilot - 실시간 프로토콜 명세

> WebSocket 및 SSE(Server-Sent Events) 기반 실시간 데이터 전달 프로토콜 정의

---

## 1. WebSocket 프로토콜

### 1.1 연결 엔드포인트

API Gateway가 단일 WebSocket 진입점을 제공한다. 프론트엔드는 이 하나의 커넥션으로 모든 실시간 데이터를 수신한다.

```
wss://api.trade-pilot.com/ws?token={JWT_ACCESS_TOKEN}
```

**인증**: 연결 시 `token` 쿼리 파라미터로 JWT Bearer 토큰을 전달한다. 토큰이 유효하지 않거나 만료된 경우 연결을 거부한다 (HTTP 401).

```
GET /ws?token=eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...
Connection: Upgrade
Upgrade: websocket
Sec-WebSocket-Version: 13
```

### 1.2 메시지 포맷

모든 메시지는 JSON 형식이다.

#### 클라이언트 → 서버 (요청)

```json
{
  "action": "subscribe | unsubscribe",
  "channel": "채널명",
  "requestId": "클라이언트 측 요청 추적 ID (선택)"
}
```

#### 서버 → 클라이언트 (응답)

**구독/해제 확인**:
```json
{
  "type": "ack",
  "action": "subscribe | unsubscribe",
  "channel": "구독한 채널명",
  "requestId": "요청 시 전달한 ID",
  "timestamp": "2024-01-01T12:00:00Z"
}
```

**데이터 메시지**:
```json
{
  "type": "data",
  "channel": "데이터가 속한 채널명",
  "data": { ... },
  "timestamp": "2024-01-01T12:00:00Z"
}
```

### 1.3 구독 가능 채널

| 채널 패턴 | 설명 | 데이터 소스 |
|-----------|------|------------|
| `candle:{symbolIdentifier}:{interval}` | 실시간 캔들 업데이트 | Market Service |
| `portfolio:{agentIdentifier}` | 포트폴리오 변동 (포지션/현금 변경) | Agent Service |
| `signal:{agentIdentifier}` | 전략 신호 생성 알림 | Agent Service |
| `order:{registrationIdentifier}` | 주문 상태 변경 | Trade / VirtualTrade Service |

#### 채널별 데이터 포맷

**`candle:{symbolIdentifier}:{interval}`** — 실시간 캔들 업데이트

```json
{
  "type": "data",
  "channel": "candle:550e8400-e29b-41d4-a716-446655440000:MIN_1",
  "data": {
    "symbolIdentifier": "550e8400-e29b-41d4-a716-446655440000",
    "interval": "MIN_1",
    "time": "2024-01-01T12:00:00Z",
    "open": "50000000",
    "high": "50100000",
    "low": "49900000",
    "close": "50050000",
    "volume": "1.5",
    "amount": "75000000"
  },
  "timestamp": "2024-01-01T12:01:00Z"
}
```

**`portfolio:{agentIdentifier}`** — 포트폴리오 변동

```json
{
  "type": "data",
  "channel": "portfolio:660e8400-e29b-41d4-a716-446655440000",
  "data": {
    "agentIdentifier": "660e8400-e29b-41d4-a716-446655440000",
    "cash": "1000000",
    "reservedCash": "500000",
    "totalValue": "2500000",
    "realizedPnl": "50000",
    "positions": [
      {
        "symbolIdentifier": "550e8400-e29b-41d4-a716-446655440000",
        "quantity": "0.03",
        "reservedQuantity": "0.01",
        "averagePrice": "50000000",
        "currentPrice": "50050000",
        "unrealizedPnl": "1500"
      }
    ],
    "changeType": "EXECUTION_CONFIRMED"
  },
  "timestamp": "2024-01-01T12:01:05Z"
}
```

**`signal:{agentIdentifier}`** — 신호 생성 알림

```json
{
  "type": "data",
  "channel": "signal:660e8400-e29b-41d4-a716-446655440000",
  "data": {
    "agentIdentifier": "660e8400-e29b-41d4-a716-446655440000",
    "signalType": "BUY",
    "confidence": 0.85,
    "symbolIdentifier": "550e8400-e29b-41d4-a716-446655440000",
    "suggestedQuantity": "0.05",
    "reason": {
      "ma_cross": "golden_cross",
      "rsi": 35.2
    }
  },
  "timestamp": "2024-01-01T12:01:10Z"
}
```

**`order:{registrationIdentifier}`** — 주문 상태 변경

```json
{
  "type": "data",
  "channel": "order:770e8400-e29b-41d4-a716-446655440000",
  "data": {
    "registrationIdentifier": "770e8400-e29b-41d4-a716-446655440000",
    "orderIdentifier": "880e8400-e29b-41d4-a716-446655440000",
    "status": "FILLED",
    "side": "BUY",
    "executedQuantity": "0.05",
    "executedPrice": "50050000",
    "executedAt": "2024-01-01T12:01:15Z"
  },
  "timestamp": "2024-01-01T12:01:15Z"
}
```

### 1.4 구독/해제 예시

**구독 요청**:
```json
{
  "action": "subscribe",
  "channel": "candle:550e8400-e29b-41d4-a716-446655440000:MIN_1",
  "requestId": "req-001"
}
```

**구독 확인**:
```json
{
  "type": "ack",
  "action": "subscribe",
  "channel": "candle:550e8400-e29b-41d4-a716-446655440000:MIN_1",
  "requestId": "req-001",
  "timestamp": "2024-01-01T12:00:00Z"
}
```

**구독 해제 요청**:
```json
{
  "action": "unsubscribe",
  "channel": "candle:550e8400-e29b-41d4-a716-446655440000:MIN_1",
  "requestId": "req-002"
}
```

### 1.5 Heartbeat

연결 유지를 위해 30초 간격으로 ping/pong을 교환한다.

```
서버 → 클라이언트: WebSocket Ping frame (30초 간격)
클라이언트 → 서버: WebSocket Pong frame (자동 응답)
```

- 서버는 60초(2회 연속 ping 누락) 내 Pong 응답이 없으면 연결을 종료한다.
- 클라이언트는 추가로 애플리케이션 레벨 ping을 보낼 수 있다:

```json
{
  "action": "ping"
}
```

서버 응답:
```json
{
  "type": "pong",
  "timestamp": "2024-01-01T12:00:30Z"
}
```

### 1.6 재연결 전략

클라이언트는 연결 끊김 시 **지수 백오프(Exponential Backoff)** 전략으로 재연결을 시도한다.

| 재시도 횟수 | 대기 시간 | 설명 |
|------------|----------|------|
| 1회차 | 1초 | 즉시 재시도 |
| 2회차 | 2초 | |
| 3회차 | 4초 | |
| 4회차 | 8초 | |
| 5회차 | 16초 | |
| 6회차 이후 | 30초 (최대) | 최대 대기 시간 고정 |

**재연결 시 동작**:
1. 새로운 WebSocket 연결 수립 (`token` 재전달)
2. 이전에 구독했던 모든 채널을 재구독한다
3. JWT 만료로 연결이 거부되면 토큰 갱신 후 재시도한다

**Jitter 적용**: 다수 클라이언트의 동시 재연결을 방지하기 위해 대기 시간에 0~1초의 랜덤 지연을 추가한다.

```
실제 대기 시간 = min(2^(retry - 1), 30) + random(0, 1000)ms
```

### 1.7 에러 메시지

서버는 에러 발생 시 아래 포맷으로 메시지를 전송한다.

```json
{
  "type": "error",
  "code": "에러 코드",
  "message": "사용자 노출용 메시지",
  "requestId": "요청 시 전달한 ID (해당 시)",
  "timestamp": "2024-01-01T12:00:00Z"
}
```

| 에러 코드 | 설명 | 후속 동작 |
|----------|------|----------|
| `INVALID_CHANNEL` | 존재하지 않는 채널 형식 | 클라이언트 재요청 필요 |
| `UNAUTHORIZED` | JWT 만료 또는 무효 | 토큰 갱신 후 재연결 |
| `FORBIDDEN` | 해당 리소스에 대한 접근 권한 없음 | 구독 불가 |
| `RATE_LIMITED` | 구독 요청 빈도 초과 | 잠시 후 재시도 |
| `CHANNEL_NOT_FOUND` | 채널 대상 리소스가 존재하지 않음 (심볼, 에이전트 등) | 채널명 확인 필요 |
| `INTERNAL_ERROR` | 서버 내부 오류 | 자동 재연결 |

### 1.8 연결 제한

| 항목 | 값 |
|------|---|
| 사용자당 최대 동시 연결 수 | 5 |
| 연결당 최대 구독 채널 수 | 50 |
| 메시지 수신 빈도 제한 | 100 msg/sec (채널당) |
| 구독 요청 빈도 제한 | 10 req/sec (연결당) |

---

## 2. SSE (Server-Sent Events) 프로토콜

### 2.1 백테스팅 진행 스트림

Simulation Service는 백테스팅 결과를 SSE로 실시간 전달한다. 클라이언트는 `POST /backtests` 요청 시 `Accept: text/event-stream` 헤더를 포함하여 SSE 스트림을 수신한다.

**요청**:
```http
POST /backtests
Content-Type: application/json
Accept: text/event-stream
Authorization: Bearer {JWT_ACCESS_TOKEN}

{
  "agentIdentifier": "660e8400-e29b-41d4-a716-446655440000",
  "symbolIdentifier": "550e8400-e29b-41d4-a716-446655440000",
  "from": "2024-01-01T00:00:00Z",
  "to": "2024-06-01T00:00:00Z",
  "interval": "HOUR_1"
}
```

### 2.2 이벤트 타입

SSE 스트림은 4가지 이벤트 타입을 전달한다.

#### `signal` — 전략 신호 결과

각 캔들 시점의 전략 평가 결과를 전달한다. Agent Service의 gRPC BacktestStrategy 스트리밍 응답을 SSE로 중계한다.

```
event: signal
data: {"signalType":"BUY","confidence":0.85,"candleOpenTime":"2024-01-01T09:00:00Z","suggestedQuantity":0.05,"cashAfter":9500.0,"totalValueAfter":10200.0,"reason":{"ma_cross":"golden_cross","rsi":35.2}}

event: signal
data: {"signalType":"HOLD","confidence":0.12,"candleOpenTime":"2024-01-01T10:00:00Z","suggestedQuantity":0.0,"cashAfter":9500.0,"totalValueAfter":10180.0,"reason":{"ma_cross":"none","rsi":48.5}}

event: signal
data: {"signalType":"SELL","confidence":0.91,"candleOpenTime":"2024-01-01T11:00:00Z","suggestedQuantity":0.03,"cashAfter":11000.0,"totalValueAfter":11000.0,"reason":{"ma_cross":"dead_cross","rsi":72.1}}
```

**`signal` data 필드**:

| 필드 | 타입 | 설명 |
|------|------|------|
| `signalType` | String | 신호 타입 — `BUY`, `SELL`, `HOLD` |
| `confidence` | Number | 신뢰도 (0.0 ~ 1.0) |
| `candleOpenTime` | String | 해당 캔들 시작 시각 (ISO-8601) |
| `suggestedQuantity` | Number | 제안 수량 (RiskConfig 기반) |
| `cashAfter` | Number | 신호 반영 후 잔여 현금 |
| `totalValueAfter` | Number | 신호 반영 후 총자산 평가액 |
| `reason` | Object | 신호 생성 근거 (지표 값, 조건 평가 결과) |

#### `progress` — 진행 상황

백테스팅 진행률을 전달한다. 전체 캔들 수 대비 처리된 캔들 수를 기반으로 계산한다.

```
event: progress
data: {"processed":150,"total":4320,"percentage":3.47}
```

| 필드 | 타입 | 설명 |
|------|------|------|
| `processed` | Integer | 처리 완료된 캔들 수 |
| `total` | Integer | 전체 캔들 수 |
| `percentage` | Number | 진행률 (소수점 2자리) |

#### `error` — 에러 발생

백테스팅 도중 에러가 발생하면 에러 이벤트를 전달하고 스트림을 종료한다.

```
event: error
data: {"code":"S003","message":"Agent Service gRPC 스트리밍 중 오류가 발생했습니다"}
```

| 필드 | 타입 | 설명 |
|------|------|------|
| `code` | String | Simulation Service 에러 코드 (S001~S005) |
| `message` | String | 사용자 노출용 메시지 |

**에러 코드 참조**:

| 코드 | 상수 | 설명 |
|------|------|------|
| `S001` | `CANDLE_DATA_EMPTY` | 조회된 캔들 데이터 없음 |
| `S002` | `AGENT_NOT_FOUND` | Agent를 찾을 수 없음 |
| `S003` | `BACKTEST_STREAM_ERROR` | Agent gRPC 스트리밍 중 오류 |
| `S004` | `MARKET_SERVICE_UNAVAILABLE` | Market Service gRPC 호출 실패 |
| `S005` | `INVALID_DATE_RANGE` | from >= to 또는 미래 날짜 |

#### `done` — 백테스팅 완료

모든 캔들 처리가 완료되면 `done` 이벤트를 전달하고 스트림을 종료한다.

```
event: done
data: {}
```

`done` 수신 후 클라이언트는 Agent Service REST API(`GET /agents/{agentId}/backtests/{backtestIdentifier}`)로 결과 요약을 조회할 수 있다.

### 2.3 전체 스트림 예시

```
event: progress
data: {"processed":0,"total":4320,"percentage":0.0}

event: signal
data: {"signalType":"HOLD","confidence":0.10,"candleOpenTime":"2024-01-01T00:00:00Z","suggestedQuantity":0.0,"cashAfter":10000.0,"totalValueAfter":10000.0,"reason":{"ma_cross":"none","rsi":50.0}}

event: signal
data: {"signalType":"BUY","confidence":0.85,"candleOpenTime":"2024-01-01T01:00:00Z","suggestedQuantity":0.05,"cashAfter":7500.0,"totalValueAfter":10050.0,"reason":{"ma_cross":"golden_cross","rsi":35.2}}

event: progress
data: {"processed":100,"total":4320,"percentage":2.31}

event: signal
data: {"signalType":"SELL","confidence":0.91,"candleOpenTime":"2024-01-02T15:00:00Z","suggestedQuantity":0.03,"cashAfter":11500.0,"totalValueAfter":11500.0,"reason":{"ma_cross":"dead_cross","rsi":72.1}}

event: progress
data: {"processed":4320,"total":4320,"percentage":100.0}

event: done
data: {}
```

### 2.4 연결 종료 조건

| 조건 | 동작 |
|------|------|
| 모든 캔들 처리 완료 | `done` 이벤트 전송 후 스트림 종료 |
| Agent gRPC 스트리밍 오류 | `error` 이벤트 전송 후 스트림 종료 |
| Market gRPC 호출 실패 | HTTP 에러 응답 반환 (SSE 시작 전) |
| 클라이언트 연결 끊김 | Simulation이 감지 후 Agent gRPC 스트림 cancel |
| 서버 타임아웃 (30분) | `error` 이벤트 전송 후 스트림 종료 |

### 2.5 에러 처리

**SSE 시작 전 에러** (HTTP 응답으로 반환):

요청 유효성 검증 실패(`S005`), Market Service 호출 실패(`S004`), 캔들 데이터 없음(`S001`) 등은 SSE 스트림 시작 전에 발생한다. 이 경우 일반 HTTP 에러 응답을 반환한다.

```json
HTTP/1.1 400 Bad Request
Content-Type: application/json

{
  "code": "S005",
  "message": "시작 날짜는 종료 날짜보다 이전이어야 합니다",
  "timestamp": "2024-01-01T12:00:00Z",
  "path": "/backtests",
  "details": null
}
```

**SSE 시작 후 에러** (SSE 이벤트로 전달):

Agent gRPC 스트리밍 도중 연결이 끊기거나 오류가 발생하면 `error` 이벤트를 전송하고 스트림을 종료한다.

```
event: error
data: {"code":"S003","message":"백테스팅 스트리밍 중 오류가 발생했습니다"}
```

**재시도 정책**: 백테스팅은 부작용 없는 읽기 전용 작업이므로, 실패 시 동일한 요청으로 재시도하면 된다. SSE 스트림의 자동 재연결(`retry` 필드)은 사용하지 않는다. 백테스팅은 매번 처음부터 실행해야 하기 때문이다.
