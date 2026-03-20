# Exchange Service - REST API 명세

> 거래소 API Key 등록 및 관리 관련 REST API 정의

---

## 공통

### 응답 래퍼

```json
// 성공 (단건)
{ "data": { ... } }

// 성공 (목록)
{ "data": [...] }

// 에러
{
  "code": "EX001",
  "message": "Exchange account not found",
  "timestamp": "2026-03-20T12:00:00+09:00",
  "path": "/exchange-accounts/...",
  "details": null
}
```

### 인증 헤더

```
Authorization: Bearer <AccessToken>
```

---

## 1. 거래소 계정 관리 (ExchangeAccount)

### API Key 등록
**`POST /exchange-accounts`** | Role: USER

**Request:**
```json
{
  "exchange": "UPBIT",
  "accessKey": "your-access-key",
  "secretKey": "your-secret-key"
}
```

| 필드 | 타입 | 필수 | 제약조건 |
|------|------|------|----------|
| `exchange` | `string` | O | `UPBIT` (현재 지원 거래소) |
| `accessKey` | `string` | O | 거래소에서 발급받은 Access Key (빈 문자열 불가) |
| `secretKey` | `string` | O | 거래소에서 발급받은 Secret Key (빈 문자열 불가) |

**Response:** `201 Created`
```json
{
  "data": {
    "accountIdentifier": "660e8400-e29b-41d4-a716-446655440000",
    "userIdentifier": "550e8400-e29b-41d4-a716-446655440000",
    "exchange": "UPBIT",
    "status": "ACTIVE",
    "createdAt": "2026-03-20T12:00:00+09:00",
    "updatedAt": "2026-03-20T12:00:00+09:00"
  }
}
```

> API Key는 AES-256-GCM으로 암호화되어 저장된다. 응답에 Key 평문은 포함되지 않는다.

**에러:**

| 코드 | 상황 |
|------|------|
| `EX006` | 해당 거래소에 이미 활성 계정이 존재 (사용자당 거래소별 1개 제한) |

---

### 내 거래소 계정 목록 조회
**`GET /exchange-accounts`** | Role: USER

**Request:**
- 파라미터 없음 (인증된 사용자의 계정만 조회)

**Response:** `200 OK`
```json
{
  "data": [
    {
      "accountIdentifier": "660e8400-e29b-41d4-a716-446655440000",
      "userIdentifier": "550e8400-e29b-41d4-a716-446655440000",
      "exchange": "UPBIT",
      "maskedAccessKey": "****a1b2",
      "status": "ACTIVE",
      "createdAt": "2026-03-20T12:00:00+09:00",
      "updatedAt": "2026-03-20T12:00:00+09:00"
    }
  ]
}
```

> API Key는 마스킹된 형태(`****xxxx`, 마지막 4자리)로만 노출된다.

---

### 거래소 계정 상세 조회
**`GET /exchange-accounts/{accountIdentifier}`** | Role: USER

**Path Parameter:**

| 필드 | 타입 | 필수 | 설명 |
|------|------|------|------|
| `accountIdentifier` | `UUID` | O | 거래소 계정 식별자 |

**Response:** `200 OK`
```json
{
  "data": {
    "accountIdentifier": "660e8400-e29b-41d4-a716-446655440000",
    "userIdentifier": "550e8400-e29b-41d4-a716-446655440000",
    "exchange": "UPBIT",
    "maskedAccessKey": "****a1b2",
    "status": "ACTIVE",
    "createdAt": "2026-03-20T12:00:00+09:00",
    "updatedAt": "2026-03-20T12:00:00+09:00"
  }
}
```

**에러:**

| 코드 | 상황 |
|------|------|
| `EX001` | 거래소 계정을 찾을 수 없음 |

---

### API Key 삭제
**`DELETE /exchange-accounts/{accountIdentifier}`** | Role: USER

**Path Parameter:**

| 필드 | 타입 | 필수 | 설명 |
|------|------|------|------|
| `accountIdentifier` | `UUID` | O | 거래소 계정 식별자 |

**Request:**
- Body 없음

**Response:** `204 No Content`

> 실제 레코드를 삭제하지 않고, 상태를 `REVOKED`로 변경하는 소프트 딜리트 방식이다. REVOKED 상태의 계정은 주문 제출/취소 요청 시 즉시 거부된다.

**에러:**

| 코드 | 상황 |
|------|------|
| `EX001` | 거래소 계정을 찾을 수 없음 |
| `EX002` | 이미 삭제(REVOKED)된 계정 |

---

### API Key 유효성 검증
**`POST /exchange-accounts/{accountIdentifier}/validate`** | Role: USER

**Path Parameter:**

| 필드 | 타입 | 필수 | 설명 |
|------|------|------|------|
| `accountIdentifier` | `UUID` | O | 거래소 계정 식별자 |

**Request:**
- Body 없음

**Response:** `200 OK`
```json
{
  "data": {
    "accountIdentifier": "660e8400-e29b-41d4-a716-446655440000",
    "valid": true,
    "exchange": "UPBIT"
  }
}
```

> 거래소 API를 실제로 호출하여 Key의 유효성을 확인한다. 유효하지 않은 경우 계정 상태를 `INVALID`로 변경한다.

**검증 실패 시 Response:** `200 OK`
```json
{
  "data": {
    "accountIdentifier": "660e8400-e29b-41d4-a716-446655440000",
    "valid": false,
    "exchange": "UPBIT"
  }
}
```

**에러:**

| 코드 | 상황 |
|------|------|
| `EX001` | 거래소 계정을 찾을 수 없음 |
| `EX002` | 이미 삭제(REVOKED)된 계정 |
| `EX004` | Rate Limit 초과로 검증 요청 불가 |
| `EX005` | 거래소 API 호출 중 오류 발생 |

---

## 에러 코드 요약

| 코드 | 상수 | 설명 |
|------|------|------|
| `EX001` | `EXCHANGE_ACCOUNT_NOT_FOUND` | 거래소 계정 없음 |
| `EX002` | `EXCHANGE_ACCOUNT_REVOKED` | 삭제된 계정 |
| `EX003` | `EXCHANGE_ACCOUNT_INVALID` | 유효하지 않은 API Key |
| `EX004` | `RATE_LIMIT_EXCEEDED` | Rate Limit 초과 |
| `EX005` | `EXCHANGE_API_ERROR` | 거래소 API 오류 (4xx/5xx) |
| `EX006` | `DUPLICATE_ACTIVE_ACCOUNT` | 해당 거래소 활성 계정 이미 존재 |
| `EX007` | `ORDER_SUBMIT_FAILED` | 주문 제출 실패 (거래소 거부) |
| `EX008` | `ORDER_CANCEL_FAILED` | 주문 취소 실패 |

> `EX007`, `EX008`은 Kafka 인터페이스(주문 제출/취소)에서 사용되며, REST API에서는 직접 발생하지 않는다.
