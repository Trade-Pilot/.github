# Agent Service — Sequence Diagram

## 1. 전략 생성 및 검증

```mermaid
sequenceDiagram
    actor User
    participant API as Agent API
    participant DB  as PostgreSQL

    Note over User, DB: 1단계 — 전략 생성 (DRAFT)
    User ->> API: POST /strategies { name, type, parameters }
    API  ->> DB:  INSERT strategy (status=DRAFT)
    API -->> User: 201 { strategyIdentifier, status: DRAFT }

    Note over User, DB: 2단계 — 백테스팅 완료 후 VALIDATED 전환
    Note right of User: Simulation 서비스가 백테스팅 완료 후<br>사용자가 직접 호출 (또는 Simulation이 API 호출)
    User ->> API: PUT /strategies/{id}/validate
    API  ->> DB:  UPDATE strategy SET status=VALIDATED
    API -->> User: 200 OK
```

---

## 2. 에이전트 생성 및 활성화

```mermaid
sequenceDiagram
    actor User
    participant API as Agent API
    participant DB  as PostgreSQL

    Note over User, DB: 1단계 — 에이전트 생성 (INACTIVE)
    User ->> API: POST /agents { name, strategyIdentifier, riskConfig }
    API  ->> DB:  SELECT strategy WHERE id=strategyIdentifier AND status != DEPRECATED
    DB  -->> API: strategy (DEPRECATED 아님 검증 — DRAFT/VALIDATED 모두 허용)
    API  ->> DB:  INSERT agent (status=INACTIVE, strategy_id, risk_config)
    API -->> User: 201 { agentIdentifier, status: INACTIVE }

    Note over User, DB: 2단계 — 에이전트 활성화 + 포트폴리오 초기화
    User ->> API: PUT /agents/{id}/activate { initialCapital }
    API  ->> DB:  INSERT portfolio (agent_id, initial_capital, cash=initialCapital)
    API  ->> DB:  UPDATE agent SET status=ACTIVE
    API -->> User: 200 OK
```

---

## 3. 신호 생성 — Kafka Command/Reply

```mermaid
sequenceDiagram
    participant VT    as VirtualTrade
    participant Kafka
    participant AG    as Agent Service
    participant Redis
    participant MKT   as Market Service (gRPC)
    participant DB    as PostgreSQL

    VT ->> Kafka: CommandBaseMessageEnvelope<AnalyzeAgentCommand><br>topic: command.agent.virtual-trade.analyze-strategy<br>{ agentIdentifier, symbolIdentifier, currentPrice }<br>callback: reply.virtual-trade.agent.analyze-strategy

    Kafka ->> AG: AnalyzeAgentCommand

    AG ->> AG: 멱등성 확인 (processed_events)

    AG ->> Redis: GET agent:{agentIdentifier}
    alt Cache Miss
        AG ->> DB: SELECT agent WHERE id=agentIdentifier
        AG ->> Redis: SET agent:{agentIdentifier} TTL 10m
    end
    AG ->> AG: agent.status == ACTIVE 검증

    AG ->> Redis: GET strategy:{strategyIdentifier}
    alt Cache Miss
        AG ->> DB: SELECT strategy WHERE id=agent.strategyIdentifier
        AG ->> Redis: SET strategy:{strategyIdentifier} TTL 10m
    end

    AG ->> MKT: gRPC GetRecentCandles { symbolIdentifier, interval, limit }
    MKT -->> AG: candles[]

    AG ->> AG: StrategyExecutorFactory.create(strategy)
    AG ->> AG: executor.analyze(candles) → SignalConditionResult
    Note right of AG: Strategy는 포트폴리오를 모름<br>순수하게 BUY/SELL/HOLD 조건만 평가

    AG ->> DB: SELECT portfolio WHERE agent_id=agentIdentifier
    DB -->> AG: portfolio (cash, positions)

    AG ->> AG: AgentRiskManager.applySizing(<br>  condition, portfolio, riskConfig, currentPrice<br>) → SignalResult
    Note right of AG: Agent의 RiskConfig 기반으로<br>포지션 크기 결정

    AG ->> DB: INSERT signal (agentIdentifier, strategyIdentifier, ...) — BUY/SELL만
    AG ->> DB: UPDATE portfolio.reserved_cash (BUY 신호 점유)<br>UPDATE position.reserved_quantity (SELL 신호 점유)
    AG ->> DB: INSERT processed_events

    AG ->> Kafka: CommandBaseMessageEnvelope<AnalyzeAgentReply><br>topic: reply.virtual-trade.agent.analyze-strategy

    Kafka ->> VT: AnalyzeAgentReply { signalType, confidence,<br>suggestedQuantity, price, reason }
```

---

## 4. 백테스팅 — gRPC Server Streaming (Simulation)

```mermaid
sequenceDiagram
    participant SIM as Simulation Service
    participant AG  as Agent Service
    participant DB  as PostgreSQL

    SIM ->> AG: gRPC BacktestStrategy { agentIdentifier, symbolIdentifier, candles[] }
    Note right of SIM: 대용량 캔들 배열 전달 (수십만 건)

    AG ->> DB: SELECT agent WHERE id=agentIdentifier
    AG ->> DB: SELECT strategy WHERE id=agent.strategyIdentifier
    DB -->> AG: agent + strategy

    AG ->> AG: StrategyExecutorFactory.create(strategy)
    Note right of AG: initialCapital = agent.initialCapital<br>riskConfig = agent.riskConfig<br>인메모리 임시 포트폴리오로 백테스팅

    loop candles 슬라이딩 윈도우 순회
        AG ->> AG: executor.analyze(window) → SignalConditionResult
        AG ->> AG: AgentRiskManager.applySizing(condition, inMemoryPortfolio, riskConfig) → SignalResult
        AG ->> AG: inMemoryPortfolio 갱신 (포지션/현금 반영)
        AG -->> SIM: stream BacktestSignalResponse<br>{ signalType, confidence, reasonJson, candleOpenTime,<br>  suggestedQuantity, cashAfter, totalValueAfter }
    end

    AG ->> DB: INSERT backtest_result (집계 결과 저장)
    Note right of AG: 실제 Portfolio/PortfolioHistory에는 기록 안 함
    Note right of SIM: 스트리밍 완료 후 클라이언트는<br>GET /agents/{id}/backtests로 결과 상세 조회 가능
```

---

## 5. 에이전트 일시 중지 / 재개

```mermaid
sequenceDiagram
    actor User
    participant API   as Agent API
    participant Redis
    participant DB    as PostgreSQL

    User ->> API: PUT /agents/{id}/pause
    API  ->> DB:  UPDATE agent SET status=PAUSED
    API  ->> Redis: DEL agent:{agentIdentifier}
    API -->> User: 200 OK

    Note right of API: 이후 AnalyzeAgentCommand 수신 시<br>ACTIVE 검증 실패 → A006 에러 Reply 발행

    User ->> API: PUT /agents/{id}/resume
    API  ->> DB:  UPDATE agent SET status=ACTIVE
    API  ->> Redis: DEL agent:{agentIdentifier}
    API -->> User: 200 OK
```

---

## 6. 회원 탈퇴 처리 (UserWithdrawnEvent)

```mermaid
sequenceDiagram
    participant Kafka
    participant AG   as Agent Service
    participant Redis
    participant DB   as PostgreSQL

    Kafka ->> AG: trade-pilot.userservice.user<br>{ eventType: "user-withdrawn", userIdentifier }

    AG ->> AG: 멱등성 확인 (processed_events)

    AG ->> DB: SELECT agent WHERE user_id=userIdentifier<br>AND status != TERMINATED

    loop 각 agent
        AG ->> DB: UPDATE agent SET status=TERMINATED
        AG ->> Redis: DEL agent:{agentIdentifier}
    end

    Note right of AG: Strategy / Portfolio / Signal / Position<br>은 감사 목적으로 모두 보존

    AG ->> DB: INSERT processed_events
```
