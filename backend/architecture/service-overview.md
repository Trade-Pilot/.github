# Trade Pilot — 서비스 구성, 보안, 성능/확장성

> 이 문서는 `backend/architecture.md`에서 분할되었습니다.

---

## 1. 서비스 구성

### 전체 구조도

```
┌───────────────────────────────────────────────────────────────────┐
│                    Frontend (React / FSD)                          │
└───────────────────────────────────────────────────────────────────┘
                              │ HTTPS
                              ▼
┌───────────────────────────────────────────────────────────────────┐
│              API Gateway  (JWT 검증 / 라우팅 / Rate Limit)           │
└───────────────────────────────────────────────────────────────────┘
                              │ HTTP (X-User-Id 헤더)
          ┌───────────────────┼───────────────────┐
          ▼                   ▼                   ▼
┌──────────────┐   ┌──────────────────┐   ┌──────────────────┐
│ User Service │   │ Market Service   │   │  Agent Service   │
└──────────────┘   └──────────────────┘   └──────────────────┘
          │              │  ▲  │                  ▲  ▲
          │         Kafka│  │  │ gRPC (캔들 조회)   │  │
          │              ▼  │  └──────────────────┘  │ gRPC
          │     ┌──────────────────┐                 │ (전략 실행)
          │     │ Exchange Service │       ┌──────────────────────┐
          │     └──────────────────┘       │  Simulation Service  │
          └────────────────────────────────┘       └──────────────────────┘
          │                                          │ gRPC
          │       ┌──────────────────────────────────┘
          │       │ (candle data — Market gRPC)
          │
          │   ┌──────────────────────┐
          │   │  VirtualTrade Service│ ◀── Market (Kafka: 실시간 이벤트)
          │   └──────────────────────┘ ◀── Agent  (Kafka: 전략 신호)
          │              │ Kafka (NOTIFICATION_COMMAND_TOPIC)
          │
          │   ┌──────────────────────┐
          │   │    Trade Service     │ ◀── Agent    (Kafka: 전략 신호)
          │   └──────────────────────┘ ──▶ Exchange (Kafka: 주문 실행)
          │              │ Kafka (NOTIFICATION_COMMAND_TOPIC)
          │              │
          │   ┌──────────┘
          │   │ Market   (Kafka: NOTIFICATION_COMMAND_TOPIC — 수집 오류 알림)
          │   │ User     (Kafka: USER_WITHDRAWN_EVENT_TOPIC)
          │   ▼
          └──▶┌──────────────────────┐
              │  Notification Service│
              └──────────────────────┘
```

**핵심 의존 관계:**

- `VirtualTrade`와 `Trade`는 **완전 독립** — 서로를 의존하지 않음
- `Trade → Exchange`: 실주문 실행은 Exchange Service가 거래소 API 어댑터 역할
- `Agent → Market`: 전략 신호 생성을 위한 캔들 데이터 조회 (gRPC)
- `Simulation → Market`: 백테스팅 대용량 캔들 조회 (gRPC)
- `Simulation → Agent`: 백테스팅 전략 실행 (gRPC, 기존 설계)

### 서비스 목록

| 서비스                  | 책임                      | 설계 상태           |
| -------------------- | ----------------------- | --------------- |
| API Gateway          | JWT 검증, 라우팅, Rate Limit | ✅ 설계 완료         |
| User Service         | 계정 관리, 인증, JWT 발급/갱신    | ✅ 설계 완료         |
| Exchange Service     | 거래소 API 어댑터, 계정 인증 정보 관리 | ✅ 설계 완료         |
| Market Service       | 심볼/캔들 수집·저장             | ✅ 설계 완료         |
| Agent Service        | 전략 관리, 신호 생성, 기술적 지표    | ✅ 설계 완료         |
| Simulation Service   | 백테스팅 (TimeTravelEngine) | ✅ 설계 완료         |
| VirtualTrade Service | 실시간 가상거래                | ✅ 설계 완료         |
| Trade Service        | 실제 거래 실행                | ✅ 설계 완료         |
| Notification Service | 알림 채널 관리, 메시지 발송        | ✅ 설계 완료         |

---

## 2. 보안 전략 (Security)

### 2.1 민감 정보 암호화 (Encryption at Rest)
거래소 API Key 등 민감 정보는 DB에 평문으로 저장하지 않는다.
- **알고리즘**: AES-256-GCM (Authenticated Encryption).
- **키 관리**: **AWS KMS** 또는 **HashiCorp Vault**를 사용하여 마스터 키를 관리한다.
- **범위**: `Exchange Service`의 계좌 Secret Key, `User Service`의 외부 연동 토큰 등.

### 2.2 gRPC 보안
- **mTLS (Mutual TLS)**: 서비스 간 gRPC 통신 시 상호 인증을 위해 mTLS를 적용한다.
- **Internal API Key**: mTLS 외에 추가로 `X-Internal-Secret` 헤더를 통해 사전에 정의된 서비스 키를 검증한다.

### 2.3 Kafka 보안
- **SASL/SCRAM**: Kafka 클러스터 접근 시 사용자 인증을 수행한다.
- **ACL (Access Control List)**: 각 서비스가 자신의 권한이 있는 토픽에만 Produce/Consume 하도록 제한한다.

---

## 3. 성능 및 확장성 전략 (Performance & Scalability)

### 3.1 수집 샤딩 (Worker Sharding)
- **Market Service**의 수집 부하 분산을 위해 `Consistency Hashing` 기반 샤딩을 적용한다.
- **샤딩 키**: `MarketSymbolId` (UUID).
- **분산 방식**: 각 수집 워커(Pod)는 자신이 담당할 해시 버킷을 인지하고, 해당 심볼의 스케줄만 실행한다.

### 3.2 다단계 캐싱 (Multi-level Caching)
- **L1 (Local Cache)**: 자주 조회되는 설정 정보 등은 Caffeine 사용 (TTL 1~5분).
- **L2 (Global Cache)**: Redis를 사용하여 캔들 데이터, 에이전트 상태 등 공유 캐싱.

### 3.3 WebSocket 통합 진입점 (Multiplexing)
프론트엔드의 커넥션 효율을 위해 개별 서비스가 아닌 **API Gateway를 단일 WebSocket 엔드포인트**로 사용한다.
*   **경로**: `wss://api.trade-pilot.com/ws`
*   **방식**: 사용자가 구독하고 싶은 주제(Topic)를 메시지로 전송하면, Gateway가 내부 서비스를 대리 구독하여 메시지를 통합 전달한다.
