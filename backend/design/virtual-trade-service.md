# VirtualTrade Service 설계

## 개요

VirtualTrade Service는 실시간으로 가상거래를 실행하는 Paper Trading 시스템입니다.

- **언어**: Kotlin 2.0.21
- **프레임워크**: Spring Boot 3.4.0
- **아키텍처**: Hexagonal Architecture (Ports & Adapters)
- **데이터베이스**: PostgreSQL
- **메시징**: Apache Kafka

## 핵심 개념

### Paper Trading이란?
실제 자금을 사용하지 않고 가상의 자금으로 실시간 시장 데이터를 기반으로 거래를 실행하는 시스템입니다.

**Simulation과의 차이**:
- **Simulation**: 과거 데이터 재생 (Time Travel)
- **VirtualTrade**: 실시간 데이터 사용 (Real-time)

**목적**:
- 실거래 전 최종 검증
- 전략의 실시간 성과 확인
- 리스크 관리 시스템 테스트

---

## 도메인 정의

### VirtualAccount (가상 계좌)

가상으로 관리되는 거래 계좌를 나타내는 도메인 객체입니다.

| **프로퍼티 (한글)** | **프로퍼티 (영문)**  | **개념**                                     | **필수** | **불변** |
|:--------------------|:---------------------|:--------------------------------------------|:---------|:---------|
| 식별자              | identifier           | 가상 계좌 식별자                             | O        | O        |
| 이름                | name                 | 가상 계좌 이름                               | O        | X        |
| 전략식별자          | strategy_identifier  | 연결된 전략의 식별자                         | O        | O        |
| 초기자본            | initial_capital      | 시작 자본                                    | O        | O        |
| 현금                | cash                 | 보유 현금                                    | O        | X        |
| 총자산가치          | total_value          | 총 자산 가치                                 | O        | X        |
| 상태                | status               | 계좌 상태 (ACTIVE, PAUSED, STOPPED)          | O        | X        |
| 생성일              | created_date         | 계좌 생성일                                  | O        | O        |

---

### VirtualOrder (가상 주문)

가상으로 실행되는 주문을 나타내는 도메인 객체입니다.

| **프로퍼티 (한글)** | **프로퍼티 (영문)**  | **개념**                                     | **필수** | **불변** |
|:--------------------|:---------------------|:--------------------------------------------|:---------|:---------|
| 식별자              | identifier           | 주문 식별자                                  | O        | O        |
| 계좌식별자          | account_identifier   | 주문이 속한 계좌의 식별자                    | O        | O        |
| 심볼식별자          | symbol_identifier    | 주문 대상 심볼의 식별자                      | O        | O        |
| 타입                | type                 | 주문 타입 (BUY, SELL)                        | O        | O        |
| 주문가격            | order_price          | 주문 가격 (지정가 주문 시)                   | X        | O        |
| 주문수량            | order_quantity       | 주문 수량                                    | O        | O        |
| 체결수량            | filled_quantity      | 체결된 수량                                  | O        | X        |
| 상태                | status               | 주문 상태                                    | O        | X        |
| 생성일시            | created_at           | 주문 생성 시각                               | O        | O        |
| 체결일시            | filled_at            | 체결 완료 시각                               | X        | O        |

**주문 상태**:
- `PENDING`: 대기 중
- `FILLED`: 체결 완료
- `PARTIALLY_FILLED`: 부분 체결
- `CANCELLED`: 취소됨

---

### VirtualPosition (가상 포지션)

가상 계좌의 자산 보유 현황을 나타내는 도메인 객체입니다.

| **프로퍼티 (한글)** | **프로퍼티 (영문)**  | **개념**                                     | **필수** | **불변** |
|:--------------------|:---------------------|:--------------------------------------------|:---------|:---------|
| 식별자              | identifier           | 포지션 식별자                                | O        | O        |
| 계좌식별자          | account_identifier   | 포지션이 속한 계좌의 식별자                  | O        | O        |
| 심볼식별자          | symbol_identifier    | 보유 자산의 심볼 식별자                      | O        | O        |
| 수량                | quantity             | 보유 수량                                    | O        | X        |
| 평균단가            | average_price        | 평균 매수 가격                               | O        | X        |
| 생성일              | created_date         | 포지션 생성일 (최초 매수일)                  | O        | O        |
| 수정일              | modified_date        | 마지막 수정일                                | O        | X        |

---

### VirtualTransaction (가상 거래 내역)

체결된 거래 내역을 기록하는 불변 값 객체입니다.

| **프로퍼티 (한글)** | **프로퍼티 (영문)**  | **개념**                                     | **필수** | **불변** |
|:--------------------|:---------------------|:--------------------------------------------|:---------|:---------|
| 식별자              | identifier           | 거래 내역 식별자                             | O        | O        |
| 계좌식별자          | account_identifier   | 거래가 발생한 계좌의 식별자                  | O        | O        |
| 주문식별자          | order_identifier     | 거래를 발생시킨 주문의 식별자                | O        | O        |
| 심볼식별자          | symbol_identifier    | 거래 대상 심볼의 식별자                      | O        | O        |
| 시각                | time                 | 거래 체결 시각                               | O        | O        |
| 타입                | type                 | 거래 타입 (BUY, SELL)                        | O        | O        |
| 수량                | quantity             | 거래 수량                                    | O        | O        |
| 가격                | price                | 체결 가격                                    | O        | O        |
| 수수료              | fee                  | 거래 수수료                                  | O        | O        |
| 총금액              | total_amount         | 거래 총 금액                                 | O        | O        |

---

## 리스크 관리 시스템

### 손절/익절 자동 실행

포지션에 대해 손절가/익절가를 설정하여 자동으로 청산합니다.

```kotlin
data class StopLossTakeProfit(
    val positionIdentifier: UUID,
    val stopLossPrice: BigDecimal?,      // 손절가
    val takeProfitPrice: BigDecimal?     // 익절가
)
```

### 포지션 크기 관리

단일 포지션의 크기를 제한하여 리스크를 분산합니다.

```kotlin
data class PositionSizingRule(
    val maxPositionSizePercent: BigDecimal = BigDecimal("20"), // 총 자산의 20%
    val maxNumberOfPositions: Int = 10                         // 최대 10개 포지션
)
```

### 일일 손실 한도

하루 동안의 손실이 일정 금액을 초과하면 자동으로 거래를 중단합니다.

```kotlin
data class DailyLossLimit(
    val maxDailyLossPercent: BigDecimal = BigDecimal("5"),  // 총 자산의 5%
    val autoStopOnLimitReached: Boolean = true              // 한도 도달 시 자동 중단
)
```

---

## 실시간 전략 실행 엔진

### 시장 데이터 스트리밍

Kafka를 통해 실시간 캔들 데이터를 수신합니다.

```kotlin
@KafkaListener(topics = ["MARKET_CANDLE_REALTIME_TOPIC"])
fun onMarketCandleUpdate(candle: MarketCandle) {
    // 전략 실행
    val activeAccounts = virtualAccountRepository.findAllByStatus(AccountStatus.ACTIVE)

    activeAccounts.forEach { account ->
        val strategy = agentService.getStrategy(account.strategyIdentifier)

        // 신호 생성
        val signal = strategy.analyze(candle.symbolIdentifier, getRecentCandles(), account)

        // 신호에 따라 주문 실행
        when (signal.type) {
            SignalType.BUY -> executeBuyOrder(account, signal)
            SignalType.SELL -> executeSellOrder(account, signal)
            SignalType.HOLD -> {
                // 아무것도 하지 않음
            }
        }
    }
}
```

---

## 알림 시스템

### Slack 알림

중요한 이벤트 발생 시 Slack으로 알림을 보냅니다.

**알림 이벤트**:
- 주문 체결
- 손실 한도 도달
- 전략 실행 오류
- 일일 수익률 리포트

### Email 알림

일일/주간/월간 리포트를 이메일로 전송합니다.

---

## API 엔드포인트

### 가상 계좌 API

#### POST /virtual-accounts
가상 계좌를 생성합니다.

#### GET /virtual-accounts
가상 계좌 목록을 조회합니다.

#### GET /virtual-accounts/{accountIdentifier}
가상 계좌 상세 정보를 조회합니다.

#### PUT /virtual-accounts/{accountIdentifier}/start
전략 실행을 시작합니다.

#### PUT /virtual-accounts/{accountIdentifier}/pause
전략 실행을 일시 중지합니다.

#### PUT /virtual-accounts/{accountIdentifier}/stop
전략 실행을 중단합니다.

### 주문 API

#### GET /virtual-accounts/{accountIdentifier}/orders
주문 내역을 조회합니다.

#### GET /virtual-accounts/{accountIdentifier}/positions
포지션 현황을 조회합니다.

#### GET /virtual-accounts/{accountIdentifier}/transactions
거래 내역을 조회합니다.

### 성과 API

#### GET /virtual-accounts/{accountIdentifier}/performance
계좌 성과를 조회합니다.

---

## 데이터베이스 스키마

### virtual_account 테이블
```sql
CREATE TABLE IF NOT EXISTS virtual_account (
    identifier          UUID                     NOT NULL,
    name                VARCHAR                  NOT NULL,
    strategy_identifier UUID                     NOT NULL,
    initial_capital     DECIMAL                  NOT NULL,
    cash                DECIMAL                  NOT NULL,
    total_value         DECIMAL                  NOT NULL,
    status              VARCHAR                  NOT NULL,
    created_date        TIMESTAMP WITH TIME ZONE NOT NULL,
    PRIMARY KEY (identifier)
);
```

### virtual_order 테이블
```sql
CREATE TABLE IF NOT EXISTS virtual_order (
    identifier         UUID                     NOT NULL,
    account_identifier UUID                     NOT NULL,
    symbol_identifier  UUID                     NOT NULL,
    type               VARCHAR                  NOT NULL,
    order_price        DECIMAL,
    order_quantity     DECIMAL                  NOT NULL,
    filled_quantity    DECIMAL                  NOT NULL,
    status             VARCHAR                  NOT NULL,
    created_at         TIMESTAMP WITH TIME ZONE NOT NULL,
    filled_at          TIMESTAMP WITH TIME ZONE,
    PRIMARY KEY (identifier)
);
```

### virtual_position 테이블
```sql
CREATE TABLE IF NOT EXISTS virtual_position (
    identifier         UUID                     NOT NULL,
    account_identifier UUID                     NOT NULL,
    symbol_identifier  UUID                     NOT NULL,
    quantity           DECIMAL                  NOT NULL,
    average_price      DECIMAL                  NOT NULL,
    created_date       TIMESTAMP WITH TIME ZONE NOT NULL,
    modified_date      TIMESTAMP WITH TIME ZONE NOT NULL,
    PRIMARY KEY (identifier)
);
```

### virtual_transaction 테이블
```sql
CREATE TABLE IF NOT EXISTS virtual_transaction (
    identifier         UUID                     NOT NULL,
    account_identifier UUID                     NOT NULL,
    order_identifier   UUID                     NOT NULL,
    symbol_identifier  UUID                     NOT NULL,
    time               TIMESTAMP WITH TIME ZONE NOT NULL,
    type               VARCHAR                  NOT NULL,
    quantity           DECIMAL                  NOT NULL,
    price              DECIMAL                  NOT NULL,
    fee                DECIMAL                  NOT NULL,
    total_amount       DECIMAL                  NOT NULL,
    PRIMARY KEY (identifier)
);
```

---

## 다음 단계

- Agent Service와 연동하여 실시간 전략 실행
- Market Service에서 실시간 캔들 데이터 수신
- 리스크 관리 시스템 구현
- 알림 시스템 구현 (Slack, Email)
