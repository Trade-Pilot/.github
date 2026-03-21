<!-- 원본: frontend/setup.md — 섹션 8~10 -->

# shared/utils 유틸리티, API 클라이언트, 전역 상태

> 숫자 포맷, 클래스 유틸, Axios 인스턴스, Zustand 스토어

---

## 8. 공용 유틸 (`shared/utils/`)

### 8.1 숫자 포맷 (`formatNumber.ts`)

```typescript
// 가격 (KRW)
formatPrice(95_000_000)        // → "95,000,000"
formatPrice(95_000_000, 'KRW') // → "95,000,000 KRW"
formatPriceCompact(95_000_000) // → "9500만" (대시보드 요약용)

// 거래량
formatVolume(12.45678)         // → "12.4568" (소수 4자리)
formatVolume(0)                // → "0" (Flat Candle)

// 수익률
formatRate(0.0512)             // → "+5.12%"  (양수: + 접두, 초록)
formatRate(-0.0215)            // → "-2.15%"  (음수: 빨강)

// 개수
formatCount(1_200)             // → "1,200"

// 날짜/시간
formatDateTime(date)           // → "2024-01-15 12:34:56"
formatRelativeTime(date)       // → "3분 전", "방금 전"
formatCandleTime(date, interval) // → 간격별 포맷
                                  //   MIN_1: "12:34"
                                  //   DAY:   "01-15"
                                  //   WEEK:  "01/03주"
                                  //   MONTH: "2024-01"
```

### 8.2 클래스 유틸 (`cn.ts`)

```typescript
// clsx + tailwind-merge 래퍼
// 조건부 클래스 + Tailwind 충돌 자동 해결

import { clsx, type ClassValue } from 'clsx'
import { twMerge } from 'tailwind-merge'

export const cn = (...inputs: ClassValue[]) => twMerge(clsx(inputs))

// 사용:
// cn('px-4 py-2', isActive && 'bg-brand-600', className)
```

---

## 9. API 클라이언트 (`shared/api/`)

### 9.1 Axios 인스턴스

```typescript
// shared/api/client.ts
export const apiClient = axios.create({
  baseURL: env.API_BASE_URL,
  timeout: 10_000,
  headers: { 'Content-Type': 'application/json' },
})

// 요청 인터셉터: Bearer 토큰 자동 주입
apiClient.interceptors.request.use((config) => {
  const token = useAuthStore.getState().token
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

// 응답 인터셉터: 공통 에러 처리
apiClient.interceptors.response.use(
  (res) => res.data,   // data만 반환
  (err) => {
    const status = err.response?.status
    if (status === 401) {
      useAuthStore.getState().logout()
      window.location.replace('/login')
    }
    // 에러 메시지 표준화
    const message = err.response?.data?.message ?? err.message ?? '알 수 없는 오류'
    return Promise.reject(new ApiError(status, message))
  }
)
```

### 9.2 공통 에러 타입

```typescript
// shared/api/errors.ts
export class ApiError extends Error {
  constructor(
    public status:  number,
    public message: string,
  ) {
    super(message)
    this.name = 'ApiError'
  }
}

export const isApiError    = (e: unknown): e is ApiError => e instanceof ApiError
export const isUnauthorized = (e: unknown) => isApiError(e) && e.status === 401
export const isNotFound     = (e: unknown) => isApiError(e) && e.status === 404
```

### 9.3 API 응답 공통 타입

```typescript
// shared/api/types.ts
// 페이지네이션 응답 래퍼 (백엔드 형식에 맞게 조정)
export interface PageResponse<T> {
  content:  T[]
  hasNext:  boolean
  cursor?:  string
}

// 에러 응답
export interface ApiErrorResponse {
  code:    string
  message: string
  details?: Record<string, string>
}
```

---

## 10. 전역 상태 (`shared/store/`)

### 10.1 인증 스토어

```typescript
// shared/store/authStore.ts
interface AuthState {
  token:           string | null
  user:            User | null
  isAuthenticated: boolean

  setAuth:  (token: string, user: User) => void
  logout:   () => void
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      token:           null,
      user:            null,
      isAuthenticated: false,
      setAuth:  (token, user) => set({ token, user, isAuthenticated: true }),
      logout:   ()            => set({ token: null, user: null, isAuthenticated: false }),
    }),
    {
      name:    'trade-pilot-auth',
      // ⚠️ 보안 정책: AT(Access Token)은 절대 localStorage에 저장하지 않음 (XSS 탈취 위험)
      // token은 Zustand 메모리에만 유지 — 페이지 새로고침 시 재로그인 필요
      partialize: (state) => ({ user: state.user }),    // user 정보만 persist, token 제외
    }
  )
)
```

### 10.2 테마 스토어

```typescript
// shared/store/themeStore.ts
type Theme = 'light' | 'dark' | 'system'

interface ThemeState {
  theme:          Theme
  resolvedTheme:  'light' | 'dark'   // system일 때 실제 적용된 값
  setTheme:       (theme: Theme) => void
}

export const useThemeStore = create<ThemeState>()(
  persist(
    (set, get) => ({
      theme:         'dark',   // 기본값: 다크
      resolvedTheme: 'dark',

      setTheme: (theme) => {
        const resolved = theme === 'system'
          ? (window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light')
          : theme

        // <html> 클래스 전환 → Tailwind darkMode: 'class' 트리거
        document.documentElement.classList.toggle('dark', resolved === 'dark')
        set({ theme, resolvedTheme: resolved })
      },
    }),
    { name: 'trade-pilot-theme', partialize: (s) => ({ theme: s.theme }) }
  )
)

// app/providers.tsx에서 앱 시작 시 테마 초기화
export const initTheme = () => {
  const { theme, setTheme } = useThemeStore.getState()
  setTheme(theme)   // 저장된 값 또는 기본값 적용

  // system 선택 시 OS 테마 변경 감지
  if (theme === 'system') {
    window.matchMedia('(prefers-color-scheme: dark)')
      .addEventListener('change', (e) =>
        document.documentElement.classList.toggle('dark', e.matches)
      )
  }
}
```

**테마 토글 버튼 예시**:
```tsx
// 헤더 or 사이드바 하단에 배치
const ThemeToggle = () => {
  const { resolvedTheme, setTheme } = useThemeStore()

  return (
    <button
      onClick={() => setTheme(resolvedTheme === 'dark' ? 'light' : 'dark')}
      className="p-2 rounded-md hover:bg-bg-elevated text-text-secondary hover:text-text-primary transition-colors"
    >
      {resolvedTheme === 'dark' ? <IconSun /> : <IconMoon />}
    </button>
  )
}
```

---

### 10.3 UI 스토어 (토스트, 모달)

```typescript
// shared/store/uiStore.ts
interface Toast {
  id:      string
  type:    'success' | 'error' | 'info' | 'warning'
  message: string
}

interface UIState {
  toasts: Toast[]
  addToast:    (toast: Omit<Toast, 'id'>) => void
  removeToast: (id: string) => void
}

export const useUIStore = create<UIState>((set) => ({
  toasts: [],
  addToast: (toast) =>
    set((s) => ({ toasts: [...s.toasts, { ...toast, id: crypto.randomUUID() }] })),
  removeToast: (id) =>
    set((s) => ({ toasts: s.toasts.filter(t => t.id !== id) })),
}))
```

---
