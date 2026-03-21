<!-- 원본: frontend/setup.md — 섹션 11~15 -->

# TanStack Query, 라우팅, 코드 컨벤션, Vite 설정

> 앱 레이어 초기화, ESLint/Prettier, 개발 착수 체크리스트

---

## 11. TanStack Query 설정 (`app/providers.tsx`)

```typescript
// app/providers.tsx
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime:          30_000,   // 30초 (기본 캐시 신선도)
      gcTime:             5 * 60_000, // 5분 (캐시 유지)
      retry:              2,
      refetchOnWindowFocus: true,   // 탭 포커스 시 자동 리패치
      throwOnError:       false,    // 에러는 컴포넌트에서 처리
    },
    mutations: {
      retry: 0,
    },
  },
})

export const Providers = ({ children }: { children: React.ReactNode }) => (
  <QueryClientProvider client={queryClient}>
    {children}
    {import.meta.env.DEV && <ReactQueryDevtools buttonPosition="bottom-right" />}
  </QueryClientProvider>
)
```

---

## 12. 라우팅 (`app/router.tsx`)

```typescript
// app/router.tsx
export const router = createBrowserRouter([
  {
    path:    '/',
    element: <RootLayout />,          // 공통 레이아웃 (사이드바 + 상단 바)
    errorElement: <ErrorPage />,
    children: [
      { index: true, element: <Navigate to="/market/collection" replace /> },
      {
        path: 'market',
        children: [
          { path: 'collection', element: <MarketCollectionPage />, },
          { path: 'chart',      element: <MarketChartPage />, },
          { path: 'symbols',    element: <MarketSymbolsPage />, },
        ],
      },
      // 이후 Phase
      // { path: 'agent',      ... }
      // { path: 'simulation', ... }
      // { path: 'trade',      ... }
      // { path: 'settings',   element: <SettingsPage /> }  ← Phase 2: BottomTabBar Settings 탭과 연동 시 추가
    ],
  },
  {
    path:    '/login',
    element: <LoginPage />,
  },
])
```

### 공통 레이아웃 구조

```
RootLayout
├── Sidebar (좌측 고정 네비게이션)
│   ├── Logo
│   ├── NavItem: 수집 현황  (/market/collection)
│   ├── NavItem: 캔들 차트  (/market/chart)
│   ├── NavItem: 심볼 관리  (/market/symbols)
│   └── UserMenu (하단 고정)
└── MainArea
    ├── TopBar (선택적: 브레드크럼, 알림 등)
    └── <Outlet />       ← 페이지 컴포넌트 렌더링
```

---

## 13. 코드 컨벤션

### 13.1 ESLint 설정 (`.eslintrc.cjs`)

```js
module.exports = {
  root: true,
  parser: '@typescript-eslint/parser',
  plugins: ['@typescript-eslint', 'react-hooks'],
  extends: [
    'eslint:recommended',
    'plugin:@typescript-eslint/recommended',
    'plugin:react-hooks/recommended',
  ],
  rules: {
    '@typescript-eslint/no-explicit-any':        'warn',
    '@typescript-eslint/no-unused-vars':         ['warn', { argsIgnorePattern: '^_' }],
    'react-hooks/rules-of-hooks':                'error',
    'react-hooks/exhaustive-deps':               'warn',
    'no-console':                                ['warn', { allow: ['warn', 'error'] }],
  },
}
```

### 13.2 Prettier 설정 (`.prettierrc`)

```json
{
  "semi":            false,
  "singleQuote":     true,
  "trailingComma":   "es5",
  "printWidth":      100,
  "tabWidth":        2,
  "plugins":         ["prettier-plugin-tailwindcss"]
}
```

### 13.3 파일/컴포넌트 네이밍

```
컴포넌트 파일:  PascalCase.tsx          (CollectTaskTable.tsx)
훅 파일:        camelCase.ts            (useMarketCollection.ts)
유틸 파일:      camelCase.ts            (formatNumber.ts)
상수 파일:      camelCase.ts            (market.ts)
타입 파일:      types.ts or camelCase.ts
스타일 없음:    Tailwind 클래스 직접 사용 (별도 CSS 파일 지양)
```

### 13.4 컴포넌트 구조 순서

```typescript
// 1. imports
// 2. 타입/인터페이스 정의
// 3. 상수 정의 (컴포넌트 외부)
// 4. 컴포넌트 선언
//    a. hooks (useState, useRef, useContext, 커스텀 훅)
//    b. 파생 상태 (useMemo, useCallback)
//    c. 이펙트 (useEffect)
//    d. 이벤트 핸들러
//    e. return JSX
// 5. export
```

---

## 14. vite.config.ts

```typescript
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      // 절대 경로 import 지원
      '@app':      path.resolve(__dirname, 'src/app'),
      '@pages':    path.resolve(__dirname, 'src/pages'),
      '@widgets':  path.resolve(__dirname, 'src/widgets'),
      '@features': path.resolve(__dirname, 'src/features'),
      '@entities': path.resolve(__dirname, 'src/entities'),
      '@shared':   path.resolve(__dirname, 'src/shared'),
    },
  },
  server: {
    port: 3000,
    proxy: {
      // 개발 환경 CORS 우회
      '/api': {
        target:    'http://localhost:8080',
        changeOrigin: true,
        rewrite:   (path) => path.replace(/^\/api/, ''),
      },
    },
  },
})
```

### tsconfig.json paths 동기화

```json
{
  "compilerOptions": {
    "baseUrl": ".",
    "paths": {
      "@app/*":      ["src/app/*"],
      "@pages/*":    ["src/pages/*"],
      "@widgets/*":  ["src/widgets/*"],
      "@features/*": ["src/features/*"],
      "@entities/*": ["src/entities/*"],
      "@shared/*":   ["src/shared/*"]
    }
  }
}
```

---

## 15. 개발 착수 체크리스트

### 프로젝트 초기화

- [ ] `npm create vite@latest` 실행
- [ ] 의존성 설치
- [ ] `tailwind.config.ts` 색상 시스템 설정
- [ ] `vite.config.ts` alias 설정
- [ ] `.env.development` / `.env.production` 작성
- [ ] ESLint + Prettier 설정

### 공용 레이어 구현

- [ ] `shared/api/client.ts`: Axios 인스턴스 + 인터셉터
- [ ] `shared/api/errors.ts`: ApiError 클래스
- [ ] `shared/store/authStore.ts`: Zustand 인증 상태
- [ ] `shared/store/uiStore.ts`: Toast 상태
- [ ] `shared/utils/cn.ts`: 클래스 유틸
- [ ] `shared/utils/formatNumber.ts`: 숫자/날짜 포맷
- [ ] `shared/hooks/useDebounce.ts`
- [ ] `shared/hooks/useUrlParams.ts`
- [ ] `shared/hooks/useIntersectionObserver.ts`

### 공용 UI 구현

- [ ] Button, Badge, StatusBadge
- [ ] Input, SearchInput
- [ ] Spinner, Skeleton, TableSkeleton
- [ ] EmptyState, ErrorBoundary
- [ ] Modal
- [ ] Toast + ToastContainer
- [ ] Table, Th, Td, TableRow

### 앱 조립

- [ ] `app/providers.tsx`: QueryClient Provider
- [ ] `app/router.tsx`: 라우팅 구조
- [ ] `RootLayout`: 사이드바 + 메인 영역

---
