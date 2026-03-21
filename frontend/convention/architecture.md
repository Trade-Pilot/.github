# 아키텍처 — FSD 레이어, 디렉토리 네이밍, Import 규칙

> 원본: `frontend/convention.md` Section 1~3

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
