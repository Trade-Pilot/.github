# User Service - 시퀀스 다이어그램

> User Service의 주요 시나리오별 상호작용 흐름

---

## 1. 회원가입 플로우

이메일 인증 없이 가입 즉시 `ACTIVE` 상태로 생성된다.

```mermaid
sequenceDiagram
    participant Client
    participant GW as API Gateway
    participant US as UserCommandService
    participant DB as Database

    Client->>GW: POST /auth/sign-up
    Note over GW: JWT 검증 불필요 (public endpoint)
    GW->>US: SignUpCommand(email, password, name)

    activate US
    US->>DB: SELECT user WHERE email = ?
    alt 이메일 중복
        DB-->>US: User found
        US-->>GW: 409 EMAIL_ALREADY_EXISTS
        GW-->>Client: 409 Conflict
    else 신규 이메일
        DB-->>US: null

        US->>US: UserFactory.create(email, bcrypt(password), name)
        Note over US: status = ACTIVE (이메일 인증 없음)

        US->>DB: BEGIN TRANSACTION
        US->>DB: INSERT user (status = ACTIVE)
        US->>DB: COMMIT

        US-->>GW: 201 Created (userId)
        GW-->>Client: 201 Created
    end
    deactivate US
```

---

## 2. 로그인 플로우

```mermaid
sequenceDiagram
    participant Client
    participant GW as API Gateway
    participant US as UserCommandService
    participant DB as Database

    Client->>GW: POST /auth/sign-in
    Note over Client: Body: email + password
    GW->>US: SignInCommand(email, password)

    activate US
    US->>DB: SELECT user WHERE email = ?
    alt 사용자 없음
        US-->>GW: 401 INVALID_PASSWORD
        GW-->>Client: 401 Unauthorized
    else 사용자 있음
        US->>US: bcrypt.verify(password, user.passwordHash)
        alt 비밀번호 불일치
            US-->>GW: 401 INVALID_PASSWORD
            GW-->>Client: 401 Unauthorized
        else 비밀번호 일치
            US->>US: user.status 검증
            alt SUSPENDED
                US-->>GW: 403 ACCOUNT_SUSPENDED
                GW-->>Client: 403 Forbidden
            else WITHDRAWN
                US-->>GW: 403 ACCOUNT_WITHDRAWN
                GW-->>Client: 403 Forbidden
            else ACTIVE
                US->>US: JWT AccessToken 생성 (RS256, 15분)
                US->>US: RefreshTokenFactory.create(userId, jti=UUID)

                US->>DB: BEGIN TRANSACTION
                US->>DB: INSERT refresh_token (SHA-256 hash)
                US->>DB: COMMIT

                US-->>GW: 200 OK
                Note over US: AccessToken (body), RefreshToken (HttpOnly Cookie)
                GW-->>Client: 200 OK (AccessToken + Set-Cookie)
            end
        end
    end
    deactivate US
```

---

## 3. 토큰 갱신 플로우

```mermaid
sequenceDiagram
    participant Client
    participant GW as API Gateway
    participant US as UserCommandService
    participant DB as Database

    Client->>GW: POST /auth/refresh
    Note over Client: Cookie: refreshToken

    GW->>US: RefreshCommand(refreshToken)

    activate US
    US->>US: refreshToken에서 jti 추출

    US->>DB: SELECT refresh_token WHERE identifier = jti
    alt 토큰 없음
        US-->>GW: 401 REFRESH_TOKEN_NOT_FOUND
        GW-->>Client: 401 Unauthorized
    else 토큰 있음
        US->>US: token.isValid() 검증
        Note over US: 만료 여부 + revoked 여부 확인

        alt 유효하지 않음 (만료 또는 revoked)
            US-->>GW: 401 REFRESH_TOKEN_EXPIRED or REVOKED
            GW-->>Client: 401 Unauthorized
        else 유효
            US->>DB: SELECT user WHERE identifier = token.userIdentifier
            Note over US: 탈퇴/정지 여부 재확인

            US->>DB: BEGIN TRANSACTION
            US->>US: token.revoke()
            US->>DB: UPDATE refresh_token SET is_revoked = true

            US->>US: 새 AccessToken 생성 (RS256, 15분)
            US->>US: 새 RefreshToken 생성 (jti = 새 UUID)
            US->>DB: INSERT new refresh_token
            US->>DB: COMMIT

            US-->>GW: 200 OK (새 AccessToken + 새 Cookie)
            GW-->>Client: 200 OK
        end
    end
    deactivate US
```

### 동시성: Refresh Token 중복 사용 방어

```mermaid
sequenceDiagram
    participant C1 as Client A
    participant C2 as Client B (동일 토큰)
    participant DB as Database

    Note over C1,C2: 동일 refreshToken으로 동시에 갱신 요청

    C1->>DB: SELECT refresh_token (is_revoked=false) OK
    C2->>DB: SELECT refresh_token (is_revoked=false) OK

    C1->>DB: UPDATE is_revoked = true (성공)
    C2->>DB: UPDATE is_revoked = true (이미 true)

    Note over C1: 새 AccessToken + RefreshToken 발급 성공
    Note over C2: token.isValid() = false → 401 REVOKED
```

> `SELECT FOR UPDATE` 없이 낙관적 접근.
> 두 번째 요청은 `isRevoked = true`로 거부된다.
> 탈취 감지 시 해당 userId의 전체 RefreshToken을 revoke 처리하는 것을 권장한다.

---

## 4. 로그아웃 플로우

```mermaid
sequenceDiagram
    participant Client
    participant GW as API Gateway
    participant US as UserCommandService
    participant DB as Database

    Client->>GW: POST /auth/sign-out
    Note over GW: JWT 검증 → X-User-Id 헤더 추가
    GW->>US: SignOutCommand(refreshToken from Cookie)

    activate US
    US->>US: refreshToken에서 jti 추출

    US->>DB: BEGIN TRANSACTION
    US->>DB: SELECT refresh_token WHERE identifier = jti
    US->>US: token.revoke()
    US->>DB: UPDATE refresh_token SET is_revoked = true
    US->>DB: COMMIT

    US-->>GW: 204 No Content
    Note over GW: Set-Cookie 만료 처리 (Max-Age 0)
    GW-->>Client: 204 No Content
    deactivate US
```

---

## 5. 회원 탈퇴 플로우

탈퇴는 `UserWithdrawnEvent`를 Outbox 패턴으로 발행하여 각 서비스의 데이터 정리를 트리거한다.

```mermaid
sequenceDiagram
    participant Client
    participant GW as API Gateway
    participant US as UserCommandService
    participant DB as Database
    participant Relay as OutboxRelayProcessor
    participant Kafka as Kafka

    Client->>GW: DELETE /users/me
    Note over Client: Body: password (비밀번호 재확인)
    Note over GW: JWT 검증 → X-User-Id 헤더

    GW->>US: WithdrawCommand(userId, password)

    activate US
    US->>DB: SELECT user WHERE identifier = userId

    US->>US: bcrypt.verify(password, user.passwordHash)
    alt 비밀번호 불일치
        US-->>GW: 401 INVALID_PASSWORD
        GW-->>Client: 401 Unauthorized
    else 비밀번호 일치
        US->>DB: BEGIN TRANSACTION

        US->>DB: SELECT user FOR UPDATE
        US->>US: user.withdraw()
        Note over US: status = WITHDRAWN

        US->>DB: UPDATE user SET status = WITHDRAWN

        US->>DB: UPDATE refresh_token SET is_revoked = true
        Note over DB: WHERE user_identifier = userId

        US->>US: OutboxEventFactory.create(UserWithdrawnEvent)
        Note over US: traceId 캡처 (MDC)
        US->>DB: INSERT outbox (status=PENDING, traceId 포함)

        US->>DB: COMMIT

        US-->>GW: 204 No Content
        Note over GW: Set-Cookie 만료 처리 (Max-Age 0)
        GW-->>Client: 204 No Content
    end
    deactivate US

    Note over Relay: Outbox 폴링 (100ms)
    Relay->>DB: SELECT outbox WHERE status = PENDING
    Relay->>Kafka: USER_WITHDRAWN_EVENT_TOPIC
    Note over Kafka: userId, withdrawnAt
    Relay->>DB: UPDATE status = PUBLISHED
```

---

## 6. JWKS 엔드포인트

API Gateway가 JWT 서명 검증에 사용하는 Public Key를 JWK Set 형식으로 제공한다.

```mermaid
sequenceDiagram
    participant GW as API Gateway
    participant US as User Service

    Note over GW: 서버 시작 시 또는 캐시 만료 시 (1시간)

    GW->>US: GET /auth/.well-known/jwks.json
    Note over GW: 인증 불필요 (public endpoint)

    activate US
    US->>US: RSA Public Key 조회 (메모리 캐시)
    US-->>GW: 200 OK
    deactivate US
```

**응답 형식 (JWK Set)**:
```json
{
  "keys": [
    {
      "kty": "RSA",
      "use": "sig",
      "alg": "RS256",
      "kid": "key-2024-01",
      "n": "...",
      "e": "AQAB"
    }
  ]
}
```

> `kid` (Key ID)를 포함하여 키 로테이션 시 구버전/신버전 키를 동시에 제공할 수 있다.

---

## 7. 트랜잭션 범위

### 7.1 회원가입

```
BEGIN
  INSERT user (ACTIVE)
COMMIT
```

### 7.2 로그인

```
비밀번호 검증 (트랜잭션 없음)
BEGIN
  INSERT refresh_token
COMMIT
→ AccessToken 반환 (트랜잭션 외부)
```

### 7.3 토큰 갱신

```
BEGIN
  UPDATE refresh_token (revoke 기존)
  INSERT refresh_token (신규)
COMMIT
→ Token 반환 (트랜잭션 외부)
```

### 7.4 로그아웃

```
BEGIN
  UPDATE refresh_token (revoke)
COMMIT
```

### 7.5 회원 탈퇴

```
BEGIN
  UPDATE user (WITHDRAWN)
  UPDATE refresh_token (전체 revoke)
  INSERT outbox (UserWithdrawnEvent + traceId)
COMMIT
→ Outbox Relay가 Kafka 발행 (별도 스레드)
```

---

## 8. 예외 처리 플로우

### 8.1 만료된 Access Token으로 요청

```mermaid
sequenceDiagram
    participant Client
    participant GW as API Gateway

    Client->>GW: GET /strategies (만료된 AccessToken)
    Note over GW: JWT 검증 → 만료 확인
    GW-->>Client: 401 Unauthorized
    Note over Client: POST /auth/refresh 호출 후 재시도
```

### 8.2 탈퇴 사용자의 Refresh Token 재사용 시도

```mermaid
sequenceDiagram
    participant Client
    participant GW as API Gateway
    participant US as UserCommandService
    participant DB as Database

    Note over Client: 탈퇴 전 발급된 RefreshToken 사용 시도

    Client->>GW: POST /auth/refresh
    GW->>US: RefreshCommand(refreshToken)

    US->>DB: SELECT refresh_token
    Note over DB: is_revoked = true (탈퇴 시 전체 revoke됨)

    US-->>GW: 401 REFRESH_TOKEN_REVOKED
    GW-->>Client: 401 Unauthorized
```

---

## 참고

- **비밀번호 해싱**: bcrypt (cost factor: 12)
- **Access Token**: RS256, 15분 만료
- **Refresh Token**: SHA-256 해시 DB 저장, 30일 만료, HttpOnly Cookie
- **이메일 인증**: 없음 (가입 즉시 ACTIVE)
- **Outbox**: `withdraw()` → `UserWithdrawnEvent` 발행 보장
- **분산 트레이싱**: Outbox traceId 캡처 → Relay에서 `traceparent` 헤더 복원
