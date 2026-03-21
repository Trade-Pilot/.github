# Agent Service — Redis 캐시 및 DB 스키마

> 이 문서는 `backend/agent/domain.md`에서 분할되었습니다.

---

## 8. 캐시 전략 (Redis)

### 8.1 캐시 대상 및 TTL

| 캐시 키 | 값 | TTL | 갱신 조건 |
|---------|-----|-----|----------|
| `strategy:{strategyIdentifier}` | `StrategyDto` (JSON) | 10분 | 수정/상태 변경 시 evict |
| `agent:{agentIdentifier}` | `AgentDto` (JSON) | 10분 | 수정/상태 변경 시 evict |
| `symbol:{symbolIdentifier}` | `SymbolMetadata` (JSON) | 10분 | Market Service에서 심볼 상태 변경 시 evict (이벤트 없음, TTL 의존) |

> **Portfolio는 캐싱하지 않는다.** 신호 생성마다 `@Lock(PESSIMISTIC_WRITE)` DB 조회가 필수이며,
> 캐시된 Portfolio로 점유 계산 시 동시성 오류가 발생한다.

### 8.2 캐시 적용 규칙

**신호 생성 흐름 (AnalyzeAgentCommand 수신 시):**
```
1. Agent 조회    : Redis 캐시 → Cache Miss 시 DB 조회 + 캐시 저장
2. Strategy 조회 : Redis 캐시 → Cache Miss 시 DB 조회 + 캐시 저장
3. Market 캔들   : Market gRPC 호출 (캐시 안 함, 실시간 데이터)
4. Portfolio 조회 : DB 직접 조회 (PESSIMISTIC_WRITE, 캐시 안 함)
```

**캐시 Invalidation:**
```kotlin
// Strategy 수정/상태 변경 시
redisTemplate.delete("strategy:${strategyIdentifier}")

// Agent 상태 변경(activate, pause, terminate) 시
redisTemplate.delete("agent:${agentIdentifier}")

// DEPRECATED 전략은 캐싱에서 제외 (변경 빈도 없으므로 TTL로 자연 만료)
```

---

## 9. DB 스키마

```sql
CREATE TABLE strategy (
    id          UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID         NOT NULL,
    name        VARCHAR(100) NOT NULL,
    description TEXT,
    type        VARCHAR(20)  NOT NULL DEFAULT 'MANUAL',
    market      VARCHAR(20)  NOT NULL DEFAULT 'COIN',
    status      VARCHAR(20)  NOT NULL DEFAULT 'DRAFT',
    parameters  JSONB        NOT NULL DEFAULT '{}',
    created_date  TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    modified_date TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_strategy_user   ON strategy (user_id);
CREATE INDEX idx_strategy_status ON strategy (status);
CREATE INDEX idx_strategy_params ON strategy USING GIN (parameters);

CREATE TABLE agent (
    id          UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID         NOT NULL,
    name        VARCHAR(100) NOT NULL,
    description TEXT,
    strategy_id     UUID          NOT NULL REFERENCES strategy(id),
    status          VARCHAR(20)   NOT NULL DEFAULT 'INACTIVE',
    risk_config     JSONB         NOT NULL DEFAULT '{}',
    initial_capital NUMERIC(30,8) NOT NULL,
    created_date  TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    modified_date TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_agent_user     ON agent (user_id);
CREATE INDEX idx_agent_strategy ON agent (strategy_id);
CREATE INDEX idx_agent_status   ON agent (status);

CREATE TABLE signal (
    id                 UUID          PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id           UUID          NOT NULL REFERENCES agent(id),
    strategy_id        UUID          NOT NULL REFERENCES strategy(id),
    symbol_id          UUID          NOT NULL,
    type               VARCHAR(10)   NOT NULL,
    confidence         NUMERIC(5,4)  NOT NULL,
    price              NUMERIC(30,8) NOT NULL,
    suggested_quantity NUMERIC(30,8) NOT NULL,
    reason             JSONB         NOT NULL DEFAULT '{}',
    created_date         TIMESTAMPTZ   NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_signal_agent    ON signal (agent_id,    created_date DESC);
CREATE INDEX idx_signal_strategy ON signal (strategy_id, created_date DESC);

CREATE TABLE portfolio (
    id              UUID          PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id        UUID          NOT NULL UNIQUE REFERENCES agent(id),
    user_id         UUID          NOT NULL,
    cash            NUMERIC(30,8) NOT NULL,          -- 실제 보유 현금 (체결 완료 기준)
    reserved_cash   NUMERIC(30,8) NOT NULL DEFAULT 0, -- BUY 신호 점유 현금 (체결 전)
    realized_pnl    NUMERIC(30,8) NOT NULL DEFAULT 0, -- 누적 실현손익
    created_date      TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ   NOT NULL DEFAULT NOW()
);

CREATE TABLE portfolio_history (
    id                  UUID          PRIMARY KEY DEFAULT gen_random_uuid(),
    portfolio_id        UUID          NOT NULL REFERENCES portfolio(id),
    snapshot_type       VARCHAR(10)   NOT NULL,          -- SIGNAL | DAILY
    cash                NUMERIC(30,8) NOT NULL,
    total_value         NUMERIC(30,8) NOT NULL,          -- cash + 포지션 평가액
    realized_pnl        NUMERIC(30,8) NOT NULL,          -- 이 시점까지 누적 실현손익
    unrealized_pnl      NUMERIC(30,8) NOT NULL,          -- 보유 포지션 미실현 손익
    positions_snapshot  JSONB         NOT NULL,          -- 시점 포지션 상태 (불변)
    trigger_signal_id   UUID,                            -- SIGNAL 타입 전용
    recorded_at         TIMESTAMPTZ   NOT NULL DEFAULT NOW()
);

-- 시계열 조회 최적화 (포트폴리오별 시간순)
CREATE INDEX idx_portfolio_history_portfolio ON portfolio_history (portfolio_id, recorded_at DESC);
-- 일별 중복 방지 (DAILY 타입은 하루 1건)
CREATE UNIQUE INDEX idx_portfolio_history_daily
    ON portfolio_history (portfolio_id, DATE(recorded_at))
    WHERE snapshot_type = 'DAILY';

CREATE TABLE position (
    id                UUID          PRIMARY KEY DEFAULT gen_random_uuid(),
    portfolio_id      UUID          NOT NULL REFERENCES portfolio(id),
    symbol_id         UUID          NOT NULL,
    quantity          NUMERIC(30,8) NOT NULL,           -- 실제 보유 수량 (체결 완료 기준)
    reserved_quantity NUMERIC(30,8) NOT NULL DEFAULT 0, -- SELL 신호 점유 수량 (체결 전)
    average_price     NUMERIC(30,8) NOT NULL,
    created_date        TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    updated_at        TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    UNIQUE (portfolio_id, symbol_id)
);

CREATE TABLE backtest_result (
    id                UUID          PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id          UUID          NOT NULL REFERENCES agent(id),
    symbol_id         UUID          NOT NULL,
    candle_from       TIMESTAMPTZ   NOT NULL,
    candle_to         TIMESTAMPTZ   NOT NULL,
    initial_capital   NUMERIC(30,8) NOT NULL,
    final_value       NUMERIC(30,8) NOT NULL,
    realized_pnl      NUMERIC(30,8) NOT NULL,
    unrealized_pnl    NUMERIC(30,8) NOT NULL,
    total_signals     INT           NOT NULL DEFAULT 0,
    signal_snapshots  JSONB         NOT NULL DEFAULT '[]',
    created_date        TIMESTAMPTZ   NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_backtest_result_agent ON backtest_result (agent_id, created_date DESC);

CREATE TABLE strategy_decision_log (
    id               UUID          PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id         UUID          NOT NULL REFERENCES agent(id),
    strategy_id      UUID          NOT NULL REFERENCES strategy(id),
    symbol_id        UUID          NOT NULL,
    signal_type      VARCHAR(10)   NOT NULL,
    current_price    NUMERIC(30,8) NOT NULL,
    indicator_values JSONB         NOT NULL DEFAULT '{}',
    evaluation_status VARCHAR(20)  NOT NULL,
    evaluation_reason TEXT,
    created_date       TIMESTAMPTZ   NOT NULL DEFAULT NOW()
);

-- 최신 로그 조회 및 특정 기간 데이터 삭제 최적화
CREATE INDEX idx_decision_log_agent_time ON strategy_decision_log (agent_id, created_date DESC);

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

## 10. API 엔드포인트

### Strategy

| Method | 경로 | Role | 설명 |
|--------|------|------|------|
| `POST` | `/strategies` | USER | 전략 생성 (DRAFT) |
| `GET` | `/strategies` | USER | 내 전략 목록 |
| `GET` | `/strategies/{id}` | USER | 전략 상세 |
| `PUT` | `/strategies/{id}` | USER | 파라미터 수정 (DRAFT만) |
| `DELETE` | `/strategies/{id}` | USER | 삭제 (DRAFT, Agent 미할당) |
| `PUT` | `/strategies/{id}/validate` | USER | VALIDATED 전환 |
| `PUT` | `/strategies/{id}/deprecate` | USER | DEPRECATED 처리 |

### Agent

| Method | 경로 | Role | 설명 |
|--------|------|------|------|
| `POST` | `/agents` | USER | 에이전트 생성 (strategyIdentifier 지정) |
| `GET` | `/agents` | USER | 내 에이전트 목록 |
| `GET` | `/agents/{id}` | USER | 에이전트 상세 |
| `PUT` | `/agents/{id}` | USER | 설정 수정 (INACTIVE만) |
| `PUT` | `/agents/{id}/activate` | USER | ACTIVE 전환 + 포트폴리오 초기화 |
| `PUT` | `/agents/{id}/pause` | USER | PAUSED 전환 |
| `PUT` | `/agents/{id}/resume` | USER | ACTIVE 복귀 |
| `PUT` | `/agents/{id}/terminate` | USER | TERMINATED 처리 |
| `GET` | `/agents/{id}/signals` | USER | 신호 이력 (페이지네이션) |
| `GET` | `/agents/{id}/portfolio` | USER | 포트폴리오 현황 (현금, 총자산, 실현손익) |
| `GET` | `/agents/{id}/portfolio/positions` | USER | 현재 보유 포지션 목록 |
| `GET` | `/agents/{id}/portfolio/history` | USER | 시간별 포트폴리오 이력 (`?from=&to=&type=SIGNAL\|DAILY`) |
| `GET` | `/agents/{id}/decision-logs` | USER | 전략 결정 감사 로그 (페이지네이션) |
| `GET` | `/agents/{id}/backtests` | USER | 백테스트 결과 목록 |
| `GET` | `/agents/{id}/backtests/{backtestIdentifier}` | USER | 백테스트 결과 상세 (신호 스냅샷 포함) |

---

## 11. 에러 코드

| 코드 | 상수 | 설명 |
|------|------|------|
| `A001` | `STRATEGY_NOT_FOUND` | 전략 없음 |
| `A002` | `STRATEGY_NOT_DRAFT` | DRAFT 상태가 아니어서 수정 불가 |
| `A003` | `STRATEGY_NOT_VALIDATED` | DRAFT 전략은 실거래(TRADE) 신호 요청 불가 |
| `A004` | `STRATEGY_DEPRECATED` | DEPRECATED 전략은 신규 Agent에 할당 불가 |
| `A005` | `AGENT_NOT_FOUND` | 에이전트 없음 |
| `A006` | `AGENT_NOT_ACTIVE` | ACTIVE 상태가 아니어서 신호 생성 불가 |
| `A007` | `AGENT_NOT_INACTIVE` | INACTIVE 상태가 아니어서 설정 수정 불가 |
| `A008` | `AGENT_ALREADY_TERMINATED` | TERMINATED 에이전트는 상태 전환 불가 |
| `A009` | `PORTFOLIO_NOT_FOUND` | 포트폴리오 없음 |
| `A010` | `INSUFFICIENT_CASH` | 매수 시 현금 부족 |
| `A011` | `CANDLE_DATA_INSUFFICIENT` | 지표 계산에 필요한 캔들 수 부족 |
| `A012` | `UNSUPPORTED_STRATEGY_TYPE` | 지원하지 않는 전략 타입 |
| `A013` | `INVALID_RISK_CONFIG` | RiskConfig 유효성 오류 |
