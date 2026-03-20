# Trade Service — REST API 명세

## 공통 사항

- 모든 USER 엔드포인트는 `X-User-Id` 헤더 기반으로 리소스 소유권을 검증한다.
- `X-User-Id`와 리소스의 `userIdentifier`가 불일치하면 `TR016 RESOURCE_NOT_OWNED` (`403 Forbidden`) 반환.
- Order 접근 시 Registration -> Order 계층으로 소유권을 이중 검증한다.
- Identifier 접미사를 사용한다 (예: `registrationIdentifier`, `orderIdentifier`).

### 공통 응답 래퍼

```json
// 성공 (단건)
{ "data": { ... } }

// 성공 (목록, 페이지네이션)
{ "data": [...], "page": { "number": 0, "size": 20, "totalElements": 100, "totalPages": 5 } }

// 에러
{ "code": "TR001", "message": "...", "timestamp": "...", "path": "...", "details": null }
```

### 리소스 소유권 검증

```kotlin
// Registration 기반 리소스 접근 시
fun validateOwnership(registrationIdentifier: UUID, userIdentifier: UUID) {
    val registration = findById(registrationIdentifier)
        ?: throw RegistrationNotFoundException()  // TR001
    if (registration.userIdentifier != userIdentifier) {
        throw ForbiddenException("TR016")  // RESOURCE_NOT_OWNED
    }
}

// Order 접근 시: Registration -> Order 계층 검증
fun validateOrderOwnership(registrationIdentifier: UUID, orderIdentifier: UUID, userIdentifier: UUID) {
    validateOwnership(registrationIdentifier, userIdentifier)
    val order = findById(orderIdentifier)
        ?: throw OrderNotFoundException()  // TR008
    if (order.registrationIdentifier != registrationIdentifier) {
        throw ForbiddenException("TR016")
    }
}
```

---

## TradeRegistration 엔드포인트

### 실거래 등록
**`POST /trade-registrations`** | Role: USER

> 하나의 Agent에 대해 하나의 실거래만 등록 가능하다 (UNIQUE 제약).

**Request:**
```json
{
  "agentIdentifier": "uuid",
  "exchangeAccountIdentifier": "uuid",
  "symbolIdentifiers": ["uuid-1", "uuid-2"],
  "allocatedCapital": 10000000,
  "orderConfig": {
    "orderType": "LIMIT",
    "limitOrderTimeoutMinutes": 30
  }
}
```

| Body Field | 타입 | 필수 | 설명 |
|------------|------|------|------|
| `agentIdentifier` | UUID | Y | 실거래를 실행할 Agent ID |
| `exchangeAccountIdentifier` | UUID | Y | 거래소 계정 ID (Exchange Service 참조) |
| `symbolIdentifiers` | List\<UUID\> | Y | 분석 대상 심볼 목록 (최소 1개) |
| `allocatedCapital` | BigDecimal | Y | 이 Registration에 할당할 자본금 |
| `orderConfig` | Object | Y | 주문 설정 |
| `orderConfig.orderType` | String | Y | `MARKET` 또는 `LIMIT` |
| `orderConfig.limitOrderTimeoutMinutes` | Int | N | LIMIT 미체결 자동 취소 대기 시간 (분). null이면 무제한 |

**Response:** `201 Created`
```json
{
  "data": {
    "registrationIdentifier": "uuid",
    "agentIdentifier": "uuid",
    "userIdentifier": "uuid",
    "exchangeAccountIdentifier": "uuid",
    "symbolIdentifiers": ["uuid-1", "uuid-2"],
    "allocatedCapital": 10000000,
    "status": "ACTIVE",
    "orderConfig": {
      "orderType": "LIMIT",
      "limitOrderTimeoutMinutes": 30
    },
    "emergencyStopped": false,
    "createdAt": "2024-01-01T00:00:00Z",
    "updatedAt": "2024-01-01T00:00:00Z"
  }
}
```

**에러:**
| 코드 | 상황 |
|------|------|
| `TR002` | 해당 Agent는 이미 실거래에 등록됨 |
| `TR006` | symbolIdentifiers는 최소 1개 이상 필요 |
| `TR010` | Exchange Service에서 계정 없음 |
| `TR015` | allocatedCapital 값이 잘못됨 (음수 또는 실계좌 초과) |

---

### 내 실거래 등록 목록
**`GET /trade-registrations`** | Role: USER

**Request:**
| Query Param | 타입 | 필수 | 기본값 | 설명 |
|-------------|------|------|--------|------|
| `status` | String | N | 전체 | `ACTIVE`, `PAUSED`, `STOPPED` |
| `page` | Int | N | 0 | 페이지 번호 |
| `size` | Int | N | 20 | 페이지 크기 |

**Response:** `200 OK`
```json
{
  "data": [
    {
      "registrationIdentifier": "uuid",
      "agentIdentifier": "uuid",
      "exchangeAccountIdentifier": "uuid",
      "symbolIdentifiers": ["uuid-1", "uuid-2"],
      "allocatedCapital": 10000000,
      "status": "ACTIVE",
      "orderConfig": {
        "orderType": "LIMIT",
        "limitOrderTimeoutMinutes": 30
      },
      "emergencyStopped": false,
      "createdAt": "2024-01-01T00:00:00Z",
      "updatedAt": "2024-01-01T00:00:00Z"
    }
  ],
  "page": { "number": 0, "size": 20, "totalElements": 2, "totalPages": 1 }
}
```

---

### 실거래 등록 상세
**`GET /trade-registrations/{id}`** | Role: USER

**Request:**
| Path Param | 타입 | 설명 |
|------------|------|------|
| `id` | UUID | registrationIdentifier |

**Response:** `200 OK`
```json
{
  "data": {
    "registrationIdentifier": "uuid",
    "agentIdentifier": "uuid",
    "userIdentifier": "uuid",
    "exchangeAccountIdentifier": "uuid",
    "symbolIdentifiers": ["uuid-1", "uuid-2"],
    "allocatedCapital": 10000000,
    "status": "ACTIVE",
    "orderConfig": {
      "orderType": "LIMIT",
      "limitOrderTimeoutMinutes": 30
    },
    "emergencyStopped": false,
    "createdAt": "2024-01-01T00:00:00Z",
    "updatedAt": "2024-01-01T00:00:00Z"
  }
}
```

**에러:**
| 코드 | 상황 |
|------|------|
| `TR001` | 실거래 등록 없음 |

---

### 실거래 활성화
**`PUT /trade-registrations/{id}/activate`** | Role: USER

> PAUSED -> ACTIVE 전환. STOPPED 상태는 재활성화 불가.

**Request:**
| Path Param | 타입 | 설명 |
|------------|------|------|
| `id` | UUID | registrationIdentifier |

**Response:** `200 OK`
```json
{
  "data": {
    "registrationIdentifier": "uuid",
    "status": "ACTIVE",
    "updatedAt": "2024-01-01T01:00:00Z"
  }
}
```

**에러:**
| 코드 | 상황 |
|------|------|
| `TR001` | 실거래 등록 없음 |
| `TR003` | STOPPED 상태는 재활성화 불가 |
| `TR005` | PAUSED 상태가 아니어서 재활성화 불가 |

---

### 실거래 일시 중지
**`PUT /trade-registrations/{id}/pause`** | Role: USER

> ACTIVE -> PAUSED 전환. 스케줄러 트리거에서 제외된다.

**Request:**
| Path Param | 타입 | 설명 |
|------------|------|------|
| `id` | UUID | registrationIdentifier |

**Response:** `200 OK`
```json
{
  "data": {
    "registrationIdentifier": "uuid",
    "status": "PAUSED",
    "updatedAt": "2024-01-01T02:00:00Z"
  }
}
```

**에러:**
| 코드 | 상황 |
|------|------|
| `TR001` | 실거래 등록 없음 |
| `TR003` | STOPPED 상태 |
| `TR004` | ACTIVE 상태가 아니어서 일시정지 불가 |

---

### 실거래 종료
**`PUT /trade-registrations/{id}/stop`** | Role: USER

> STOPPED 상태로 전환. 재활성화 불가.

**Request:**
| Path Param | 타입 | 설명 |
|------------|------|------|
| `id` | UUID | registrationIdentifier |

**Response:** `200 OK`
```json
{
  "data": {
    "registrationIdentifier": "uuid",
    "status": "STOPPED",
    "updatedAt": "2024-01-01T03:00:00Z"
  }
}
```

**에러:**
| 코드 | 상황 |
|------|------|
| `TR001` | 실거래 등록 없음 |
| `TR003` | 이미 STOPPED 상태 |

---

### 분석 대상 심볼 수정
**`PUT /trade-registrations/{id}/symbols`** | Role: USER

> ACTIVE 또는 PAUSED 상태에서만 수정 가능하다. 배열 전체 교체 방식으로 처리한다.

**Request:**
| Path Param | 타입 | 설명 |
|------------|------|------|
| `id` | UUID | registrationIdentifier |

```json
{
  "symbolIdentifiers": ["uuid-1", "uuid-2", "uuid-3"]
}
```

**Response:** `200 OK`
```json
{
  "data": {
    "registrationIdentifier": "uuid",
    "symbolIdentifiers": ["uuid-1", "uuid-2", "uuid-3"],
    "updatedAt": "2024-01-01T04:00:00Z"
  }
}
```

**에러:**
| 코드 | 상황 |
|------|------|
| `TR001` | 실거래 등록 없음 |
| `TR003` | STOPPED 상태에서는 수정 불가 |
| `TR006` | symbolIdentifiers는 최소 1개 이상 필요 |

---

### 주문 설정 수정
**`PUT /trade-registrations/{id}/order-config`** | Role: USER

> PAUSED 상태에서만 수정 가능하다. 실행 중 주문 설정 변경을 방지한다.

**Request:**
| Path Param | 타입 | 설명 |
|------------|------|------|
| `id` | UUID | registrationIdentifier |

```json
{
  "orderConfig": {
    "orderType": "MARKET",
    "limitOrderTimeoutMinutes": null
  }
}
```

**Response:** `200 OK`
```json
{
  "data": {
    "registrationIdentifier": "uuid",
    "orderConfig": {
      "orderType": "MARKET",
      "limitOrderTimeoutMinutes": null
    },
    "updatedAt": "2024-01-01T05:00:00Z"
  }
}
```

**에러:**
| 코드 | 상황 |
|------|------|
| `TR001` | 실거래 등록 없음 |
| `TR005` | PAUSED 상태가 아님 |

---

### 비상 정지
**`PUT /trade-registrations/{id}/emergency-stop`** | Role: USER

> 즉시 모든 신호 처리를 차단하고 미체결 주문을 취소 요청한다.
> `emergencyStopped = true`, `status = PAUSED`로 전환된다.

**Request:**
| Path Param | 타입 | 설명 |
|------------|------|------|
| `id` | UUID | registrationIdentifier |

**Response:** `200 OK`
```json
{
  "data": {
    "registrationIdentifier": "uuid",
    "status": "PAUSED",
    "emergencyStopped": true,
    "cancelledOrderCount": 3,
    "updatedAt": "2024-01-01T06:00:00Z"
  }
}
```

> `cancelledOrderCount`: 취소 요청된 미체결 주문 수 (PENDING, SUBMITTED, PARTIALLY_FILLED 상태).

**에러:**
| 코드 | 상황 |
|------|------|
| `TR001` | 실거래 등록 없음 |

---

### 비상 정지 해제
**`PUT /trade-registrations/{id}/emergency-resume`** | Role: USER

> `emergencyStopped = false`로 전환. 상태는 `PAUSED`를 유지한다.
> 재개하려면 사용자가 직접 `PUT /trade-registrations/{id}/activate`를 호출해야 한다.

**Request:**
| Path Param | 타입 | 설명 |
|------------|------|------|
| `id` | UUID | registrationIdentifier |

**Response:** `200 OK`
```json
{
  "data": {
    "registrationIdentifier": "uuid",
    "status": "PAUSED",
    "emergencyStopped": false,
    "updatedAt": "2024-01-01T07:00:00Z"
  }
}
```

**에러:**
| 코드 | 상황 |
|------|------|
| `TR001` | 실거래 등록 없음 |
| `TR013` | 비상 정지 상태가 아님 |

---

### [ADMIN] 전체 비상 정지
**`POST /admin/trade-registrations/emergency-stop-all`** | Role: ADMIN

> 모든 ACTIVE 상태의 TradeRegistration에 대해 비상 정지를 발동한다.
> 각 Registration에 대해 `emergencyStopped = true`, `status = PAUSED` 처리 및 미체결 주문 취소 요청.

**Request:** (Body 없음)

**Response:** `200 OK`
```json
{
  "data": {
    "stoppedRegistrationCount": 5,
    "cancelledOrderCount": 12
  }
}
```

---

### [ADMIN] 할당 자본 수동 조정
**`PUT /admin/trade-registrations/{id}/allocated-capital`** | Role: ADMIN

> Account Reconciliation 불일치 해결을 위한 관리자 전용 API.

**Request:**
| Path Param | 타입 | 설명 |
|------------|------|------|
| `id` | UUID | registrationIdentifier |

```json
{
  "newAllocatedCapital": 10000000
}
```

**Response:** `200 OK`
```json
{
  "data": {
    "registrationIdentifier": "uuid",
    "allocatedCapital": 10000000,
    "updatedAt": "2024-01-01T08:00:00Z"
  }
}
```

**에러:**
| 코드 | 상황 |
|------|------|
| `TR001` | 실거래 등록 없음 |
| `TR015` | allocatedCapital 값이 잘못됨 (음수 또는 실계좌 초과) |

---

## Order 엔드포인트

### 주문 이력 조회
**`GET /trade-registrations/{id}/orders`** | Role: USER

**Request:**
| Path Param | 타입 | 설명 |
|------------|------|------|
| `id` | UUID | registrationIdentifier |

| Query Param | 타입 | 필수 | 기본값 | 설명 |
|-------------|------|------|--------|------|
| `status` | String | N | 전체 | `PENDING`, `SUBMITTED`, `PARTIALLY_FILLED`, `FILLED`, `CANCELLED`, `REJECTED` |
| `page` | Int | N | 0 | 페이지 번호 |
| `size` | Int | N | 20 | 페이지 크기 |

**Response:** `200 OK`
```json
{
  "data": [
    {
      "orderIdentifier": "uuid",
      "registrationIdentifier": "uuid",
      "agentIdentifier": "uuid",
      "symbolIdentifier": "uuid",
      "signalIdentifier": "uuid",
      "side": "BUY",
      "type": "LIMIT",
      "requestedQuantity": 0.05,
      "requestedPrice": 95000000,
      "executedQuantity": 0.05,
      "averageExecutedPrice": 94800000,
      "status": "FILLED",
      "exchangeOrderId": "EX-12345",
      "timeoutAt": "2024-01-01T10:00:00Z",
      "createdAt": "2024-01-01T09:30:00Z",
      "updatedAt": "2024-01-01T09:35:00Z"
    }
  ],
  "page": { "number": 0, "size": 20, "totalElements": 15, "totalPages": 1 }
}
```

**에러:**
| 코드 | 상황 |
|------|------|
| `TR001` | 실거래 등록 없음 |
| `TR016` | 리소스가 요청 사용자 소유가 아님 |

---

### 주문 상세 조회
**`GET /trade-registrations/{id}/orders/{orderId}`** | Role: USER

> Execution(체결 이력)을 포함하여 반환한다.

**Request:**
| Path Param | 타입 | 설명 |
|------------|------|------|
| `id` | UUID | registrationIdentifier |
| `orderId` | UUID | orderIdentifier |

**Response:** `200 OK`
```json
{
  "data": {
    "orderIdentifier": "uuid",
    "registrationIdentifier": "uuid",
    "agentIdentifier": "uuid",
    "symbolIdentifier": "uuid",
    "signalIdentifier": "uuid",
    "side": "BUY",
    "type": "LIMIT",
    "requestedQuantity": 0.05,
    "requestedPrice": 95000000,
    "executedQuantity": 0.05,
    "averageExecutedPrice": 94800000,
    "status": "FILLED",
    "exchangeOrderId": "EX-12345",
    "timeoutAt": "2024-01-01T10:00:00Z",
    "createdAt": "2024-01-01T09:30:00Z",
    "updatedAt": "2024-01-01T09:35:00Z",
    "executions": [
      {
        "executionIdentifier": "uuid",
        "orderIdentifier": "uuid",
        "quantity": 0.03,
        "price": 94900000,
        "fee": 14235,
        "executedAt": "2024-01-01T09:32:00Z"
      },
      {
        "executionIdentifier": "uuid",
        "orderIdentifier": "uuid",
        "quantity": 0.02,
        "price": 94650000,
        "fee": 9465,
        "executedAt": "2024-01-01T09:34:00Z"
      }
    ]
  }
}
```

**에러:**
| 코드 | 상황 |
|------|------|
| `TR001` | 실거래 등록 없음 |
| `TR008` | 주문 없음 |
| `TR016` | 리소스가 요청 사용자 소유가 아님 |

---

### 미체결 주문 수동 취소
**`DELETE /trade-registrations/{id}/orders/{orderId}`** | Role: USER

> SUBMITTED 또는 PARTIALLY_FILLED 상태의 주문만 취소 가능하다.
> Exchange Service에 취소 요청을 발행하며, 실제 CANCELLED 상태 전환은 Exchange Service 이벤트 수신 시 처리된다.

**Request:**
| Path Param | 타입 | 설명 |
|------------|------|------|
| `id` | UUID | registrationIdentifier |
| `orderId` | UUID | orderIdentifier |

**Response:** `202 Accepted`
```json
{
  "data": {
    "orderIdentifier": "uuid",
    "status": "SUBMITTED",
    "message": "취소 요청이 거래소에 전달되었습니다. 실제 취소는 비동기로 처리됩니다."
  }
}
```

**에러:**
| 코드 | 상황 |
|------|------|
| `TR001` | 실거래 등록 없음 |
| `TR008` | 주문 없음 |
| `TR009` | 취소 불가 상태의 주문 (FILLED / CANCELLED / REJECTED) |
| `TR016` | 리소스가 요청 사용자 소유가 아님 |

---

## 에러 코드 요약

| 코드 | 상수 | HTTP | 설명 |
|------|------|------|------|
| `TR001` | `REGISTRATION_NOT_FOUND` | 404 | 실거래 등록 없음 |
| `TR002` | `ALREADY_REGISTERED` | 409 | 해당 Agent는 이미 실거래에 등록됨 |
| `TR003` | `REGISTRATION_STOPPED` | 409 | STOPPED 상태는 재활성화 불가 |
| `TR004` | `REGISTRATION_NOT_ACTIVE` | 409 | ACTIVE 상태가 아니어서 일시정지 불가 |
| `TR005` | `REGISTRATION_NOT_PAUSED` | 409 | PAUSED 상태가 아니어서 재활성화 불가 |
| `TR006` | `SYMBOL_IDS_EMPTY` | 400 | symbolIdentifiers는 최소 1개 이상 필요 |
| `TR007` | `CURRENT_PRICE_UNAVAILABLE` | 502 | Market Service에서 현재가 조회 실패 |
| `TR008` | `ORDER_NOT_FOUND` | 404 | 주문 없음 |
| `TR009` | `ORDER_NOT_CANCELLABLE` | 409 | 취소 불가 상태의 주문 |
| `TR010` | `EXCHANGE_ACCOUNT_NOT_FOUND` | 404 | Exchange Service에서 계정 없음 |
| `TR011` | `ORDER_SUBMIT_FAILED` | 502 | Exchange Service 주문 제출 실패 |
| `TR012` | `EMERGENCY_STOP_ACTIVE` | 409 | 비상 정지 상태이므로 주문 처리 불가 |
| `TR013` | `NOT_EMERGENCY_STOPPED` | 409 | 비상 정지 상태가 아님 |
| `TR014` | `ACCOUNT_BALANCE_INSUFFICIENT` | 409 | 거래소 계정 실제 잔고 부족 |
| `TR015` | `ALLOCATED_CAPITAL_INVALID` | 400 | allocatedCapital 값이 잘못됨 |
| `TR016` | `RESOURCE_NOT_OWNED` | 403 | 리소스가 요청 사용자 소유가 아님 |
