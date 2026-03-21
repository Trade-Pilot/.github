# 서비스별 초기 마이그레이션 SQL

> 원본: `backend/database-migration.md` Section 3

---


## 3. 서비스별 초기 마이그레이션 목록

### 3.1 User Service

#### V20260320_001__create_user_table.sql
```sql
CREATE TABLE "user" (
    identifier    UUID        PRIMARY KEY,
    email         VARCHAR     NOT NULL UNIQUE,
    password_hash VARCHAR     NOT NULL,
    name          VARCHAR     NOT NULL,
    role          VARCHAR     NOT NULL DEFAULT 'USER',
    status        VARCHAR     NOT NULL DEFAULT 'ACTIVE',
    created_date  TIMESTAMP WITH TIME ZONE NOT NULL,
    modified_date TIMESTAMP WITH TIME ZONE NOT NULL
);

CREATE INDEX user_email_idx  ON "user" (email);
CREATE INDEX user_status_idx ON "user" (status);
```

#### V20260320_002__create_refresh_token_table.sql
```sql
CREATE TABLE refresh_token (
    identifier       UUID    PRIMARY KEY,
    user_identifier  UUID    NOT NULL,
    token_hash       VARCHAR NOT NULL,
    expires_at       TIMESTAMP WITH TIME ZONE NOT NULL,
    is_revoked       BOOLEAN NOT NULL DEFAULT FALSE,
    created_at       TIMESTAMP WITH TIME ZONE NOT NULL,

    FOREIGN KEY (user_identifier) REFERENCES "user"(identifier)
);

CREATE INDEX refresh_token_user_idx   ON refresh_token (user_identifier);
CREATE INDEX refresh_token_expiry_idx ON refresh_token (expires_at);
```

#### V20260320_003__create_outbox_table.sql
```sql
CREATE TABLE outbox (
    id               UUID    PRIMARY KEY,
    aggregate_type   VARCHAR NOT NULL,
    aggregate_id     VARCHAR NOT NULL,
    event_type       VARCHAR NOT NULL,
    payload          TEXT    NOT NULL,
    trace_id         VARCHAR,
    parent_span_id   VARCHAR,
    status           VARCHAR NOT NULL DEFAULT 'PENDING',
    retry_count      INT     NOT NULL DEFAULT 0,
    created_at       TIMESTAMP WITH TIME ZONE NOT NULL,
    published_at     TIMESTAMP WITH TIME ZONE
);

CREATE INDEX outbox_relay_idx ON outbox (created_at)
    WHERE status IN ('PENDING', 'FAILED');

CREATE INDEX outbox_dead_idx ON outbox (created_at)
    WHERE status = 'DEAD';
```

---

### 3.2 Exchange Service

#### V20260320_001__create_exchange_account_table.sql
```sql
CREATE TABLE exchange_account (
    id                  UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id             UUID        NOT NULL,
    exchange            VARCHAR(20) NOT NULL DEFAULT 'UPBIT',
    encrypted_access_key TEXT       NOT NULL,
    encrypted_secret_key TEXT       NOT NULL,
    status              VARCHAR(20) NOT NULL DEFAULT 'ACTIVE',
    created_at          TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_ea_user   ON exchange_account (user_id);
CREATE INDEX idx_ea_status ON exchange_account (status);

CREATE UNIQUE INDEX idx_ea_user_exchange_active
    ON exchange_account (user_id, exchange)
    WHERE status = 'ACTIVE';
```

---

### 3.3 Market Service

Market Service는 TimescaleDB 확장을 사용한다. 마이그레이션 실행 전 TimescaleDB 확장이 설치되어 있어야 한다.

#### V20260320_001__enable_timescaledb.sql
```sql
CREATE EXTENSION IF NOT EXISTS timescaledb;
```

#### V20260320_002__create_market_symbol_table.sql
```sql
CREATE TABLE market_symbol (
    identifier    UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    code          VARCHAR(20)  NOT NULL UNIQUE,
    name          VARCHAR(100) NOT NULL,
    market        VARCHAR(20)  NOT NULL DEFAULT 'COIN',
    status        VARCHAR(20)  NOT NULL DEFAULT 'LISTED',
    created_date  TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    modified_date TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_ms_market ON market_symbol (market);
CREATE INDEX idx_ms_status ON market_symbol (status);
```

#### V20260320_003__create_market_candle_table.sql
```sql
CREATE TABLE market_candle (
    symbol_id  UUID           NOT NULL,
    interval   VARCHAR(10)    NOT NULL,
    time       TIMESTAMP WITH TIME ZONE NOT NULL,
    open       NUMERIC(30,8)  NOT NULL,
    high       NUMERIC(30,8)  NOT NULL,
    low        NUMERIC(30,8)  NOT NULL,
    close      NUMERIC(30,8)  NOT NULL,
    volume     NUMERIC(30,8)  NOT NULL,
    amount     NUMERIC(30,8)  NOT NULL,

    PRIMARY KEY (symbol_id, interval, time)
);

-- TimescaleDB hypertable 변환 (월별 chunk)
SELECT create_hypertable('market_candle', 'time',
    chunk_time_interval => INTERVAL '1 month'
);

-- 심볼+간격별 시계열 조회 최적화
CREATE INDEX idx_mc_symbol_interval_time
    ON market_candle (symbol_id, interval, time DESC);
```

#### V20260320_004__create_market_candle_collect_task_table.sql
```sql
CREATE TABLE market_candle_collect_task (
    identifier          UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    symbol_id           UUID         NOT NULL REFERENCES market_symbol(identifier),
    interval            VARCHAR(10)  NOT NULL,
    created_date        TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    last_collected_time TIMESTAMP WITH TIME ZONE,
    last_collected_price NUMERIC(30,8),
    status              VARCHAR(20)  NOT NULL DEFAULT 'CREATED',
    retry_count         INT          NOT NULL DEFAULT 0,

    UNIQUE (symbol_id, interval)
);

CREATE INDEX idx_mcct_status ON market_candle_collect_task (status);
```

#### V20260320_005__create_outbox_table.sql
```sql
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
    created_at     TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    published_at   TIMESTAMP WITH TIME ZONE
);

CREATE INDEX outbox_relay_idx ON outbox (created_at)
    WHERE status IN ('PENDING', 'FAILED');
CREATE INDEX outbox_dead_idx ON outbox (created_at)
    WHERE status = 'DEAD';
```

#### V20260320_006__configure_timescaledb_policies.sql
```sql
-- 7일 이후 자동 압축
ALTER TABLE market_candle SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'symbol_id, interval',
    timescaledb.compress_orderby = 'time DESC'
);

SELECT add_compression_policy('market_candle', INTERVAL '7 days');

-- 2년 이후 자동 삭제 (Cold Storage 이동 후 실행)
SELECT add_retention_policy('market_candle', INTERVAL '2 years');
```

---

### 3.4 Agent Service

FK 의존성 순서: strategy → agent → signal, portfolio → position, backtest_result, strategy_decision_log

#### V20260320_001__create_strategy_table.sql
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
    created_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_strategy_user   ON strategy (user_id);
CREATE INDEX idx_strategy_status ON strategy (status);
CREATE INDEX idx_strategy_params ON strategy USING GIN (parameters);
```

#### V20260320_002__create_agent_table.sql
```sql
CREATE TABLE agent (
    id          UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID         NOT NULL,
    name        VARCHAR(100) NOT NULL,
    description TEXT,
    strategy_id     UUID          NOT NULL REFERENCES strategy(id),
    status          VARCHAR(20)   NOT NULL DEFAULT 'INACTIVE',
    risk_config     JSONB         NOT NULL DEFAULT '{}',
    initial_capital NUMERIC(30,8) NOT NULL,
    created_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_agent_user     ON agent (user_id);
CREATE INDEX idx_agent_strategy ON agent (strategy_id);
CREATE INDEX idx_agent_status   ON agent (status);
```

#### V20260320_003__create_signal_table.sql
```sql
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
    created_at         TIMESTAMPTZ   NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_signal_agent    ON signal (agent_id,    created_at DESC);
CREATE INDEX idx_signal_strategy ON signal (strategy_id, created_at DESC);
```

#### V20260320_004__create_portfolio_table.sql
```sql
CREATE TABLE portfolio (
    id              UUID          PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id        UUID          NOT NULL UNIQUE REFERENCES agent(id),
    user_id         UUID          NOT NULL,
    cash            NUMERIC(30,8) NOT NULL,
    reserved_cash   NUMERIC(30,8) NOT NULL DEFAULT 0,
    realized_pnl    NUMERIC(30,8) NOT NULL DEFAULT 0,
    created_at      TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ   NOT NULL DEFAULT NOW()
);
```

#### V20260320_005__create_position_table.sql
```sql
CREATE TABLE position (
    id                UUID          PRIMARY KEY DEFAULT gen_random_uuid(),
    portfolio_id      UUID          NOT NULL REFERENCES portfolio(id),
    symbol_id         UUID          NOT NULL,
    quantity          NUMERIC(30,8) NOT NULL,
    reserved_quantity NUMERIC(30,8) NOT NULL DEFAULT 0,
    average_price     NUMERIC(30,8) NOT NULL,
    created_at        TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    updated_at        TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    UNIQUE (portfolio_id, symbol_id)
);
```

#### V20260320_006__create_portfolio_history_table.sql
```sql
CREATE TABLE portfolio_history (
    id                  UUID          PRIMARY KEY DEFAULT gen_random_uuid(),
    portfolio_id        UUID          NOT NULL REFERENCES portfolio(id),
    snapshot_type       VARCHAR(10)   NOT NULL,
    cash                NUMERIC(30,8) NOT NULL,
    total_value         NUMERIC(30,8) NOT NULL,
    realized_pnl        NUMERIC(30,8) NOT NULL,
    unrealized_pnl      NUMERIC(30,8) NOT NULL,
    positions_snapshot  JSONB         NOT NULL,
    trigger_signal_id   UUID,
    recorded_at         TIMESTAMPTZ   NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_portfolio_history_portfolio ON portfolio_history (portfolio_id, recorded_at DESC);
CREATE UNIQUE INDEX idx_portfolio_history_daily
    ON portfolio_history (portfolio_id, DATE(recorded_at))
    WHERE snapshot_type = 'DAILY';
```

#### V20260320_007__create_backtest_result_table.sql
```sql
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
    created_at        TIMESTAMPTZ   NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_backtest_result_agent ON backtest_result (agent_id, created_at DESC);
```

#### V20260320_008__create_strategy_decision_log_table.sql
```sql
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
    created_at       TIMESTAMPTZ   NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_decision_log_agent_time ON strategy_decision_log (agent_id, created_at DESC);
```

#### V20260320_009__create_outbox_table.sql
```sql
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
    created_at     TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    published_at   TIMESTAMP WITH TIME ZONE
);

CREATE INDEX outbox_relay_idx ON outbox (created_at)
    WHERE status IN ('PENDING', 'FAILED');
CREATE INDEX outbox_dead_idx ON outbox (created_at)
    WHERE status = 'DEAD';
```

#### V20260320_010__create_processed_events_table.sql
```sql
CREATE TABLE processed_events (
    topic       VARCHAR(255) NOT NULL,
    partition   INT          NOT NULL,
    offset      BIGINT       NOT NULL,
    consumed_at TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    PRIMARY KEY (topic, partition, offset)
);
```

---

### 3.5 Simulation Service

자체 DB 없음. Redis 캐시만 사용하므로 Flyway 마이그레이션 불필요.

---

### 3.6 VirtualTrade Service

#### V20260320_001__create_virtual_trade_registration_table.sql
```sql
CREATE TABLE virtual_trade_registration (
    id          UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id    UUID         NOT NULL UNIQUE,
    user_id     UUID         NOT NULL,
    symbol_ids  JSONB        NOT NULL DEFAULT '[]',
    status      VARCHAR(20)  NOT NULL DEFAULT 'ACTIVE',
    created_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_vtr_user   ON virtual_trade_registration (user_id);
CREATE INDEX idx_vtr_status ON virtual_trade_registration (status);
```

#### V20260320_002__create_outbox_table.sql
```sql
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
    created_at     TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    published_at   TIMESTAMP WITH TIME ZONE
);

CREATE INDEX outbox_relay_idx ON outbox (created_at)
    WHERE status IN ('PENDING', 'FAILED');
CREATE INDEX outbox_dead_idx ON outbox (created_at)
    WHERE status = 'DEAD';
```

#### V20260320_003__create_processed_events_table.sql
```sql
CREATE TABLE processed_events (
    topic       VARCHAR(255) NOT NULL,
    partition   INT          NOT NULL,
    offset      BIGINT       NOT NULL,
    consumed_at TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    PRIMARY KEY (topic, partition, offset)
);
```

---

### 3.7 Trade Service

FK 의존성 순서: trade_registration → trade_order → execution

#### V20260320_001__create_trade_registration_table.sql
```sql
CREATE TABLE trade_registration (
    id                   UUID          PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id             UUID          NOT NULL UNIQUE,
    user_id              UUID          NOT NULL,
    exchange_account_id  UUID          NOT NULL,
    symbol_ids           JSONB         NOT NULL DEFAULT '[]',
    allocated_capital    NUMERIC(30,8) NOT NULL,
    status               VARCHAR(20)   NOT NULL DEFAULT 'ACTIVE',
    order_config         JSONB         NOT NULL DEFAULT '{}',
    emergency_stopped    BOOLEAN       NOT NULL DEFAULT FALSE,
    created_at           TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    updated_at           TIMESTAMPTZ   NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_tr_user   ON trade_registration (user_id);
CREATE INDEX idx_tr_status ON trade_registration (status);
```

#### V20260320_002__create_trade_order_table.sql
```sql
CREATE TABLE trade_order (
    id                     UUID          PRIMARY KEY DEFAULT gen_random_uuid(),
    registration_id        UUID          NOT NULL REFERENCES trade_registration(id),
    agent_id               UUID          NOT NULL,
    symbol_id              UUID          NOT NULL,
    signal_id              UUID          NOT NULL,
    side                   VARCHAR(10)   NOT NULL,
    type                   VARCHAR(10)   NOT NULL,
    requested_quantity     NUMERIC(30,8) NOT NULL,
    requested_price        NUMERIC(30,8),
    executed_quantity      NUMERIC(30,8) NOT NULL DEFAULT 0,
    average_executed_price NUMERIC(30,8),
    status                 VARCHAR(20)   NOT NULL DEFAULT 'PENDING',
    exchange_order_id      VARCHAR(100),
    timeout_at             TIMESTAMPTZ,
    created_at             TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    updated_at             TIMESTAMPTZ   NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_order_agent       ON trade_order (agent_id,    created_at DESC);
CREATE INDEX idx_order_status      ON trade_order (status);
CREATE INDEX idx_order_active      ON trade_order (agent_id, symbol_id)
    WHERE status IN ('PENDING', 'SUBMITTED', 'PARTIALLY_FILLED');
CREATE INDEX idx_order_timeout     ON trade_order (timeout_at)
    WHERE status IN ('SUBMITTED', 'PARTIALLY_FILLED') AND timeout_at IS NOT NULL;
CREATE INDEX idx_order_exchange_id ON trade_order (exchange_order_id)
    WHERE exchange_order_id IS NOT NULL;
```

#### V20260320_003__create_execution_table.sql
```sql
CREATE TABLE execution (
    id           UUID          PRIMARY KEY DEFAULT gen_random_uuid(),
    order_id     UUID          NOT NULL REFERENCES trade_order(id),
    quantity     NUMERIC(30,8) NOT NULL,
    price        NUMERIC(30,8) NOT NULL,
    fee          NUMERIC(30,8) NOT NULL DEFAULT 0,
    executed_at  TIMESTAMPTZ   NOT NULL
);

CREATE INDEX idx_execution_order ON execution (order_id, executed_at ASC);
```

#### V20260320_004__create_outbox_table.sql
```sql
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
    created_at     TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    published_at   TIMESTAMP WITH TIME ZONE
);

CREATE INDEX outbox_relay_idx ON outbox (created_at)
    WHERE status IN ('PENDING', 'FAILED');
CREATE INDEX outbox_dead_idx ON outbox (created_at)
    WHERE status = 'DEAD';
```

#### V20260320_005__create_processed_events_table.sql
```sql
CREATE TABLE processed_events (
    topic       VARCHAR(255) NOT NULL,
    partition   INT          NOT NULL,
    offset      BIGINT       NOT NULL,
    consumed_at TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    PRIMARY KEY (topic, partition, offset)
);
```

#### V20260320_006__create_account_reconciliation_log_table.sql
```sql
CREATE TABLE account_reconciliation_log (
    id                      UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    exchange_account_id     UUID         NOT NULL,
    actual_cash             NUMERIC(30,8) NOT NULL,
    total_allocated_capital NUMERIC(30,8) NOT NULL,
    discrepancy             NUMERIC(30,8) NOT NULL,
    threshold               NUMERIC(30,8) NOT NULL,
    status                  VARCHAR(20)  NOT NULL,
    action_taken            TEXT,
    reconciled_at           TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_reconciliation_account ON account_reconciliation_log
    (exchange_account_id, reconciled_at DESC);
```

---

### 3.8 Notification Service

#### V20260320_001__create_notification_channel_table.sql
```sql
CREATE TABLE notification_channel (
    identifier      UUID    PRIMARY KEY,
    user_identifier UUID    NOT NULL,
    type            VARCHAR NOT NULL,
    config          JSONB   NOT NULL,
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    is_deleted      BOOLEAN NOT NULL DEFAULT FALSE,
    deleted_at      TIMESTAMP WITH TIME ZONE,
    created_date    TIMESTAMP WITH TIME ZONE NOT NULL,
    modified_date   TIMESTAMP WITH TIME ZONE NOT NULL
);

CREATE INDEX notification_channel_user_idx ON notification_channel (user_identifier)
    WHERE is_deleted = FALSE;
```

#### V20260320_002__create_notification_preference_table.sql
```sql
CREATE TABLE notification_preference (
    identifier          UUID    PRIMARY KEY,
    user_identifier     UUID    NOT NULL,
    event_type          VARCHAR NOT NULL,
    channel_identifiers UUID[]  NOT NULL,
    is_enabled          BOOLEAN NOT NULL DEFAULT FALSE,
    is_deleted          BOOLEAN NOT NULL DEFAULT FALSE,
    deleted_at          TIMESTAMP WITH TIME ZONE,
    created_date        TIMESTAMP WITH TIME ZONE NOT NULL,
    modified_date       TIMESTAMP WITH TIME ZONE NOT NULL,

    UNIQUE (user_identifier, event_type)
);

CREATE INDEX notification_preference_user_idx ON notification_preference (user_identifier)
    WHERE is_deleted = FALSE;
```

#### V20260320_003__create_notification_log_table.sql
```sql
CREATE TABLE notification_log (
    identifier          UUID    PRIMARY KEY,
    user_identifier     UUID    NOT NULL,
    channel_identifier  UUID    NOT NULL,
    event_type          VARCHAR NOT NULL,
    event_payload       TEXT    NOT NULL,
    message             TEXT    NOT NULL,
    status              VARCHAR NOT NULL,
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

#### V20260320_004__create_notification_template_table.sql
```sql
CREATE TABLE notification_template (
    identifier      UUID    PRIMARY KEY,
    event_type      VARCHAR NOT NULL,
    channel_type    VARCHAR NOT NULL,
    title_template  VARCHAR NOT NULL,
    body_template   TEXT    NOT NULL,
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    created_date    TIMESTAMP WITH TIME ZONE NOT NULL,
    modified_date   TIMESTAMP WITH TIME ZONE NOT NULL,

    UNIQUE (event_type, channel_type)
);

CREATE INDEX notification_template_event_idx ON notification_template (event_type, channel_type)
    WHERE is_active = TRUE;
```

#### V20260320_005__create_processed_events_table.sql
```sql
CREATE TABLE processed_events (
    topic       VARCHAR(255) NOT NULL,
    partition   INT          NOT NULL,
    offset      BIGINT       NOT NULL,
    consumed_at TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    PRIMARY KEY (topic, partition, offset)
);
```

---
