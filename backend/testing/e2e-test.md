# E2E 테스트

> 원본: `backend/testing-strategy.md` Section 4

---

## 4. E2E 테스트

### 4.1 주요 시나리오

#### 시나리오 1: 가상거래 전체 흐름

```
회원가입 → 로그인 → 전략 생성(MA Crossover)
→ 에이전트 생성 → 에이전트 활성화(Portfolio 초기화)
→ 가상거래 등록 → 스케줄러 트리거(AnalyzeAgentCommand 발행)
→ Agent Service 신호 생성(BUY) → VirtualTrade Service 가상 체결
→ Portfolio 갱신(cash 차감, Position 생성) 확인
```

#### 시나리오 2: 회원 탈퇴 — Eventually Consistent 데이터 정리

```
회원 탈퇴 요청 → User.status == WITHDRAWN
→ UserWithdrawnEvent Kafka 발행
→ 각 서비스 Consumer 수신:
  - Agent Service: 해당 유저의 ACTIVE Agent → TERMINATED
  - Trade Service: ACTIVE Registration → STOPPED, 미체결 주문 취소
  - VirtualTrade Service: ACTIVE VirtualTrade → STOPPED
  - Notification Service: 알림 채널/설정 soft delete
→ 최종 확인: 모든 서비스에서 해당 유저 리소스 비활성화
```

#### 시나리오 3: 비상 정지

```
실거래 중 비상 정지 요청
→ TradeRegistration.emergencyStopped = true, status = PAUSED
→ 미체결 주문(SUBMITTED, PARTIALLY_FILLED) 취소 요청 발행
→ Exchange Service 취소 처리 → OrderStatusEvent(CANCELLED) 수신
→ 포트폴리오 점유 해제 확인 (reservedCash, reservedQuantity 복원)
```

### 4.2 구성

```yaml
# docker-compose.e2e.yml
services:
  postgres:
    image: postgres:16-alpine
  kafka:
    image: confluentinc/cp-kafka:7.6.0
  redis:
    image: redis:7-alpine
  user-service:
    build: ./user-service
  exchange-service:
    build: ./exchange-service
  market-service:
    build: ./market-service
  agent-service:
    build: ./agent-service
  virtual-trade-service:
    build: ./virtual-trade-service
  trade-service:
    build: ./trade-service
  notification-service:
    build: ./notification-service
```

- **REST Assured**: API 호출 및 응답 검증
- **Awaitility**: 비동기 이벤트 처리 대기 (Kafka 이벤트 전파, Eventually Consistent 상태 수렴)

```kotlin
@Test
fun `E2E_가상거래전체흐름`() {
    // Given: 회원가입 + 로그인 (JWT 발급)
    val token = signUpAndSignIn()

    // When: 전략 → 에이전트 → 가상거래 등록
    val strategyId = createStrategy(token, maCrossoverParams)
    val agentId = createAndActivateAgent(token, strategyId)
    val virtualTradeId = registerVirtualTrade(token, agentId)

    // Then: 신호 생성 및 가상 체결 대기 (최대 60초)
    await().atMost(60, SECONDS).untilAsserted {
        val portfolio = getPortfolio(token, agentId)
        assertThat(portfolio.positions).isNotEmpty()
    }
}
```
