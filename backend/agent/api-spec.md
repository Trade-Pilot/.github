# Agent Service — REST API 명세

## 공통 사항

- 모든 USER 엔드포인트는 `X-User-Id` 헤더 기반으로 리소스 소유권을 검증한다.
- `X-User-Id`와 리소스의 `userIdentifier`가 불일치하면 `403 Forbidden` 반환.
- Identifier 접미사를 사용한다 (예: `strategyIdentifier`, `agentIdentifier`).

### 공통 응답 래퍼

```json
// 성공 (단건)
{ "data": { ... } }

// 성공 (목록, 페이지네이션)
{ "data": [...], "page": { "number": 0, "size": 20, "totalElements": 100, "totalPages": 5 } }

// 에러
{ "code": "A001", "message": "...", "timestamp": "...", "path": "...", "details": null }
```

---

## Strategy 엔드포인트

### 전략 생성
**`POST /strategies`** | Role: USER

**Request:**
```json
{
  "name": "MA 골든크로스 전략",
  "description": "단기/장기 이동평균선 교차 기반 매매 전략",
  "type": "MANUAL",
  "market": "COIN",
  "parameters": {
    "strategyKind": "MA_CROSSOVER",
    "shortPeriod": 5,
    "longPeriod": 20,
    "interval": "HOUR_1"
  }
}
```

> `parameters`는 `strategyKind`에 따라 스키마가 달라진다:
>
> **MA_CROSSOVER:**
> ```json
> { "strategyKind": "MA_CROSSOVER", "shortPeriod": 5, "longPeriod": 20, "interval": "HOUR_1" }
> ```
>
> **RSI:**
> ```json
> { "strategyKind": "RSI", "period": 14, "oversoldThreshold": 30, "overboughtThreshold": 70, "interval": "MINUTE_15" }
> ```
>
> **BOLLINGER_BREAKOUT:**
> ```json
> { "strategyKind": "BOLLINGER_BREAKOUT", "period": 20, "multiplier": 2.0, "interval": "HOUR_1" }
> ```

**Response:** `201 Created`
```json
{
  "data": {
    "strategyIdentifier": "uuid",
    "userIdentifier": "uuid",
    "name": "MA 골든크로스 전략",
    "description": "단기/장기 이동평균선 교차 기반 매매 전략",
    "type": "MANUAL",
    "market": "COIN",
    "status": "DRAFT",
    "parameters": {
      "strategyKind": "MA_CROSSOVER",
      "shortPeriod": 5,
      "longPeriod": 20,
      "interval": "HOUR_1"
    },
    "createdAt": "2024-01-01T00:00:00Z",
    "updatedAt": "2024-01-01T00:00:00Z"
  }
}
```

**에러:**
| 코드 | 상황 |
|------|------|
| `A012` | 지원하지 않는 전략 타입 (strategyKind 미지원) |

---

### 내 전략 목록
**`GET /strategies`** | Role: USER

**Request:**
| Query Param | 타입 | 필수 | 기본값 | 설명 |
|-------------|------|------|--------|------|
| `status` | String | N | 전체 | `DRAFT`, `VALIDATED`, `DEPRECATED` |
| `page` | Int | N | 0 | 페이지 번호 |
| `size` | Int | N | 20 | 페이지 크기 |

**Response:** `200 OK`
```json
{
  "data": [
    {
      "strategyIdentifier": "uuid",
      "name": "MA 골든크로스 전략",
      "type": "MANUAL",
      "market": "COIN",
      "status": "DRAFT",
      "parameters": { "strategyKind": "MA_CROSSOVER", "shortPeriod": 5, "longPeriod": 20, "interval": "HOUR_1" },
      "createdAt": "2024-01-01T00:00:00Z",
      "updatedAt": "2024-01-01T00:00:00Z"
    }
  ],
  "page": { "number": 0, "size": 20, "totalElements": 3, "totalPages": 1 }
}
```

---

### 전략 상세
**`GET /strategies/{id}`** | Role: USER

**Request:**
| Path Param | 타입 | 설명 |
|------------|------|------|
| `id` | UUID | strategyIdentifier |

**Response:** `200 OK`
```json
{
  "data": {
    "strategyIdentifier": "uuid",
    "userIdentifier": "uuid",
    "name": "MA 골든크로스 전략",
    "description": "단기/장기 이동평균선 교차 기반 매매 전략",
    "type": "MANUAL",
    "market": "COIN",
    "status": "DRAFT",
    "parameters": {
      "strategyKind": "MA_CROSSOVER",
      "shortPeriod": 5,
      "longPeriod": 20,
      "interval": "HOUR_1"
    },
    "createdAt": "2024-01-01T00:00:00Z",
    "updatedAt": "2024-01-01T00:00:00Z"
  }
}
```

**에러:**
| 코드 | 상황 |
|------|------|
| `A001` | 전략 없음 |

---

### 전략 파라미터 수정
**`PUT /strategies/{id}`** | Role: USER

> DRAFT 상태에서만 수정 가능하다.

**Request:**
| Path Param | 타입 | 설명 |
|------------|------|------|
| `id` | UUID | strategyIdentifier |

```json
{
  "name": "MA 골든크로스 전략 v2",
  "description": "수정된 설명",
  "parameters": {
    "strategyKind": "MA_CROSSOVER",
    "shortPeriod": 10,
    "longPeriod": 30,
    "interval": "HOUR_1"
  }
}
```

**Response:** `200 OK`
```json
{
  "data": {
    "strategyIdentifier": "uuid",
    "userIdentifier": "uuid",
    "name": "MA 골든크로스 전략 v2",
    "description": "수정된 설명",
    "type": "MANUAL",
    "market": "COIN",
    "status": "DRAFT",
    "parameters": {
      "strategyKind": "MA_CROSSOVER",
      "shortPeriod": 10,
      "longPeriod": 30,
      "interval": "HOUR_1"
    },
    "createdAt": "2024-01-01T00:00:00Z",
    "updatedAt": "2024-01-01T01:00:00Z"
  }
}
```

**에러:**
| 코드 | 상황 |
|------|------|
| `A001` | 전략 없음 |
| `A002` | DRAFT 상태가 아니어서 수정 불가 |

---

### 전략 삭제
**`DELETE /strategies/{id}`** | Role: USER

> DRAFT 상태이며 Agent에 할당되지 않은 전략만 삭제 가능하다.

**Request:**
| Path Param | 타입 | 설명 |
|------------|------|------|
| `id` | UUID | strategyIdentifier |

**Response:** `204 No Content`

**에러:**
| 코드 | 상황 |
|------|------|
| `A001` | 전략 없음 |
| `A002` | DRAFT 상태가 아니어서 삭제 불가 |

---

### 전략 검증 (VALIDATED 전환)
**`PUT /strategies/{id}/validate`** | Role: USER

> DRAFT -> VALIDATED 전환. 이후 실거래 Agent에 할당 가능해진다.

**Request:**
| Path Param | 타입 | 설명 |
|------------|------|------|
| `id` | UUID | strategyIdentifier |

**Response:** `200 OK`
```json
{
  "data": {
    "strategyIdentifier": "uuid",
    "status": "VALIDATED",
    "updatedAt": "2024-01-01T01:00:00Z"
  }
}
```

**에러:**
| 코드 | 상황 |
|------|------|
| `A001` | 전략 없음 |
| `A002` | DRAFT 상태가 아님 |

---

### 전략 비활성화 (DEPRECATED 처리)
**`PUT /strategies/{id}/deprecate`** | Role: USER

> VALIDATED -> DEPRECATED 전환. 신규 Agent 할당 불가, 기존 Active Agent는 계속 사용 가능.

**Request:**
| Path Param | 타입 | 설명 |
|------------|------|------|
| `id` | UUID | strategyIdentifier |

**Response:** `200 OK`
```json
{
  "data": {
    "strategyIdentifier": "uuid",
    "status": "DEPRECATED",
    "updatedAt": "2024-01-01T02:00:00Z"
  }
}
```

**에러:**
| 코드 | 상황 |
|------|------|
| `A001` | 전략 없음 |

---

## Agent 엔드포인트

### 에이전트 생성
**`POST /agents`** | Role: USER

> DEPRECATED 전략은 할당 불가. DRAFT / VALIDATED는 모두 허용.

**Request:**
```json
{
  "name": "BTC 자동매매 에이전트",
  "description": "비트코인 MA 크로스 전략 기반",
  "strategyIdentifier": "uuid",
  "riskConfig": {
    "positionSizeRatio": 0.5,
    "maxConcurrentPositions": 3,
    "stopLossPercent": 0.05,
    "takeProfitPercent": 0.10
  },
  "initialCapital": 10000000
}
```

**Response:** `201 Created`
```json
{
  "data": {
    "agentIdentifier": "uuid",
    "userIdentifier": "uuid",
    "name": "BTC 자동매매 에이전트",
    "description": "비트코인 MA 크로스 전략 기반",
    "strategyIdentifier": "uuid",
    "status": "INACTIVE",
    "riskConfig": {
      "positionSizeRatio": 0.5,
      "maxConcurrentPositions": 3,
      "stopLossPercent": 0.05,
      "takeProfitPercent": 0.10
    },
    "initialCapital": 10000000,
    "createdAt": "2024-01-01T00:00:00Z",
    "updatedAt": "2024-01-01T00:00:00Z"
  }
}
```

**에러:**
| 코드 | 상황 |
|------|------|
| `A001` | 전략 없음 |
| `A004` | DEPRECATED 전략은 신규 Agent에 할당 불가 |
| `A013` | RiskConfig 유효성 오류 |

---

### 내 에이전트 목록
**`GET /agents`** | Role: USER

**Request:**
| Query Param | 타입 | 필수 | 기본값 | 설명 |
|-------------|------|------|--------|------|
| `status` | String | N | 전체 | `INACTIVE`, `ACTIVE`, `PAUSED`, `TERMINATED` |
| `page` | Int | N | 0 | 페이지 번호 |
| `size` | Int | N | 20 | 페이지 크기 |

**Response:** `200 OK`
```json
{
  "data": [
    {
      "agentIdentifier": "uuid",
      "name": "BTC 자동매매 에이전트",
      "strategyIdentifier": "uuid",
      "status": "ACTIVE",
      "riskConfig": {
        "positionSizeRatio": 0.5,
        "maxConcurrentPositions": 3,
        "stopLossPercent": 0.05,
        "takeProfitPercent": 0.10
      },
      "initialCapital": 10000000,
      "createdAt": "2024-01-01T00:00:00Z",
      "updatedAt": "2024-01-01T00:00:00Z"
    }
  ],
  "page": { "number": 0, "size": 20, "totalElements": 5, "totalPages": 1 }
}
```

---

### 에이전트 상세
**`GET /agents/{id}`** | Role: USER

**Request:**
| Path Param | 타입 | 설명 |
|------------|------|------|
| `id` | UUID | agentIdentifier |

**Response:** `200 OK`
```json
{
  "data": {
    "agentIdentifier": "uuid",
    "userIdentifier": "uuid",
    "name": "BTC 자동매매 에이전트",
    "description": "비트코인 MA 크로스 전략 기반",
    "strategyIdentifier": "uuid",
    "status": "ACTIVE",
    "riskConfig": {
      "positionSizeRatio": 0.5,
      "maxConcurrentPositions": 3,
      "stopLossPercent": 0.05,
      "takeProfitPercent": 0.10
    },
    "initialCapital": 10000000,
    "createdAt": "2024-01-01T00:00:00Z",
    "updatedAt": "2024-01-01T00:00:00Z"
  }
}
```

**에러:**
| 코드 | 상황 |
|------|------|
| `A005` | 에이전트 없음 |

---

### 에이전트 설정 수정
**`PUT /agents/{id}`** | Role: USER

> INACTIVE 상태에서만 수정 가능하다.

**Request:**
| Path Param | 타입 | 설명 |
|------------|------|------|
| `id` | UUID | agentIdentifier |

```json
{
  "name": "BTC 자동매매 에이전트 v2",
  "description": "수정된 설명",
  "riskConfig": {
    "positionSizeRatio": 0.3,
    "maxConcurrentPositions": 5,
    "stopLossPercent": 0.03,
    "takeProfitPercent": 0.15
  },
  "initialCapital": 20000000
}
```

**Response:** `200 OK`
```json
{
  "data": {
    "agentIdentifier": "uuid",
    "userIdentifier": "uuid",
    "name": "BTC 자동매매 에이전트 v2",
    "description": "수정된 설명",
    "strategyIdentifier": "uuid",
    "status": "INACTIVE",
    "riskConfig": {
      "positionSizeRatio": 0.3,
      "maxConcurrentPositions": 5,
      "stopLossPercent": 0.03,
      "takeProfitPercent": 0.15
    },
    "initialCapital": 20000000,
    "createdAt": "2024-01-01T00:00:00Z",
    "updatedAt": "2024-01-01T01:00:00Z"
  }
}
```

**에러:**
| 코드 | 상황 |
|------|------|
| `A005` | 에이전트 없음 |
| `A007` | INACTIVE 상태가 아니어서 설정 수정 불가 |
| `A013` | RiskConfig 유효성 오류 |

---

### 에이전트 활성화
**`PUT /agents/{id}/activate`** | Role: USER

> INACTIVE -> ACTIVE 전환. Portfolio가 `initialCapital` 기준으로 초기화된다.

**Request:**
| Path Param | 타입 | 설명 |
|------------|------|------|
| `id` | UUID | agentIdentifier |

**Response:** `200 OK`
```json
{
  "data": {
    "agentIdentifier": "uuid",
    "status": "ACTIVE",
    "updatedAt": "2024-01-01T01:00:00Z"
  }
}
```

**에러:**
| 코드 | 상황 |
|------|------|
| `A005` | 에이전트 없음 |
| `A007` | INACTIVE 상태가 아님 |

---

### 에이전트 일시 중지
**`PUT /agents/{id}/pause`** | Role: USER

> ACTIVE -> PAUSED 전환. 신호 생성이 중단된다.

**Request:**
| Path Param | 타입 | 설명 |
|------------|------|------|
| `id` | UUID | agentIdentifier |

**Response:** `200 OK`
```json
{
  "data": {
    "agentIdentifier": "uuid",
    "status": "PAUSED",
    "updatedAt": "2024-01-01T02:00:00Z"
  }
}
```

**에러:**
| 코드 | 상황 |
|------|------|
| `A005` | 에이전트 없음 |
| `A006` | ACTIVE 상태가 아님 |
| `A008` | TERMINATED 에이전트는 상태 전환 불가 |

---

### 에이전트 재개
**`PUT /agents/{id}/resume`** | Role: USER

> PAUSED -> ACTIVE 전환.

**Request:**
| Path Param | 타입 | 설명 |
|------------|------|------|
| `id` | UUID | agentIdentifier |

**Response:** `200 OK`
```json
{
  "data": {
    "agentIdentifier": "uuid",
    "status": "ACTIVE",
    "updatedAt": "2024-01-01T03:00:00Z"
  }
}
```

**에러:**
| 코드 | 상황 |
|------|------|
| `A005` | 에이전트 없음 |
| `A008` | TERMINATED 에이전트는 상태 전환 불가 |

---

### 에이전트 종료
**`PUT /agents/{id}/terminate`** | Role: USER

> TERMINATED 상태로 전환. 복구 불가. `AgentTerminatedEvent`가 발행되어 VirtualTrade/Trade Service에서 관련 Registration이 STOPPED 처리된다.

**Request:**
| Path Param | 타입 | 설명 |
|------------|------|------|
| `id` | UUID | agentIdentifier |

**Response:** `200 OK`
```json
{
  "data": {
    "agentIdentifier": "uuid",
    "status": "TERMINATED",
    "updatedAt": "2024-01-01T04:00:00Z"
  }
}
```

**에러:**
| 코드 | 상황 |
|------|------|
| `A005` | 에이전트 없음 |
| `A008` | 이미 TERMINATED 상태 |

---

### 신호 이력 조회
**`GET /agents/{id}/signals`** | Role: USER

**Request:**
| Path Param | 타입 | 설명 |
|------------|------|------|
| `id` | UUID | agentIdentifier |

| Query Param | 타입 | 필수 | 기본값 | 설명 |
|-------------|------|------|--------|------|
| `page` | Int | N | 0 | 페이지 번호 |
| `size` | Int | N | 20 | 페이지 크기 |

**Response:** `200 OK`
```json
{
  "data": [
    {
      "signalIdentifier": "uuid",
      "agentIdentifier": "uuid",
      "strategyIdentifier": "uuid",
      "symbolIdentifier": "uuid",
      "type": "BUY",
      "confidence": 0.85,
      "price": 95000000,
      "suggestedQuantity": 0.05,
      "reason": {
        "indicator": "MA_CROSSOVER",
        "details": { "shortMA": 94500000, "longMA": 93000000 }
      },
      "createdAt": "2024-01-01T09:00:00Z"
    }
  ],
  "page": { "number": 0, "size": 20, "totalElements": 42, "totalPages": 3 }
}
```

**에러:**
| 코드 | 상황 |
|------|------|
| `A005` | 에이전트 없음 |

---

### 포트폴리오 현황
**`GET /agents/{id}/portfolio`** | Role: USER

**Request:**
| Path Param | 타입 | 설명 |
|------------|------|------|
| `id` | UUID | agentIdentifier |

**Response:** `200 OK`
```json
{
  "data": {
    "portfolioIdentifier": "uuid",
    "agentIdentifier": "uuid",
    "cash": 5000000,
    "reservedCash": 500000,
    "realizedPnl": 150000,
    "createdAt": "2024-01-01T00:00:00Z",
    "updatedAt": "2024-01-15T12:30:00Z"
  }
}
```

**에러:**
| 코드 | 상황 |
|------|------|
| `A005` | 에이전트 없음 |
| `A009` | 포트폴리오 없음 (에이전트가 아직 활성화되지 않은 경우) |

---

### 보유 포지션 목록
**`GET /agents/{id}/portfolio/positions`** | Role: USER

**Request:**
| Path Param | 타입 | 설명 |
|------------|------|------|
| `id` | UUID | agentIdentifier |

**Response:** `200 OK`
```json
{
  "data": [
    {
      "positionIdentifier": "uuid",
      "portfolioIdentifier": "uuid",
      "symbolIdentifier": "uuid",
      "quantity": 0.05,
      "reservedQuantity": 0,
      "averagePrice": 95000000,
      "createdAt": "2024-01-01T09:00:00Z",
      "updatedAt": "2024-01-10T15:00:00Z"
    }
  ]
}
```

**에러:**
| 코드 | 상황 |
|------|------|
| `A005` | 에이전트 없음 |
| `A009` | 포트폴리오 없음 |

---

### 포트폴리오 이력
**`GET /agents/{id}/portfolio/history`** | Role: USER

**Request:**
| Path Param | 타입 | 설명 |
|------------|------|------|
| `id` | UUID | agentIdentifier |

| Query Param | 타입 | 필수 | 기본값 | 설명 |
|-------------|------|------|--------|------|
| `from` | OffsetDateTime | N | - | 조회 시작일 (ISO-8601) |
| `to` | OffsetDateTime | N | - | 조회 종료일 (ISO-8601) |
| `type` | String | N | 전체 | `SIGNAL`, `DAILY` |
| `page` | Int | N | 0 | 페이지 번호 |
| `size` | Int | N | 20 | 페이지 크기 |

**Response:** `200 OK`
```json
{
  "data": [
    {
      "historyIdentifier": "uuid",
      "portfolioIdentifier": "uuid",
      "snapshotType": "SIGNAL",
      "cash": 5000000,
      "totalValue": 9750000,
      "realizedPnl": 150000,
      "unrealizedPnl": -250000,
      "positionsSnapshot": [
        {
          "symbolIdentifier": "uuid",
          "quantity": 0.05,
          "averagePrice": 95000000
        }
      ],
      "triggerSignalIdentifier": "uuid",
      "recordedAt": "2024-01-15T12:30:00Z"
    }
  ],
  "page": { "number": 0, "size": 20, "totalElements": 100, "totalPages": 5 }
}
```

**에러:**
| 코드 | 상황 |
|------|------|
| `A005` | 에이전트 없음 |
| `A009` | 포트폴리오 없음 |

---

### 결정 감사 로그
**`GET /agents/{id}/decision-logs`** | Role: USER

**Request:**
| Path Param | 타입 | 설명 |
|------------|------|------|
| `id` | UUID | agentIdentifier |

| Query Param | 타입 | 필수 | 기본값 | 설명 |
|-------------|------|------|--------|------|
| `page` | Int | N | 0 | 페이지 번호 |
| `size` | Int | N | 20 | 페이지 크기 |

**Response:** `200 OK`
```json
{
  "data": [
    {
      "logIdentifier": "uuid",
      "agentIdentifier": "uuid",
      "strategyIdentifier": "uuid",
      "symbolIdentifier": "uuid",
      "signalType": "HOLD",
      "currentPrice": 95500000,
      "evaluationStatus": "SUCCESS",
      "indicatorValues": {
        "rsi": 45.2,
        "shortMA": 95200000,
        "longMA": 95300000
      },
      "evaluationReason": null,
      "createdAt": "2024-01-15T12:00:00Z"
    }
  ],
  "page": { "number": 0, "size": 20, "totalElements": 500, "totalPages": 25 }
}
```

**에러:**
| 코드 | 상황 |
|------|------|
| `A005` | 에이전트 없음 |

---

### 백테스트 결과 목록
**`GET /agents/{id}/backtests`** | Role: USER

**Request:**
| Path Param | 타입 | 설명 |
|------------|------|------|
| `id` | UUID | agentIdentifier |

**Response:** `200 OK`
```json
{
  "data": [
    {
      "backtestIdentifier": "uuid",
      "agentIdentifier": "uuid",
      "symbolIdentifier": "uuid",
      "candleFrom": "2024-01-01T00:00:00Z",
      "candleTo": "2024-06-01T00:00:00Z",
      "initialCapital": 10000000,
      "finalValue": 12500000,
      "realizedPnl": 2800000,
      "unrealizedPnl": -300000,
      "totalSignals": 15,
      "createdAt": "2024-06-15T10:00:00Z"
    }
  ]
}
```

**에러:**
| 코드 | 상황 |
|------|------|
| `A005` | 에이전트 없음 |

---

### 백테스트 결과 상세
**`GET /agents/{id}/backtests/{backtestId}`** | Role: USER

**Request:**
| Path Param | 타입 | 설명 |
|------------|------|------|
| `id` | UUID | agentIdentifier |
| `backtestId` | UUID | backtestIdentifier |

**Response:** `200 OK`
```json
{
  "data": {
    "backtestIdentifier": "uuid",
    "agentIdentifier": "uuid",
    "symbolIdentifier": "uuid",
    "candleFrom": "2024-01-01T00:00:00Z",
    "candleTo": "2024-06-01T00:00:00Z",
    "initialCapital": 10000000,
    "finalValue": 12500000,
    "realizedPnl": 2800000,
    "unrealizedPnl": -300000,
    "totalSignals": 15,
    "signalSnapshots": [
      {
        "signalType": "BUY",
        "confidence": 0.85,
        "candleOpenTime": "2024-01-15T09:00:00Z",
        "suggestedQuantity": 0.05,
        "cashAfter": 5250000,
        "totalValueAfter": 10050000,
        "reason": { "indicator": "MA_CROSSOVER", "details": { "shortMA": 94500000, "longMA": 93000000 } }
      }
    ],
    "createdAt": "2024-06-15T10:00:00Z"
  }
}
```

**에러:**
| 코드 | 상황 |
|------|------|
| `A005` | 에이전트 없음 |

---

## 에러 코드 요약

| 코드 | 상수 | HTTP | 설명 |
|------|------|------|------|
| `A001` | `STRATEGY_NOT_FOUND` | 404 | 전략 없음 |
| `A002` | `STRATEGY_NOT_DRAFT` | 409 | DRAFT 상태가 아니어서 수정 불가 |
| `A003` | `STRATEGY_NOT_VALIDATED` | 409 | DRAFT 전략은 실거래(TRADE) 신호 요청 불가 |
| `A004` | `STRATEGY_DEPRECATED` | 409 | DEPRECATED 전략은 신규 Agent에 할당 불가 |
| `A005` | `AGENT_NOT_FOUND` | 404 | 에이전트 없음 |
| `A006` | `AGENT_NOT_ACTIVE` | 409 | ACTIVE 상태가 아니어서 신호 생성 불가 |
| `A007` | `AGENT_NOT_INACTIVE` | 409 | INACTIVE 상태가 아니어서 설정 수정 불가 |
| `A008` | `AGENT_ALREADY_TERMINATED` | 409 | TERMINATED 에이전트는 상태 전환 불가 |
| `A009` | `PORTFOLIO_NOT_FOUND` | 404 | 포트폴리오 없음 |
| `A010` | `INSUFFICIENT_CASH` | 409 | 매수 시 현금 부족 |
| `A011` | `CANDLE_DATA_INSUFFICIENT` | 502 | 지표 계산에 필요한 캔들 수 부족 |
| `A012` | `UNSUPPORTED_STRATEGY_TYPE` | 400 | 지원하지 않는 전략 타입 |
| `A013` | `INVALID_RISK_CONFIG` | 400 | RiskConfig 유효성 오류 |
