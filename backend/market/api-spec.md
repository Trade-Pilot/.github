# Market Service - REST API 명세

> 시장 데이터 수집 관리 및 캔들/심볼 조회 관련 REST API 정의

---

## 공통

### 응답 래퍼

```json
// 성공 (단건)
{ "data": { ... } }

// 성공 (목록, 페이지네이션)
{
  "data": [...],
  "page": {
    "number": 0,
    "size": 20,
    "totalElements": 100,
    "totalPages": 5
  }
}

// 에러
{
  "code": "MS001",
  "message": "Market symbol not found",
  "timestamp": "2026-03-20T12:00:00Z",
  "path": "/market-symbols/...",
  "details": null
}
```

### 인증 헤더

```
Authorization: Bearer <AccessToken>
```

---

## 1. 심볼 관리 (MarketSymbol)

### 수동 심볼 수집 트리거
**`POST /market-symbols/collect`** | Role: ADMIN

**Request:**
```json
{
  "market": "COIN"
}
```

| 필드 | 타입 | 필수 | 제약조건 |
|------|------|------|----------|
| `market` | `string` | O | `COIN`, `STOCK` |

**Response:** `202 Accepted`
```json
{
  "data": {
    "message": "심볼 수집이 시작되었습니다.",
    "market": "COIN"
  }
}
```

> Exchange Service에 Kafka Command를 발행하여 거래소에서 심볼 목록을 수집한다. 비동기 처리이므로 202 Accepted를 반환한다.

---

### 심볼 목록 조회
**`GET /market-symbols`** | Role: USER

**Query Parameter:**

| 필드 | 타입 | 필수 | 기본값 | 제약조건 |
|------|------|------|--------|----------|
| `market` | `string` | X | - | `COIN`, `STOCK` (미지정 시 전체) |
| `status` | `string` | X | `LISTED` | `LISTED`, `WARNING`, `CAUTION`, `TRADING_HALTED`, `DELISTED` |
| `page` | `int` | X | `0` | 0 이상 |
| `size` | `int` | X | `20` | 1~100 |

**Response:** `200 OK`
```json
{
  "data": [
    {
      "symbolIdentifier": "770e8400-e29b-41d4-a716-446655440000",
      "code": "KRW-BTC",
      "name": "비트코인",
      "market": "COIN",
      "status": "LISTED",
      "createdDate": "2026-01-01T00:00:00Z",
      "modifiedDate": "2026-03-20T08:00:00Z"
    },
    {
      "symbolIdentifier": "770e8400-e29b-41d4-a716-446655440001",
      "code": "KRW-ETH",
      "name": "이더리움",
      "market": "COIN",
      "status": "LISTED",
      "createdDate": "2026-01-01T00:00:00Z",
      "modifiedDate": "2026-03-20T08:00:00Z"
    }
  ],
  "page": {
    "number": 0,
    "size": 20,
    "totalElements": 150,
    "totalPages": 8
  }
}
```

---

### 심볼 상세 조회
**`GET /market-symbols/{symbolIdentifier}`** | Role: USER

**Path Parameter:**

| 필드 | 타입 | 필수 | 설명 |
|------|------|------|------|
| `symbolIdentifier` | `UUID` | O | 심볼 식별자 |

**Response:** `200 OK`
```json
{
  "data": {
    "symbolIdentifier": "770e8400-e29b-41d4-a716-446655440000",
    "code": "KRW-BTC",
    "name": "비트코인",
    "market": "COIN",
    "status": "LISTED",
    "createdDate": "2026-01-01T00:00:00Z",
    "modifiedDate": "2026-03-20T08:00:00Z"
  }
}
```

**에러:**

| 코드 | 상황 |
|------|------|
| `MS001` | 심볼을 찾을 수 없음 |

---

## 2. 캔들 수집 작업 관리 (MarketCandleCollectTask)

### 수집 작업 목록 조회
**`GET /market-candle-collect-tasks`** | Role: ADMIN

**Query Parameter:**

| 필드 | 타입 | 필수 | 기본값 | 제약조건 |
|------|------|------|--------|----------|
| `symbolIdentifier` | `UUID` | X | - | 특정 심볼의 작업만 필터 |
| `status` | `string` | X | - | `CREATED`, `COLLECTING`, `COLLECTED`, `ERROR`, `PAUSED`, `DELISTED` |
| `page` | `int` | X | `0` | 0 이상 |
| `size` | `int` | X | `20` | 1~100 |

**Response:** `200 OK`
```json
{
  "data": [
    {
      "taskIdentifier": "880e8400-e29b-41d4-a716-446655440000",
      "symbolIdentifier": "770e8400-e29b-41d4-a716-446655440000",
      "interval": "MIN_1",
      "status": "COLLECTED",
      "retryCount": 0,
      "lastCollectedTime": "2026-03-20T11:59:00Z",
      "lastCollectedPrice": "95000000",
      "createdDate": "2026-01-01T00:00:00Z"
    },
    {
      "taskIdentifier": "880e8400-e29b-41d4-a716-446655440001",
      "symbolIdentifier": "770e8400-e29b-41d4-a716-446655440000",
      "interval": "MIN_5",
      "status": "ERROR",
      "retryCount": 2,
      "lastCollectedTime": "2026-03-20T11:55:00Z",
      "lastCollectedPrice": "94800000",
      "createdDate": "2026-01-01T00:00:00Z"
    }
  ],
  "page": {
    "number": 0,
    "size": 20,
    "totalElements": 24,
    "totalPages": 2
  }
}
```

---

### 전체 수집 작업 일시정지
**`PUT /market-candle-collect-tasks/pause-all`** | Role: ADMIN

**Request:**
- Body 없음

**Response:** `200 OK`
```json
{
  "data": {
    "message": "모든 수집 작업이 일시정지되었습니다.",
    "pausedCount": 150
  }
}
```

> `PAUSABLE_STATUS`(CREATED, COLLECTING, COLLECTED, ERROR)에 해당하는 모든 작업을 PAUSED로 변경한다.

---

### 전체 수집 작업 재개
**`PUT /market-candle-collect-tasks/resume-all`** | Role: ADMIN

**Request:**
- Body 없음

**Response:** `200 OK`
```json
{
  "data": {
    "message": "모든 수집 작업이 재개되었습니다.",
    "resumedCount": 150
  }
}
```

> PAUSED 상태의 모든 작업을 COLLECTED로 변경하여 다음 스케줄 사이클에 수집을 재개한다.

---

### 개별 수집 작업 일시정지
**`PUT /market-candle-collect-tasks/{taskIdentifier}/pause`** | Role: ADMIN

**Path Parameter:**

| 필드 | 타입 | 필수 | 설명 |
|------|------|------|------|
| `taskIdentifier` | `UUID` | O | 수집 작업 식별자 |

**Request:**
- Body 없음

**Response:** `200 OK`
```json
{
  "data": {
    "taskIdentifier": "880e8400-e29b-41d4-a716-446655440000",
    "status": "PAUSED"
  }
}
```

**에러:**

| 코드 | 상황 |
|------|------|
| `MCT001` | 수집 작업을 찾을 수 없음 |
| `MCT005` | 현재 상태에서 일시정지 불가 (DELISTED 등) |

---

### 개별 수집 작업 재개
**`PUT /market-candle-collect-tasks/{taskIdentifier}/resume`** | Role: ADMIN

**Path Parameter:**

| 필드 | 타입 | 필수 | 설명 |
|------|------|------|------|
| `taskIdentifier` | `UUID` | O | 수집 작업 식별자 |

**Request:**
- Body 없음

**Response:** `200 OK`
```json
{
  "data": {
    "taskIdentifier": "880e8400-e29b-41d4-a716-446655440000",
    "status": "COLLECTED"
  }
}
```

> PAUSED 상태의 작업을 COLLECTED로 변경한다. ERROR 상태에서 `retryCount >= MAX_RETRY_COUNT(3)`인 경우에도 수동 복구 용도로 사용한다.

**에러:**

| 코드 | 상황 |
|------|------|
| `MCT001` | 수집 작업을 찾을 수 없음 |

---

## 3. 캔들 데이터 조회 (Candle)

### 캔들 데이터 조회
**`GET /candles`** | Role: USER

**Query Parameter:**

| 필드 | 타입 | 필수 | 기본값 | 제약조건 |
|------|------|------|--------|----------|
| `symbolIdentifier` | `UUID` | O | - | 조회 대상 심볼 식별자 |
| `interval` | `string` | O | - | `MIN_1`, `MIN_3`, `MIN_5`, `MIN_10`, `MIN_15`, `MIN_30`, `MIN_60`, `MIN_120`, `MIN_180`, `DAY`, `WEEK`, `MONTH` |
| `from` | `string` | X | - | ISO-8601 형식 (시작 시각) |
| `to` | `string` | X | - | ISO-8601 형식 (종료 시각) |
| `limit` | `int` | X | `200` | 1~1000, `from`/`to` 미지정 시 최근 N개 조회 |

> `from`/`to`가 지정되면 해당 기간의 캔들을 조회한다. 미지정 시 최근 `limit`개의 캔들을 시간 역순으로 조회한다.

**Response:** `200 OK`
```json
{
  "data": [
    {
      "symbolIdentifier": "770e8400-e29b-41d4-a716-446655440000",
      "interval": "MIN_1",
      "time": "2026-03-20T11:59:00Z",
      "open": "95000000",
      "high": "95100000",
      "low": "94900000",
      "close": "95050000",
      "volume": "1.5432",
      "amount": "146700000"
    },
    {
      "symbolIdentifier": "770e8400-e29b-41d4-a716-446655440000",
      "interval": "MIN_1",
      "time": "2026-03-20T11:58:00Z",
      "open": "94800000",
      "high": "95050000",
      "low": "94750000",
      "close": "95000000",
      "volume": "2.1000",
      "amount": "199500000"
    }
  ]
}
```

> 가격 및 수량 필드는 정밀도 손실 방지를 위해 문자열로 반환한다.

**에러:**

| 코드 | 상황 |
|------|------|
| `MS001` | 심볼을 찾을 수 없음 |

---

## 에러 코드 요약

### MarketSymbol 에러

| 코드 | 상수 | 설명 |
|------|------|------|
| `MS001` | `MARKET_SYMBOL_NOT_FOUND` | 심볼을 찾을 수 없음 |

### MarketCandleCollectTask 에러

| 코드 | 상수 | 설명 |
|------|------|------|
| `MCT001` | `TASK_NOT_FOUND` | 수집 작업을 찾을 수 없음 |
| `MCT002` | `INVALID_STATUS_FOR_START` | 수집 시작 불가능한 상태 |
| `MCT003` | `INVALID_STATUS_FOR_COMPLETE` | 수집 완료 불가능한 상태 |
| `MCT004` | `INVALID_STATUS_FOR_FAIL` | 수집 실패 처리 불가능한 상태 |
| `MCT005` | `INVALID_STATUS_FOR_PAUSE` | 일시정지 불가능한 상태 |

> `MCT002`~`MCT004`는 내부 스케줄러/Kafka 처리 과정에서 발생하며, REST API에서는 `MCT001`, `MCT005`가 주로 발생한다.
