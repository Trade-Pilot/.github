# Frontend Convention — Trade Pilot

> 이 문서는 Trade Pilot 프론트엔드 전체에 적용되는 코드 컨벤션을 정의합니다.
> 새 기능 추가·코드 리뷰·온보딩 시 이 문서를 기준으로 삼습니다.

---

## 목차

1. [아키텍처 — FSD 레이어](#1-아키텍처--fsd-레이어)
2. [디렉토리 & 파일 네이밍](#2-디렉토리--파일-네이밍)
3. [Import 경로 규칙](#3-import-경로-규칙)
4. [TypeScript 타입 컨벤션](#4-typescript-타입-컨벤션)
5. [Tailwind / CSS 토큰 컨벤션](#5-tailwind--css-토큰-컨벤션)
6. [컴포넌트 작성 규칙](#6-컴포넌트-작성-규칙)
7. [상태 관리 컨벤션 (Zustand)](#7-상태-관리-컨벤션-zustand)
8. [서버 상태 / API 컨벤션 (TanStack Query)](#8-서버-상태--api-컨벤션-tanstack-query)
9. [보안 컨벤션](#9-보안-컨벤션)
10. [에러 처리 컨벤션](#10-에러-처리-컨벤션)
11. [성능 최적화 컨벤션](#11-성능-최적화-컨벤션)
12. [테스트 컨벤션](#12-테스트-컨벤션)
13. [환경 변수 규칙](#13-환경-변수-규칙)
14. [코드 스타일 (ESLint / Prettier)](#14-코드-스타일-eslint--prettier)
15. [Git / 커밋 컨벤션](#15-git--커밋-컨벤션)
16. [**디자인 시스템 컴포넌트 사용 규칙**](#16-디자인-시스템-컴포넌트-사용-규칙)
17. [타이포그래피 규칙](#17-타이포그래피-규칙)
18. [스페이싱 규칙](#18-스페이싱-규칙)
19. [컴포넌트 Variant 선택 기준](#19-컴포넌트-variant-선택-기준)
20. [반응형 브레이크포인트 규칙](#20-반응형-브레이크포인트-규칙)
21. [애니메이션 / 트랜지션 규칙](#21-애니메이션--트랜지션-규칙)
22. [Z-index 계층 규칙](#22-z-index-계층-규칙)
23. [레이아웃 패턴 선택 기준](#23-레이아웃-패턴-선택-기준)
24. [아이콘 사용 규칙](#24-아이콘-사용-규칙)
25. [**개발 워크플로우**](#25-개발-워크플로우)

---

## 1. 아키텍처 — FSD 레이어

[Feature-Sliced Design](https://feature-sliced.design/) 방법론을 따릅니다.
레이어 간 의존성은 **단방향 하향** 만 허용합니다.

```
app → pages → widgets → features → entities → shared
```

| 레이어 | 역할 | 하위 레이어 참조 가능 여부 |
|--------|------|--------------------------|
| `app` | 앱 초기화, 라우터, 전역 Provider | ✅ 전부 |
| `pages` | 라우트 단위 페이지 조립 | widgets ↓ |
| `widgets` | 독립 재사용 블록 (페이지 여러 곳에서 사용) | features ↓ |
| `features` | 사용자 인터랙션 단위 기능 | entities ↓ |
| `entities` | 도메인 타입 + API + Query 훅 | shared ↓ |
| `shared` | 도메인 독립 공용 유틸·UI | ❌ 상위 참조 불가 |

> **규칙**: 같은 레이어 간 직접 import는 금지합니다. 예를 들어 `features/a`에서 `features/b`를 import하면 안 됩니다.

---

## 2. 디렉토리 & 파일 네이밍

### 2.1 디렉토리 네이밍

| 레이어 | 네이밍 규칙 | 예시 |
|--------|------------|------|
| `pages` | `kebab-case` (도메인-기능) | `market-collection/`, `market-chart/` |
| `widgets` | `kebab-case` | `candle-chart/`, `task-table/` |
| `features` | `kebab-case` | `market-collection-control/` |
| `entities` | `kebab-case` (도메인명) | `market/` |
| `shared/ui` | 컴포넌트별 파일 | `Button.tsx`, `Badge.tsx` |

### 2.2 파일 네이밍

| 종류 | 규칙 | 예시 |
|------|------|------|
| React 컴포넌트 | `PascalCase.tsx` | `TaskCard.tsx`, `CandleChart.tsx` |
| 커스텀 훅 | `camelCase.ts` (`use` 접두사) | `useIsMobile.ts`, `useChartPage.ts` |
| 유틸 함수 | `camelCase.ts` | `formatPrice.ts`, `cn.ts` |
| 타입 정의 | `camelCase.ts` | `types.ts`, `schemas.ts` |
| 상수 | `camelCase.ts` | `market.ts`, `zIndex.ts` |
| 레이어 진입점 | `index.ts` (export 전용) | `entities/market/index.ts` |
| 스토어 | `camelCase.ts` (`Store` 접미사) | `authStore.ts`, `themeStore.ts` |

### 2.3 컴포넌트 내부 구조

```
features/market-collection-control/
├── ui/
│   ├── ResumeAllButton.tsx   # 단일 책임 컴포넌트
│   ├── PauseAllButton.tsx
│   └── TaskActionButtons.tsx
└── model/
    ├── useResumeAll.ts       # mutation 훅 (UI 로직 분리)
    ├── usePauseAll.ts
    └── useTaskAction.ts
```

> **규칙**: `ui/`는 렌더링, `model/`은 비즈니스 로직. 컴포넌트에서 fetch/mutation 로직을 직접 쓰지 않습니다.

---

## 3. Import 경로 규칙

`vite.config.ts`에 FSD 레이어별 경로 앨리어스를 설정합니다.

```typescript
// vite.config.ts
resolve: {
  alias: {
    '@app':      '/src/app',
    '@pages':    '/src/pages',
    '@widgets':  '/src/widgets',
    '@features': '/src/features',
    '@entities': '/src/entities',
    '@shared':   '/src/shared',
  },
}
```

### 규칙

```typescript
// ✅ 앨리어스 사용 — 항상
import { Button }        from '@shared/ui/Button'
import { useAuthStore }  from '@shared/store/authStore'
import { throttle }      from '@shared/utils/throttle'
import { marketQueryKeys } from '@entities/market/queries/queryKeys'

// ❌ 상대 경로 금지 (레이어 경계 넘을 때)
import { Button } from '../../../shared/ui/Button'

// ✅ 같은 슬라이스 내부는 상대 경로 허용
import { formatPrice } from './utils'
```

### Import 순서 (ESLint `import/order`)

```typescript
// 1. Node.js 내장
// 2. 외부 라이브러리
import React, { useState, useEffect } from 'react'
import { useQuery } from '@tanstack/react-query'

// 3. 내부 — 레이어 순서 (상위 → 하위)
import { RootLayout } from '@app/RootLayout'
import { useChartPage } from '@pages/market-chart/model/useChartPage'
import { CandleChart } from '@widgets/candle-chart'
import { useTaskAction } from '@features/market-collection-control/model/useTaskAction'
import { useSymbolsQuery } from '@entities/market/queries/useSymbolsQuery'
import { Button, Badge } from '@shared/ui'

// 4. 타입 import (type-only)
import type { MarketSymbol } from '@entities/market'

// 5. 스타일 (최하단)
import './styles.css'
```

---

## 4. TypeScript 타입 컨벤션

### 4.1 도메인 모델 — 단일 스키마 원칙

> **핵심 규칙**: API 응답으로 받는 도메인 모델은 `interface`로 따로 선언하지 않습니다.
> Zod 스키마 하나에서 `z.infer`로 TypeScript 타입을 추출합니다.

```
entities/market/model/
├── enums.ts     # Enum (런타임 JS 값 필요 → z.infer 불가)
├── schemas.ts   # Zod 스키마 + z.infer 타입 ← 단일 진실 공급원
└── params.ts    # 요청 파라미터 interface (런타임 검증 불필요)
```

```typescript
// ✅ 단일 스키마 방식 — schemas.ts
import { z } from 'zod'
import { MarketSymbolStatus, MarketType } from './enums'

export const MarketSymbolSchema = z.object({
  identifier:   z.string().uuid(),
  code:         z.string(),
  status:       z.nativeEnum(MarketSymbolStatus),
  createdDate:  z.string().datetime(),
  modifiedDate: z.string().datetime(),
})

// 스키마 → 타입 자동 추출. 스키마 수정 시 타입 자동 반영
export type MarketSymbol = z.infer<typeof MarketSymbolSchema>
```

```typescript
// ❌ interface 이중 선언 금지 — 불일치 버그의 원인
// types.ts
interface MarketSymbol {
  identifier: string
  createdDate: Date
}

// schemas.ts (types.ts와 따로 관리하다가 불일치 발생)
const MarketSymbolSchema = z.object({
  identifier:   z.string().uuid(),
  lastCollectedAt: z.string(),   // ← 실제로는 lastCollectedTime인데 불일치
})
```

### 4.2 인터페이스 사용 규칙

`interface`는 런타임 검증이 필요 없는 곳에만 사용합니다.

| 종류 | 방식 | 이유 |
|------|------|------|
| API 응답 도메인 모델 | `z.infer<typeof Schema>` | 런타임 검증 필요 |
| API 요청 파라미터 | `interface` | 검증 불필요, 코드가 단순함 |
| 컴포넌트 Props | `interface` | 검증 불필요 |
| 유니언·인터섹션 | `type` | interface로 표현 불가 |

```typescript
// ✅ 요청 파라미터 — interface 사용
interface CollectTaskListParams {
  keyword?: string
  statuses?: MarketCandleCollectStatus[]
  limit?: number
}

// ✅ 컴포넌트 Props — interface 사용
interface TaskCardProps {
  task:     MarketCandleCollectTask   // ← z.infer 타입 참조
  onResume: (id: string) => void
  onPause:  (id: string) => void
}

// ✅ 유니언 타입 — type 사용
type Theme = 'light' | 'dark' | 'system'
```

### 4.3 PK 필드명 규칙

백엔드 API 응답의 Primary Key 필드는 `identifier`를 사용합니다.

```typescript
// ✅ Zod 스키마에서
export const MarketSymbolSchema = z.object({
  identifier: z.string().uuid(),   // PK
  // ...
})

// ❌ 사용 금지
z.object({ id: z.string() })
```

### 4.4 날짜 필드명 규칙

| 용도 | 필드명 |
|------|--------|
| 생성일시 | `createdDate` |
| 수정일시 | `modifiedDate` |
| 도메인 특정 시각 | `lastCollectedTime` (의미 있는 이름) |

```typescript
// ✅ schemas.ts
export const CollectTaskSchema = z.object({
  createdDate:       z.string().datetime(),
  lastCollectedTime: z.string().datetime().nullable(),  // ← lastCollectedAt 금지
})

// ❌
z.object({ createdAt: z.string(), lastCollectedAt: z.string() })
```

### 4.5 Enum 규칙

Enum은 런타임 JavaScript 값이 필요하므로 `z.infer`로 대체할 수 없습니다.
`enums.ts`에 별도로 관리하고 `z.nativeEnum()`으로 스키마에 연결합니다.

```typescript
// ✅ const enum 대신 일반 enum — tree-shaking 호환
// enums.ts
export enum MarketCandleCollectStatus {
  CREATED    = 'CREATED',
  COLLECTING = 'COLLECTING',   // 활성 상태 (RUNNING 없음)
  COLLECTED  = 'COLLECTED',
  ERROR      = 'ERROR',
  PAUSED     = 'PAUSED',
  DELISTED   = 'DELISTED',
}

// schemas.ts — z.nativeEnum으로 연결
status: z.nativeEnum(MarketCandleCollectStatus)

// 코드에서 — enum 멤버 직접 참조 (문자열 리터럴 금지)
if (task.status === MarketCandleCollectStatus.COLLECTING) { ... }

// ❌ 문자열 리터럴로 비교 금지
if (task.status === 'RUNNING') { ... }   // 존재하지 않는 값, 오타도 감지 불가
```

### 4.6 parseOrThrow 사용 규칙

```typescript
// shared/utils/parse.ts
export const parseOrThrow = <T>(schema: ZodSchema<T>, raw: unknown): T => {
  const result = schema.safeParse(raw)
  if (result.success) return result.data
  if (import.meta.env.DEV) {
    console.error('[ParseError]', result.error, '\nraw:', raw)
  }
  throw result.error
}

// ✅ API 응답은 반드시 parseOrThrow를 거쳐 도메인 모델로 변환
const symbol = parseOrThrow(MarketSymbolSchema, response.data)

// ❌ API 응답을 타입 단언으로 직접 사용 금지
const symbol = response.data as MarketSymbol   // 런타임 불일치 감지 불가
```

### 4.7 Props 타입 위치

```typescript
// ✅ Props 타입은 컴포넌트 파일 상단에 선언, export 불필요
interface TaskCardProps {
  task:     MarketCandleCollectTask   // z.infer 타입
  onResume: (id: string) => void
  onPause:  (id: string) => void
}

export const TaskCard = ({ task, onResume, onPause }: TaskCardProps) => { ... }
```

---

## 5. Tailwind / CSS 토큰 컨벤션

### 5.1 색상 — 반드시 토큰 사용

```typescript
// ✅ 시맨틱 토큰 사용
className="bg-semantic-danger/10 text-semantic-danger"
className="bg-bg-surface border-border text-text-primary"

// ❌ 하드코딩 금지
className="bg-red-500 text-white"
className="bg-[#F04452]"
```

| 카테고리 | 토큰 접두사 | 예시 |
|----------|------------|------|
| 배경 | `bg-bg-*` | `bg-base`, `bg-surface`, `bg-elevated` |
| 텍스트 | `text-text-*` | `text-primary`, `text-secondary`, `text-tertiary` |
| 테두리 | `border-border*` | `border-border`, `border-border-strong` |
| 브랜드 | `bg-brand-*` | `bg-brand-500`, `text-brand-400` |
| 시맨틱 | `bg-semantic-*` | `bg-semantic-success`, `text-semantic-danger` |

### 5.2 투명도 수식어 (Opacity Modifier)

`semantic-*` 색상은 CSS 변수 기반(공백 분리 RGB)으로 정의되어 투명도 수식어를 지원합니다.

```typescript
// ✅ 투명도 수식어 사용 가능
className="bg-semantic-danger/10"      // rgba(220, 38, 38, 0.10)
className="bg-semantic-success/15"
className="text-semantic-info/60"

// ❌ hex 직접 정의 시 투명도 수식어 불가
// semantic-* 토큰을 hex로 재정의하지 않도록 주의
```

### 5.3 다크 모드

`darkMode: 'class'`를 사용합니다. `<html class="dark">` 전환으로 테마가 적용됩니다.

```typescript
// ✅ 토큰이 다크 모드를 자동 처리
className="bg-bg-surface text-text-primary"

// ✅ 토큰으로 처리 안 되는 값만 dark: 수식어 사용
className="bg-white dark:bg-slate-900"

// ❌ dark: 수식어로 색상 토큰 덮어쓰기 금지 (토큰이 이미 처리)
className="bg-bg-surface dark:bg-[#1C1B2E]"
```

### 5.4 boxShadow 'panel'

```typescript
// ✅ 토큰 사용 — CSS 변수 기반
className="shadow-panel"

// ❌ 직접 정의 금지 (하드코딩 hex는 테마 전환 불가)
// style={{ boxShadow: 'rgba(255,255,255,0.06) ...' }}
```

### 5.5 한국 주식 색상 컨벤션

> **⚠️ 주의**: 한국 주식 컨벤션은 미국/서양과 반대입니다.

| 의미 | 색상 | 토큰 |
|------|------|------|
| 상승 (양봉) | **빨강** `#F04452` | `stock-up` |
| 하락 (음봉) | **파랑** `#4066E4` | `stock-down` |

```typescript
// Lightweight Charts 설정 — 반드시 한국 컨벤션 유지
const candleSeries = chart.addCandlestickSeries({
  upColor:         '#F04452',   // 상승 = 빨강
  downColor:       '#4066E4',   // 하락 = 파랑
  borderUpColor:   '#F04452',
  borderDownColor: '#4066E4',
  wickUpColor:     '#F04452',
  wickDownColor:   '#4066E4',
})
```

### 5.6 Safe Area (iOS)

```html
<!-- index.html — viewport-fit=cover 필수 -->
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover" />
```

```typescript
// ✅ Safe Area 처리는 BottomTabBar 한 곳에서만
// body에 padding-bottom 추가 금지 (이중 패딩 발생)
className="pb-[env(safe-area-inset-bottom)]"   // BottomTabBar에서만
```

### 5.7 cn() 유틸리티

조건부 클래스 조합 시 반드시 `cn()` 사용합니다.

```typescript
// shared/utils/cn.ts
import { clsx } from 'clsx'
import { twMerge } from 'tailwind-merge'

export const cn = (...inputs: ClassValue[]) => twMerge(clsx(inputs))

// ✅ 사용
className={cn(
  'base-class',
  isActive && 'active-class',
  variant === 'danger' && 'danger-class',
)}

// ❌ 문자열 연결 금지
className={'base-class ' + (isActive ? 'active-class' : '')}
```

---

## 6. 컴포넌트 작성 규칙

### 6.1 기본 구조

```typescript
// ✅ 함수 선언식 또는 화살표 함수 (팀 내 통일)
// Trade Pilot은 const 화살표 함수 + named export 사용
export const TaskCard = ({ task, onResume, onPause }: TaskCardProps) => {
  // 1. 훅
  const isMobile = useIsMobile()

  // 2. 파생 상태
  const isActive = task.status === MarketCandleCollectStatus.COLLECTING

  // 3. 핸들러

  // 4. 조건부 렌더링 (얼리 리턴)
  if (!task) return null

  // 5. JSX 반환
  return (
    <div>...</div>
  )
}
```

### 6.2 React.memo 규칙

```typescript
// ✅ 목록 아이템 컴포넌트는 React.memo 적용 (1,200개 행 렌더링 최적화)
const TaskRow = React.memo(
  ({ task, onResume, onPause }: TaskRowProps) => { ... },
  (prev, next) =>
    prev.task.status            === next.task.status            &&
    prev.task.retryCount        === next.task.retryCount        &&
    prev.task.lastCollectedTime === next.task.lastCollectedTime  // ← 반드시 lastCollectedTime
)

// ✅ 비교 함수의 필드명은 타입 정의와 100% 일치해야 함
```

### 6.3 React Router v6 레이아웃

```typescript
// ✅ 중첩 라우트 레이아웃은 <Outlet /> 사용
import { Outlet } from 'react-router-dom'

export const RootLayout = () => (
  <div className="flex h-dvh">
    <aside>...</aside>
    <main>
      <Outlet />   {/* 자식 라우트가 여기 렌더링됨 */}
    </main>
  </div>
)

// ❌ children prop 방식 금지 (React Router v6에서 동작하지 않음)
export const RootLayout = ({ children }: { children: React.ReactNode }) => (
  <main>{children}</main>   // 페이지가 렌더링되지 않음
)
```

### 6.4 이벤트 핸들러 네이밍

```typescript
// Props: on + 동사 (PascalCase)
interface Props {
  onResume: (id: string) => void
  onPause:  (id: string) => void
  onChange: (value: string) => void
}

// 내부 핸들러: handle + 동사 (camelCase)
const handleResume = () => onResume(task.identifier)
const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => { ... }
```

### 6.5 조건부 렌더링

```typescript
// ✅ 단순 show/hide
{isLoading && <Spinner />}

// ✅ 두 가지 상태
{isError
  ? <ErrorState message={error.message} />
  : <TaskList tasks={tasks} />
}

// ❌ 3항 연산자 중첩 금지
{a ? b ? c : d : e}   // 가독성 저하

// ✅ 중첩 조건은 얼리 리턴 또는 변수로 분리
if (isLoading) return <Spinner />
if (isError)   return <ErrorState />
```

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

> **⚠️ 보안 필수 규칙**: Access Token은 절대 `localStorage`에 저장하지 않습니다.

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

---

## 9. 보안 컨벤션

### 9.1 인증 토큰 관리

| 토큰 종류 | 저장 위치 | 만료 시 처리 |
|-----------|-----------|-------------|
| Access Token (AT) | Zustand 메모리 | 401 응답 시 로그아웃 |
| Refresh Token (RT) | HttpOnly Cookie | 서버 발급, JS 접근 불가 |

### 9.2 환경 변수 노출 주의

```typescript
// ✅ VITE_로 시작하는 변수만 클라이언트에 노출됨
const apiUrl = import.meta.env.VITE_API_BASE_URL

// ❌ 비밀 키를 클라이언트 env에 절대 포함 금지
VITE_SECRET_KEY=...   // 클라이언트 번들에 포함되어 노출됨
```

### 9.3 XSS 방지

```typescript
// ✅ dangerouslySetInnerHTML 사용 시 반드시 DOMPurify 적용
import DOMPurify from 'dompurify'
<div dangerouslySetInnerHTML={{ __html: DOMPurify.sanitize(userInput) }} />

// ❌ 사용자 입력을 그대로 HTML에 삽입 금지
<div dangerouslySetInnerHTML={{ __html: userInput }} />
```

---

## 10. 에러 처리 컨벤션

### 10.1 API 응답 파싱 규칙

```typescript
// shared/utils/parse.ts
// ✅ safeParse: 개발 = console.error + throw, 프로덕션 = throw
// 향후 Sentry 도입 시 captureException 추가 예정
export const parseOrThrow = <T>(schema: ZodSchema<T>, raw: unknown): T => {
  const result = schema.safeParse(raw)
  if (result.success) return result.data

  if (import.meta.env.DEV) {
    console.error('[ParseError] API 응답 스키마 불일치:', result.error, '\nraw:', raw)
  }
  throw result.error   // 항상 throw (unsafe fallback 금지)
}

// ❌ 파싱 실패 시 raw를 그대로 반환하는 것 금지
return raw as T   // 타입 안전성 붕괴
```

### 10.2 컴포넌트 에러 처리

```typescript
// ✅ 페이지 단위 ErrorBoundary 적용
<ErrorBoundary fallback={<ErrorPage />}>
  <MarketCollectionPage />
</ErrorBoundary>

// ✅ TanStack Query 에러는 isError + error 상태로 처리
if (tasksQuery.isError) {
  return <ErrorState message={tasksQuery.error.message} />
}
```

### 10.3 async/await 에러 처리

```typescript
// ✅ mutation의 에러는 onError 콜백에서 처리
useMutation({
  mutationFn: resumeTask,
  onError: (error) => {
    toast.error(`재시작 실패: ${error.message}`)
  },
})

// ✅ 독립적인 async 함수는 try/catch 사용
// ❌ 컴포넌트 이벤트 핸들러에서 unhandled rejection 발생 금지
```

---

## 11. 성능 최적화 컨벤션

### 11.1 WebSocket 렌더링 throttle

```typescript
// ✅ 초당 여러 번 오는 WebSocket 메시지는 500ms throttle
import { throttle } from '@shared/utils/throttle'   // 앨리어스 필수

const handleMessage = throttle((data: MessageEvent) => {
  setRealtimeCandle(parseWebSocketCandle(JSON.parse(data.data)))
}, 500)
```

### 11.2 가상 스크롤 기준

```typescript
// 렌더링 행 수 > 200개 → @tanstack/react-virtual 적용
// CollectTaskTable: 심볼 × 12간격 → 수백~수천 행

const rowVirtualizer = useVirtualizer({
  count:            tasks.length,
  getScrollElement: () => scrollRef.current,
  estimateSize:     () => 52,    // px
  overscan:         10,
})
```

### 11.3 코드 스플리팅

```typescript
// ✅ 페이지 컴포넌트는 lazy import
const MarketCollectionPage = lazy(() => import('@pages/market-collection'))
const MarketChartPage      = lazy(() => import('@pages/market-chart'))

// vite.config.ts — 벤더 청크 분리
manualChunks: {
  'react-vendor':  ['react', 'react-dom', 'react-router-dom'],
  'query-vendor':  ['@tanstack/react-query'],
  'chart-vendor':  ['lightweight-charts'],
}
```

### 11.4 dayjs 플러그인 등록

```typescript
// ✅ 사용하는 플러그인 전부 명시적으로 등록
import dayjs from 'dayjs'
import utc        from 'dayjs/plugin/utc'
import timezone   from 'dayjs/plugin/timezone'
import weekOfYear from 'dayjs/plugin/weekOfYear'  // d.week() 사용 전 반드시 필요

dayjs.extend(utc)
dayjs.extend(timezone)
dayjs.extend(weekOfYear)

// ❌ 플러그인 미등록 상태에서 d.week() 호출 → undefined 반환
```

---

## 12. 테스트 컨벤션

### 12.1 테스트 파일 위치

```
src/
└── shared/
    └── utils/
        ├── cn.ts
        └── cn.test.ts     # 테스트 파일은 대상 파일 옆에 위치
```

### 12.2 테스트 명명 규칙

```typescript
// vitest 사용
describe('formatPrice', () => {
  it('1000 이상은 쉼표 구분자 포함', () => {
    expect(formatPrice(1000000)).toBe('1,000,000')
  })

  it('null 입력 시 "-" 반환', () => {
    expect(formatPrice(null)).toBe('-')
  })
})
```

### 12.3 vitest 경로 앨리어스

```typescript
// vitest.config.ts — vite.config.ts와 동일한 앨리어스 6개 모두 등록
resolve: {
  alias: {
    '@app':      resolve(__dirname, 'src/app'),
    '@pages':    resolve(__dirname, 'src/pages'),
    '@widgets':  resolve(__dirname, 'src/widgets'),
    '@features': resolve(__dirname, 'src/features'),
    '@entities': resolve(__dirname, 'src/entities'),
    '@shared':   resolve(__dirname, 'src/shared'),
  },
}
```

### 12.4 테스트 커버리지 기준

| 레이어 | 목표 커버리지 | 우선 대상 |
|--------|-------------|-----------|
| `shared/utils` | 90% 이상 | formatPrice, formatRelativeTime, cn |
| `entities/*/model` | 80% 이상 | 파서, Zod 스키마 |
| `features/*/model` | 70% 이상 | mutation 훅, 비즈니스 로직 |
| `shared/ui` | 주요 컴포넌트 | Button, Badge, Toggle |

---

## 13. 환경 변수 규칙

```bash
# .env.local (git에 커밋하지 않음)
VITE_API_BASE_URL=http://localhost:8080
VITE_WS_BASE_URL=ws://localhost:8080

# .env.example (git에 커밋, 실제 값 제외)
VITE_API_BASE_URL=
VITE_WS_BASE_URL=
```

```typescript
// shared/config/env.ts — 접근 일원화 + 타입 보장
export const env = {
  apiBaseUrl: import.meta.env.VITE_API_BASE_URL as string,
  wsBaseUrl:  import.meta.env.VITE_WS_BASE_URL  as string,
}

// ✅ 컴포넌트에서 직접 import.meta.env 접근 금지
// import { env } from '@shared/config/env' 로 통일
```

---

## 14. 코드 스타일 (ESLint / Prettier)

### 14.1 Prettier 설정

```json
// .prettierrc
{
  "semi": false,
  "singleQuote": true,
  "trailingComma": "es5",
  "printWidth": 100,
  "tabWidth": 2,
  "plugins": ["prettier-plugin-tailwindcss"]
}
```

> `prettier-plugin-tailwindcss`: Tailwind 클래스를 자동으로 권장 순서로 정렬합니다.

### 14.2 ESLint 핵심 규칙

```json
{
  "rules": {
    "react-hooks/rules-of-hooks":  "error",    // 훅 규칙 강제
    "react-hooks/exhaustive-deps": "warn",     // useEffect 의존성 경고
    "@typescript-eslint/no-explicit-any": "error",   // any 금지
    "@typescript-eslint/no-unused-vars":  "error",   // 미사용 변수 금지
    "import/no-cycle": "error"                 // 순환 의존성 금지 (FSD 위반 감지)
  }
}
```

### 14.3 금지 패턴

```typescript
// ❌ any 사용 금지 — unknown 또는 구체적 타입 사용
const data: any = response.data

// ✅ 대안
const data: unknown = response.data
const result = schema.parse(data)    // Zod로 타입 좁히기

// ❌ console.log 프로덕션 코드에 남기지 않음 (eslint no-console)
console.log('debug:', task)

// ✅ 디버깅 후 반드시 제거 (프로덕션 빌드 전 ESLint no-console으로 확인)
// 향후 모니터링 도구 도입 시 console.log 대신 전용 logger 유틸로 교체 예정
```

---

## 15. Git / 커밋 컨벤션

### 15.1 브랜치 네이밍

```
main          # 배포 브랜치 (직접 push 금지)
develop       # 통합 개발 브랜치
feat/<ticket>-<desc>    # 기능 개발
fix/<ticket>-<desc>     # 버그 수정
refactor/<desc>         # 리팩토링
chore/<desc>            # 빌드/설정 변경
```

예시:
```
feat/TP-42-candle-chart-widget
fix/TP-101-ws-reconnect
refactor/auth-store-security
```

### 15.2 커밋 메시지 — Conventional Commits

```
<type>(<scope>): <subject>

[body]

[footer]
```

| type | 용도 |
|------|------|
| `feat` | 새 기능 |
| `fix` | 버그 수정 |
| `refactor` | 기능 변화 없는 코드 개선 |
| `style` | 포맷팅 (로직 변화 없음) |
| `test` | 테스트 추가·수정 |
| `chore` | 빌드·설정·패키지 변경 |
| `docs` | 문서 수정 |
| `perf` | 성능 개선 |

예시:
```
feat(chart): add Korean stock color convention to CandleChart

upColor/downColor을 한국 주식 컨벤션(빨강=상승, 파랑=하락)으로 변경
Lightweight Charts의 기본값(서양 컨벤션)과 반대이므로 명시적 설정 필수

Closes #42
```

### 15.3 PR 규칙

- 하나의 PR = 하나의 기능/수정 (범위 최소화)
- 셀프 리뷰 후 팀원 1인 이상 리뷰 승인 필요
- `main` 브랜치에 직접 push 금지 — PR + CI 통과 후 머지
- 스쿼시 머지 권장 (커밋 히스토리 단순화)

---

## 16. 디자인 시스템 컴포넌트 사용 규칙

> **핵심 원칙**: 화면을 구성할 때 **날 HTML 태그를 직접 쓰지 않습니다.**
> `shared/ui`에 정의된 디자인 시스템 컴포넌트를 반드시 사용합니다.
> 필요한 컴포넌트가 없으면 먼저 `shared/ui`에 추가한 뒤 사용합니다.

### 16.1 HTML 태그 → 디자인 시스템 컴포넌트 대응표

| ❌ 날 HTML 태그 | ✅ 디자인 시스템 컴포넌트 | 위치 |
|----------------|--------------------------|------|
| `<button>` | `<Button>` | `shared/ui/Button` |
| `<input type="checkbox">` | `<Checkbox>` | `shared/ui/Checkbox` |
| `<input type="text">` | `<Input>` | `shared/ui/Input` |
| `<select>` | `<Select>` | `shared/ui/Select` |
| `<span class="badge">` | `<Badge>` | `shared/ui/Badge` |
| `<span class="status">` | `<StatusBadge>` | `shared/ui/StatusBadge` |
| `<input type="range">` / 온오프 토글 | `<Toggle>` | `shared/ui/Toggle` |
| `<div class="tooltip">` | `<Tooltip>` | `shared/ui/Tooltip` |
| `<div class="popover">` | `<Popover>` | `shared/ui/Popover` |
| `<svg>` / `<img>` (아이콘) | `<IconPlay>` 등 | `shared/ui/icons` |
| `<div class="spinner">` | `<Spinner>` | `shared/ui/Spinner` |
| `<div class="empty">` | `<EmptyState>` | `shared/ui/EmptyState` |

### 16.2 사용 예시

```tsx
// ✅ 디자인 시스템 컴포넌트 사용
import { Button, Badge, Toggle, Checkbox } from '@shared/ui'
import { IconPlay, IconPause }             from '@shared/ui/icons'

<Button variant="primary" size="md" onClick={handleResume}>
  재시작
</Button>

<Badge variant="success">완료</Badge>

<Toggle
  checked={task.status === 'COLLECTING'}
  onChange={(v) => v ? onResume(task.identifier) : onPause(task.identifier)}
  size="sm"
/>

<Checkbox
  checked={isSelected}
  onChange={(v) => toggleSelect(symbol.identifier, v)}
/>
```

```tsx
// ❌ 날 HTML 태그 직접 사용 금지
<button onClick={handleResume} className="bg-brand-500 text-white px-4 py-2 rounded">
  재시작
</button>

<span className="bg-green-100 text-green-700 px-2 py-0.5 rounded text-xs">완료</span>

<input
  type="checkbox"
  checked={isSelected}
  onChange={(e) => toggleSelect(symbol.identifier, e.target.checked)}
/>
```

### 16.3 예외 — 날 태그 허용 케이스

아래 경우에만 날 HTML 태그 사용이 허용됩니다.

| 케이스 | 이유 |
|--------|------|
| 디자인 시스템 컴포넌트 **내부 구현** | `Button.tsx` 내부에서 `<button>` 사용 |
| 시맨틱 마크업 구조 (`<main>`, `<aside>`, `<section>`, `<article>`) | 레이아웃 의미 부여, 스타일 컴포넌트 없음 |
| 텍스트 구조 (`<h1>`~`<h6>`, `<p>`, `<ul>`, `<li>`) | 콘텐츠 계층 표현 (Typography 토큰 적용 필수) |
| `<form>` | form 제출 의미 구조 |

```tsx
// ✅ 허용 — 레이아웃 구조 태그
<main className="flex-1 overflow-y-auto">
  <section className="p-4">
    <h2 className="text-lg font-semibold text-text-primary">수집 현황</h2>
    <p className="text-sm text-text-secondary mt-1">실시간 업데이트</p>
  </section>
</main>

// ✅ 허용 — Button 컴포넌트 내부 구현
// shared/ui/Button.tsx
export const Button = ({ children, ...props }: ButtonProps) => (
  <button className={cn(baseClass, variantClass[variant])} {...props}>
    {children}
  </button>
)
```

### 16.4 새 컴포넌트 추가 절차

필요한 UI 요소가 디자인 시스템에 없을 때 날 태그를 쓰지 말고 컴포넌트를 먼저 만듭니다.

```
1. shared/ui/[ComponentName].tsx 생성
2. Props 인터페이스 정의 (variant, size, disabled 등)
3. 디자인 토큰 기반으로 스타일 구현 (cn() 사용)
4. shared/ui/index.ts에 export 추가
5. 사용처에서 import 후 사용
```

---

## 17. 타이포그래피 규칙

### 17.1 폰트 사이즈 스케일

Tailwind의 기본 스케일을 사용합니다. 임의의 값(`text-[13px]`)은 금지합니다.

| 용도 | 클래스 | 크기 |
|------|--------|------|
| 페이지 제목 | `text-xl font-semibold` | 20px |
| 섹션 제목 | `text-lg font-semibold` | 18px |
| 카드 제목 / 강조 텍스트 | `text-base font-semibold` | 16px |
| 본문 (기본) | `text-sm` | 14px |
| 보조 텍스트 / 레이블 | `text-xs` | 12px |
| 숫자 데이터 (가격·수량) | `text-sm font-mono` | 14px (고정폭) |

```tsx
// ✅ 스케일 준수
<h1 className="text-xl font-semibold text-text-primary">수집 현황</h1>
<p  className="text-sm text-text-secondary">실시간으로 업데이트됩니다</p>
<span className="text-xs text-text-tertiary">12:34:01</span>
<span className="font-mono text-sm text-text-primary">{formatPrice(price)}</span>

// ❌ 임의 크기 금지
<p className="text-[13px]">...</p>
<p style={{ fontSize: '13px' }}>...</p>
```

### 17.2 폰트 웨이트

| 용도 | 클래스 |
|------|--------|
| 제목·강조 | `font-semibold` (600) |
| 중간 강조 | `font-medium` (500) |
| 본문 | `font-normal` (400, 기본값) |
| 숫자·코드 | `font-mono` (고정폭) |

> `font-bold`(700)는 특별한 강조가 필요한 경우에만 제한적으로 사용합니다.

### 17.3 텍스트 색상

텍스트 색상은 반드시 `text-text-*` 토큰을 사용합니다.

| 토큰 | 용도 |
|------|------|
| `text-text-primary` | 제목, 핵심 데이터 |
| `text-text-secondary` | 본문, 일반 설명 |
| `text-text-tertiary` | 보조 정보, 타임스탬프 |
| `text-text-disabled` | 비활성 항목 |

### 17.4 줄바꿈·말줄임

```tsx
// ✅ 단일 행 말줄임
<p className="truncate">긴 텍스트...</p>

// ✅ 다중 행 말줄임 (2줄)
<p className="line-clamp-2">긴 텍스트...</p>

// ✅ 줄바꿈 방지 (심볼 코드, 배지 등)
<span className="whitespace-nowrap">KRW-BTC</span>
```

---

## 18. 스페이싱 규칙

### 18.1 4px 그리드 시스템

모든 여백·크기는 **4px 단위(Tailwind 기본 단위)** 를 사용합니다.

```
1 unit = 4px

p-1  = 4px    p-2  = 8px    p-3  = 12px
p-4  = 16px   p-5  = 20px   p-6  = 24px
p-8  = 32px   p-10 = 40px   p-12 = 48px
```

```tsx
// ✅ 4px 단위 준수
<div className="p-4 gap-3">...</div>

// ❌ 임의 값 금지
<div className="p-[14px] gap-[7px]">...</div>
```

### 18.2 컴포넌트 내부 패딩 기준

| 컴포넌트 크기 | 패딩 |
|-------------|------|
| 버튼 sm | `px-3 py-1.5` |
| 버튼 md | `px-4 py-2` |
| 버튼 lg | `px-5 py-2.5` |
| 카드 | `p-4` |
| 테이블 셀 | `px-4 py-3` |
| 페이지 콘텐츠 | `p-4 sm:p-5 lg:p-6` (반응형) |
| 모달 | `p-6` |

### 18.3 간격(gap) 기준

| 용도 | 클래스 |
|------|--------|
| 인라인 아이콘·텍스트 간격 | `gap-1.5` (6px) |
| 폼 필드 간 간격 | `gap-3` (12px) |
| 카드 사이 간격 | `gap-3` ~ `gap-4` |
| 섹션 사이 간격 | `gap-6` ~ `gap-8` |

---

## 19. 컴포넌트 Variant 선택 기준

### 19.1 Button

| Variant | 사용 시점 | 예시 |
|---------|-----------|------|
| `primary` | 페이지당 1개, 핵심 CTA | 저장, 확인, 재시작 |
| `secondary` | 보조 액션 | 취소, 이전 |
| `ghost` | 테이블·카드 내 인라인 액션 | ▶ 재시작, ⏸ 정지 |
| `danger` | 비가역적 삭제·경고 액션 | 삭제, 초기화 |

```tsx
// ✅ 수집 작업 개별 제어 → ghost (테이블 인라인)
<Button variant="ghost" size="sm" onClick={() => onPause(task.identifier)}>
  <IconPause />
</Button>

// ✅ 페이지 핵심 액션 → primary
<Button variant="primary" onClick={handleResumeAll}>
  전체 재시작
</Button>

// ✅ 위험 액션 → danger
<Button variant="danger" onClick={handleDelete}>
  수집 작업 삭제
</Button>
```

### 19.2 Badge / StatusBadge

```tsx
// StatusBadge — 수집 상태 표시 (MarketCandleCollectStatus 전용)
<StatusBadge status={task.status} retryCount={task.retryCount} />

// Badge — 일반 레이블 (상태 외 용도)
<Badge variant="info">COIN</Badge>      // 마켓 타입
<Badge variant="success">LISTED</Badge>  // 심볼 상태
<Badge variant="error">DELISTED</Badge>
```

| Variant | 색상 | 사용 시점 |
|---------|------|----------|
| `default` | 회색 | 중립, 기본 레이블 |
| `success` | 초록 | 정상·완료·활성 |
| `error` | 빨강 | 실패·오류·비활성 |
| `warning` | 노랑 | 경고·주의 |
| `info` | 보라(브랜드) | 정보·진행 중 |
| `neutral` | 연회색 | 폐지·무관 |

### 19.3 Toggle vs Button(ghost)

```tsx
// Toggle — 즉시 반영되는 on/off 상태 전환 (낙관적 업데이트)
<Toggle
  checked={task.status === 'COLLECTING'}
  onChange={(v) => v ? onResume(task.identifier) : onPause(task.identifier)}
/>

// Button ghost — 명시적 액션 (클릭 → API → UI 반영)
<Button variant="ghost" size="sm" onClick={() => onResume(task.identifier)}>
  <IconPlay />
</Button>
```

> Toggle은 "현재 상태 표시 + 전환"이 동시에 필요할 때 사용합니다.
> 단순 액션 트리거는 Button을 사용합니다.

### 19.4 Select vs 체크박스 필터

```tsx
// Select — 단일 선택 필터 (마켓 타입, 인터벌)
<Select
  value={marketType}
  onChange={setMarketType}
  options={[
    { value: 'COIN',  label: 'COIN' },
    { value: 'STOCK', label: 'STOCK' },
  ]}
/>

// Checkbox 그룹 — 복수 선택 필터 (상태, 인터벌 멀티 선택)
{STATUS_OPTIONS.map(opt => (
  <Checkbox
    key={opt.value}
    label={opt.label}
    checked={filters.statuses.includes(opt.value)}
    onChange={(v) => toggleStatusFilter(opt.value, v)}
  />
))}
```

---

## 20. 반응형 브레이크포인트 규칙

### 20.1 브레이크포인트 정의

Tailwind 기본값을 그대로 사용합니다.

| 접두사 | 기준 | 대상 기기 |
|--------|------|----------|
| (없음) | 0px ~ | 모바일 (기본) |
| `sm:` | 640px ~ | 태블릿 세로 |
| `lg:` | 1024px ~ | 데스크탑 |
| `xl:` | 1280px ~ | 넓은 데스크탑 |

> `md:`(768px)는 사용하지 않습니다. 분기점을 단순화하기 위해 `sm` / `lg` 두 단계만 사용합니다.

### 20.2 레이아웃 분기 기준

| 요소 | 모바일 (기본) | 태블릿+ (`sm:`) | 데스크탑 (`lg:`) |
|------|-------------|----------------|----------------|
| 네비게이션 | BottomTabBar | 사이드바 (아이콘) | 사이드바 (아이콘+텍스트) |
| 사이드바 너비 | 없음 | `w-16` | `w-60` |
| 수집 현황 목록 | 카드 뷰 (`TaskCardList`) | 테이블 (`TaskTable`) | 테이블 |
| 차트 컨트롤 | 하단 스크롤 바 | 하단 스크롤 바 | 우측 사이드 패널 |
| 페이지 패딩 | `p-4` | `p-5` | `p-6` |

### 20.3 반응형 작성 순서 — Mobile First

```tsx
// ✅ 모바일 기본값 → sm → lg 순으로 작성
className="flex flex-col sm:flex-row lg:gap-6"
className="text-sm lg:text-base"
className="w-full sm:w-auto"

// ❌ 데스크탑 기준으로 작성 후 모바일 덮어쓰기 금지
className="flex-row sm:flex-col"  // 의도가 뒤집혀 가독성 저하
```

### 20.4 JS 분기 — `useIsMobile` 사용 기준

CSS만으로 처리할 수 없는 경우(가상화 행 높이 계산, 조건부 렌더링)에만 사용합니다.

```tsx
// ✅ JS 분기가 필요한 경우
const isMobile = useIsMobile()
return isMobile
  ? <TaskCardList tasks={tasks} onResume={onResume} onPause={onPause} />
  : <TaskTable tasks={tasks} />

// ✅ CSS로 처리 가능한 경우 — useIsMobile 사용 금지
<div className="hidden sm:block">...</div>   // 태블릿+ 전용
<div className="sm:hidden">...</div>         // 모바일 전용
```

---

## 21. 애니메이션 / 트랜지션 규칙

### 21.1 트랜지션 기본 원칙

```tsx
// ✅ 모든 인터랙티브 요소에 transition 적용
className="transition-colors duration-150"   // 색상 변화 (버튼 hover)
className="transition-all duration-200"      // 레이아웃 변화 (사이드바 너비)
className="transition-opacity duration-150"  // 나타남/사라짐

// ❌ transition 없는 즉각 색상 변화 금지 (눈에 거슬림)
className="hover:bg-brand-600"   // transition 없으면 딱딱한 느낌
```

### 21.2 duration 기준

| 용도 | duration | 클래스 |
|------|----------|--------|
| 버튼 hover, 색상 전환 | 150ms | `duration-150` |
| 토글, 체크박스 | 200ms | `duration-200` |
| 사이드바 너비 변화 | 200ms | `duration-200` |
| 모달·드로어 진입 | 150ms | `duration-150` |
| 페이지 전환 | 150ms | `duration-150` |

> 300ms 이상은 사용자가 느리다고 느낍니다. 복잡한 애니메이션이 아니면 200ms를 넘지 않습니다.

### 21.3 easing 기준

```tsx
// ✅ 기본값 — ease-in-out (자연스러운 가속·감속)
className="transition-all duration-200 ease-in-out"

// ✅ 토글 thumb 이동
className="transition-transform duration-200 ease-in-out"

// ❌ linear는 기계적으로 느껴짐 — 색상 전환에만 사용
```

### 21.4 애니메이션 토큰

```tsx
// tailwind.config.ts에 정의된 커스텀 애니메이션
className="animate-fade-in"     // 요소 진입 (opacity 0→1, 0.15s)
className="animate-pulse"       // 수집 중 상태 점멸 (Tailwind 기본)
className="animate-spin"        // 로딩 스피너 (Tailwind 기본)

// 사용 예시
<StatusBadge
  className={task.status === 'COLLECTING' ? 'animate-pulse' : ''}
/>
```

> `animate-*`를 제외한 커스텀 `@keyframes`는 `tailwind.config.ts`에 등록 후 사용합니다.
> 컴포넌트 파일 내 인라인 `@keyframes` 정의는 금지합니다.

---

## 22. Z-index 계층 규칙

### 22.1 계층 정의

`shared/config/zIndex.ts`에 정의된 값만 사용합니다. 임의 숫자 직접 입력은 금지합니다.

```typescript
// shared/config/zIndex.ts
export const Z_INDEX = {
  base:     0,    // 일반 콘텐츠
  sticky:   10,   // 고정 헤더, 사이드바
  dropdown: 20,   // 드롭다운, Select 메뉴
  modal:    30,   // 모달 오버레이 + 패널
  toast:    40,   // 토스트 알림 (최상단)
}
```

```typescript
// tailwind.config.ts — zIndex 토큰으로 등록
zIndex: {
  'sticky':   '10',
  'dropdown': '20',
  'modal':    '30',
  'toast':    '40',
}
```

### 22.2 사용 규칙

```tsx
// ✅ Tailwind 토큰 사용
className="z-dropdown"   // Select, Popover 드롭다운
className="z-modal"      // 모달 오버레이
className="z-toast"      // 토스트 메시지

// ❌ 임의 숫자 금지
className="z-[999]"
style={{ zIndex: 9999 }}
```

> Popover, Select, Tooltip 등 Portal로 렌더링되는 컴포넌트는 `z-dropdown`을 기본으로 사용합니다.
> 모달이 Popover 위에 떠야 할 경우 `z-modal`을 사용합니다.

---

## 23. 레이아웃 패턴 선택 기준

### 23.1 데이터 표시 패턴

| 패턴 | 사용 시점 | 컴포넌트 |
|------|-----------|---------|
| **테이블** | 행이 많고 컬럼 비교가 중요할 때, 데스크탑 | `TaskTable`, `SymbolsTable` |
| **카드 리스트** | 모바일, 항목당 정보가 많아 테이블이 좁을 때 | `TaskCardList`, `TaskCard` |
| **통계 카드** | 숫자 요약, 대시보드 상단 | `StatsCard` |
| **사이드바 + 메인** | 필터·탐색 + 콘텐츠 분리가 필요할 때 | `CollectionSidebar + TaskTable` |

### 23.2 모달 vs 페이지 이동 vs 드로어

| 패턴 | 사용 시점 |
|------|-----------|
| **페이지 이동** | 독립적인 콘텐츠, URL이 필요할 때 |
| **모달** | 간단한 확인·입력, 현재 컨텍스트 유지 필요 시 |
| **드로어 (하단)** | 모바일에서 보조 정보나 액션 목록 표시 |
| **Popover** | 인라인 추가 정보, 클릭 대상 주변에 띄울 때 |
| **Tooltip** | 호버 시 짧은 설명 (1줄 이내) |

### 23.3 빈 상태 / 로딩 / 에러 패턴

```tsx
// 모든 비동기 데이터 영역은 세 가지 상태를 처리합니다
if (query.isLoading) return <Spinner />         // ← Spinner 컴포넌트
if (query.isError)   return <ErrorState />      // ← ErrorState 컴포넌트
if (!data.length)    return <EmptyState />      // ← EmptyState 컴포넌트

return <TaskTable tasks={data} />
```

> 로딩 중에 레이아웃이 뚝뚝 변하는 CLS(Cumulative Layout Shift)를 방지하려면
> Spinner는 실제 콘텐츠와 동일한 높이 영역 안에 렌더링합니다.

### 23.4 스크롤 처리

```tsx
// ✅ 스크롤바 숨김 (가로 스크롤 탭 등)
className="overflow-x-auto scrollbar-none"

// ✅ 콘텐츠 영역 세로 스크롤
className="overflow-y-auto"

// ✅ 무한 스크롤 트리거 — IntersectionObserver
<div ref={infiniteScrollRef} className="h-1" />   // 하단 감지 sentinel

// ❌ 스크롤 이벤트 직접 바인딩 금지 (성능 저하)
window.addEventListener('scroll', handleScroll)
```

---

## 24. 아이콘 사용 규칙

### 24.1 아이콘 소스

모든 아이콘은 `react-icons`의 **Feather Icons (`Fi` 접두사)** 를 사용합니다.
`shared/ui/icons/index.ts`에 등록된 아이콘만 사용합니다.

```typescript
// shared/ui/icons/index.ts — 등록된 아이콘 목록
export { FiPlay     as IconPlay    } from 'react-icons/fi'
export { FiPause    as IconPause   } from 'react-icons/fi'
export { FiRefreshCw as IconRefresh } from 'react-icons/fi'
export { FiSearch   as IconSearch  } from 'react-icons/fi'
export { FiSettings as IconSettings } from 'react-icons/fi'
export { FiBarChart2 as IconChart  } from 'react-icons/fi'
export { FiList     as IconList    } from 'react-icons/fi'
export { FiSun      as IconSun     } from 'react-icons/fi'
export { FiMoon     as IconMoon    } from 'react-icons/fi'
export { FiChevronDown as IconChevronDown } from 'react-icons/fi'
export { FiX        as IconX       } from 'react-icons/fi'
export { FiCheck    as IconCheck   } from 'react-icons/fi'
export { FiAlertCircle as IconAlert } from 'react-icons/fi'
```

### 24.2 사용 규칙

```tsx
// ✅ icons/index.ts에서 import
import { IconPlay, IconPause, IconRefresh } from '@shared/ui/icons'

<Button variant="ghost" size="sm">
  <IconPlay className="text-base" />
</Button>

// ❌ react-icons에서 직접 import 금지 (아이콘 분산 관리)
import { FiPlay } from 'react-icons/fi'

// ❌ 새 아이콘을 icons/index.ts에 등록하지 않고 사용 금지
import { FiStar } from 'react-icons/fi'   // 등록 후 사용할 것
```

### 24.3 아이콘 크기 기준

```tsx
// ✅ 텍스트 기준 상대 크기 사용
className="text-sm"     // 14px — 버튼 내 아이콘 (sm 버튼)
className="text-base"   // 16px — 버튼 내 아이콘 (md 버튼), 인라인 아이콘
className="text-lg"     // 18px — 사이드바 네비게이션 아이콘
className="text-xl"     // 20px — 강조 아이콘

// ❌ 픽셀 직접 지정 금지
style={{ fontSize: '16px' }}
className="text-[16px]"
```

### 24.4 아이콘 + 텍스트 정렬

```tsx
// ✅ items-center + gap으로 정렬
<span className="flex items-center gap-1.5">
  <IconSearch className="text-base shrink-0" />
  <span>검색</span>
</span>

// ✅ 아이콘만 있는 버튼은 aria-label 필수
<Button variant="ghost" size="sm" aria-label="새로고침">
  <IconRefresh className="text-base" />
</Button>
```

### 24.5 새 아이콘 추가 절차

```
1. Feather Icons에서 적합한 아이콘 선택 (https://feathericons.com)
2. shared/ui/icons/index.ts에 Icon* 형식으로 등록
3. 팀 공유 후 사용
```

> 다른 아이콘 라이브러리 (`Heroicons`, `Lucide` 등) 혼용 금지.
> 디자인 일관성을 위해 Feather Icons 단일 소스를 유지합니다.

---

## 25. 개발 워크플로우

> PR을 올리기 전 아래 4단계를 순서대로 완료해야 합니다.
> CI에서도 동일한 단계가 자동 실행되므로, 로컬에서 통과하지 못하면 CI도 실패합니다.

```
개발 → 테스트 코드 작성 → 린트 검증 → 코드 검증
```

---

### 25.1 개발

#### 시작 전 체크리스트

```
□ 브랜치를 develop에서 분기했는가?
  git checkout develop && git pull
  git checkout -b feat/TP-{번호}-{간략설명}

□ 구현할 컴포넌트가 shared/ui에 있는가?
  없으면 먼저 공통 컴포넌트를 만들고 시작

□ FSD 레이어 규칙을 확인했는가?
  구현 위치: pages / widgets / features / entities / shared 중 어디?
```

#### 개발 서버 실행

```bash
npm run dev          # Vite 개발 서버 (http://localhost:5173)
```

#### 새 기능 구현 순서

```
1. entities/   — 타입 정의, Zod 스키마, API 함수, Query 훅
2. features/   — mutation 훅, 비즈니스 로직
3. widgets/    — 재사용 UI 블록 (필요 시)
4. pages/      — model/ 훅으로 데이터 연결, ui/ 컴포넌트 조립
5. shared/ui/  — 신규 공통 컴포넌트 (필요 시 먼저 추가)
```

#### 개발 중 지켜야 할 규칙

```
□ 날 HTML 태그 대신 shared/ui 컴포넌트 사용 (Section 16)
□ 색상·간격은 Tailwind 토큰 사용, 하드코딩 금지 (Section 5, 18)
□ import 경로는 @shared / @entities 등 앨리어스 사용 (Section 3)
□ any 타입 사용 금지 — TypeScript 엄격 모드 (Section 4)
□ console.log 프로덕션 코드에 남기지 않기
```

---

### 25.2 테스트 코드 작성

#### 테스트 실행 명령어

```bash
npm run test           # vitest watch 모드 (개발 중 실시간)
npm run test:run       # 단일 실행 (CI용)
npm run test:coverage  # 커버리지 리포트 생성
```

#### 작성 대상 및 우선순위

| 우선순위 | 대상 | 예시 |
|---------|------|------|
| **필수** | `shared/utils/` 유틸 함수 | `formatPrice`, `formatRelativeTime`, `cn` |
| **필수** | `entities/*/model/` 파서·스키마 | Zod 스키마 검증, 파서 변환 |
| **권장** | `features/*/model/` 훅 비즈니스 로직 | mutation 성공·실패 케이스 |
| **선택** | `shared/ui/` 핵심 컴포넌트 | `Button` variant, `Badge` 렌더링 |

#### 테스트 작성 원칙

```typescript
// ✅ 테스트 파일은 대상 파일 옆에 위치
// shared/utils/formatPrice.ts
// shared/utils/formatPrice.test.ts

// ✅ 정상 케이스 + 엣지 케이스 + 경계값 모두 작성
describe('formatPrice', () => {
  // 정상
  it('천 단위 쉼표를 붙인다', () => {
    expect(formatPrice(1000000)).toBe('1,000,000')
  })
  // 엣지 케이스
  it('null이면 "-"를 반환한다', () => {
    expect(formatPrice(null)).toBe('-')
  })
  // 경계값
  it('0은 "0"을 반환한다', () => {
    expect(formatPrice(0)).toBe('0')
  })
})

// ✅ Zod 스키마 — 유효/무효 데이터 모두 검증
describe('MarketSymbolSchema', () => {
  it('올바른 데이터는 파싱에 성공한다', () => {
    const result = MarketSymbolSchema.safeParse(validFixture)
    expect(result.success).toBe(true)
  })
  it('identifier가 UUID 형식이 아니면 실패한다', () => {
    const result = MarketSymbolSchema.safeParse({ ...validFixture, identifier: 'not-uuid' })
    expect(result.success).toBe(false)
  })
})

// ❌ 구현 세부사항을 테스트하지 않음 (내부 상태, private 변수)
// ❌ 외부 API를 실제로 호출하는 테스트 금지 — msw로 모킹
```

#### 커버리지 기준

| 레이어 | 목표 | 미달 시 |
|--------|------|---------|
| `shared/utils` | 90% | PR 블로킹 |
| `entities/*/model` | 80% | PR 블로킹 |
| `features/*/model` | 70% | 경고 후 머지 가능 |
| `shared/ui` | 주요 컴포넌트 | 권장 |

---

### 25.3 린트 검증

#### 실행 명령어

```bash
npm run lint           # ESLint 검사
npm run lint:fix       # ESLint 자동 수정
npm run format         # Prettier 포맷팅 적용
npm run format:check   # Prettier 포맷팅 검사 (CI용)
```

#### package.json scripts 정의

```json
{
  "scripts": {
    "dev":            "vite",
    "build":          "tsc && vite build",
    "lint":           "eslint src --ext .ts,.tsx --report-unused-disable-directives",
    "lint:fix":       "eslint src --ext .ts,.tsx --fix",
    "format":         "prettier --write src",
    "format:check":   "prettier --check src",
    "test":           "vitest",
    "test:run":       "vitest run",
    "test:coverage":  "vitest run --coverage",
    "type-check":     "tsc --noEmit"
  }
}
```

#### 린트에서 반드시 통과해야 하는 규칙

```
□ @typescript-eslint/no-explicit-any    — any 사용 금지
□ @typescript-eslint/no-unused-vars     — 미사용 변수 금지
□ react-hooks/rules-of-hooks            — 훅 규칙 위반 금지
□ react-hooks/exhaustive-deps           — useEffect 의존성 누락 경고
□ import/no-cycle                        — 순환 의존성 금지
□ no-console                             — console.log 프로덕션 금지
```

#### 린트 오류 처리 원칙

```typescript
// ✅ 오류를 근본적으로 수정
const data: SymbolData = response.data   // any 대신 구체적 타입

// ⚠️ eslint-disable은 불가피한 경우에만, 이유를 반드시 주석으로 명시
// eslint-disable-next-line @typescript-eslint/no-explicit-any
const legacy: any = window.__LEGACY_DATA__   // 레거시 전역 변수 접근 불가피

// ❌ 이유 없는 eslint-disable 금지 — 코드 리뷰에서 반려
// eslint-disable-next-line @typescript-eslint/no-explicit-any
const foo: any = bar
```

---

### 25.4 코드 검증

#### 실행 명령어

```bash
npm run type-check     # TypeScript 타입 검사 (tsc --noEmit)
npm run build          # 프로덕션 빌드 검증 (tsc + vite build)
```

#### 타입 검사 원칙

```bash
# ✅ 타입 에러 0건 상태에서 PR 제출
npm run type-check
# Found 0 errors ← 이 상태여야 함

# 타입 에러 예시 및 수정 방향
# Error: Property 'identifier' does not exist on type 'MarketSymbol'
# → 타입 정의 확인, 'id' 대신 'identifier' 사용
```

#### 빌드 검증

```bash
npm run build
# ✅ dist/ 폴더 생성 및 경고 없이 완료되어야 함
# ⚠️ 번들 크기 경고(500kb↑) 발생 시 코드 스플리팅 검토
```

#### PR 제출 전 최종 체크리스트

```
개발
□ 날 HTML 태그를 쓰지 않고 디자인 시스템 컴포넌트를 사용했는가?
□ 색상·간격에 하드코딩된 값이 없는가?
□ FSD 레이어 경계를 넘는 import가 없는가?
□ console.log가 남아 있지 않은가?
□ any 타입을 사용하지 않았는가?

테스트
□ 새로 추가한 유틸·파서에 테스트를 작성했는가?
□ npm run test:run 전체 통과했는가?
□ 커버리지 기준을 충족하는가?

린트
□ npm run lint 오류 0건인가?
□ npm run format:check 통과했는가?

코드 검증
□ npm run type-check 에러 0건인가?
□ npm run build 성공했는가?
□ 셀프 리뷰를 완료했는가? (변경된 파일 전체 diff 확인)
```

#### CI 파이프라인 구성 (참고)

```yaml
# .github/workflows/ci.yml (예시)
jobs:
  verify:
    steps:
      - run: npm run type-check   # 1. 타입 검사
      - run: npm run lint         # 2. 린트
      - run: npm run format:check # 3. 포맷 검사
      - run: npm run test:run     # 4. 테스트
      - run: npm run build        # 5. 빌드
```

> CI의 모든 단계는 로컬 명령어와 동일합니다.
> 로컬에서 전부 통과하면 CI도 통과합니다. CI에서만 실패하는 경우는 없어야 합니다.

---

## 부록 — 빠른 참조

### 자주 헷갈리는 필드명

| ❌ 잘못된 이름 | ✅ 올바른 이름 | 근거 |
|--------------|--------------|------|
| `id` | `identifier` | 백엔드 PK 필드명 통일 |
| `symbolId` | `symbolIdentifier` | FK도 동일 규칙 |
| `createdAt` | `createdDate` | 백엔드 네이밍 통일 |
| `lastCollectedAt` | `lastCollectedTime` | 백엔드 네이밍 통일 |
| `isActive` | `status === 'COLLECTING'` | 해당 필드 없음 |

### 존재하지 않는 Enum 값

| ❌ 잘못된 값 | ✅ 올바른 값 |
|-------------|------------|
| `'RUNNING'` | `'COLLECTING'` |
| `'ACTIVE'`  | `'COLLECTING'` |
| `'STOPPED'` | `'PAUSED'` |
