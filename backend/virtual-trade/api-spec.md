# VirtualTrade Service — REST API 명세

## 공통 사항

- 모든 USER 엔드포인트는 `X-User-Id` 헤더 기반으로 리소스 소유권을 검증한다.
- `X-User-Id`와 리소스의 `userIdentifier`가 불일치하면 `403 Forbidden` 반환.
- Identifier 접미사를 사용한다 (예: `registrationIdentifier`, `agentIdentifier`).

### 공통 응답 래퍼

```json
// 성공 (단건)
{ "data": { ... } }

// 성공 (목록, 페이지네이션)
{ "data": [...], "page": { "number": 0, "size": 20, "totalElements": 100, "totalPages": 5 } }

// 에러
{ "code": "VT001", "message": "...", "timestamp": "...", "path": "...", "details": null }
```

### 리소스 소유권 검증

```kotlin
fun validateOwnership(registrationIdentifier: UUID, userIdentifier: UUID) {
    val registration = findById(registrationIdentifier)
        ?: throw RegistrationNotFoundException()  // VT001
    if (registration.userIdentifier != userIdentifier) {
        throw ForbiddenException()  // 403
    }
}
```

---

## 가상거래 등록
**`POST /virtual-trades`** | Role: USER

> 하나의 Agent에 대해 하나의 가상거래만 등록 가능하다 (UNIQUE 제약).

**Request:**
```json
{
  "agentIdentifier": "uuid",
  "symbolIdentifiers": ["uuid-1", "uuid-2"]
}
```

| Body Field | 타입 | 필수 | 설명 |
|------------|------|------|------|
| `agentIdentifier` | UUID | Y | 가상거래를 실행할 Agent ID |
| `symbolIdentifiers` | List\<UUID\> | Y | 분석 대상 심볼 목록 (최소 1개) |

**Response:** `201 Created`
```json
{
  "data": {
    "registrationIdentifier": "uuid",
    "agentIdentifier": "uuid",
    "userIdentifier": "uuid",
    "symbolIdentifiers": ["uuid-1", "uuid-2"],
    "status": "ACTIVE",
    "createdDate": "2024-01-01T00:00:00Z",
    "modifiedDate": "2024-01-01T00:00:00Z"
  }
}
```

**에러:**
| 코드 | 상황 |
|------|------|
| `VT002` | 해당 Agent는 이미 가상거래에 등록됨 |
| `VT006` | symbolIdentifiers는 최소 1개 이상 필요 |

---

## 내 가상거래 등록 목록
**`GET /virtual-trades`** | Role: USER

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
      "symbolIdentifiers": ["uuid-1", "uuid-2"],
      "status": "ACTIVE",
      "createdDate": "2024-01-01T00:00:00Z",
      "modifiedDate": "2024-01-01T00:00:00Z"
    }
  ],
  "page": { "number": 0, "size": 20, "totalElements": 3, "totalPages": 1 }
}
```

---

## 가상거래 등록 상세
**`GET /virtual-trades/{id}`** | Role: USER

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
    "symbolIdentifiers": ["uuid-1", "uuid-2"],
    "status": "ACTIVE",
    "createdDate": "2024-01-01T00:00:00Z",
    "modifiedDate": "2024-01-01T00:00:00Z"
  }
}
```

**에러:**
| 코드 | 상황 |
|------|------|
| `VT001` | 가상거래 등록 없음 |

---

## 가상거래 활성화
**`PUT /virtual-trades/{id}/activate`** | Role: USER

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
    "modifiedDate": "2024-01-01T01:00:00Z"
  }
}
```

**에러:**
| 코드 | 상황 |
|------|------|
| `VT001` | 가상거래 등록 없음 |
| `VT003` | STOPPED 상태는 재활성화 불가 |
| `VT005` | PAUSED 상태가 아니어서 재활성화 불가 |

---

## 가상거래 일시 중지
**`PUT /virtual-trades/{id}/pause`** | Role: USER

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
    "modifiedDate": "2024-01-01T02:00:00Z"
  }
}
```

**에러:**
| 코드 | 상황 |
|------|------|
| `VT001` | 가상거래 등록 없음 |
| `VT003` | STOPPED 상태 |
| `VT004` | ACTIVE 상태가 아니어서 일시정지 불가 |

---

## 가상거래 종료
**`PUT /virtual-trades/{id}/stop`** | Role: USER

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
    "modifiedDate": "2024-01-01T03:00:00Z"
  }
}
```

**에러:**
| 코드 | 상황 |
|------|------|
| `VT001` | 가상거래 등록 없음 |
| `VT003` | 이미 STOPPED 상태 |

---

## 분석 대상 심볼 수정
**`PUT /virtual-trades/{id}/symbols`** | Role: USER

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
    "modifiedDate": "2024-01-01T04:00:00Z"
  }
}
```

**에러:**
| 코드 | 상황 |
|------|------|
| `VT001` | 가상거래 등록 없음 |
| `VT003` | STOPPED 상태에서는 수정 불가 |
| `VT006` | symbolIdentifiers는 최소 1개 이상 필요 |

---

## 에러 코드 요약

| 코드 | 상수 | HTTP | 설명 |
|------|------|------|------|
| `VT001` | `REGISTRATION_NOT_FOUND` | 404 | 가상거래 등록 없음 |
| `VT002` | `ALREADY_REGISTERED` | 409 | 해당 Agent는 이미 가상거래에 등록됨 |
| `VT003` | `REGISTRATION_STOPPED` | 409 | STOPPED 상태는 재활성화 불가 |
| `VT004` | `REGISTRATION_NOT_ACTIVE` | 409 | ACTIVE 상태가 아니어서 일시정지 불가 |
| `VT005` | `REGISTRATION_NOT_PAUSED` | 409 | PAUSED 상태가 아니어서 재활성화 불가 |
| `VT006` | `SYMBOL_IDS_EMPTY` | 400 | symbolIdentifiers는 최소 1개 이상 필요 |
| `VT007` | `CURRENT_PRICE_UNAVAILABLE` | 502 | Market Service에서 현재가 조회 실패 |
