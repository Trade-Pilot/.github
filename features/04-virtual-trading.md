# 가상 거래 (Virtual Trading)

> 💰 실시간 Paper Trading 기능

---

## 개요

### 목적
실제 자금을 사용하지 않고 가상의 자금으로 실시간 시장 데이터를 기반으로 거래를 실행하여 전략을 최종 검증합니다.

### 핵심 가치
- **실거래 전 최종 검증**: 백테스팅을 통과한 전략의 실시간 성과 확인
- **리스크 없는 테스트**: 실제 자금 손실 없이 전략 검증
- **리스크 관리 시스템 테스트**: 손절/익절, 한도 관리 등 실전 대비
- **실시간 모니터링**: 24/7 운영 및 성과 추적

### Simulation vs VirtualTrade
```
Simulation (백테스팅):
  - 과거 데이터 재생 (Time Travel)
  - 빠른 실행 (1개월 데이터를 1분에 처리)
  - 목적: 전략 검증

VirtualTrade (가상거래):
  - 실시간 데이터 사용
  - 실제 시간 소요 (1개월은 1개월)
  - 목적: 실거래 전 최종 검증
```

---

## 주요 기능

### 1. 가상 계좌 관리
```
기능: 가상 자금으로 거래하는 계좌 관리
상태: ACTIVE (활성), PAUSED (일시정지), STOPPED (중단)
```

**계좌 구성**:
- **초기 자본**: 시작 시 투입된 가상 자금
- **현금**: 현재 보유 현금
- **포지션**: 보유 중인 자산 목록
- **총 자산 가치**: 현금 + 포지션 가치
- **수익률**: (총 자산 - 초기 자본) / 초기 자본

### 2. 실시간 전략 실행
```
기능: 전략을 실시간으로 실행하여 신호 생성 및 주문
주기: 새로운 캔들 데이터 수신 시마다 (1분마다)
```

**실행 프로세스**:
```
1. Kafka로부터 실시간 캔들 데이터 수신
2. 활성 상태인 가상 계좌 조회
3. 각 계좌의 전략 실행
   3.1. 최근 캔들 데이터 조회
   3.2. 전략에 데이터 제공
   3.3. 신호 생성 (BUY/SELL/HOLD)
4. 신호에 따라 가상 주문 실행
   4.1. BUY 신호: 가상 매수 주문
   4.2. SELL 신호: 가상 매도 주문
   4.3. HOLD: 아무 행동도 하지 않음
5. 포트폴리오 업데이트
6. 리스크 체크 (손절/익절, 한도)
```

### 3. 가상 주문 체결
```
기능: 실제 주문과 동일하게 가상으로 체결
고려 사항: 현재 시장가, 수수료, 슬리피지
```

**주문 체결 시뮬레이션**:
```kotlin
fun executeVirtualOrder(order: VirtualOrder) {
    // 현재 시장가 조회
    val marketPrice = getCurrentMarketPrice(order.symbolIdentifier)

    // 슬리피지 적용
    val slippage = when (order.type) {
        OrderType.BUY -> marketPrice * 0.001  // 매수 시 +0.1%
        OrderType.SELL -> marketPrice * -0.001 // 매도 시 -0.1%
    }
    val executionPrice = marketPrice + slippage

    // 수수료 계산
    val totalAmount = order.quantity * executionPrice
    val fee = totalAmount * 0.0005 // 0.05%

    // 주문 체결
    order.fill(executionPrice, fee)

    // 포트폴리오 업데이트
    updatePortfolio(order, executionPrice, fee)

    // 거래 내역 기록
    recordTransaction(order, executionPrice, fee)
}
```

### 4. 리스크 관리 시스템

#### 손절/익절 자동 실행
```kotlin
data class StopLossTakeProfit(
    val positionId: UUID,
    val stopLossPrice: BigDecimal?,   // 손절가 (진입가 -5%)
    val takeProfitPrice: BigDecimal?  // 익절가 (진입가 +10%)
)

// 매 분마다 체크
fun checkStopLossTakeProfit() {
    positions.forEach { position ->
        val currentPrice = getCurrentPrice(position.symbolId)

        val stopLoss = position.averagePrice * BigDecimal("0.95")
        val takeProfit = position.averagePrice * BigDecimal("1.10")

        when {
            currentPrice <= stopLoss -> {
                // 손절 실행
                executeSellOrder(position, "STOP_LOSS")
            }
            currentPrice >= takeProfit -> {
                // 익절 실행
                executeSellOrder(position, "TAKE_PROFIT")
            }
        }
    }
}
```

#### 포지션 크기 관리
```kotlin
data class PositionSizingRule(
    val maxPositionSizePercent: BigDecimal = BigDecimal("20"), // 20%
    val maxNumberOfPositions: Int = 10
)

fun validatePositionSize(orderSize: BigDecimal): Boolean {
    val positionValue = orderSize * currentPrice
    val maxAllowed = account.totalValue * 0.2

    return positionValue <= maxAllowed &&
           account.positions.size < 10
}
```

#### 일일 손실 한도
```kotlin
data class DailyLossLimit(
    val maxDailyLossPercent: BigDecimal = BigDecimal("3"), // 3%
    val autoStopOnLimit: Boolean = true
)

fun checkDailyLossLimit() {
    val todayReturn = calculateTodayReturn()
    val lossPercent = abs(min(todayReturn, 0.0))

    if (lossPercent >= 3.0) {
        // 자동 거래 중단
        account.pause()
        sendSlackAlert("일일 손실 한도 도달: ${lossPercent}%")
    }
}
```

### 5. 알림 시스템

#### Slack 알림
```
이벤트:
  - 주문 체결 (매수/매도)
  - 손절/익절 실행
  - 손실 한도 도달
  - 전략 실행 오류
  - 일일 수익률 리포트
```

#### Email 알림
```
이벤트:
  - 일일 거래 리포트
  - 주간 성과 리포트
  - 월간 성과 리포트
```

### 6. 성과 모니터링
```
기능: 실시간 수익률 및 리스크 지표 추적
주기: 실시간 (1분마다 업데이트)
```

**모니터링 지표**:
- 실시간 수익률 (일/주/월)
- 현재 포지션 현황
- 미실현 손익
- 실현 손익
- MDD (최대 낙폭)
- 샤프 비율

---

## 개발 로드맵

### Phase 1: 기본 구조 (2주)
- [ ] Domain 모델
  - [ ] VirtualAccount
  - [ ] VirtualOrder
  - [ ] VirtualPosition
  - [ ] VirtualTransaction
  - [ ] VirtualBalance
- [ ] 데이터베이스 스키마

### Phase 2: 실시간 전략 실행 (2주)
- [ ] Kafka 실시간 캔들 데이터 수신
- [ ] 전략 시그널 생성
- [ ] 가상 주문 생성 및 체결
- [ ] 포지션 관리

### Phase 3: 리스크 관리 (2주)
- [ ] 손절/익절 자동 실행
- [ ] 포지션 크기 관리
- [ ] 일일 손실 한도
- [ ] 긴급 중단 시스템

### Phase 4: 알림 시스템 (1주)
- [ ] Slack 알림 구현
- [ ] Email 알림 구현
- [ ] 손실 한도 경고

### Phase 5: 성과 모니터링 (1주)
- [ ] 실시간 수익률 추적
- [ ] 일일/주간/월간 리포트
- [ ] 전략별 성과 비교

### Phase 6: API 및 Frontend (2주)
- [ ] REST API 구현
- [ ] 가상거래 대시보드
- [ ] 실시간 차트
- [ ] 알림 설정 UI

---

## 기술 설계

### API 엔드포인트

```http
POST /virtual-accounts
→ 가상 계좌 생성

GET /virtual-accounts
→ 가상 계좌 목록

GET /virtual-accounts/{accountId}
→ 계좌 상세 조회

PUT /virtual-accounts/{accountId}/start
→ 전략 실행 시작

PUT /virtual-accounts/{accountId}/pause
→ 전략 일시 중지

PUT /virtual-accounts/{accountId}/stop
→ 전략 중단

GET /virtual-accounts/{accountId}/orders
→ 주문 내역

GET /virtual-accounts/{accountId}/positions
→ 포지션 현황

GET /virtual-accounts/{accountId}/transactions
→ 거래 내역

GET /virtual-accounts/{accountId}/performance
→ 성과 조회
```

### 데이터베이스 스키마

```sql
CREATE TABLE virtual_account (
    identifier          UUID PRIMARY KEY,
    name                VARCHAR NOT NULL,
    strategy_identifier UUID NOT NULL,
    initial_capital     DECIMAL NOT NULL,
    cash                DECIMAL NOT NULL,
    total_value         DECIMAL NOT NULL,
    status              VARCHAR NOT NULL,
    created_date        TIMESTAMP WITH TIME ZONE
);

CREATE TABLE virtual_order (
    identifier         UUID PRIMARY KEY,
    account_identifier UUID NOT NULL,
    symbol_identifier  UUID NOT NULL,
    type               VARCHAR NOT NULL,
    order_quantity     DECIMAL NOT NULL,
    filled_quantity    DECIMAL NOT NULL,
    status             VARCHAR NOT NULL,
    created_at         TIMESTAMP WITH TIME ZONE,
    filled_at          TIMESTAMP WITH TIME ZONE
);

CREATE TABLE virtual_position (
    identifier         UUID PRIMARY KEY,
    account_identifier UUID NOT NULL,
    symbol_identifier  UUID NOT NULL,
    quantity           DECIMAL NOT NULL,
    average_price      DECIMAL NOT NULL,
    created_date       TIMESTAMP WITH TIME ZONE,
    modified_date      TIMESTAMP WITH TIME ZONE
);

CREATE TABLE virtual_transaction (
    identifier         UUID PRIMARY KEY,
    account_identifier UUID NOT NULL,
    order_identifier   UUID NOT NULL,
    symbol_identifier  UUID NOT NULL,
    time               TIMESTAMP WITH TIME ZONE,
    type               VARCHAR NOT NULL,
    quantity           DECIMAL NOT NULL,
    price              DECIMAL NOT NULL,
    fee                DECIMAL NOT NULL,
    total_amount       DECIMAL NOT NULL
);
```

---

## KPI 지표

### 가상거래 성과
| 지표 | 목표값 | 측정 주기 |
|------|--------|-----------|
| 월평균 수익률 | > 3% | 월 1회 |
| BTC 대비 초과 수익 | > +3% | 월 1회 |
| 최대 낙폭 (MDD) | < 15% | 실시간 |
| 샤프 비율 | > 1.5 | 월 1회 |
| 손실 한도 준수율 | 100% | 실시간 |

### 비즈니스 지표
| 지표 | 목표값 | 측정 주기 |
|------|--------|-----------|
| 전략당 평균 거래 횟수 | > 10회/월 | 월 1회 |
| 포지션 보유 기간 | 3~7일 | 거래별 |
| 자금 활용률 | 70~90% | 일 1회 |
| 평균 체결 시간 | < 1초 | 실시간 |

### 운영 지표
| 지표 | 목표값 | 측정 주기 |
|------|--------|-----------|
| 시스템 가동률 | > 99.9% | 월 1회 |
| 장애 복구 시간 | < 5분 | 장애별 |
| 알림 전송 성공률 | > 99% | 일 1회 |

---

## 리스크 관리

### 1. 전략 실패 리스크
**대응**:
- 연속 3회 손실 시 자동 일시 중지
- MDD 15% 초과 시 즉시 중단

### 2. 시장 급변 리스크
**대응**:
- 변동성 > 50% 시 자동 거래 중지
- 손절가 자동 설정 (진입가 -5%)

### 3. 시스템 장애 리스크
**대응**:
- Kubernetes 자동 재시작
- RTO < 5분

---

## 완료 조건

### 필수 조건
- ✅ 가상거래 시스템 24/7 안정 운영
- ✅ 최소 1개월 실시간 가상거래 성과
- ✅ 월평균 수익률 > 3%
- ✅ BTC 대비 초과 수익 > +3%
- ✅ MDD < 15%
- ✅ 리스크 관리 시스템 정상 작동

### 권장 조건
- ✅ Slack/Email 알림 시스템
- ✅ 실시간 대시보드
- ✅ 자동 리포트 생성

---

## 다음 단계

가상 거래 완료 후:
1. **[실거래](05-real-trading.md)** - 실제 거래 실행

---

## 참고 문서
- [데이터 수집](01-data-collection.md)
- [전략 구성](02-agent-strategy.md)
- [시뮬레이션](03-simulation.md)
- [KPI 측정 지표](../kpi-metrics.md)
- [리스크 관리 계획](../risk-management-plan.md)
