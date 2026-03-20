# Notification Service - REST API 명세

> 알림 채널 관리, 수신 설정, 발송 이력 조회 및 템플릿 관리 REST API 정의

---

## 공통

### 인증 헤더

```
Authorization: Bearer <AccessToken>
```

### 응답 래퍼

```json
// 성공 (단건)
{ "data": { ... } }

// 성공 (페이징)
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
  "code": "N001",
  "message": "Notification channel not found",
  "timestamp": "2026-03-20T12:00:00+09:00",
  "path": "/notification-channels/...",
  "details": null
}
```

### 에러 코드 요약

| 코드 | 상수 | 설명 |
|------|------|------|
| `N001` | `CHANNEL_NOT_FOUND` | 알림 채널을 찾을 수 없음 |
| `N002` | `CHANNEL_NOT_OWNED` | 본인 소유가 아닌 채널 |
| `N003` | `CHANNEL_ALREADY_INACTIVE` | 이미 비활성화된 채널 |
| `N004` | `PREFERENCE_NOT_FOUND` | 수신 설정을 찾을 수 없음 |
| `N005` | `DISPATCH_FAILED` | 알림 발송 실패 |
| `N006` | `TEMPLATE_NOT_FOUND` | 템플릿을 찾을 수 없음 |

---

## 1. 채널 관리 (Notification Channels)

### 채널 등록
**`POST /notification-channels`** | Role: USER

**Request:**
```json
{
  "type": "DISCORD",
  "config": {
    "webhookUrl": "https://discord.com/api/webhooks/1234567890/abcdefg"
  }
}
```

| 필드 | 타입 | 필수 | 제약조건 |
|------|------|------|----------|
| `type` | `string` | O | `DISCORD` (향후 확장: `APP_PUSH`, `TELEGRAM`) |
| `config` | `object` | O | 채널 타입에 따른 설정 객체 |
| `config.webhookUrl` | `string` | O | Discord Webhook URL 형식 (`https://discord.com/api/webhooks/...`) |

**Response:** `201 Created`
```json
{
  "data": {
    "channelIdentifier": "550e8400-e29b-41d4-a716-446655440000",
    "type": "DISCORD",
    "config": {
      "webhookUrl": "https://discord.com/api/webhooks/1234567890/abcdefg"
    },
    "isActive": true,
    "createdDate": "2026-03-20T12:00:00+09:00",
    "modifiedDate": "2026-03-20T12:00:00+09:00"
  }
}
```

**에러:**

| 코드 | 상황 |
|------|------|
| — | 유효성 검증 실패 (400) — webhookUrl 형식 오류 등 |

---

### 내 채널 목록 조회
**`GET /notification-channels`** | Role: USER

**Request:**
- 파라미터 없음

> `isDeleted = false`인 채널만 반환한다. 소프트 딜리트된 채널은 조회 대상에서 제외된다.

**Response:** `200 OK`
```json
{
  "data": [
    {
      "channelIdentifier": "550e8400-e29b-41d4-a716-446655440000",
      "type": "DISCORD",
      "config": {
        "webhookUrl": "https://discord.com/api/webhooks/1234567890/abcdefg"
      },
      "isActive": true,
      "createdDate": "2026-03-20T12:00:00+09:00",
      "modifiedDate": "2026-03-20T12:00:00+09:00"
    }
  ]
}
```

---

### 채널 활성화
**`PUT /notification-channels/{channelIdentifier}/activate`** | Role: USER

**Path Parameter:**

| 필드 | 타입 | 필수 | 설명 |
|------|------|------|------|
| `channelIdentifier` | `UUID` | O | 대상 채널 식별자 |

**Request:**
- Body 없음

**Response:** `200 OK`
```json
{
  "data": {
    "channelIdentifier": "550e8400-e29b-41d4-a716-446655440000",
    "isActive": true,
    "modifiedDate": "2026-03-20T12:30:00+09:00"
  }
}
```

**에러:**

| 코드 | 상황 |
|------|------|
| `N001` | 채널을 찾을 수 없음 |
| `N002` | 본인 소유가 아닌 채널 |

---

### 채널 비활성화
**`PUT /notification-channels/{channelIdentifier}/deactivate`** | Role: USER

**Path Parameter:**

| 필드 | 타입 | 필수 | 설명 |
|------|------|------|------|
| `channelIdentifier` | `UUID` | O | 대상 채널 식별자 |

**Request:**
- Body 없음

**Response:** `200 OK`
```json
{
  "data": {
    "channelIdentifier": "550e8400-e29b-41d4-a716-446655440000",
    "isActive": false,
    "modifiedDate": "2026-03-20T12:30:00+09:00"
  }
}
```

**에러:**

| 코드 | 상황 |
|------|------|
| `N001` | 채널을 찾을 수 없음 |
| `N002` | 본인 소유가 아닌 채널 |
| `N003` | 이미 비활성화된 채널 |

---

### 채널 삭제 (소프트 딜리트)
**`DELETE /notification-channels/{channelIdentifier}`** | Role: USER

**Path Parameter:**

| 필드 | 타입 | 필수 | 설명 |
|------|------|------|------|
| `channelIdentifier` | `UUID` | O | 대상 채널 식별자 |

**Request:**
- Body 없음

**Response:** `204 No Content`

> `isDeleted = true`, `deletedAt = now()`로 설정한다. 해당 채널을 참조하는 `NotificationPreference`의 `channelIdentifiers`에서도 제거된다.

**에러:**

| 코드 | 상황 |
|------|------|
| `N001` | 채널을 찾을 수 없음 |
| `N002` | 본인 소유가 아닌 채널 |

---

## 2. 수신 설정 (Notification Preferences)

### 수신 설정 목록 조회
**`GET /notification-preferences`** | Role: USER

**Request:**
- 파라미터 없음

> 사용자가 등록한 수신 설정 목록을 반환한다. 아직 설정하지 않은 이벤트 타입은 `isEnabled = false` 기본값으로 포함한다.

**Response:** `200 OK`
```json
{
  "data": [
    {
      "eventType": "VIRTUAL_ORDER_FILLED",
      "isEnabled": true,
      "channelIdentifiers": [
        "550e8400-e29b-41d4-a716-446655440000"
      ]
    },
    {
      "eventType": "VIRTUAL_STOP_LOSS",
      "isEnabled": false,
      "channelIdentifiers": []
    },
    {
      "eventType": "REAL_ORDER_FILLED",
      "isEnabled": true,
      "channelIdentifiers": [
        "550e8400-e29b-41d4-a716-446655440000"
      ]
    }
  ]
}
```

---

### 수신 설정 변경
**`PUT /notification-preferences/{eventType}`** | Role: USER

**Path Parameter:**

| 필드 | 타입 | 필수 | 설명 |
|------|------|------|------|
| `eventType` | `string` | O | 이벤트 타입 식별자 (예: `VIRTUAL_ORDER_FILLED`) |

**Request:**
```json
{
  "isEnabled": true,
  "channelIdentifiers": [
    "550e8400-e29b-41d4-a716-446655440000"
  ]
}
```

| 필드 | 타입 | 필수 | 제약조건 |
|------|------|------|----------|
| `isEnabled` | `boolean` | O | 수신 활성화 여부 |
| `channelIdentifiers` | `UUID[]` | O | 알림을 수신할 채널 식별자 목록. 본인 소유 채널만 허용 |

> 해당 `eventType`에 대한 `NotificationPreference`가 없으면 새로 생성하고, 이미 있으면 업데이트한다 (Upsert 동작).

**Response:** `200 OK`
```json
{
  "data": {
    "eventType": "VIRTUAL_ORDER_FILLED",
    "isEnabled": true,
    "channelIdentifiers": [
      "550e8400-e29b-41d4-a716-446655440000"
    ],
    "modifiedDate": "2026-03-20T13:00:00+09:00"
  }
}
```

**에러:**

| 코드 | 상황 |
|------|------|
| `N001` | `channelIdentifiers`에 포함된 채널을 찾을 수 없음 |
| `N002` | `channelIdentifiers`에 본인 소유가 아닌 채널 포함 |

---

## 3. 발송 이력 (Notification Logs)

### 발송 이력 조회
**`GET /notification-logs`** | Role: USER

**Query Parameter:**

| 필드 | 타입 | 필수 | 기본값 | 설명 |
|------|------|------|--------|------|
| `from` | `string (date)` | X | — | 조회 시작일 (`yyyy-MM-dd`) |
| `to` | `string (date)` | X | — | 조회 종료일 (`yyyy-MM-dd`) |
| `status` | `string` | X | — | 필터: `SENT` 또는 `FAILED` |
| `page` | `int` | X | `0` | 페이지 번호 (0-based) |
| `size` | `int` | X | `20` | 페이지 크기 (최대 100) |

**Response:** `200 OK`
```json
{
  "data": [
    {
      "logIdentifier": "660e8400-e29b-41d4-a716-446655440000",
      "channelIdentifier": "550e8400-e29b-41d4-a716-446655440000",
      "eventType": "VIRTUAL_ORDER_FILLED",
      "message": "[가상거래] 주문 체결 — KRW-BTC BUY 0.001개 @ 95000000원",
      "status": "SENT",
      "failureReason": null,
      "retryCount": 0,
      "createdAt": "2026-03-20T14:00:00+09:00",
      "sentAt": "2026-03-20T14:00:01+09:00"
    }
  ],
  "page": {
    "number": 0,
    "size": 20,
    "totalElements": 42,
    "totalPages": 3
  }
}
```

---

## 4. 템플릿 관리 (Notification Templates) — ADMIN

### 템플릿 목록 조회
**`GET /notification-templates`** | Role: ADMIN

**Request:**
- 파라미터 없음

**Response:** `200 OK`
```json
{
  "data": [
    {
      "templateIdentifier": "770e8400-e29b-41d4-a716-446655440000",
      "eventType": "VIRTUAL_ORDER_FILLED",
      "channelType": "DISCORD",
      "titleTemplate": "[가상거래] 주문 체결",
      "bodyTemplate": "${symbol} ${side} ${quantity}개 @ ${price}원",
      "isActive": true,
      "createdDate": "2026-01-15T10:00:00+09:00",
      "modifiedDate": "2026-03-20T08:00:00+09:00"
    }
  ]
}
```

---

### 템플릿 생성
**`POST /notification-templates`** | Role: ADMIN

**Request:**
```json
{
  "eventType": "VIRTUAL_ORDER_FILLED",
  "channelType": "DISCORD",
  "titleTemplate": "[가상거래] 주문 체결",
  "bodyTemplate": "${symbol} ${side} ${quantity}개 @ ${price}원"
}
```

| 필드 | 타입 | 필수 | 제약조건 |
|------|------|------|----------|
| `eventType` | `string` | O | 이벤트 타입 식별자 |
| `channelType` | `string` | O | `DISCORD` |
| `titleTemplate` | `string` | O | 제목 템플릿. 변수: `${변수명}` 형식 |
| `bodyTemplate` | `string` | O | 본문 템플릿. 변수: `${변수명}` 형식 |

> `(eventType, channelType)` 조합은 unique 제약이 있다. 이미 존재하는 조합으로 생성 시 409 Conflict를 반환한다.

**Response:** `201 Created`
```json
{
  "data": {
    "templateIdentifier": "770e8400-e29b-41d4-a716-446655440000",
    "eventType": "VIRTUAL_ORDER_FILLED",
    "channelType": "DISCORD",
    "titleTemplate": "[가상거래] 주문 체결",
    "bodyTemplate": "${symbol} ${side} ${quantity}개 @ ${price}원",
    "isActive": true,
    "createdDate": "2026-03-20T15:00:00+09:00",
    "modifiedDate": "2026-03-20T15:00:00+09:00"
  }
}
```

---

### 템플릿 수정
**`PUT /notification-templates/{templateIdentifier}`** | Role: ADMIN

**Path Parameter:**

| 필드 | 타입 | 필수 | 설명 |
|------|------|------|------|
| `templateIdentifier` | `UUID` | O | 대상 템플릿 식별자 |

**Request:**
```json
{
  "titleTemplate": "[가상거래] 주문 체결 완료",
  "bodyTemplate": "${symbol} ${side} ${quantity}개 @ ${price}원 체결되었습니다.",
  "isActive": true
}
```

| 필드 | 타입 | 필수 | 제약조건 |
|------|------|------|----------|
| `titleTemplate` | `string` | X | 수정할 제목 템플릿 |
| `bodyTemplate` | `string` | X | 수정할 본문 템플릿 |
| `isActive` | `boolean` | X | 템플릿 활성화 여부 |

> 최소 하나 이상의 필드가 포함되어야 한다.

**Response:** `200 OK`
```json
{
  "data": {
    "templateIdentifier": "770e8400-e29b-41d4-a716-446655440000",
    "eventType": "VIRTUAL_ORDER_FILLED",
    "channelType": "DISCORD",
    "titleTemplate": "[가상거래] 주문 체결 완료",
    "bodyTemplate": "${symbol} ${side} ${quantity}개 @ ${price}원 체결되었습니다.",
    "isActive": true,
    "createdDate": "2026-01-15T10:00:00+09:00",
    "modifiedDate": "2026-03-20T15:30:00+09:00"
  }
}
```

**에러:**

| 코드 | 상황 |
|------|------|
| `N006` | 템플릿을 찾을 수 없음 |
