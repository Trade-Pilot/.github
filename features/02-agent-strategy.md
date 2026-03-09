# 전략 구성 (Agent Strategy)

> 🤖 거래 전략 정의 및 신호 생성 기능

---

## 개요

### 목적
시장 데이터를 분석하여 매수/매도/관망 의사결정을 내리는 거래 전략을 구성하고 실행합니다.

### 핵심 가치
- **수동에서 AI로**: 기술적 지표 기반 수동 전략부터 시작하여 AI 전략으로 진화
- **전략 다양성**: 여러 전략을 조합하여 리스크 분산
- **검증 우선**: 모든 전략은 백테스팅 필수
- **투명성**: 신호 생성 이유를 명확히 기록

### Agent란?
시장 데이터를 분석하고 매수/매도 의사결정을 내리는 **자율적인 거래 주체**입니다.

```
Agent = Strategy + Portfolio Management + Signal Generation
```

---

## 주요 기능

### 1. 전략 정의
```
목적: 거래 전략 로직을 정의하고 관리
타입: MANUAL (수동), AI (강화학습)
```

**전략 생명 주기**:
```
DRAFT (작성 중)
  ↓
VALIDATED (백테스팅 통과)
  ↓
DEPLOYED (배포됨)
  ↓
PAUSED (일시 중지) ↔ DEPLOYED
  ↓
ARCHIVED (보관됨)
```

**전략 파라미터 예시** (이동평균 크로스오버):
```json
{
  "shortPeriod": 5,
  "longPeriod": 20,
  "entryCondition": "GOLDEN_CROSS",
  "exitCondition": "DEAD_CROSS"
}
```

### 2. 신호 생성
```
목적: 전략이 시장 분석 결과를 신호로 변환
타입: BUY (매수), SELL (매도), HOLD (관망)
```

**신호 구성**:
- **전략 식별자**: 어떤 전략이 생성했는지
- **심볼 식별자**: 거래 대상
- **시각**: 신호 생성 시점
- **타입**: BUY/SELL/HOLD
- **신뢰도**: 0.0 ~ 1.0 (전략의 확신 정도)
- **가격**: 신호 생성 시점 가격
- **이유**: 신호 생성 근거 (JSON)

**신호 이유 예시**:
```json
{
  "indicator": "MA_CROSSOVER",
  "shortMA": 51234.56,
  "longMA": 50123.45,
  "crossType": "GOLDEN_CROSS"
}
```

### 3. 포트폴리오 관리
```
목적: Agent가 보유한 자산 현황 관리
```

**포트폴리오 구성**:
- **초기 자본**: 시작 시 투입된 자금
- **현금**: 현재 보유 현금
- **포지션**: 보유 중인 자산 목록
- **총 자산 가치**: 현금 + 포지션 가치
- **수익률**: (총 자산 - 초기 자본) / 초기 자본

**포지션 관리**:
- 평균 단가 계산 (추가 매수 시)
- 미실현 손익 계산
- 실현 손익 추적

### 4. 기술적 지표 라이브러리
```
목적: 전략에서 사용할 수 있는 기술적 지표 제공
```

**지원 지표**:
- **MA (Moving Average)**: 이동평균
- **EMA (Exponential MA)**: 지수 이동평균
- **RSI (Relative Strength Index)**: 상대강도지수
- **MACD**: 이동평균 수렴/확산
- **Bollinger Bands**: 볼린저 밴드
- **Stochastic**: 스토캐스틱

---

## 개발 로드맵

### Phase 1: 기본 구조 (2주)
- [ ] Domain 모델 설계
  - [ ] Strategy (전략)
  - [ ] Signal (신호)
  - [ ] Portfolio (포트폴리오)
  - [ ] Position (포지션)
  - [ ] Trade (거래 내역)
- [ ] Strategy Interface 정의
- [ ] 데이터베이스 스키마

### Phase 2: 기술적 지표 라이브러리 (2주)
- [ ] MA (이동평균)
- [ ] EMA (지수 이동평균)
- [ ] RSI (상대강도지수)
- [ ] MACD
- [ ] Bollinger Bands
- [ ] Stochastic
- [ ] 지표 검증 테스트

### Phase 3: 수동 전략 구현 (3주)
- [ ] 전략 1: 이동평균 크로스오버
  - [ ] Golden Cross (매수)
  - [ ] Dead Cross (매도)
- [ ] 전략 2: RSI 과매수/과매도
  - [ ] RSI < 30 (매수)
  - [ ] RSI > 70 (매도)
- [ ] 전략 3: 볼린저 밴드 브레이크아웃
  - [ ] 하단 돌파 (매수)
  - [ ] 상단 돌파 (매도)
- [ ] 전략 조합 (앙상블)
  - [ ] 다수결 투표
  - [ ] 가중 평균

### Phase 4: 포트폴리오 관리 (2주)
- [ ] 포지션 진입/청산
- [ ] 평균 단가 계산
- [ ] 수익률 계산
- [ ] 거래 내역 기록
- [ ] 성과 분석

### Phase 5: API 구현 (1주)
- [ ] 전략 CRUD API
- [ ] 전략 파라미터 설정 API
- [ ] 신호 조회 API
- [ ] 포트폴리오 조회 API

---

## 기술 설계

### 전략 인터페이스
```kotlin
interface TradingStrategy {
    /**
     * 전략 식별자
     */
    val strategyIdentifier: UUID

    /**
     * 시장 데이터를 분석하여 신호를 생성합니다.
     */
    fun analyze(
        symbol: MarketSymbol,
        candles: List<MarketCandle>,
        portfolio: Portfolio
    ): Signal

    /**
     * 신호를 기반으로 주문 크기를 결정합니다.
     */
    fun calculateOrderSize(
        signal: Signal,
        portfolio: Portfolio,
        currentPrice: BigDecimal
    ): BigDecimal

    /**
     * 전략 파라미터를 반환합니다.
     */
    fun getParameters(): Map<String, Any>
}
```

### 수동 전략 예시: 이동평균 크로스오버
```kotlin
class MovingAverageCrossoverStrategy(
    override val strategyIdentifier: UUID,
    private val shortPeriod: Int = 5,
    private val longPeriod: Int = 20
) : TradingStrategy {

    override fun analyze(
        symbol: MarketSymbol,
        candles: List<MarketCandle>,
        portfolio: Portfolio
    ): Signal {
        require(candles.size >= longPeriod)

        val shortMA = calculateMA(candles, shortPeriod)
        val longMA = calculateMA(candles, longPeriod)

        val prevShortMA = calculateMA(candles.dropLast(1), shortPeriod)
        val prevLongMA = calculateMA(candles.dropLast(1), longPeriod)

        val currentPrice = candles.last().close

        return when {
            // Golden Cross: 매수
            prevShortMA <= prevLongMA && shortMA > longMA -> {
                Signal(
                    strategyIdentifier = strategyIdentifier,
                    symbolIdentifier = symbol.identifier,
                    time = candles.last().time,
                    type = SignalType.BUY,
                    confidence = 0.8,
                    price = currentPrice,
                    reason = mapOf(
                        "indicator" to "MA_CROSSOVER",
                        "shortMA" to shortMA,
                        "longMA" to longMA,
                        "crossType" to "GOLDEN_CROSS"
                    )
                )
            }
            // Dead Cross: 매도
            prevShortMA >= prevLongMA && shortMA < longMA -> {
                Signal(
                    strategyIdentifier = strategyIdentifier,
                    symbolIdentifier = symbol.identifier,
                    time = candles.last().time,
                    type = SignalType.SELL,
                    confidence = 0.8,
                    price = currentPrice,
                    reason = mapOf(
                        "indicator" to "MA_CROSSOVER",
                        "crossType" to "DEAD_CROSS"
                    )
                )
            }
            else -> {
                Signal(
                    strategyIdentifier = strategyIdentifier,
                    symbolIdentifier = symbol.identifier,
                    time = candles.last().time,
                    type = SignalType.HOLD,
                    confidence = 1.0,
                    price = currentPrice
                )
            }
        }
    }

    override fun calculateOrderSize(
        signal: Signal,
        portfolio: Portfolio,
        currentPrice: BigDecimal
    ): BigDecimal {
        return when (signal.type) {
            SignalType.BUY -> {
                // 보유 현금의 50% 사용
                val budget = portfolio.cash * BigDecimal("0.5")
                budget / currentPrice
            }
            SignalType.SELL -> {
                // 보유 수량의 100% 매도
                val position = portfolio.getPosition(signal.symbolIdentifier)
                position?.quantity ?: BigDecimal.ZERO
            }
            SignalType.HOLD -> BigDecimal.ZERO
        }
    }

    override fun getParameters(): Map<String, Any> {
        return mapOf(
            "shortPeriod" to shortPeriod,
            "longPeriod" to longPeriod
        )
    }
}
```

### API 엔드포인트

#### 전략 관리
```http
POST /strategies
→ 새로운 전략 생성

GET /strategies?status=VALIDATED&type=MANUAL
→ 전략 목록 조회 (필터, 정렬)

GET /strategies/{strategyId}
→ 전략 상세 조회

PUT /strategies/{strategyId}
→ 전략 수정

DELETE /strategies/{strategyId}
→ 전략 삭제

PUT /strategies/{strategyId}/validate
→ 백테스팅 통과 후 검증 상태로 변경

PUT /strategies/{strategyId}/deploy
→ 전략 배포

PUT /strategies/{strategyId}/pause
→ 전략 일시 중지
```

#### 신호 조회
```http
GET /strategies/{strategyId}/signals?from=2024-01-01&to=2024-12-31
→ 특정 전략이 생성한 신호 목록

GET /signals/{signalId}
→ 신호 상세 조회
```

#### 포트폴리오 조회
```http
GET /portfolios/{portfolioId}
→ 포트폴리오 조회

GET /portfolios/{portfolioId}/positions
→ 포지션 목록 조회

GET /portfolios/{portfolioId}/trades
→ 거래 내역 조회
```

### 데이터베이스 스키마

#### strategy
```sql
CREATE TABLE strategy (
    identifier    UUID PRIMARY KEY,
    name          VARCHAR NOT NULL,
    description   TEXT,
    type          VARCHAR NOT NULL,      -- MANUAL, AI
    market        VARCHAR NOT NULL,      -- COIN, STOCK
    status        VARCHAR NOT NULL,      -- DRAFT, VALIDATED, DEPLOYED
    parameters    JSONB,
    creator       UUID NOT NULL,
    created_date  TIMESTAMP WITH TIME ZONE,
    modified_date TIMESTAMP WITH TIME ZONE
);
```

#### portfolio
```sql
CREATE TABLE portfolio (
    identifier          UUID PRIMARY KEY,
    strategy_identifier UUID NOT NULL,
    initial_capital     DECIMAL NOT NULL,
    cash                DECIMAL NOT NULL,
    total_value         DECIMAL NOT NULL,
    created_date        TIMESTAMP WITH TIME ZONE,
    modified_date       TIMESTAMP WITH TIME ZONE
);
```

#### position
```sql
CREATE TABLE position (
    identifier           UUID PRIMARY KEY,
    portfolio_identifier UUID NOT NULL,
    symbol_identifier    UUID NOT NULL,
    quantity             DECIMAL NOT NULL,
    average_price        DECIMAL NOT NULL,
    created_date         TIMESTAMP WITH TIME ZONE,
    modified_date        TIMESTAMP WITH TIME ZONE,

    UNIQUE (portfolio_identifier, symbol_identifier)
);
```

#### trade
```sql
CREATE TABLE trade (
    identifier           UUID PRIMARY KEY,
    portfolio_identifier UUID NOT NULL,
    symbol_identifier    UUID NOT NULL,
    time                 TIMESTAMP WITH TIME ZONE,
    type                 VARCHAR NOT NULL,  -- BUY, SELL
    quantity             DECIMAL NOT NULL,
    price                DECIMAL NOT NULL,
    fee                  DECIMAL NOT NULL,
    total_amount         DECIMAL NOT NULL
);

CREATE INDEX trade_portfolio_idx ON trade (portfolio_identifier);
CREATE INDEX trade_time_idx ON trade (time);
```

---

## KPI 지표

### 전략 개발
| 지표 | 목표값 | 측정 주기 |
|------|--------|-----------|
| 검증된 전략 수 | > 3개 | Phase 완료 시 |
| 전략 다양성 | > 2개 타입 | Phase 완료 시 |
| 백테스팅 기간 | > 3개월 | 전략별 |

### 신호 품질
| 지표 | 목표값 | 측정 주기 |
|------|--------|-----------|
| 신호 생성 빈도 | 10~30회/월 | 전략별 |
| 신호 평균 신뢰도 | > 0.7 | 전략별 |
| 신호 정확도 | > 60% | 백테스팅 |

### 전략 성과
| 지표 | 목표값 | 측정 주기 |
|------|--------|-----------|
| 백테스팅 승률 | > 60% | 전략별 |
| 평균 손익비 | > 2.0 | 전략별 |
| 샤프 비율 | > 1.5 | 전략별 |
| 최대 낙폭 (MDD) | < 20% | 전략별 |

---

## 리스크 관리

### 1. 전략 과적합 리스크
**현상**: 백테스팅은 성공했으나 실제 성과가 나쁨

**예방**:
- Walk-Forward Analysis
- Out-Sample 검증 (30%)
- 파라미터 최적화 제한

**대응**:
- 가상거래 1개월 필수 검증
- 실패 시 전략 재조정
- 과적합 지표 모니터링

**목표**: 백테스팅 vs 실거래 성과 차이 < 20%

### 2. 전략 실패 리스크
**현상**: 연속 손실로 전략 신뢰도 하락

**예방**:
- 손절가 자동 설정
- 포지션 크기 제한
- 일일 손실 한도

**대응**:
```
경고 단계: 연속 2회 손실
  → 포지션 크기 50% 축소

위험 단계: 연속 3회 손실
  → 전략 자동 일시 중지

중단 단계: MDD 15% 초과
  → 전략 즉시 중단
```

**목표**: 전략 생존율 > 80% (3개월 기준)

### 3. 신호 과다 발생 리스크
**현상**: 전략이 너무 많은 신호를 생성 (과도한 매매)

**예방**:
- 신호 생성 빈도 제한 (월 10~30회)
- 최소 보유 기간 설정 (3일)
- 거래 수수료 고려

**대응**:
- 월 30회 초과 시 경고
- 수수료 손실 모니터링
- 전략 파라미터 재조정

**목표**: 월 거래 횟수 10~30회

---

## 완료 조건

### 필수 조건 (Must Have)
- ✅ 3개 이상 검증된 수동 전략 보유
- ✅ 기술적 지표 라이브러리 완성 (6개 이상)
- ✅ 전략 인터페이스 정의 완료
- ✅ 백테스팅 승률 > 60%
- ✅ 샤프 비율 > 1.5
- ✅ MDD < 20%
- ✅ 전략 CRUD API 구현

### 권장 조건 (Should Have)
- ✅ 전략 조합 (앙상블) 기능
- ✅ 신호 생성 이유 상세 기록
- ✅ 포트폴리오 성과 분석
- ✅ 전략 파라미터 최적화 기능

### 선택 조건 (Nice to Have)
- AI 전략 (강화학습) - Phase 5
- 뉴스 기반 전략
- 감성 분석 전략

---

## 성공 지표

### Phase 2 완료 시 (2개월)
- 검증된 전략 수: > 3개
- 백테스팅 데이터 기간: > 3개월
- 백테스팅 거래 횟수: > 100회 (전략별)
- 평균 승률: > 60%
- 평균 샤프 비율: > 1.5

### 전략 활용도
- Simulation Service에서 백테스팅에 활용
- VirtualTrade Service에서 가상거래에 활용
- Trade Service에서 실거래에 활용

---

## 다음 단계

전략 구성 완료 후:
1. **[시뮬레이션](03-simulation.md)** - 전략 백테스팅
2. **[가상 거래](04-virtual-trading.md)** - 실시간 가상거래
3. **[실거래](05-real-trading.md)** - 실제 거래 실행

---

## 참고 문서
- [데이터 수집](01-data-collection.md)
- [프로젝트 개요](../project-overview.md)
- [KPI 측정 지표](../kpi-metrics.md)
- [리스크 관리 계획](../risk-management-plan.md)
