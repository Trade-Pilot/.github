# 시뮬레이션 (Simulation)

> 📈 과거 데이터 기반 백테스팅 기능

---

## 개요

### 목적
과거 시장 데이터를 재생하여 전략의 성과를 검증하고, 실거래 전 리스크를 사전에 파악합니다.

### 핵심 가치
- **검증 우선**: 모든 전략은 시뮬레이션 필수
- **Time Travel**: 과거 데이터를 시간 순서대로 재생
- **성과 측정**: 수익률, MDD, 샤프 비율 등 정확한 지표 계산
- **최적화**: 파라미터 Grid Search 및 Walk-Forward Analysis

### Backtesting이란?
```
과거 데이터 → 전략 실행 → 성과 측정 → 리포트 생성
```

**목적**:
- 전략의 수익성 검증
- 리스크 분석
- 최적 파라미터 탐색
- 과적합 방지

---

## 주요 기능

### 1. 시뮬레이션 실행
```
기능: 특정 기간 동안 전략을 과거 데이터로 테스트
입력: 전략, 심볼, 기간, 초기 자본
출력: 성과 리포트, 거래 내역, 자산 변동 곡선
```

**시뮬레이션 상태**:
- `CREATED`: 생성됨 (실행 대기)
- `RUNNING`: 실행 중
- `COMPLETED`: 완료됨
- `FAILED`: 실패함

**진행률 추적**:
- 0~100% 실시간 진행률 표시
- 예상 완료 시간 계산
- **Server-Sent Events(SSE)로 프론트엔드에 실시간 스트리밍** — `GET /simulations/{id}/progress` 엔드포인트

### 2. Time Travel 엔진
```
기능: 과거 데이터를 시간 순서대로 재생
방법: 각 시점마다 전략에 "현재까지의 데이터"만 제공
```

**프로세스**:
```
1. 시간 범위 설정 (2024-01-01 ~ 2024-12-31)
2. 초기 포트폴리오 생성 (초기 자본: 1000만원)
3. 시간 순회 시작

for each time in timeRange:
    3.1. 현재 시점까지의 캔들 데이터 조회
    3.2. 전략에 데이터 제공
    3.3. 신호 생성 (BUY/SELL/HOLD)
    3.4. 신호에 따라 주문 실행 (가상)
    3.5. 포트폴리오 업데이트
    3.6. 스냅샷 저장 (자산 변동)
    3.7. 다음 시점으로 이동

4. 최종 성과 계산
5. 리포트 생성
```

### 3. 가상 주문 실행
```
기능: 실제 주문과 동일하게 시뮬레이션
고려 사항: 수수료, 슬리피지, 자금 부족
```

**매수 시뮬레이션**:
```kotlin
fun executeBuy(signal: Signal, portfolio: Portfolio) {
    // 슬리피지 적용 (매수 시 가격 상승)
    val slippage = signal.price * 0.001 // 0.1%
    val executionPrice = signal.price + slippage

    // 수수료 계산
    val orderSize = calculateOrderSize(signal, portfolio)
    val totalCost = orderSize * executionPrice
    val fee = totalCost * 0.0005 // 0.05%

    // 자금 확인
    if (portfolio.cash < totalCost + fee) {
        return // 주문 실패
    }

    // 포트폴리오 업데이트
    portfolio.buy(signal.symbolIdentifier, orderSize, executionPrice)
    portfolio.cash -= (totalCost + fee)

    // 거래 내역 기록
    recordTrade(BUY, orderSize, executionPrice, fee)
}
```

### 4. 성과 측정
```
기능: 다양한 지표로 전략 성과 평가
지표: 수익률, MDD, 샤프 비율, 승률, 손익비 등
```

**주요 지표**:

#### 총 수익률 (Total Return)
```kotlin
totalReturn = ((finalCapital - initialCapital) / initialCapital) * 100
```

#### 연환산 수익률 (Annualized Return)
```kotlin
val days = ChronoUnit.DAYS.between(startDate, endDate)
val years = days / 365.0
annualizedReturn = ((finalCapital / initialCapital).pow(1 / years) - 1) * 100
```

#### 최대 낙폭 (MDD, Maximum Drawdown)
```kotlin
var peak = initialCapital
var maxDrawdown = 0.0

equityCurve.forEach { equity ->
    if (equity > peak) peak = equity
    val drawdown = ((peak - equity) / peak) * 100
    if (drawdown > maxDrawdown) maxDrawdown = drawdown
}
```

#### 샤프 비율 (Sharpe Ratio)
```kotlin
val returns = calculateDailyReturns(equityCurve)
val avgReturn = returns.average()
val stdDev = calculateStdDev(returns)
val riskFreeRate = 0.02 / 365 // 연 2%

sharpeRatio = (avgReturn - riskFreeRate) / stdDev * sqrt(365)
```

#### 승률 (Win Rate)
```kotlin
winRate = (winningTrades / totalTrades) * 100
```

#### 손익비 (Profit/Loss Ratio)
```kotlin
val avgProfit = winningTrades.map { it.profit }.average()
val avgLoss = losingTrades.map { it.loss }.average()
profitLossRatio = avgProfit / avgLoss
```

### 5. 파라미터 최적화

#### Grid Search
```
목적: 모든 파라미터 조합을 체계적으로 탐색
방법: 각 파라미터의 가능한 값들의 조합을 모두 시도
```

**예시**:
```kotlin
val parameterGrid = mapOf(
    "shortPeriod" to listOf(3, 5, 7, 10),
    "longPeriod" to listOf(15, 20, 25, 30)
)
// 총 4 × 4 = 16가지 조합

// 각 조합마다 백테스팅 실행
// 최고 샤프 비율을 가진 조합 선택
```

#### Walk-Forward Analysis
```
목적: 과적합 방지
방법: In-Sample(최적화) / Out-Sample(검증) 분할
```

**프로세스**:
```
전체 기간: 12개월
윈도우: 5개

Window 1:
  In-Sample (70%): 1월~2월 → 최적 파라미터 탐색
  Out-Sample (30%): 3월 → 성과 검증

Window 2:
  In-Sample: 3월~5월 → 최적 파라미터 탐색
  Out-Sample: 6월 → 성과 검증

...

최종 평가: Out-Sample 평균 성과
```

---

## 개발 로드맵

### Phase 1: 기본 구조 (2주)
- [ ] Domain 모델
  - [ ] Simulation
  - [ ] SimulationConfig
  - [ ] SimulationResult
  - [ ] SimulationTrade
  - [ ] SimulationSnapshot
- [ ] 데이터베이스 스키마

### Phase 2: Time Travel 엔진 (3주)
- [ ] 과거 데이터 재생 엔진
- [ ] 가상 주문 실행
- [ ] 수수료 시뮬레이션 (0.05%)
- [ ] 슬리피지 시뮬레이션 (0.1%)
- [ ] 포트폴리오 관리
- [ ] 진행률 추적 (SSE 스트리밍 포함)

### Phase 3: 성과 측정 (2주)
- [ ] 수익률 계산
- [ ] MDD 계산
- [ ] 샤프 비율 계산
- [ ] 소티노 비율 계산
- [ ] 승률/손익비 계산
- [ ] 평균 보유 기간 계산

### Phase 4: 최적화 시스템 (2주)
- [ ] Grid Search
- [ ] Walk-Forward Analysis
- [ ] 병렬 시뮬레이션 실행
- [ ] 최적 파라미터 추천

### Phase 5: 리포트 생성 (1주)
- [ ] 거래 내역 타임라인
- [ ] 자산 변동 차트
- [ ] 성과 지표 요약
- [ ] PDF 리포트 생성

### Phase 6: API 구현 (1주)
- [ ] 시뮬레이션 CRUD
- [ ] 시뮬레이션 시작/중지
- [ ] 결과 조회
- [ ] 리포트 다운로드

---

## 기술 설계

### API 엔드포인트

```http
POST /simulations
→ 시뮬레이션 생성

POST /simulations/{simulationId}/start
→ 시뮬레이션 시작

GET /simulations/{simulationId}
→ 시뮬레이션 상태 및 결과 조회

GET /simulations
→ 시뮬레이션 목록 조회

GET /simulations/{simulationId}/trades
→ 거래 내역 조회

GET /simulations/{simulationId}/snapshots
→ 자산 변동 스냅샷 조회

GET /simulations/{simulationId}/progress
→ 시뮬레이션 진행률 SSE 스트리밍 (Accept: text/event-stream)
  응답 형식:
    data: {"simulationId": "uuid", "progress": 42, "status": "RUNNING", "processedCandles": 210000, "totalCandles": 500000}
    data: {"simulationId": "uuid", "progress": 100, "status": "COMPLETED", "result": {...}}

GET /simulations/{simulationId}/report.pdf
→ 리포트 다운로드

POST /optimizations/grid-search
→ Grid Search 최적화 실행

POST /optimizations/walk-forward
→ Walk-Forward Analysis 실행
```

### 데이터베이스 스키마

#### simulation
```sql
CREATE TABLE simulation (
    identifier          UUID PRIMARY KEY,
    name                VARCHAR NOT NULL,
    strategy_identifier UUID NOT NULL,
    start_date          TIMESTAMP WITH TIME ZONE,
    end_date            TIMESTAMP WITH TIME ZONE,
    initial_capital     DECIMAL NOT NULL,
    status              VARCHAR NOT NULL,
    progress            INT DEFAULT 0,
    created_date        TIMESTAMP WITH TIME ZONE,
    started_at          TIMESTAMP WITH TIME ZONE,
    completed_at        TIMESTAMP WITH TIME ZONE
);
```

#### simulation_result
```sql
CREATE TABLE simulation_result (
    simulation_identifier UUID PRIMARY KEY,
    final_capital         DECIMAL,
    total_return          DECIMAL,
    annualized_return     DECIMAL,
    max_drawdown          DECIMAL,
    sharpe_ratio          DECIMAL,
    sortino_ratio         DECIMAL,
    win_rate              DECIMAL,
    profit_loss_ratio     DECIMAL,
    total_trades          INT,
    winning_trades        INT,
    losing_trades         INT
);
```

---

## KPI 지표

### 백테스팅 성과
| 지표 | 목표값 | 측정 기준 |
|------|--------|-----------|
| 시뮬레이션 승률 | > 60% | 전략별 |
| 평균 손익비 | > 2.0 | 전략별 |
| 샤프 비율 | > 1.5 | 전략별 |
| 최대 낙폭 (MDD) | < 20% | 전략별 |

### 시스템 성능
| 지표 | 목표값 | 측정 주기 |
|------|--------|-----------|
| 시뮬레이션 실행 시간 | < 1분/월 | 실행별 |
| 병렬 시뮬레이션 처리 | > 10개 동시 | 시스템 |
| 리포트 생성 시간 | < 10초 | 리포트별 |

---

## 리스크 관리

### 1. 과적합 리스크
**예방**: Walk-Forward Analysis, Out-Sample 30%
**대응**: 실거래 전 가상거래 1개월 필수 검증

### 2. 데이터 품질 리스크
**예방**: Flat Candle 비율 < 5% 확인
**대응**: 데이터 품질 불량 시 시뮬레이션 중단

### 3. 계산 오류 리스크
**예방**: 단위 테스트, 수동 검증
**대응**: 이상 결과 감지 시 알림

---

## 완료 조건

### 필수 조건
- ✅ Time Travel 엔진 정상 작동
- ✅ 3개 이상 전략 백테스팅 승률 > 60%
- ✅ 샤프 비율 > 1.5
- ✅ MDD < 20%
- ✅ 3개월 이상 과거 데이터 백테스팅
- ✅ 성과 리포트 자동 생성

### 권장 조건
- ✅ Grid Search 최적화 기능
- ✅ Walk-Forward Analysis
- ✅ 병렬 시뮬레이션 실행
- ✅ PDF 리포트 생성

---

## 다음 단계

시뮬레이션 완료 후:
1. **[가상 거래](04-virtual-trading.md)** - 실시간 가상거래 검증
2. **[실거래](05-real-trading.md)** - 실제 거래 실행

---

## 참고 문서
- [데이터 수집](01-data-collection.md)
- [전략 구성](02-agent-strategy.md)
- [KPI 측정 지표](../kpi-metrics.md)
- [리스크 관리 계획](../risk-management-plan.md)
