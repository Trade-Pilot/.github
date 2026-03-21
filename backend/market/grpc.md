# Market Service — 핵심 비즈니스 규칙, gRPC 인터페이스

> 이 문서는 `backend/market/domain.md`에서 분할되었습니다.

---

## 11. 핵심 비즈니스 규칙

### 11.0 "최신 캔들" 정의

`GetRecentCandles(limit=1)`이 반환하는 캔들은 **가장 최근 종료된 캔들**이다.

```
MarketCandle.time = 캔들 시작 시각 (예: 13:59:00)
MarketCandle.close = 해당 봉의 마지막 거래가 (13:59:59까지의 종가)
```

- 현재 진행 중인 캔들(아직 종료되지 않은 봉)은 **반환하지 않는다**.
- 따라서 `GetRecentCandles(limit=1).close`를 현재가로 사용하면, 실제 최신 가격과 최대 1분(MIN_1 기준)의 차이가 발생할 수 있다.
- VirtualTrade / Trade 스케줄러가 이 값을 `currentPrice`로 사용할 때 이 지연을 인지해야 한다.

### 11.1 Flat Candle 생성 규칙
- 이전 종가가 있는 경우에만 생성
- `volume = 0`, `amount = 0`
- `open = high = low = close = 이전 종가`

### 11.2 간격 계산 순서
- MIN_1 수집 완료 후 이벤트 발행
- 모든 파생 간격(MIN_3 ~ MONTH)을 순차적으로 계산
- 각 간격은 `baseInterval` 기준으로 계산

### 11.3 수집 실패 처리
- 상태를 ERROR로 변경, `retryCount` 1 증가
- 다음 스케줄 사이클(기본: 1분)에 자동 재시도 (`retryCount < MAX_RETRY_COUNT = 3` 조건 충족 시)
- 3회 초과 시 자동 재시도 중단 → 수동 복구 필요 (`PUT /tasks/{id}/resume`)

**스케줄러 설정 예시**:
```yaml
# application.yml
scheduler:
  market:
    candle-collect-interval: 60000  # 밀리초 (기본: 1분)
```

```kotlin
// MarketCandleCollectScheduler.kt
@Component
class MarketCandleCollectScheduler(
    @Value("\${scheduler.market.candle-collect-interval:60000}")
    private val collectInterval: Long,
    // ...
) {
    @Scheduled(fixedDelayString = "\${scheduler.market.candle-collect-interval:60000}")
    fun collectCandles() {
        // MIN_1 간격 수집 작업 처리
        // ...
    }
}
```

### 11.4 데이터 검증
- OHLC 관계 검증 (Factory에서 수행)
- 가격 급등락 감지 (추가 구현 필요)
- Flat Candle 비율 모니터링 (< 5%)

---

## 12. gRPC 인터페이스

Market Service는 다른 서비스에 캔들 데이터 및 심볼 메타데이터를 제공하는 gRPC 서버를 운영한다.

### 12.1 Proto 정의 (market-service.proto)

```protobuf
syntax = "proto3";

package market;

option java_package = "com.tradepilot.market.grpc";
option java_multiple_files = true;

// ============================================
// Market Candle Service
// ============================================
service MarketCandle {
  // 최근 N개 캔들 조회 (Agent Service, VirtualTrade Service, Trade Service 사용)
  rpc GetRecentCandles(GetRecentCandlesRequest) returns (GetRecentCandlesResponse);

  // 기간 기반 과거 캔들 조회 (Simulation Service 사용)
  rpc GetHistoricalCandles(GetHistoricalCandlesRequest) returns (GetHistoricalCandlesResponse);
}

// 최근 캔들 조회
message GetRecentCandlesRequest {
  string symbol_id = 1;  // UUID
  string interval  = 2;  // MIN_1, MIN_5, MIN_60, DAY 등 (MarketCandleInterval enum 값)
  int32  limit     = 3;  // 최대 1000개
}

message GetRecentCandlesResponse {
  repeated CandleProto candles = 1;
}

// 과거 캔들 조회 (기간 기반)
message GetHistoricalCandlesRequest {
  string symbol_id = 1;  // UUID
  string interval  = 2;  // MIN_1, MIN_5, MIN_60, DAY 등 (MarketCandleInterval enum 값)
  string from      = 3;  // ISO-8601 (예: 2024-01-01T00:00:00Z)
  string to        = 4;  // ISO-8601
}

message GetHistoricalCandlesResponse {
  repeated CandleProto candles = 1;
}

message CandleProto {
  string symbol_id = 1;
  string interval  = 2;
  string time      = 3;  // ISO-8601
  string open      = 4;  // BigDecimal → String
  string high      = 5;
  string low       = 6;
  string close     = 7;
  string volume    = 8;
  string amount    = 9;
}

// ============================================
// Market Symbol Service
// ============================================
service MarketSymbol {
  // 심볼 메타데이터 조회 (Agent Service, Trade Service 사용)
  rpc GetSymbol(GetSymbolRequest) returns (GetSymbolResponse);

  // 여러 심볼 일괄 조회
  rpc GetSymbols(GetSymbolsRequest) returns (GetSymbolsResponse);

  // 거래 가능한 심볼 목록 조회
  rpc ListSymbols(ListSymbolsRequest) returns (ListSymbolsResponse);
}

message GetSymbolRequest {
  string symbol_id = 1;  // UUID
}

message GetSymbolResponse {
  SymbolProto symbol = 1;
}

message GetSymbolsRequest {
  repeated string symbol_ids = 1;  // UUID 배열
}

message GetSymbolsResponse {
  repeated SymbolProto symbols = 1;
}

message ListSymbolsRequest {
  string market = 1;     // COIN, STOCK
  string status = 2;     // LISTED (optional, 기본값: LISTED만 조회)
  int32  page   = 3;     // 페이지 번호 (0부터 시작)
  int32  size   = 4;     // 페이지 크기 (기본 100, 최대 1000)
}

message ListSymbolsResponse {
  repeated SymbolProto symbols = 1;
  int32 total_count = 2;
}

message SymbolProto {
  string symbol_id = 1;  // UUID
  string code      = 2;  // KRW-BTC
  string name      = 3;  // 비트코인
  string market    = 4;  // COIN
  string status    = 5;  // LISTED, WARNING, CAUTION, TRADING_HALTED, DELISTED
}
```

### 12.2 gRPC 서버 구현

**Infrastructure Layer**:
```
infrastructure/
  grpc/
    MarketCandleGrpcServer    (implements MarketCandleGrpc.MarketCandleImplBase)
    MarketSymbolGrpcServer    (implements MarketSymbolGrpc.MarketSymbolImplBase)
    GrpcExceptionHandler      (gRPC 에러 변환)
```

**에러 매핑**:
```kotlin
도메인 예외                         → gRPC Status
MarketSymbolNotFoundException      → NOT_FOUND
MarketCandleCollectTaskNotFoundException → NOT_FOUND
ValidationException                 → INVALID_ARGUMENT
InternalError                       → INTERNAL
TimeoutException                    → DEADLINE_EXCEEDED
```

### 12.3 타임아웃 및 성능

**타임아웃 설정**:
```yaml
GetRecentCandles:       5초
GetHistoricalCandles:   30초 (대용량 데이터)
GetSymbol:              3초
GetSymbols:             10초
ListSymbols:            10초
```

**캐싱 전략**:
- `GetSymbol`: Redis 캐싱 (TTL 10분)
  - Key: `symbol:{symbolIdentifier}`
  - Value: `SymbolProto` JSON

- `GetRecentCandles`: 최신 캔들(limit=1)만 Redis 캐싱 (TTL 10초)
  - Key: `candle:recent:{symbolIdentifier}:{interval}`
  - 이유: 현재가 조회 용도로 자주 호출됨

**페이징**:
- `ListSymbols`: 최대 1000개까지 한 번에 조회 가능
- 기본 페이지 크기: 100개
