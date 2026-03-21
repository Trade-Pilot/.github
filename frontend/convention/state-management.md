# 상태 관리 컨벤션 (Zustand, TanStack Query)

> 원본: `frontend/convention.md` Section 7~8

---

## 7. 상태 관리 컨벤션 (Zustand)

### 7.1 클라이언트 상태 분류

| 상태 | 저장 위치 | 이유 |
|------|-----------|------|
| 서버 데이터 | TanStack Query | 캐싱·재패치 자동화 |
| 인증 상태 | Zustand | 전역, 비동기 필요 없음 |
| UI 테마 | Zustand + persist | 새로고침 후 유지 필요 |
| 페이지 필터 | URL SearchParams | 공유·북마크 가능 |
| 로컬 UI 상태 | `useState` | 컴포넌트 범위 |

### 7.2 보안 — AT(Access Token) 저장 규칙

> **보안 필수 규칙**: Access Token은 절대 `localStorage`에 저장하지 않습니다.

```typescript
// ✅ token을 partialize에서 제외 — 메모리(Zustand)에만 유지
export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({ ... }),
    {
      name: 'trade-pilot-auth',
      partialize: (state) => ({ user: state.user }),  // user만 persist
      // token은 persist 목록에 포함하지 않음 → 새로고침 시 재로그인
    }
  )
)

// ❌ 절대 금지
partialize: (state) => ({ token: state.token })   // XSS 탈취 가능
```

**근거**: XSS 공격으로 `localStorage`의 AT가 탈취되면 계정이 장기 노출됩니다. 메모리 저장 시 탭 닫으면 만료되어 피해가 최소화됩니다.

### 7.3 스토어 구조 규칙

```typescript
// ✅ 스토어는 상태 + 액션을 하나의 인터페이스로 정의
interface AuthState {
  // 상태
  token:           string | null
  user:            User | null
  isAuthenticated: boolean
  // 액션 (동사형)
  setAuth:  (token: string, user: User) => void
  logout:   () => void
}

// ✅ 컴포넌트 외부에서 상태 읽기 (인터셉터 등)
const token = useAuthStore.getState().token
```

---

## 8. 서버 상태 / API 컨벤션 (TanStack Query)

### 8.1 Query Key 구조

```typescript
// entities/market/queries/queryKeys.ts
// ✅ 팩토리 함수 패턴 — 계층적 무효화 가능
export const marketQueryKeys = {
  symbols:      (market?: MarketType) => ['market', 'symbols', market] as const,
  collectTasks: (params: CollectTaskListParams) => ['market', 'collect-tasks', params] as const,
  candles:      (symbolId: string, interval: MarketCandleInterval) =>
                  ['market', 'candles', symbolId, interval] as const,
}

// ✅ 무효화 시 상위 키로 일괄 처리
queryClient.invalidateQueries({ queryKey: ['market', 'collect-tasks'] })
```

### 8.2 InfiniteQuery 데이터 접근

```typescript
// ✅ pages 배열을 flatMap으로 펼쳐 단일 배열로
const tasks = tasksQuery.data?.pages.flatMap(page => page) ?? []

// ❌ .data.items 등 존재하지 않는 필드 접근
const tasks = tasksQuery.data?.items ?? []
```

### 8.3 낙관적 업데이트 (Optimistic Update)

```typescript
onMutate: async ({ taskId, action }) => {
  // 1. 진행 중인 쿼리 취소 (race condition 방지)
  await queryClient.cancelQueries({ queryKey: ['market', 'collect-tasks'] })

  // 2. 이전 데이터 스냅샷 저장
  const snapshot = queryClient.getQueryData(['market', 'collect-tasks'])

  // 3. UI 즉시 업데이트
  queryClient.setQueriesData(...)

  // 4. rollback 함수 반환
  return { snapshot }
},
onError: (err, vars, ctx) => {
  // 5. 오류 시 롤백
  queryClient.setQueryData(['market', 'collect-tasks'], ctx?.snapshot)
},
onSettled: () => {
  // 6. 항상 서버 재동기화
  queryClient.invalidateQueries({ queryKey: ['market', 'collect-tasks'] })
},
```

### 8.4 자동 리패치 정책

| 쿼리 | `refetchInterval` | 이유 |
|------|-------------------|------|
| 수집 작업 통계 | 30초 | 실시간성 필요 |
| 수집 작업 목록 | 30초 | 상태 변화 감지 |
| 심볼 목록 | 5분 (`staleTime`) | 자주 변하지 않음 |
| 캔들 데이터 | WebSocket으로 대체 | 실시간 차트 |

### 8.5 Axios 인터셉터 규칙

```typescript
// ✅ 요청 인터셉터: Zustand에서 토큰 직접 읽기 (훅 외부 접근)
apiClient.interceptors.request.use((config) => {
  const token = useAuthStore.getState().token   // getState() 사용 — 훅 아님
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

// ✅ 응답 인터셉터: 401은 로그아웃 + 리다이렉트
apiClient.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401) {
      useAuthStore.getState().logout()
      window.location.href = '/login'
    }
    return Promise.reject(err)
  }
)
```
