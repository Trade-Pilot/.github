# Auth - 프론트엔드 설계

> 회원가입, 로그인, 프로필 관리 및 인증 상태 관리 설계

---

## 1. 개요

인증은 Trade Pilot의 모든 기능 접근의 시작점이다.
Access Token은 메모리(Zustand)에만 보관하고, Refresh Token은 HttpOnly Cookie로 관리한다.

| 토큰 종류 | 저장 위치 | 만료 | 비고 |
|-----------|-----------|------|------|
| Access Token | Zustand 메모리 | 15분 (`expiresIn: 900`) | `localStorage` 저장 금지 (XSS 방지) |
| Refresh Token | HttpOnly Cookie | 30일 | `Secure`, `SameSite=Strict`, JS 접근 불가 |

---

## 2. FSD 디렉토리 구조

```text
src/
├── pages/
│   ├── sign-up/                   # 회원가입 페이지
│   ├── sign-in/                   # 로그인 페이지
│   └── profile-settings/          # 프로필 수정 + 비밀번호 변경 + 회원 탈퇴
│
├── features/
│   ├── sign-up/                   # 회원가입 폼 액션
│   ├── sign-in/                   # 로그인 폼 액션
│   ├── sign-out/                  # 로그아웃 액션
│   ├── change-password/           # 비밀번호 변경 액션
│   └── withdraw-account/          # 회원 탈퇴 액션 (2중 확인)
│
└── entities/
    └── user/                      # User 도메인 슬라이스
        ├── api/                   # authApi (sign-up, sign-in, refresh, sign-out)
        ├── model/                 # schemas.ts (User, TokenPair), params.ts
        ├── queries/               # useUserQuery
        └── store/                 # authStore.ts (Zustand)
```

---

## 3. 핵심 기능 설계

### 3.1 회원가입 (`/sign-up`)

**엔드포인트**: `POST /auth/sign-up` (PUBLIC)

- 입력: 이메일, 비밀번호, 이름
- 유효성 검사: Zod + react-hook-form 실시간 검증
  - `email`: 이메일 형식 (`^[^@]+@[^@]+\.[^@]+$`), 중복 불가
  - `password`: 최소 8자, 영문 + 숫자 + 특수문자 조합
  - `name`: 1~50자
- 성공 시: 로그인 페이지로 리다이렉트 + "가입이 완료되었습니다" 토스트
- 에러:

| 코드 | 프론트엔드 처리 |
|------|----------------|
| `U002` (`EMAIL_ALREADY_EXISTS`) | 이메일 필드 인라인 메시지: "이미 등록된 이메일입니다" |

### 3.2 로그인 (`/sign-in`)

**엔드포인트**: `POST /auth/sign-in` (PUBLIC)

- 입력: 이메일, 비밀번호
- 성공 시:
  1. Access Token -> Zustand authStore에 저장 (메모리)
  2. Refresh Token -> HttpOnly Cookie (서버가 `Set-Cookie` 헤더로 전달)
  3. `GET /users/me`로 User 정보 조회 -> Zustand authStore + persist (localStorage)
  4. 대시보드로 리다이렉트
- 에러:

| 코드 | 프론트엔드 처리 |
|------|----------------|
| `U001` (`USER_NOT_FOUND`) | "이메일 또는 비밀번호가 올바르지 않습니다" |
| `U003` (`INVALID_PASSWORD`) | "이메일 또는 비밀번호가 올바르지 않습니다" |
| `U004` (`ACCOUNT_SUSPENDED`) | "계정이 정지되었습니다. 관리자에게 문의하세요" |
| `U005` (`ACCOUNT_WITHDRAWN`) | "탈퇴한 계정입니다" |

> U001과 U003은 보안상 동일한 메시지를 노출한다. 존재 여부를 유추할 수 없도록 한다.

### 3.3 토큰 갱신 (자동)

**엔드포인트**: `POST /auth/refresh` (PUBLIC, Cookie)

- Access Token 만료(15분) 직전에 Axios 인터셉터에서 자동 갱신
- Cookie의 Refresh Token이 자동 전송됨 (Body 없음)
- 성공: 새 Access Token으로 갱신 + 원래 요청 재실행
  - 기존 Refresh Token은 서버에서 revoke 처리되고, 새 Refresh Token이 `Set-Cookie`로 전달
- 실패 시 로그아웃 처리 -> 로그인 페이지 리다이렉트

| 코드 | 의미 |
|------|------|
| `U006` (`REFRESH_TOKEN_NOT_FOUND`) | RefreshToken을 찾을 수 없음 |
| `U007` (`REFRESH_TOKEN_EXPIRED`) | RefreshToken 만료 |
| `U008` (`REFRESH_TOKEN_REVOKED`) | 이미 revoke된 RefreshToken |

**구현 패턴**:

```typescript
// shared/api/tokenRefresh.ts
let refreshPromise: Promise<string> | null = null

export async function tryRefreshToken(): Promise<string | null> {
  if (refreshPromise) return refreshPromise  // 동시 요청 방지

  refreshPromise = authApi.refresh()
    .then(({ accessToken }) => {
      useAuthStore.getState().setToken(accessToken)
      return accessToken
    })
    .catch(() => {
      useAuthStore.getState().logout()
      return null
    })
    .finally(() => { refreshPromise = null })

  return refreshPromise
}
```

> 동시에 여러 API가 401을 받아도 refresh 요청은 한 번만 발생한다.

### 3.4 로그아웃

**엔드포인트**: `POST /auth/sign-out` (USER, Cookie)

1. `POST /auth/sign-out` 호출 (Refresh Token revoke, 서버가 `Set-Cookie: Max-Age=0`으로 쿠키 삭제)
2. Zustand authStore 초기화
3. BroadcastChannel로 `AUTH_LOGOUT` 이벤트 전파 -> 다른 탭도 로그아웃
4. 로그인 페이지로 리다이렉트

| 코드 | 의미 |
|------|------|
| `U006` (`REFRESH_TOKEN_NOT_FOUND`) | RefreshToken을 찾을 수 없음 (이미 로그아웃 상태) |

### 3.5 프로필 관리 (`/profile-settings`)

#### 프로필 수정

**엔드포인트**: `PUT /users/me` (USER)

- 입력: 이름 (1~50자)
- 성공 시: User 정보 갱신 + "프로필이 수정되었습니다" 토스트

| 코드 | 프론트엔드 처리 |
|------|----------------|
| `U001` (`USER_NOT_FOUND`) | 로그아웃 처리 (세션 무효) |

#### 비밀번호 변경

**엔드포인트**: `PUT /users/me/password` (USER)

- 입력: 현재 비밀번호 + 새 비밀번호 (최소 8자, 영문 + 숫자 + 특수문자 조합, 현재 비밀번호와 다를 것)
- 성공 시 (204): "비밀번호가 변경되었습니다" 토스트

| 코드 | 프론트엔드 처리 |
|------|----------------|
| `U001` (`USER_NOT_FOUND`) | 로그아웃 처리 (세션 무효) |
| `U003` (`INVALID_PASSWORD`) | "현재 비밀번호가 올바르지 않습니다" |

#### 회원 탈퇴

**엔드포인트**: `DELETE /users/me` (USER)

- 입력: 비밀번호 재확인
- 플로우: 비밀번호 입력 -> 1차 확인 모달 -> 2차 확인 모달("정말 탈퇴하시겠습니까?") -> API 호출
- 성공 시 (204):
  - 서버: User 상태 WITHDRAWN 변경, 모든 RefreshToken revoke, `UserWithdrawnEvent` 발행
  - 클라이언트: 모든 탭 로그아웃 (BroadcastChannel) + "탈퇴가 완료되었습니다" 안내 페이지

| 코드 | 프론트엔드 처리 |
|------|----------------|
| `U001` (`USER_NOT_FOUND`) | 로그아웃 처리 (세션 무효) |
| `U003` (`INVALID_PASSWORD`) | "비밀번호가 올바르지 않습니다" |

### 3.6 인증 상태 가드 (Route Guard)

```typescript
// app/router/AuthGuard.tsx
export const AuthGuard = ({ children }: { children: React.ReactNode }) => {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated)
  const location = useLocation()

  if (!isAuthenticated) {
    return <Navigate to="/sign-in" state={{ from: location }} replace />
  }

  return <>{children}</>
}

// ADMIN 전용
export const AdminGuard = ({ children }: { children: React.ReactNode }) => {
  const role = useAuthStore((s) => s.user?.role)
  if (role !== 'ADMIN') return <Navigate to="/" replace />
  return <>{children}</>
}
```

- `AuthGuard`: 미인증 사용자를 `/sign-in`으로 리다이렉트. `state.from`에 원래 경로를 저장하여 로그인 후 복귀.
- `AdminGuard`: `ADMIN` 역할이 아닌 사용자를 홈으로 리다이렉트.

---

## 4. 도메인 모델

```typescript
// entities/user/model/schemas.ts
export const UserSchema = z.object({
  userIdentifier: z.string().uuid(),
  email:          z.string().email(),
  name:           z.string().min(1).max(50),
  role:           z.enum(['ADMIN', 'USER']),
  status:         z.enum(['ACTIVE', 'SUSPENDED', 'WITHDRAWN']),
  createdDate:    z.string().datetime(),
  modifiedDate:   z.string().datetime(),
})

export type User = z.infer<typeof UserSchema>

// entities/user/model/params.ts
export const SignUpParamsSchema = z.object({
  email:    z.string().email(),
  password: z.string().min(8).regex(
    /^(?=.*[A-Za-z])(?=.*\d)(?=.*[@$!%*#?&])/,
    '영문, 숫자, 특수문자를 모두 포함해야 합니다'
  ),
  name:     z.string().min(1).max(50),
})

export type SignUpParams = z.infer<typeof SignUpParamsSchema>

export const SignInParamsSchema = z.object({
  email:    z.string().email(),
  password: z.string().min(1),
})

export type SignInParams = z.infer<typeof SignInParamsSchema>

export const ChangePasswordParamsSchema = z.object({
  currentPassword: z.string().min(1),
  newPassword:     z.string().min(8).regex(
    /^(?=.*[A-Za-z])(?=.*\d)(?=.*[@$!%*#?&])/,
    '영문, 숫자, 특수문자를 모두 포함해야 합니다'
  ),
})

export type ChangePasswordParams = z.infer<typeof ChangePasswordParamsSchema>

export const WithdrawParamsSchema = z.object({
  password: z.string().min(1),
})

export type WithdrawParams = z.infer<typeof WithdrawParamsSchema>
```

---

## 5. Zustand Auth Store

```typescript
// entities/user/store/authStore.ts
interface AuthState {
  token:           string | null
  user:            User | null
  isAuthenticated: boolean

  setAuth:   (token: string, user: User) => void
  setToken:  (token: string) => void
  logout:    () => void
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      token: null,
      user: null,
      isAuthenticated: false,

      setAuth: (token, user) => set({ token, user, isAuthenticated: true }),
      setToken: (token) => set({ token }),
      logout: () => {
        set({ token: null, user: null, isAuthenticated: false })
        broadcastChannel.postMessage({ type: 'AUTH_LOGOUT' })
      },
    }),
    {
      name: 'trade-pilot-auth',
      partialize: (state) => ({ user: state.user }),  // token은 persist 제외 (XSS 방지)
    }
  )
)
```

> `token`은 `partialize`에서 제외하여 `localStorage`에 저장하지 않는다. 새로고침 시 Refresh Token으로 재발급받는다.

---

## 6. API 함수 명세

```typescript
// entities/user/api/authApi.ts
export const authApi = {
  signUp:   (params: SignUpParams) =>
    apiClient.post<{ userIdentifier: string }>('/auth/sign-up', params),

  signIn:   (params: SignInParams) =>
    apiClient.post<{ accessToken: string; expiresIn: number }>('/auth/sign-in', params),

  refresh:  () =>
    apiClient.post<{ accessToken: string; expiresIn: number }>('/auth/refresh'),

  signOut:  () =>
    apiClient.post<void>('/auth/sign-out'),
}

// entities/user/api/userApi.ts
export const userApi = {
  getMe:            () =>
    apiClient.get<User>('/users/me'),

  updateMe:         (params: { name: string }) =>
    apiClient.put<User>('/users/me', params),

  changePassword:   (params: ChangePasswordParams) =>
    apiClient.put<void>('/users/me/password', params),

  withdraw:         (params: WithdrawParams) =>
    apiClient.delete<void>('/users/me', { data: params }),
}
```

---

## 7. BroadcastChannel 멀티 탭 동기화

```typescript
// shared/lib/broadcastChannel.ts
const channel = new BroadcastChannel('trade-pilot')

channel.onmessage = (event) => {
  if (event.data.type === 'AUTH_LOGOUT') {
    useAuthStore.getState().logout()
    window.location.href = '/sign-in'
  }
}

export { channel as broadcastChannel }
```

동기화 대상 이벤트:
- `AUTH_LOGOUT`: 로그아웃 / 회원 탈퇴 시 모든 탭에서 즉시 세션 종료

---

## 8. 에러 코드 - 프론트엔드 매핑 요약

| 코드 | 상수 | 발생 엔드포인트 | 프론트엔드 처리 |
|------|------|----------------|----------------|
| `U001` | `USER_NOT_FOUND` | sign-in, users/me, password, withdraw | 로그인: 통합 메시지 / 그 외: 로그아웃 |
| `U002` | `EMAIL_ALREADY_EXISTS` | sign-up | 이메일 필드 인라인 에러 |
| `U003` | `INVALID_PASSWORD` | sign-in, password, withdraw | 로그인: 통합 메시지 / 그 외: 비밀번호 에러 |
| `U004` | `ACCOUNT_SUSPENDED` | sign-in | "계정이 정지되었습니다" 안내 |
| `U005` | `ACCOUNT_WITHDRAWN` | sign-in | "탈퇴한 계정입니다" 안내 |
| `U006` | `REFRESH_TOKEN_NOT_FOUND` | refresh, sign-out | 로그아웃 처리 |
| `U007` | `REFRESH_TOKEN_EXPIRED` | refresh | 로그아웃 처리 |
| `U008` | `REFRESH_TOKEN_REVOKED` | refresh | 로그아웃 처리 |
