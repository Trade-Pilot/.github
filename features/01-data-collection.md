# 데이터 수집 (Data Collection)

> 📊 시장 데이터 수집 및 관리 기능

---

## 개요

### 목적
안정적이고 품질 높은 시장 데이터를 수집하여 전략 분석 및 거래 의사결정의 기반을 제공합니다.

### 핵심 가치
- **데이터 우선**: 충분한 데이터 없이는 어떤 전략도 시작하지 않음
- **품질 관리**: Flat Candle 자동 생성으로 누락 구간 보정
- **실시간 수집**: 1분봉 기준 실시간 데이터 수집
- **다양한 간격**: 12개 시간 간격 지원 (1분 ~ 월봉)

### 담당 서비스
- **Market Service**: 시장 데이터 수집 및 저장
- **Exchange Service**: 거래소 API 연동

---

## 주요 기능

### 1. 심볼 관리
```
기능: 거래 가능한 심볼 자동 수집 및 상태 추적
주기: 매일 09:00 (KST)
대상: 업비트 KRW 마켓
```

**심볼 상태**:
- `LISTED`: 정상 거래 가능
- `WARNING`: 경고
- `CAUTION`: 주의
- `TRADING_HALTED`: 거래 중지
- `DELISTED`: 상장 폐지

**자동화**:
- 신규 심볼 감지 시 자동 수집 작업 생성
- 상장 폐지 시 수집 작업 자동 비활성화

### 2. 캔들 데이터 수집
```
기능: 1분봉 캔들 데이터 실시간 수집
주기: 매 분 0초
간격: MIN_1 (기준), MIN_3, MIN_5, MIN_10, MIN_15, MIN_30,
      MIN_60, MIN_120, MIN_180, DAY, WEEK, MONTH
```

**수집 프로세스**:
1. 수집 가능한 작업 조회 (PESSIMISTIC_WRITE Lock)
2. 상태를 `COLLECTING`으로 변경
3. Exchange Service에 데이터 요청 (Kafka)
4. 응답 수신 및 검증
5. Flat Candle 생성 (누락 구간)
6. 데이터베이스 저장 (파티션 테이블)
7. 상태를 `COLLECTED`로 변경
8. 다른 간격 캔들 자동 계산

### 3. 데이터 품질 관리

**Flat Candle**:
```
목적: 데이터 누락 구간 자동 보정
방법: 이전 종가로 OHLC 채움
     - Open = High = Low = Close = 이전 종가
     - Volume = Amount = 0
```

**간격 계산**:
```
MIN_1 (외부 수집)
├─ MIN_3 ← MIN_1 (3개 결합)
│  ├─ MIN_10 ← MIN_3 (3개 결합) + MIN_1 (1개)
│  └─ MIN_15 ← MIN_3 (5개 결합)
├─ MIN_5 ← MIN_1 (5개 결합)
│  └─ MIN_30 ← MIN_5 (6개 결합)
│     └─ MIN_60 ← MIN_30 (2개 결합)
│        ├─ MIN_120 ← MIN_60 (2개 결합)
│        └─ MIN_180 ← MIN_60 (3개 결합)
│           └─ DAY ← MIN_180 (8개 결합)
│              ├─ WEEK ← DAY (7개 결합)
│              └─ MONTH ← DAY (월별 전체 결합)
```

### 4. 파티션 관리
```
목적: 대용량 시계열 데이터 효율적 관리
방법: PostgreSQL 월별 파티션
주기: 매월 1일 00:00 자동 생성
```

---

## 개발 로드맵

### Phase 1: 기본 구조 (2주)
- [x] Hexagonal Architecture 구조 설계
- [x] 도메인 모델 구현
  - [x] MarketSymbol
  - [x] MarketCandleCollectTask
  - [x] MarketCandle
- [x] PostgreSQL 스키마 설계
- [x] 파티션 테이블 구성

### Phase 2: 거래소 연동 (2주)
- [ ] 업비트 API 연동
- [ ] 심볼 목록 조회 기능
- [ ] 캔들 데이터 조회 기능
- [ ] Rate Limiting 처리 (초당 10개, 분당 600개)
- [ ] Exponential Backoff 재시도
- [ ] Circuit Breaker 패턴

### Phase 3: 데이터 수집 자동화 (3주)
- [ ] 심볼 수집 스케줄러 (일 1회)
- [ ] 캔들 수집 스케줄러 (분 1회)
- [ ] Kafka 메시징 구성
- [ ] 수집 작업 상태 관리
- [ ] Flat Candle 생성 로직
- [ ] 동시성 제어 (PESSIMISTIC_WRITE Lock)

### Phase 4: 데이터 가공 (2주)
- [ ] 간격별 캔들 계산 로직
- [ ] 파티션 자동 생성 스케줄러
- [ ] 데이터 검증 로직
  - [ ] High >= Low 체크
  - [ ] 가격 급등락 감지 (±30%)
- [ ] 수집 현황 모니터링 API

### Phase 5: Frontend 대시보드 (2주)
- [ ] 수집 현황 조회 화면
- [ ] 수집 작업 제어 (시작/중지)
- [ ] 캔들 차트 뷰어 (TradingView)
- [ ] 실시간 업데이트 (WebSocket)

### Phase 6: 인프라 구축 (3주)
- [ ] PostgreSQL HA 구성
- [ ] Kafka 클러스터 구성
- [ ] Monitoring Stack
  - [ ] Prometheus 메트릭
  - [ ] Grafana 대시보드
  - [ ] 알람 설정

---

## 기술 설계

### 아키텍처
```
Hexagonal Architecture (Ports & Adapters)

├─ domain/              # 도메인 모델
│  ├─ MarketSymbol
│  ├─ MarketCandleCollectTask
│  └─ MarketCandle
│
├─ application/         # 애플리케이션 서비스
│  ├─ port/
│  │  ├─ input/        # Use Cases
│  │  └─ output/       # Output Ports
│  └─ service/         # 비즈니스 로직
│
└─ adapter/            # 어댑터
   ├─ input/           # Inbound
   │  ├─ web/          # REST API
   │  ├─ batch/        # Scheduler
   │  └─ event/        # Event Listener
   └─ output/          # Outbound
      ├─ persistence/  # Database
      └─ message/      # Kafka
```

### 기술 스택
- **Backend**: Kotlin 2.0.21, Spring Boot 3.4.0
- **Database**: PostgreSQL (파티션 테이블)
- **Messaging**: Apache Kafka
- **ORM**: JPA, QueryDSL
- **동시성**: Virtual Threads (Kafka Concurrency 1000)

### API 엔드포인트

#### 심볼 관리
```http
GET /market-symbols?markets=COIN
→ 시장 타입별 심볼 목록 조회
```

#### 수집 작업 관리
```http
GET /market-candle-collect-task-status
→ 수집 작업 상태별 통계

GET /market-candle-collect-tasks?keyword=BTC&statuses=COLLECTED
→ 수집 작업 목록 조회 (검색, 필터, 페이징)

PUT /market-candle-collect-tasks/resume-all
→ 모든 수집 작업 재시작

PUT /market-candle-collect-tasks/pause-all
→ 모든 수집 작업 일시정지

PUT /market-candle-collect-task/{taskId}/resume
→ 특정 수집 작업 재시작

PUT /market-candle-collect-task/{taskId}/pause
→ 특정 수집 작업 일시정지
```

#### 캔들 데이터 조회
```http
GET /symbols/{symbolId}/intervals/{interval}/market-candles
  ?orderBy=DESC&cursor=2024-01-01T00:00:00Z&limit=100
→ 특정 심볼의 캔들 데이터 조회

GET /market-candles/search
→ 쿼리 기반 캔들 데이터 검색
```

### 데이터베이스 스키마

#### market_symbol
```sql
CREATE TABLE market_symbol (
    identifier    UUID PRIMARY KEY,
    code          VARCHAR NOT NULL,           -- KRW-BTC
    name          VARCHAR NOT NULL,           -- 비트코인
    market        VARCHAR NOT NULL,           -- COIN
    status        VARCHAR NOT NULL,           -- LISTED
    created_date  TIMESTAMP WITH TIME ZONE,
    modified_date TIMESTAMP WITH TIME ZONE
);
```

#### market_candle_collect_task
```sql
CREATE TABLE market_candle_collect_task (
    identifier           UUID PRIMARY KEY,
    symbol_identifier    UUID NOT NULL,
    interval             VARCHAR NOT NULL,   -- MIN_1
    created_date         TIMESTAMP WITH TIME ZONE,
    last_collected_time  TIMESTAMP WITH TIME ZONE,
    last_collected_price DECIMAL,
    status               VARCHAR NOT NULL    -- COLLECTED
);

CREATE INDEX collect_task_idx
    ON market_candle_collect_task (symbol_identifier, interval);
```

#### market_candle (파티션 테이블)
```sql
CREATE TABLE market_candle (
    symbol_identifier UUID NOT NULL,
    interval          VARCHAR NOT NULL,
    time              TIMESTAMP WITH TIME ZONE NOT NULL,
    open              DECIMAL NOT NULL,
    high              DECIMAL NOT NULL,
    low               DECIMAL NOT NULL,
    close             DECIMAL NOT NULL,
    volume            DECIMAL NOT NULL,
    amount            DECIMAL NOT NULL,
    PRIMARY KEY (symbol_identifier, interval, time)
) PARTITION BY RANGE (time);

-- 월별 파티션 자동 생성
CREATE TABLE market_candle_2024_01
    PARTITION OF market_candle
    FOR VALUES FROM ('2024-01-01') TO ('2024-02-01');
```

### Kafka 메시징

#### 심볼 수집
```yaml
Command Topic: FIND_ALL_MARKET_SYMBOL_COMMAND_TOPIC
  Producer: Market Service
  Consumer: Exchange Service
  Message:
    - market: COIN
    - requestId: UUID

Reply Topic: FIND_ALL_MARKET_SYMBOL_REPLY_TOPIC
  Producer: Exchange Service
  Consumer: Market Service
  Message:
    - requestId: UUID
    - symbols: List<SymbolDto>
```

#### 캔들 수집
```yaml
Command Topic: FIND_ALL_MARKET_CANDLE_COMMAND_TOPIC
  Producer: Market Service
  Consumer: Exchange Service
  Message:
    - symbolCode: KRW-BTC
    - interval: MIN_1
    - count: 200
    - requestId: UUID

Reply Topic (Success): FIND_ALL_MARKET_CANDLE_REPLY_TOPIC
  Message:
    - requestId: UUID
    - candles: List<CandleDto>

Reply Topic (Failure): FIND_ALL_MARKET_CANDLE_REPLY_FAILURE_TOPIC
  Message:
    - requestId: UUID
    - errorMessage: String
```

---

## KPI 지표

### 시스템 안정성
| 지표 | 목표값 | 측정 주기 |
|------|--------|-----------|
| 데이터 수집 성공률 | > 99.9% | 일 1회 |
| 캔들 수집 지연 시간 | < 10초 | 실시간 |
| API 응답 시간 (p95) | < 100ms | 시간당 |
| 시스템 가동률 | > 99.5% | 월 1회 |

### 데이터 품질
| 지표 | 목표값 | 측정 주기 |
|------|--------|-----------|
| Flat Candle 비율 | < 5% | 일 1회 |
| 파티션 테이블 크기 | < 100GB/월 | 월 1회 |
| 심볼 커버리지 | > 95% | 일 1회 |
| 데이터 검증 실패율 | < 0.1% | 일 1회 |

### API 성능
| 지표 | 목표값 | 측정 주기 |
|------|--------|-----------|
| API 호출 성공률 | > 99.5% | 일 1회 |
| 평균 응답 시간 | < 200ms | 시간당 |
| Circuit Breaker 발동 | < 1회/월 | 월 1회 |

---

## 리스크 관리

### 1. 데이터 누락 리스크
**현상**: 거래소 API 장애, 네트워크 오류로 인한 데이터 누락

**예방**:
- Flat Candle 자동 생성
- 수집 작업 재시도 (최대 3회)
- 수집 상태 모니터링

**대응**:
- 누락 구간 감지 시 Flat Candle로 즉시 보정
- 거래소 API 복구 후 자동 재수집
- 연속 10개 이상 누락 시 알람

**목표**: Flat Candle 비율 < 5%

### 2. 거래소 API 장애
**현상**: 업비트 API 다운, Rate Limit 초과, 응답 지연

**예방**:
- Rate Limiting 준수 (초당 10개, 분당 600개)
- Exponential Backoff 재시도
- Circuit Breaker 패턴

**대응**:
```
1. 일시적 장애 (1~5분)
   - 자동 재시도 (1초 → 2초 → 4초)
   - Circuit Breaker Open
   - 수집 작업 일시 중단

2. 장기 장애 (5분 이상)
   - Slack 긴급 알림
   - 모든 수집 작업 PAUSED
   - 수동 재개 대기

3. Rate Limit 초과
   - 다음 윈도우까지 대기
   - 요청 빈도 자동 조절
```

**목표**: API 호출 성공률 > 99.5%

### 3. 시스템 장애
**현상**: 서버 다운, 데이터베이스 장애

**예방**:
- PostgreSQL HA 구성
- Kubernetes 자동 재시작
- Liveness/Readiness Probe

**대응**:
- RTO (Recovery Time Objective): < 5분
- RPO (Recovery Point Objective): < 1분
- 자동 복구 후 누락 구간 재수집

**목표**: 시스템 가동률 > 99.5%

### 4. 데이터 품질 문제
**현상**: 잘못된 가격 데이터, 급등락 오류

**예방**:
- 데이터 검증 로직
  - High >= Low
  - High >= Open, Close
  - Low <= Open, Close
- 급등락 감지 (±30%)

**대응**:
- 검증 실패 시 저장 거부
- Flat Candle로 대체
- Slack 알림 (수동 확인)

**목표**: 데이터 검증 실패율 < 0.1%

---

## 완료 조건

### 필수 조건 (Must Have)
- ✅ 100개 이상 코인 심볼 자동 수집
- ✅ 1분봉 데이터 실시간 수집 (성공률 > 99.9%)
- ✅ 12개 간격 캔들 자동 생성
- ✅ Flat Candle 자동 보정 (비율 < 5%)
- ✅ 수집 현황 대시보드 운영
- ✅ 최소 3개월 과거 데이터 축적

### 권장 조건 (Should Have)
- ✅ API 응답 시간 < 100ms (p95)
- ✅ 파티션 자동 생성
- ✅ Circuit Breaker 정상 작동
- ✅ 실시간 모니터링 (Grafana)

### 선택 조건 (Nice to Have)
- WebSocket 실시간 스트리밍
- 다중 거래소 지원 (바이낸스, 코인원)
- 데이터 백업 자동화

---

## 성공 지표

### Phase 1 완료 시 (3개월)
- 심볼 수: > 100개
- 누적 캔들 수: > 500만개 (100심볼 × 3개월 × 12간격)
- 데이터 수집 성공률: > 99.9%
- Flat Candle 비율: < 5%
- 시스템 가동률: > 99.5%

### 데이터 활용도
- Agent Service에서 전략 분석에 활용
- Simulation Service에서 백테스팅에 활용
- Frontend에서 차트 시각화에 활용

---

## 다음 단계

데이터 수집 완료 후:
1. **[전략 구성](02-agent-strategy.md)** - 수집된 데이터로 전략 개발
2. **[시뮬레이션](03-simulation.md)** - 과거 데이터로 백테스팅
3. **[가상 거래](04-virtual-trading.md)** - 실시간 데이터로 가상거래
4. **[실거래](05-real-trading.md)** - 실제 거래 실행

---

## 참고 문서
- [프로젝트 개요](../project-overview.md)
- [개발 로드맵](../development-roadmap.md)
- [KPI 측정 지표](../kpi-metrics.md)
- [리스크 관리 계획](../risk-management-plan.md)
