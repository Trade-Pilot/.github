# VirtualTrade Service — Domain 설계

## 1. Bounded Context

VirtualTrade Service는 **사용자가 등록한 Agent를 대상으로 주기적으로 신호 생성을 트리거하고, 신호 결과를 받아 가상 체결을 확정해 Agent Service에 전달**하는 역할을 담당한다.

```
VirtualTrade Service 책임
├── 등록 관리      Agent의 가상거래 등록 및 상태 관리
├── 트리거         스케줄러가 주기적으로 Kafka AnalyzeAgentCommand 발행
├── 현재가 조회    Market Service gRPC로 분석 직전 currentPrice 획득
├── 가상 체결 확정 AnalyzeAgentReply 수신 → BUY/SELL 신호를 즉시 체결로 간주하고
│                  ExecutionConfirmedEvent 발행 → Agent Service 포트폴리오 갱신
└── 알림 처리      체결 이벤트 기반 사용자 알림 (선택적)
```

### 책임 분리

| | VirtualTrade Service | Agent Service |
|---|---|---|
| **Agent 등록/활성화** | ❌ | ✅ |
| **전략 신호 생성** | ❌ (위임) | ✅ |
| **포트폴리오 추적** | ❌ | ✅ |
| **가상거래 등록 관리** | ✅ | ❌ |
| **주기적 트리거** | ✅ | ❌ |
| **현재가 조회** | ✅ (트리거 전) | ✅ (stopLoss/takeProfit용) |

Portfolio 관리(현금, 포지션, 손익)는 Agent Service가 담당한다.
VirtualTrade Service는 **신호 트리거와 결과 수신/알림**에만 집중한다.

---

## 2. 헥사고날 아키텍처 레이어

```
domain/
  model/         VirtualTradeRegistration, RegistrationStatus
  port/
    in/          RegisterVirtualTradeUseCase
                 ActivateRegistrationUseCase
                 PauseRegistrationUseCase
                 StopRegistrationUseCase
                 HandleAgentReplyUseCase     (AnalyzeAgentReply 수신 → 가상 체결 확정)
    out/         FindRegistrationOutput, SaveRegistrationOutput
                 FindCurrentPriceOutput              (Market Service gRPC)
                 PublishAnalyzeCommandOutput          (Kafka → Agent Service 신호 요청)
                 PublishExecutionConfirmedOutput      (Kafka → Agent Service 가상 체결 확정)

application/
  usecase/       RegisterVirtualTradeService
                 ActivateRegistrationService
                 PauseRegistrationService         (implements PauseRegistrationUseCase)
                 StopRegistrationService          (implements StopRegistrationUseCase)
                 HandleAgentReplyService          (implements HandleAgentReplyUseCase)
                 VirtualTradeScheduler            (스케줄러 — 내부 트리거)

infrastructure/
  kafka/         AnalyzeAgentCommandProducer      (implements PublishAnalyzeCommandOutput)
                 AnalyzeAgentReplyConsumer        (reply.agent.virtual-trade.analyze-strategy 구독)
                 ExecutionConfirmedEventProducer  (implements PublishExecutionConfirmedOutput)
                 AgentTerminatedEventConsumer     (trade-pilot.agentservice.agent 구독)
  grpc/          MarketCandleGrpcAdapter          (implements FindCurrentPriceOutput)
  persistence/   VirtualTradeRegistrationJpaAdapter
                   (implements FindRegistrationOutput, SaveRegistrationOutput)
  web/           VirtualTradeRegistrationController
```

---

## 3. 도메인 모델

```
VirtualTradeRegistration (Aggregate Root)
├── registrationId : UUID
├── agentId        : UUID              -- Agent Service 참조 (FK 없음, 별도 서비스)
├── userId         : UUID
├── symbolIds      : List<UUID>        -- 분석 대상 심볼 목록 (JSONB)
├── status         : RegistrationStatus
├── createdAt      : OffsetDateTime
└── updatedAt      : OffsetDateTime
```

### Value Objects

```kotlin
enum class RegistrationStatus {
    ACTIVE,    // 스케줄러가 주기적으로 신호 요청 발행 중
    PAUSED,    // 일시 중지 — 스케줄러 트리거 제외
    STOPPED,   // 종료 — 재활성화 불가
}
```

### 생명주기

```
ACTIVE ◀──activate()──┐
  │                    │
pause()            resume()
  │                    │
  ▼                    │
PAUSED ─────────────────┘
  │
stop() (또는 ACTIVE에서 직접)
  │
  ▼
STOPPED
```

> Agent Service에서 Agent가 TERMINATED되면
> VirtualTrade Service도 해당 registrationId를 STOPPED 처리한다 (이벤트 연동).
>
> `symbolIds`는 ACTIVE / PAUSED 상태에서만 수정 가능하다.
> STOPPED 상태는 복구 불가.

### symbolIds 설계 원칙

- 하나의 Registration이 여러 심볼을 추적할 수 있다.
- 스케줄러 실행 시 각 `(agentId, symbolId)` 조합마다 독립적으로 `AnalyzeAgentCommand`를 발행한다.
- 심볼별로 각각 현재가를 조회한 후 발행한다.

---

## 4. 도메인 포트

```kotlin
// Input Ports
interface RegisterVirtualTradeUseCase {
    fun register(command: RegisterVirtualTradeCommand): VirtualTradeRegistration
}

interface ActivateRegistrationUseCase {
    fun activate(registrationId: UUID): VirtualTradeRegistration
}

interface PauseRegistrationUseCase {
    fun pause(registrationId: UUID): VirtualTradeRegistration
}

interface StopRegistrationUseCase {
    fun stop(registrationId: UUID): VirtualTradeRegistration
}

data class RegisterVirtualTradeCommand(
    val agentId   : UUID,
    val userId    : UUID,
    val symbolIds : List<UUID>,
)

interface HandleAgentReplyUseCase {
    fun handle(reply: AnalyzeAgentReply)
}

// Output Ports
interface FindRegistrationOutput {
    fun findById(registrationId: UUID): VirtualTradeRegistration?
    fun findAllByStatus(status: RegistrationStatus): List<VirtualTradeRegistration>
    fun findByAgentId(agentId: UUID): VirtualTradeRegistration?
}

interface SaveRegistrationOutput {
    fun save(registration: VirtualTradeRegistration): VirtualTradeRegistration
}

// Market Service에서 심볼의 현재가(최근 캔들 종가) 조회
interface FindCurrentPriceOutput {
    fun getCurrentPrice(symbolId: UUID, interval: CandleInterval): BigDecimal
}

// Kafka AnalyzeAgentCommand 발행
interface PublishAnalyzeCommandOutput {
    fun publish(topic: String, command: AnalyzeAgentCommand)
}

// Agent Service에 가상 체결 완료 통보
interface PublishExecutionConfirmedOutput {
    fun publish(event: ExecutionConfirmedEvent)
}

data class ExecutionConfirmedEvent(
    val agentId    : UUID,
    val signalId   : UUID,           // Agent Service가 저장한 Signal ID (필수)
    val symbolId   : UUID,
    val side       : OrderSide,      // BUY | SELL
    val quantity   : BigDecimal,     // 체결 수량 (= suggestedQuantity)
    val price      : BigDecimal,     // 체결가 (= AnalyzeAgentReply.price)
    val fee        : BigDecimal,     // 가상 체결이므로 0
    val executedAt : OffsetDateTime,
) : EventBaseMessage
```

---

## 5. 스케줄러

### 트리거 방식

VirtualTradeScheduler는 **설정 가능한 고정 주기(기본: 1분)**로 실행된다.
각 실행마다 ACTIVE 상태의 모든 `VirtualTradeRegistration`을 조회하고,
각 `(agentId, symbolId)` 조합에 대해 Kafka 커맨드를 발행한다.

**설정 예시**:
```yaml
# application.yml
scheduler:
  virtual-trade:
    interval: 60000  # 밀리초 (기본: 1분)
```

```kotlin
// VirtualTradeScheduler.kt
@Component
class VirtualTradeScheduler(
    @Value("\${scheduler.virtual-trade.interval:60000}")
    private val schedulerInterval: Long,
    // ...
) {
    @Scheduled(fixedDelayString = "\${scheduler.virtual-trade.interval:60000}")
    fun triggerAnalysis() {
        // ...
    }
}
```

> 신호 분석의 캔들 주기(`interval`)는 Strategy 파라미터에 저장되어 있어 Agent Service가 결정한다.
> VirtualTrade는 Strategy interval에 관계없이 고정 주기로 트리거만 발행한다.
> Agent Service 내부에서 올바른 interval로 캔들을 조회하므로, 중복 트리거는 Agent Service의 멱등성으로 처리한다.

### 실행 흐름

```
[매 1분 실행]
1. FindRegistrationOutput.findAllByStatus(ACTIVE) → List<VirtualTradeRegistration>
2. 각 registration에 대해:
   각 symbolId에 대해:
     a. FindCurrentPriceOutput.getCurrentPrice(symbolId, interval=MINUTE_1)
        └ MarketCandleGrpcAdapter.getRecentCandles(limit=1).close
     b. PublishAnalyzeCommandOutput.publish(
          topic   = "command.agent.virtual-trade.analyze-strategy",
          command = AnalyzeAgentCommand(agentId, symbolId, currentPrice)
        )
3. 발행 실패 시 로그 기록 (재시도는 Kafka producer retry 정책 위임)
```

> currentPrice 조회 실패 시 해당 `(agentId, symbolId)` 쌍의 발행을 건너뛰고 로그를 남긴다.
> 다른 조합의 발행은 계속 진행한다.

---

## 6. Kafka 인터페이스

### Command 발행 — 신호 생성 요청

```kotlin
// 발행 토픽
// command.agent.virtual-trade.analyze-strategy

data class AnalyzeAgentCommand(
    val agentId      : UUID,
    val symbolId     : UUID,
    val currentPrice : BigDecimal,
) : CommandBaseMessage
```

### Reply 수신 — 신호 생성 결과

```kotlin
// 구독 토픽 — Envelope.callback으로 동적 결정 (Agent Service가 설정)
// reply.agent.virtual-trade.analyze-strategy (예시)

data class AnalyzeAgentReply(
    val agentId           : UUID,
    val signalId          : UUID?,        // BUY/SELL이면 Agent Service가 저장한 Signal ID, HOLD이면 null
    val strategyId        : UUID,
    val symbolId          : UUID,
    val signalType        : SignalType,
    val confidence        : BigDecimal,
    val suggestedQuantity : BigDecimal,
    val price             : BigDecimal,
    val reason            : Map<String, Any>,
) : CommandBaseMessage
```

**Reply 수신 후 처리:**

```
1. AnalyzeAgentReply 수신
2. signalType 확인
   - HOLD       : 단순 로그. 처리 종료.
   - BUY / SELL :
       a. ExecutionConfirmedEvent 생성
            agentId    = reply.agentId
            signalId   = reply.signalId  (Agent Service가 저장한 Signal의 ID)
            symbolId   = reply.symbolId
            side       = reply.signalType (BUY → BUY, SELL → SELL)
            quantity   = reply.suggestedQuantity
            price      = reply.price
            fee        = 0               (가상 체결 — 수수료 없음)
            executedAt = now
       b. PublishExecutionConfirmedOutput.publish(event)
            └ 발행 토픽: event.virtual-trade.execution
       c. 사용자 알림 발송 (선택적 — 알림 서비스 연동)
```

> Agent Service는 `event.virtual-trade.execution` 토픽을 구독해 Portfolio를 갱신한다.
> VirtualTrade는 포트폴리오 연산을 직접 수행하지 않는다.

### Event 수신 — AgentTerminatedEvent

```
구독 토픽 : trade-pilot.agentservice.agent  (eventType: "agent-terminated")
처리      : agentId에 해당하는 VirtualTradeRegistration → STOPPED 처리
```

---

## 7. gRPC 인터페이스

### VirtualTrade → Market (현재가 조회)

스케줄러 실행 시 각 심볼의 현재가가 필요하다.
Market Service의 `GetRecentCandles(limit=1)` RPC를 호출해 가장 최근 캔들의 **종가(close)를 현재가로 대체**한다.

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

> Agent Service의 `PortfolioHistoryRecorder`와 동일한 방식으로 현재가를 근사한다.
> 별도의 현재가 RPC 없이 기존 `GetRecentCandles` 인터페이스를 재사용한다.

---

## 8. DB 스키마

```sql
CREATE TABLE virtual_trade_registration (
    id          UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id    UUID         NOT NULL UNIQUE,   -- Agent Service 참조 (외부 서비스)
    user_id     UUID         NOT NULL,
    symbol_ids  JSONB        NOT NULL DEFAULT '[]',  -- List<UUID>
    status      VARCHAR(20)  NOT NULL DEFAULT 'ACTIVE',
    created_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_vtr_user   ON virtual_trade_registration (user_id);
CREATE INDEX idx_vtr_status ON virtual_trade_registration (status);
-- 스케줄러가 ACTIVE 목록을 자주 조회하므로 status 인덱스 필수

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

CREATE TABLE processed_events (
    topic       VARCHAR(255) NOT NULL,
    partition   INT          NOT NULL,
    offset      BIGINT       NOT NULL,
    consumed_at TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    PRIMARY KEY (topic, partition, offset)
);
```

> `virtual_trade_registration.agent_id`에 UNIQUE 제약을 두어 하나의 Agent가 중복 등록되지 않도록 한다.
> `symbol_ids`는 JSONB 배열로 저장한다. 심볼 추가/삭제는 배열 전체 교체 방식으로 처리한다.

---

## 9. API 엔드포인트

| Method | 경로 | Role | 설명 |
|--------|------|------|------|
| `POST` | `/virtual-trades` | USER | 가상거래 등록 (agentId + symbolIds) |
| `GET` | `/virtual-trades` | USER | 내 가상거래 등록 목록 |
| `GET` | `/virtual-trades/{id}` | USER | 등록 상세 |
| `PUT` | `/virtual-trades/{id}/activate` | USER | ACTIVE 전환 |
| `PUT` | `/virtual-trades/{id}/pause` | USER | PAUSED 전환 |
| `PUT` | `/virtual-trades/{id}/stop` | USER | STOPPED 처리 |
| `PUT` | `/virtual-trades/{id}/symbols` | USER | 분석 대상 심볼 목록 수정 (ACTIVE/PAUSED만) |

---

## 10. 에러 코드

| 코드 | 상수 | 설명 |
|------|------|------|
| `VT001` | `REGISTRATION_NOT_FOUND` | 가상거래 등록 없음 |
| `VT002` | `ALREADY_REGISTERED` | 해당 Agent는 이미 가상거래에 등록됨 |
| `VT003` | `REGISTRATION_STOPPED` | STOPPED 상태는 재활성화 불가 |
| `VT004` | `REGISTRATION_NOT_ACTIVE` | ACTIVE 상태가 아니어서 일시정지 불가 |
| `VT005` | `REGISTRATION_NOT_PAUSED` | PAUSED 상태가 아니어서 재활성화 불가 |
| `VT006` | `SYMBOL_IDS_EMPTY` | symbolIds는 최소 1개 이상 필요 |
| `VT007` | `CURRENT_PRICE_UNAVAILABLE` | Market Service에서 현재가 조회 실패 |
