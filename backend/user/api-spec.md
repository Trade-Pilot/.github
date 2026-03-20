# User Service - REST API 명세

> 사용자 계정 관리 및 인증/인가 관련 REST API 정의

---

## 공통

### 응답 래퍼

```json
// 성공 (단건)
{ "data": { ... } }

// 에러
{
  "code": "U001",
  "message": "User not found",
  "timestamp": "2026-03-20T12:00:00Z",
  "path": "/users/me",
  "details": null
}
```

### 인증 헤더

```
Authorization: Bearer <AccessToken>
```

---

## 1. 인증 (Auth)

### 회원가입
**`POST /auth/sign-up`** | Role: PUBLIC

**Request:**
```json
{
  "email": "user@example.com",
  "password": "secureP@ss1",
  "name": "홍길동"
}
```

| 필드 | 타입 | 필수 | 제약조건 |
|------|------|------|----------|
| `email` | `string` | O | 이메일 형식 (`^[^@]+@[^@]+\.[^@]+$`), 중복 불가 |
| `password` | `string` | O | 최소 8자, 영문+숫자+특수문자 조합 |
| `name` | `string` | O | 1~50자 |

**Response:** `201 Created`
```json
{
  "data": {
    "userIdentifier": "550e8400-e29b-41d4-a716-446655440000"
  }
}
```

**에러:**

| 코드 | 상황 |
|------|------|
| `U002` | 이미 등록된 이메일 |

---

### 로그인
**`POST /auth/sign-in`** | Role: PUBLIC

**Request:**
```json
{
  "email": "user@example.com",
  "password": "secureP@ss1"
}
```

| 필드 | 타입 | 필수 | 제약조건 |
|------|------|------|----------|
| `email` | `string` | O | 이메일 형식 |
| `password` | `string` | O | - |

**Response:** `200 OK`
```json
{
  "data": {
    "accessToken": "eyJhbGciOiJSUzI1NiIs...",
    "expiresIn": 900
  }
}
```

> RefreshToken은 `Set-Cookie` 헤더로 전달 (HttpOnly, Secure, SameSite=Strict, Max-Age=2592000)

**에러:**

| 코드 | 상황 |
|------|------|
| `U001` | 존재하지 않는 사용자 |
| `U003` | 비밀번호 불일치 |
| `U004` | 정지된 계정으로 로그인 시도 |
| `U005` | 탈퇴한 계정으로 로그인 시도 |

---

### 토큰 갱신
**`POST /auth/refresh`** | Role: PUBLIC (Cookie)

**Request:**
- Body 없음
- RefreshToken은 `Cookie` 헤더에서 자동 전달

**Response:** `200 OK`
```json
{
  "data": {
    "accessToken": "eyJhbGciOiJSUzI1NiIs...",
    "expiresIn": 900
  }
}
```

> 기존 RefreshToken은 revoke 처리되고, 새 RefreshToken이 `Set-Cookie`로 전달

**에러:**

| 코드 | 상황 |
|------|------|
| `U006` | RefreshToken을 찾을 수 없음 |
| `U007` | RefreshToken 만료 |
| `U008` | 이미 revoke된 RefreshToken |

---

### 로그아웃
**`POST /auth/sign-out`** | Role: USER

**Request:**
- Body 없음
- RefreshToken은 `Cookie` 헤더에서 자동 전달

**Response:** `204 No Content`

> RefreshToken을 revoke 처리하고, `Set-Cookie`로 쿠키 삭제 (Max-Age=0)

**에러:**

| 코드 | 상황 |
|------|------|
| `U006` | RefreshToken을 찾을 수 없음 |

---

### JWKS (Public Key 배포)
**`GET /auth/.well-known/jwks.json`** | Role: PUBLIC

**Request:**
- 파라미터 없음

**Response:** `200 OK`
```json
{
  "keys": [
    {
      "kty": "RSA",
      "alg": "RS256",
      "use": "sig",
      "kid": "key-id-001",
      "n": "0vx7agoebGcQSuuPiLJXZpt...",
      "e": "AQAB"
    }
  ]
}
```

> RFC 7517 JWK Set 형식. API Gateway가 AccessToken 서명 검증에 사용한다.

---

## 2. 사용자 관리 (Users)

### 내 프로필 조회
**`GET /users/me`** | Role: USER

**Request:**
- 파라미터 없음

**Response:** `200 OK`
```json
{
  "data": {
    "userIdentifier": "550e8400-e29b-41d4-a716-446655440000",
    "email": "user@example.com",
    "name": "홍길동",
    "role": "USER",
    "status": "ACTIVE",
    "createdDate": "2026-01-15T10:30:00Z",
    "modifiedDate": "2026-03-20T08:00:00Z"
  }
}
```

**에러:**

| 코드 | 상황 |
|------|------|
| `U001` | 사용자를 찾을 수 없음 (토큰의 sub에 해당하는 사용자 없음) |

---

### 내 프로필 수정
**`PUT /users/me`** | Role: USER

**Request:**
```json
{
  "name": "김철수"
}
```

| 필드 | 타입 | 필수 | 제약조건 |
|------|------|------|----------|
| `name` | `string` | O | 1~50자 |

**Response:** `200 OK`
```json
{
  "data": {
    "userIdentifier": "550e8400-e29b-41d4-a716-446655440000",
    "email": "user@example.com",
    "name": "김철수",
    "role": "USER",
    "status": "ACTIVE",
    "createdDate": "2026-01-15T10:30:00Z",
    "modifiedDate": "2026-03-20T12:00:00Z"
  }
}
```

**에러:**

| 코드 | 상황 |
|------|------|
| `U001` | 사용자를 찾을 수 없음 |

---

### 비밀번호 변경
**`PUT /users/me/password`** | Role: USER

**Request:**
```json
{
  "currentPassword": "secureP@ss1",
  "newPassword": "newSecureP@ss2"
}
```

| 필드 | 타입 | 필수 | 제약조건 |
|------|------|------|----------|
| `currentPassword` | `string` | O | 현재 비밀번호 확인용 |
| `newPassword` | `string` | O | 최소 8자, 영문+숫자+특수문자 조합, 현재 비밀번호와 다를 것 |

**Response:** `204 No Content`

**에러:**

| 코드 | 상황 |
|------|------|
| `U001` | 사용자를 찾을 수 없음 |
| `U003` | 현재 비밀번호 불일치 |

---

### 회원 탈퇴
**`DELETE /users/me`** | Role: USER

**Request:**
```json
{
  "password": "secureP@ss1"
}
```

| 필드 | 타입 | 필수 | 제약조건 |
|------|------|------|----------|
| `password` | `string` | O | 비밀번호 재확인용 |

**Response:** `204 No Content`

> User 상태를 WITHDRAWN으로 변경하고, 모든 RefreshToken을 revoke 처리한 뒤 `UserWithdrawnEvent`를 발행한다.

**에러:**

| 코드 | 상황 |
|------|------|
| `U001` | 사용자를 찾을 수 없음 |
| `U003` | 비밀번호 불일치 |

---

### 특정 사용자 조회
**`GET /users/{userIdentifier}`** | Role: ADMIN

**Path Parameter:**

| 필드 | 타입 | 필수 | 설명 |
|------|------|------|------|
| `userIdentifier` | `UUID` | O | 조회 대상 사용자 식별자 |

**Response:** `200 OK`
```json
{
  "data": {
    "userIdentifier": "550e8400-e29b-41d4-a716-446655440000",
    "email": "user@example.com",
    "name": "홍길동",
    "role": "USER",
    "status": "ACTIVE",
    "createdDate": "2026-01-15T10:30:00Z",
    "modifiedDate": "2026-03-20T08:00:00Z"
  }
}
```

**에러:**

| 코드 | 상황 |
|------|------|
| `U001` | 사용자를 찾을 수 없음 |

---

### 계정 정지
**`PUT /users/{userIdentifier}/suspend`** | Role: ADMIN

**Path Parameter:**

| 필드 | 타입 | 필수 | 설명 |
|------|------|------|------|
| `userIdentifier` | `UUID` | O | 대상 사용자 식별자 |

**Request:**
- Body 없음

**Response:** `200 OK`
```json
{
  "data": {
    "userIdentifier": "550e8400-e29b-41d4-a716-446655440000",
    "status": "SUSPENDED"
  }
}
```

> 상태가 ACTIVE인 사용자만 정지 가능. WITHDRAWN 상태에서는 전이 불가.

**에러:**

| 코드 | 상황 |
|------|------|
| `U001` | 사용자를 찾을 수 없음 |
| `U005` | 탈퇴한 계정은 상태 변경 불가 |

---

### 계정 활성화
**`PUT /users/{userIdentifier}/activate`** | Role: ADMIN

**Path Parameter:**

| 필드 | 타입 | 필수 | 설명 |
|------|------|------|------|
| `userIdentifier` | `UUID` | O | 대상 사용자 식별자 |

**Request:**
- Body 없음

**Response:** `200 OK`
```json
{
  "data": {
    "userIdentifier": "550e8400-e29b-41d4-a716-446655440000",
    "status": "ACTIVE"
  }
}
```

> 상태가 SUSPENDED인 사용자만 활성화 가능. WITHDRAWN 상태에서는 전이 불가.

**에러:**

| 코드 | 상황 |
|------|------|
| `U001` | 사용자를 찾을 수 없음 |
| `U005` | 탈퇴한 계정은 상태 변경 불가 |

---

## 에러 코드 요약

| 코드 | 상수 | 설명 |
|------|------|------|
| `U001` | `USER_NOT_FOUND` | 사용자를 찾을 수 없음 |
| `U002` | `EMAIL_ALREADY_EXISTS` | 이미 등록된 이메일 |
| `U003` | `INVALID_PASSWORD` | 비밀번호 불일치 |
| `U004` | `ACCOUNT_SUSPENDED` | 정지된 계정 |
| `U005` | `ACCOUNT_WITHDRAWN` | 탈퇴한 계정 |
| `U006` | `REFRESH_TOKEN_NOT_FOUND` | RefreshToken을 찾을 수 없음 |
| `U007` | `REFRESH_TOKEN_EXPIRED` | RefreshToken 만료 |
| `U008` | `REFRESH_TOKEN_REVOKED` | 이미 revoke된 RefreshToken |
