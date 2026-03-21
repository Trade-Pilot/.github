# Trade Service — gRPC 인터페이스, DB 스키마, API, 에러 코드

> 이 문서는 `backend/trade/domain.md`에서 분할되었습니다.

---

## 7. gRPC 인터페이스

### Trade → Market (현재가 조회)

스케줄러가 `AnalyzeAgentCommand`에 포함할 `currentPrice`를 조회한다.
VirtualTrade와 동일하게 `GetRecentCandles(limit=1).close`를 현재가로 사용한다.

```
Market Service proto (market-service.proto)
────────────────────────────────────────────
service MarketCandle {
  rpc GetRecentCandles(GetRecentCandlesRequest) returns (GetRecentCandlesResponse);
}
```

```
FindCurrentPriceOutput (domain port)
        ▲
        │ implements
MarketCandleGrpcAdapter (infrastructure/grpc)
        │ uses generated stub
        ▼
MarketCandleGrpc.MarketCandleBlockingStub  ←  Market Service gRPC Server
```

---

## 8. DB 스키마

```sql
CREATE TABLE trade_registration (
    id                   UUID          PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id             UUID          NOT NULL UNIQUE,
    user_id              UUID          NOT NULL,
    exchange_account_id  UUID          NOT NULL,
    symbol_ids           JSONB         NOT NULL DEFAULT '[]',
    allocated_capital    NUMERIC(30,8) NOT NULL,                -- 할당 자본금 (Account Reconciliation용)
    status               VARCHAR(20)   NOT NULL DEFAULT 'ACTIVE',
    order_config         JSONB         NOT NULL DEFAULT '{}',
    emergency_stopped    BOOLEAN       NOT NULL DEFAULT FALSE,  -- 비상 정지 여부
    created_date           TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    modified_date           TIMESTAMPTZ   NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_tr_user   ON trade_registration (user_id);
CREATE INDEX idx_tr_status ON trade_registration (status);

CREATE TABLE trade_order (
    id                     UUID          PRIMARY KEY DEFAULT gen_random_uuid(),
    registration_id        UUID          NOT NULL REFERENCES trade_registration(id),
    agent_id               UUID          NOT NULL,
    symbol_id              UUID          NOT NULL,
    signal_id              UUID          NOT NULL,             -- Agent Service Signal 참조 (감사용)
    side                   VARCHAR(10)   NOT NULL,             -- BUY | SELL
    type                   VARCHAR(10)   NOT NULL,             -- MARKET | LIMIT
    requested_quantity     NUMERIC(30,8) NOT NULL,
    requested_price        NUMERIC(30,8),                      -- LIMIT이면 목표가, MARKET이면 null
    executed_quantity      NUMERIC(30,8) NOT NULL DEFAULT 0,
    average_executed_price NUMERIC(30,8),                      -- 평균 체결가 (미체결이면 null)
    status                 VARCHAR(20)   NOT NULL DEFAULT 'PENDING',
    exchange_order_id      VARCHAR(100),                       -- 거래소 주문 ID
    timeout_at             TIMESTAMPTZ,                        -- LIMIT 주문 자동 취소 기준 시각
    created_date             TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    modified_date             TIMESTAMPTZ   NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_order_agent       ON trade_order (agent_id,    created_date DESC);
CREATE INDEX idx_order_status      ON trade_order (status);
-- 중복 주문 방지: agentIdentifier + symbolIdentifier 기준 active 주문 조회
CREATE INDEX idx_order_active      ON trade_order (agent_id, symbol_id)
    WHERE status IN ('PENDING', 'SUBMITTED', 'PARTIALLY_FILLED');
-- 타임아웃 스케줄러 쿼리 최적화
CREATE INDEX idx_order_timeout     ON trade_order (timeout_at)
    WHERE status IN ('SUBMITTED', 'PARTIALLY_FILLED') AND timeout_at IS NOT NULL;
-- Exchange 이벤트 수신 시 exchangeOrderId로 Order 조회
CREATE INDEX idx_order_exchange_id ON trade_order (exchange_order_id)
    WHERE exchange_order_id IS NOT NULL;

CREATE TABLE execution (
    id           UUID          PRIMARY KEY DEFAULT gen_random_uuid(),
    order_id     UUID          NOT NULL REFERENCES trade_order(id),
    quantity     NUMERIC(30,8) NOT NULL,
    price        NUMERIC(30,8) NOT NULL,
    fee          NUMERIC(30,8) NOT NULL DEFAULT 0,
    executed_at  TIMESTAMPTZ   NOT NULL
);

CREATE INDEX idx_execution_order ON execution (order_id, executed_at ASC);

CREATE TABLE outbox (
    id             UUID    PRIMARY KEY DEFAULT gen_random_uuid(),
    aggregate_type VARCHAR NOT NULL,
    aggregate_id   VARCHAR NOT NULL,
    event_type     VARCHAR NOT NULL,
    payload        TEXT    NOT NULL,
    trace_id       VARCHAR,
    parent_span_id VARCHAR,
    status         VARCHAR NOT NULL DEFAULT 'PENDING',
    retry_count    INT     NOT NULL DEFAULT 0,
    created_date     TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    published_at   TIMESTAMP WITH TIME ZONE
);

CREATE INDEX outbox_relay_idx ON outbox (created_date)
    WHERE status IN ('PENDING', 'FAILED');
CREATE INDEX outbox_dead_idx ON outbox (created_date)
    WHERE status = 'DEAD';

CREATE TABLE processed_events (
    topic       VARCHAR(255) NOT NULL,
    partition   INT          NOT NULL,
    offset      BIGINT       NOT NULL,
    consumed_at TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    PRIMARY KEY (topic, partition, offset)
);
```

---

## 9. API 엔드포인트

### TradeRegistration

| Method | 경로 | Role | 설명 |
|--------|------|------|------|
| `POST` | `/trade-registrations` | USER | 실거래 등록 (agentIdentifier + exchangeAccountIdentifier + symbolIdentifiers + orderConfig) |
| `GET` | `/trade-registrations` | USER | 내 실거래 등록 목록 |
| `GET` | `/trade-registrations/{id}` | USER | 등록 상세 |
| `PUT` | `/trade-registrations/{id}/activate` | USER | ACTIVE 전환 |
| `PUT` | `/trade-registrations/{id}/pause` | USER | PAUSED 전환 |
| `PUT` | `/trade-registrations/{id}/stop` | USER | STOPPED 처리 |
| `PUT` | `/trade-registrations/{id}/symbols` | USER | 분석 대상 심볼 목록 수정 |
| `PUT` | `/trade-registrations/{id}/order-config` | USER | 주문 설정 수정 (PAUSED 상태만) |
| `PUT` | `/trade-registrations/{id}/emergency-stop` | USER | 비상 정지 (즉시 모든 신호 처리 차단 + 미체결 주문 취소) |
| `PUT` | `/trade-registrations/{id}/emergency-resume` | USER | 비상 정지 해제 (PAUSED 상태로 복귀 — 자동 재시작 안 함) |
| `POST` | `/admin/trade-registrations/emergency-stop-all` | ADMIN | 전체 실거래 비상 정지 |
| `PUT` | `/admin/trade-registrations/{id}/allocated-capital` | ADMIN | 할당 자본 수동 조정 (Account Reconciliation 불일치 해결) |

### Order

| Method | 경로 | Role | 설명 |
|--------|------|------|------|
| `GET` | `/trade-registrations/{id}/orders` | USER | 주문 이력 (페이지네이션) |
| `GET` | `/trade-registrations/{id}/orders/{orderIdentifier}` | USER | 주문 상세 (Execution 포함) |
| `DELETE` | `/trade-registrations/{id}/orders/{orderIdentifier}` | USER | 미체결 주문 수동 취소 (SUBMITTED / PARTIALLY_FILLED만) |

### 리소스 소유권 검증 규칙

모든 USER 엔드포인트는 `X-User-Id` 헤더와 리소스 소유권 일치를 검증한다.

```kotlin
// 공통 패턴: TradeRegistration 기반 리소스 접근 시
fun validateOwnership(registrationIdentifier: UUID, userIdentifier: UUID) {
    val registration = findById(registrationIdentifier)
        ?: throw RegistrationNotFoundException()
    if (registration.userIdentifier != userIdentifier) {
        throw ForbiddenException("TR016")  // RESOURCE_NOT_OWNED
    }
}

// Order 접근 시: Registration → Order 계층 검증
fun validateOrderOwnership(registrationIdentifier: UUID, orderIdentifier: UUID, userIdentifier: UUID) {
    validateOwnership(registrationIdentifier, userIdentifier)
    val order = findById(orderIdentifier)
        ?: throw OrderNotFoundException()
    if (order.registrationIdentifier != registrationIdentifier) {
        throw ForbiddenException("TR016")
    }
}
```

> **미검증 시 위험**: 다른 사용자의 주문을 취소하거나 거래 설정을 변경할 수 있다.
> 모든 Controller에서 `@RequestHeader("X-User-Id")` 기반 소유권 검증을 수행해야 한다.

---

## 10. 에러 코드

| 코드 | 상수 | 설명 |
|------|------|------|
| `TR001` | `REGISTRATION_NOT_FOUND` | 실거래 등록 없음 |
| `TR002` | `ALREADY_REGISTERED` | 해당 Agent는 이미 실거래에 등록됨 |
| `TR003` | `REGISTRATION_STOPPED` | STOPPED 상태는 재활성화 불가 |
| `TR004` | `REGISTRATION_NOT_ACTIVE` | ACTIVE 상태가 아니어서 일시정지 불가 |
| `TR005` | `REGISTRATION_NOT_PAUSED` | PAUSED 상태가 아니어서 재활성화 불가 |
| `TR006` | `SYMBOL_IDS_EMPTY` | symbolIdentifiers는 최소 1개 이상 필요 |
| `TR007` | `CURRENT_PRICE_UNAVAILABLE` | Market Service에서 현재가 조회 실패 |
| `TR008` | `ORDER_NOT_FOUND` | 주문 없음 |
| `TR009` | `ORDER_NOT_CANCELLABLE` | 취소 불가 상태의 주문 (FILLED / CANCELLED / REJECTED) |
| `TR010` | `EXCHANGE_ACCOUNT_NOT_FOUND` | Exchange Service에서 계정 없음 |
| `TR011` | `ORDER_SUBMIT_FAILED` | Exchange Service 주문 제출 실패 |
| `TR012` | `EMERGENCY_STOP_ACTIVE` | 비상 정지 상태이므로 주문 처리 불가 |
| `TR013` | `NOT_EMERGENCY_STOPPED` | 비상 정지 상태가 아님 |
| `TR014` | `ACCOUNT_BALANCE_INSUFFICIENT` | 거래소 계정 실제 잔고 부족 (Reconciliation 실패) |
| `TR015` | `ALLOCATED_CAPITAL_INVALID` | allocatedCapital 값이 잘못됨 (음수 또는 실계좌 초과) |
| `TR016` | `RESOURCE_NOT_OWNED` | 리소스가 요청 사용자 소유가 아님 (403 Forbidden) |
