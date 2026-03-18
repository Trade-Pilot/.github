# User Service - 도메인 설계

> 사용자 계정 관리 및 인증/인가를 담당하는 User Service의 도메인 모델 정의

---

## 1. 서비스 책임

**담당**:
- 회원가입 / 로그인 / 로그아웃
- JWT(Access Token) 발급 및 갱신
- 사용자 프로필 관리

**담당하지 않음**:
- 알림 채널 설정 (Discord webhook URL 등) → Notification Service 담당
- 전략/포트폴리오 정보 → Agent Service 담당

---

## 2. Aggregate Root

### 2.1 User (사용자)

**속성**:
```kotlin
class User(
    val identifier: UserId,                 // 고유 식별자 (UUID)
    val email: UserEmail,                   // 이메일 (로그인 ID)
    var passwordHash: String,               // bcrypt 해시
    var name: String,                       // 표시 이름
    val role: UserRole,                     // 권한 (ADMIN, USER)
    var status: UserStatus,                 // 계정 상태
    val createdDate: OffsetDateTime,
    var modifiedDate: OffsetDateTime,
)
```

**비즈니스 로직**:
```kotlin
fun suspend()       // 계정 정지 (SUSPENDED)
fun activate()      // 계정 활성화 (ACTIVE)
fun withdraw()      // 회원 탈퇴 (WITHDRAWN)
fun changePassword(newPasswordHash: String)
fun updateProfile(name: String)
```

**상태 전이**:
```
ACTIVE ⇄ SUSPENDED
ACTIVE → WITHDRAWN   (종료 상태)
SUSPENDED → WITHDRAWN (종료 상태)
```

**불변 조건 (Invariants)**:
- `email`은 변경 불가
- `role`은 변경 불가 (변경 필요 시 Admin이 별도 처리)
- `WITHDRAWN` 상태에서는 어떤 상태로도 전이 불가

**도메인 이벤트**:
- `UserCreatedEvent`: 회원가입 완료
- `UserActivatedEvent`: 계정 활성화
- `UserSuspendedEvent`: 계정 정지
- `UserWithdrawnEvent`: 회원 탈퇴

---

## 3. Entity

### 3.1 RefreshToken (리프레시 토큰)

**목적**: Refresh Token을 DB에 저장하여 탈취 시 즉시 무효화할 수 있도록 한다.

**속성**:
```kotlin
class RefreshToken(
    val identifier: RefreshTokenId,         // 고유 식별자 (UUID = jti claim)
    val userIdentifier: UserId,             // 소유자
    val tokenHash: String,                  // SHA-256 해시 (원문 저장 금지)
    val expiresAt: OffsetDateTime,          // 만료 시각 (발급 + 30일)
    var isRevoked: Boolean = false,         // 명시적 무효화 여부
    val createdAt: OffsetDateTime,
)
```

**비즈니스 로직**:
```kotlin
fun revoke()                    // 토큰 무효화
fun isValid(): Boolean          // 만료 && 미취소 여부 확인
```

**불변 조건 (Invariants)**:
- `tokenHash`는 생성 후 변경 불가
- `expiresAt` 이후에는 `isValid() == false`

---

## 4. Value Object

### 4.1 UserId
```kotlin
@JvmInline
value class UserId(val value: UUID) {
    companion object {
        fun of(value: UUID) = UserId(value)
        fun generate() = UserId(UUID.randomUUID())
    }
}
```

### 4.2 UserEmail
```kotlin
@JvmInline
value class UserEmail(val value: String) {
    init {
        require(value.isNotBlank()) { "Email cannot be blank" }
        require(value.matches(Regex("^[^@]+@[^@]+\\.[^@]+$"))) {
            "Invalid email format"
        }
    }

    companion object {
        fun of(value: String) = UserEmail(value)
    }
}
```

### 4.3 RefreshTokenId
```kotlin
@JvmInline
value class RefreshTokenId(val value: UUID) {
    companion object {
        fun of(value: UUID) = RefreshTokenId(value)
        fun generate() = RefreshTokenId(UUID.randomUUID())
    }
}
```

---

## 5. Enum

### 5.1 UserRole (권한)
```kotlin
enum class UserRole {
    ADMIN,  // 관리자 (수집 작업 제어, 전략 배포 승인 등)
    USER,   // 일반 사용자
}
```

### 5.2 UserStatus (계정 상태)
```kotlin
enum class UserStatus {
    ACTIVE,     // 정상 활성 (회원가입 즉시)
    SUSPENDED,  // 관리자에 의해 정지
    WITHDRAWN,  // 회원 탈퇴
}
```

---

## 6. JWT 전략

### Access Token
- **알고리즘**: RS256 (비대칭키)
- **만료**: 15분
- **Payload**:
```json
{
  "sub": "user-uuid",
  "role": "USER",
  "iat": 1700000000,
  "exp": 1700000900,
  "jti": "token-uuid"
}
```
- **Public Key 배포**: API Gateway가 JWKS 엔드포인트에서 Public Key를 조회하여 자체 검증
  → User Service에 검증 요청 불필요 (트래픽 분산)

### Refresh Token
- **알고리즘**: HMAC-SHA256 (서명 후 jti를 DB에 저장)
- **만료**: 30일
- **저장**: DB에 SHA-256 해시로 저장 (원문 보관 금지)
- **전달**: HttpOnly Cookie

### 토큰 갱신 플로우
```
Client ──▶ POST /auth/refresh (Refresh Token in Cookie)
                │
                ▼
           RefreshToken 조회 (jti로)
                │
           isValid() 검증
                │
           기존 RefreshToken revoke()
                │
           새 AccessToken + RefreshToken 발급
                │
Client ◀── 200 OK (새 AccessToken, 새 RefreshToken in Cookie)
```

---

## 7. Use Case

### 7.1 인증
```kotlin
interface SignUpUseCase {
    fun signUp(command: SignUpCommand): UserId
}

interface SignInUseCase {
    fun signIn(command: SignInCommand): TokenPair
}

interface RefreshTokenUseCase {
    fun refresh(refreshToken: String): TokenPair
}

interface SignOutUseCase {
    fun signOut(refreshTokenId: RefreshTokenId)
}
```

### 7.2 사용자 관리
```kotlin
interface GetUserUseCase {
    fun getUser(userId: UserId): User
}

interface UpdateUserUseCase {
    fun updateProfile(userId: UserId, command: UpdateProfileCommand)
    fun changePassword(userId: UserId, command: ChangePasswordCommand)
}

interface WithdrawUseCase {
    // 본인이 직접 탈퇴. 비밀번호 재확인 후 USER_WITHDRAWN_EVENT_TOPIC 발행 → 각 서비스 데이터 정리
    fun withdraw(command: WithdrawCommand)
}

data class WithdrawCommand(
    val userId: UserId,
    val password: String,   // 비밀번호 재확인용 (평문, bcrypt 검증 후 파기)
)

interface ManageUserUseCase {
    fun suspend(userId: UserId)         // ADMIN only
    fun activate(userId: UserId)        // ADMIN only
}
```

---

## 8. API 엔드포인트

```http
POST /auth/sign-up
→ 회원가입 (이메일 + 비밀번호 + 이름, 즉시 ACTIVE)

POST /auth/sign-in
→ 로그인 (AccessToken 반환, RefreshToken은 HttpOnly Cookie)

POST /auth/refresh
→ AccessToken 갱신 (Cookie의 RefreshToken 사용)

POST /auth/sign-out
→ 로그아웃 (RefreshToken revoke)

DELETE /users/me
→ 회원 탈퇴 (User WITHDRAWN, 모든 RefreshToken revoke, UserWithdrawnEvent 발행)
  ※ 비밀번호 재확인 필요 (Body: password)

GET /auth/.well-known/jwks.json
→ Public Key 배포 (API Gateway가 JWT 서명 검증에 사용)
  응답: JWK Set 형식 (RFC 7517)

GET /users/me
→ 내 프로필 조회

PUT /users/me
→ 내 프로필 수정

PUT /users/me/password
→ 비밀번호 변경

GET /users/{userId}           (ADMIN)
→ 특정 사용자 조회

PUT /users/{userId}/suspend   (ADMIN)
→ 계정 정지

PUT /users/{userId}/activate  (ADMIN)
→ 계정 활성화
```

---

## 9. 데이터베이스 스키마

### user 테이블
```sql
CREATE TABLE "user" (
    identifier    UUID        PRIMARY KEY,
    email         VARCHAR     NOT NULL UNIQUE,
    password_hash VARCHAR     NOT NULL,
    name          VARCHAR     NOT NULL,
    role          VARCHAR     NOT NULL DEFAULT 'USER',
    status        VARCHAR     NOT NULL DEFAULT 'ACTIVE',
    created_date  TIMESTAMP WITH TIME ZONE NOT NULL,
    modified_date TIMESTAMP WITH TIME ZONE NOT NULL
);

CREATE INDEX user_email_idx  ON "user" (email);
CREATE INDEX user_status_idx ON "user" (status);
```

### refresh_token 테이블
```sql
CREATE TABLE refresh_token (
    identifier       UUID    PRIMARY KEY,           -- jti
    user_identifier  UUID    NOT NULL,
    token_hash       VARCHAR NOT NULL,              -- SHA-256 해시
    expires_at       TIMESTAMP WITH TIME ZONE NOT NULL,
    is_revoked       BOOLEAN NOT NULL DEFAULT FALSE,
    created_at       TIMESTAMP WITH TIME ZONE NOT NULL,

    FOREIGN KEY (user_identifier) REFERENCES "user"(identifier)
);

CREATE INDEX refresh_token_user_idx   ON refresh_token (user_identifier);
CREATE INDEX refresh_token_expiry_idx ON refresh_token (expires_at);
```

### outbox 테이블

회원 탈퇴 시 `UserWithdrawnEvent`를 Kafka에 안정적으로 발행하기 위한 Outbox 테이블.
공통 스키마 및 Relay 설계는 [outbox-pattern.md](../outbox-pattern.md) 참조.

```sql
CREATE TABLE outbox (
    id               UUID    PRIMARY KEY,
    aggregate_type   VARCHAR NOT NULL,                    -- User
    aggregate_id     VARCHAR NOT NULL,                    -- User UUID
    event_type       VARCHAR NOT NULL,                    -- USER_WITHDRAWN_EVENT
    payload          TEXT    NOT NULL,
    trace_id         VARCHAR,
    parent_span_id   VARCHAR,
    status           VARCHAR NOT NULL DEFAULT 'PENDING', -- PENDING | PUBLISHED | FAILED | DEAD
    retry_count      INT     NOT NULL DEFAULT 0,
    created_at       TIMESTAMP WITH TIME ZONE NOT NULL,
    published_at     TIMESTAMP WITH TIME ZONE
);

CREATE INDEX outbox_relay_idx ON outbox (created_at)
    WHERE status IN ('PENDING', 'FAILED');

CREATE INDEX outbox_dead_idx ON outbox (created_at)
    WHERE status = 'DEAD';
```

---

## 10. 예외

```kotlin
enum class UserErrorCode(
    override val code: String,
    override val message: String,
) : ErrorCode {
    USER_NOT_FOUND("U001", "User not found"),
    EMAIL_ALREADY_EXISTS("U002", "Email already exists"),
    INVALID_PASSWORD("U003", "Invalid password"),
    ACCOUNT_SUSPENDED("U004", "Account is suspended"),
    ACCOUNT_WITHDRAWN("U005", "Account is withdrawn"),
    REFRESH_TOKEN_NOT_FOUND("U006", "Refresh token not found"),
    REFRESH_TOKEN_EXPIRED("U007", "Refresh token expired"),
    REFRESH_TOKEN_REVOKED("U008", "Refresh token revoked"),
}
```

---

## 11. 도메인 관계

```
User (1) ──< (N) RefreshToken
```

**생명주기**:
1. `signUp()` → `User` 생성 (`ACTIVE` 상태, 즉시 사용 가능)
2. `signIn()` → `RefreshToken` 생성
3. `signOut()` → `refreshToken.revoke()`
4. `withdraw()` → `User` WITHDRAWN, 모든 `RefreshToken` revoke
