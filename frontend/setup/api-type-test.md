<!-- 원본: frontend/setup.md — 섹션 16~18 -->

# API 타입 자동 생성, 테스트 전략, MSW 모킹

> openapi-typescript, Zod 스키마, Vitest, RTL, Playwright, MSW

---

## 16. API 타입 자동 생성 & 런타임 검증

### 16.1 openapi-typescript (백엔드 스펙 → 타입 자동 생성)

백엔드 Swagger 스펙으로부터 API 요청/응답 타입을 자동 생성합니다. 수동으로 타입을 유지하는 비용을 제거하고, 백엔드 변경 시 타입 오류를 컴파일 타임에 즉시 감지합니다.

```bash
npm install -D openapi-typescript
```

```json
// package.json scripts
{
  "generate:api": "openapi-typescript http://localhost:8080/v3/api-docs -o src/shared/api/schema.d.ts"
}
```

```typescript
// 생성된 schema.d.ts를 기반으로 타입 추출
// shared/api/types.ts
import type { paths } from './schema'

// 경로별 응답 타입 추출
type CollectTaskListResponse =
  paths['/market-candle-collect-tasks']['get']['responses']['200']['content']['application/json']

type CollectTaskStatusResponse =
  paths['/market-candle-collect-task-status']['get']['responses']['200']['content']['application/json']
```

**운영 방식**: 백엔드 API 변경 시 `npm run generate:api` 실행 → 타입 오류 확인 → 수정

---

### 16.2 Zod — 단일 스키마 원칙 (런타임 검증 + 타입 추론)

TypeScript 타입은 컴파일 타임에만 존재합니다. 백엔드가 예상치 못한 형태의 응답을 보내도 런타임에서는 감지할 수 없습니다.

**기존 방식의 문제**: `types.ts`(interface)와 `schemas.ts`(Zod)를 따로 두면 두 곳이 불일치할 수 있습니다. 실제로 이 프로젝트에서 `lastCollectedAt` vs `lastCollectedTime` 불일치 버그가 이 구조에서 발생했습니다.

**단일 스키마 원칙**: Zod 스키마 하나에서 `z.infer`로 TypeScript 타입까지 추출합니다. 스키마와 타입의 단일 진실 공급원(Single Source of Truth)을 유지합니다.

```bash
npm install zod
```

#### 파일 구조

```
entities/market/model/
├── enums.ts     # Enum만 (z.nativeEnum과 함께 쓰이므로 별도 유지)
├── schemas.ts   # Zod 스키마 + z.infer 타입 export ← 핵심
└── params.ts    # 요청 파라미터 interface (런타임 검증 불필요)
```

```typescript
// entities/market/model/enums.ts
// Enum은 런타임 JS 값이 필요하므로 z.infer 대체 불가 — 별도 파일 유지
export enum MarketType               { COIN = 'COIN', STOCK = 'STOCK' }
export enum MarketSymbolStatus       { LISTED = 'LISTED', /* ... */ }
export enum MarketCandleInterval     { MIN_1 = 'MIN_1', /* ... */ }
export enum MarketCandleCollectStatus { CREATED = 'CREATED', COLLECTING = 'COLLECTING', /* ... */ }
```

```typescript
// entities/market/model/schemas.ts
import { z } from 'zod'
import {
  MarketCandleCollectStatus,
  MarketCandleInterval,
  MarketSymbolStatus,
  MarketType,
} from './enums'

// ── 스키마 정의 ────────────────────────────────────────────────

export const MarketSymbolSchema = z.object({
  identifier:   z.string().uuid(),
  code:         z.string().regex(/^[A-Z]+-[A-Z]+$/),
  name:         z.string(),
  market:       z.nativeEnum(MarketType),
  status:       z.nativeEnum(MarketSymbolStatus),
  createdDate:  z.string().datetime(),
  modifiedDate: z.string().datetime(),
})

export const CollectTaskSchema = z.object({
  identifier:         z.string().uuid(),
  symbolIdentifier:   z.string().uuid(),
  symbol:             MarketSymbolSchema.optional(),
  interval:           z.nativeEnum(MarketCandleInterval),
  status:             z.nativeEnum(MarketCandleCollectStatus),
  retryCount:         z.number().int().min(0),
  createdDate:        z.string().datetime(),
  lastCollectedTime:  z.string().datetime().nullable(),
  lastCollectedPrice: z.string().nullable(),
})

export const MarketCandleSchema = z.object({
  symbolIdentifier: z.string().uuid(),
  interval:         z.nativeEnum(MarketCandleInterval),
  time:             z.string().datetime(),
  open:             z.string(),
  high:             z.string(),
  low:              z.string(),
  close:            z.string(),
  volume:           z.string(),
  amount:           z.string(),
  isFlat:           z.boolean(),
})

export const CollectTaskStatsSchema = z.object({
  total:        z.number().int(),
  byStatus:     z.record(z.nativeEnum(MarketCandleCollectStatus), z.number()),
  byMarketType: z.record(z.nativeEnum(MarketType), z.number()),
})

// ── 타입 추출 (interface 이중 선언 없음) ────────────────────────
// z.infer가 스키마로부터 TypeScript 타입을 자동 생성
// 스키마 수정 → 타입 자동 반영 → 불일치 버그 구조적 불가능

export type MarketSymbol            = z.infer<typeof MarketSymbolSchema>
export type MarketCandleCollectTask = z.infer<typeof CollectTaskSchema>
export type MarketCandle            = z.infer<typeof MarketCandleSchema>
export type CollectTaskStats        = z.infer<typeof CollectTaskStatsSchema>
```

```typescript
// entities/market/model/params.ts
// 요청 파라미터는 API 응답이 아니므로 런타임 검증 불필요 → interface 사용
import type { MarketCandleCollectStatus, MarketCandleInterval, MarketType } from './enums'

export interface CollectTaskListParams {
  keyword?: string; statuses?: MarketCandleCollectStatus[]
  market?: MarketType[]; intervals?: MarketCandleInterval[]
  symbolCursor?: string; intervalCursor?: MarketCandleInterval; limit?: number
}

export interface CandleListParams {
  symbolId: string; interval: MarketCandleInterval
  cursor?: string; limit?: number; orderBy?: 'ASC' | 'DESC'
}
```

**검증 전략**: `parseOrThrow()` (`shared/utils/parse.ts`) 사용. 개발 환경은 `console.error`로 원인 출력 후 throw, 프로덕션은 그냥 throw. 향후 모니터링 도구 도입 시 해당 함수만 수정.

---

## 17. 테스트 전략

금융 앱이므로 버그가 실제 손실로 이어질 수 있습니다. 레이어별로 테스트 범위를 명확히 합니다.

```bash
npm install -D \
  vitest \
  @vitest/ui \
  @testing-library/react \
  @testing-library/user-event \
  @testing-library/jest-dom \
  jsdom \
  playwright \
  @playwright/test \
  msw   # 17절 MSW와 공유
```

### 17.1 테스트 레이어 구분

```
테스트 피라미드:

        /\
       /E2E\         playwright (핵심 사용자 시나리오)
      /──────\
     /통합테스트\      RTL + MSW (페이지 단위, API 모킹)
    /────────────\
   /  단위 테스트  \   Vitest (유틸, 훅, 도메인 로직)
  /────────────────\
```

| 대상 | 도구 | 범위 |
|------|------|------|
| 유틸 함수 (`formatNumber`, `cn` 등) | Vitest | 100% 커버리지 목표 |
| 도메인 로직 (parsers, Zod schemas) | Vitest | 100% 커버리지 목표 |
| 커스텀 훅 | Vitest + renderHook | 주요 시나리오 |
| 공용 컴포넌트 (shared/ui) | RTL | 인터랙션 위주 |
| 페이지 통합 | RTL + MSW | 핵심 플로우 |
| E2E | Playwright | 수집 제어, 차트 로딩 등 |

### 17.2 Vitest 설정

```typescript
// vitest.config.ts
import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'
import path from 'path'

export default defineConfig({
  plugins: [react()],
  test: {
    globals:     true,
    environment: 'jsdom',
    setupFiles:  ['./src/test/setup.ts'],
    alias: {
      // vite.config.ts의 alias와 동일하게 유지 (누락 시 테스트에서 import 오류 발생)
      '@app':      path.resolve(__dirname, 'src/app'),
      '@pages':    path.resolve(__dirname, 'src/pages'),
      '@widgets':  path.resolve(__dirname, 'src/widgets'),
      '@features': path.resolve(__dirname, 'src/features'),
      '@entities': path.resolve(__dirname, 'src/entities'),
      '@shared':   path.resolve(__dirname, 'src/shared'),
    },
  },
})
```

```typescript
// src/test/setup.ts
import '@testing-library/jest-dom'
import { server } from './mocks/server'    // MSW 서버

beforeAll(()  => server.listen())
afterEach(()  => server.resetHandlers())
afterAll(()   => server.close())
```

### 17.3 단위 테스트 예시 (유틸)

```typescript
// shared/utils/formatNumber.test.ts
describe('formatPrice', () => {
  it('천 단위 구분자를 붙인다', () => {
    expect(formatPrice(95_000_000)).toBe('95,000,000')
  })
  it('0은 0으로 표시한다', () => {
    expect(formatPrice(0)).toBe('0')
  })
})

describe('formatRate', () => {
  it('양수에는 + 접두사를 붙인다', () => {
    expect(formatRate(0.0512)).toBe('+5.12%')
  })
  it('음수는 그대로 표시한다', () => {
    expect(formatRate(-0.0215)).toBe('-2.15%')
  })
})
```

### 17.4 훅 테스트 예시

```typescript
// entities/market/queries/useCollectTasksQuery.test.ts
describe('useCollectTasksInfiniteQuery', () => {
  it('초기 로드 시 첫 페이지 데이터를 반환한다', async () => {
    const { result } = renderHook(
      () => useCollectTasksInfiniteQuery({}),
      { wrapper: QueryClientWrapper }
    )
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data?.pages[0]).toHaveLength(100)
  })

  it('hasNextPage가 false이면 fetchNextPage를 호출해도 추가 요청이 없다', async () => {
    // ...
  })
})
```

### 17.5 테스트 파일 위치 규칙

```
컴포넌트/훅과 같은 디렉토리에 배치:
  shared/utils/formatNumber.ts
  shared/utils/formatNumber.test.ts

  entities/market/queries/useCollectTasksQuery.ts
  entities/market/queries/useCollectTasksQuery.test.ts

E2E는 별도 디렉토리:
  e2e/
  ├── market-collection.spec.ts
  ├── market-chart.spec.ts
  └── auth.spec.ts
```

---

## 18. 개발 API 모킹 (MSW)

백엔드 API가 완성되기 전에도 프론트엔드 개발을 병렬로 진행할 수 있습니다. 테스트에서도 동일한 핸들러를 재사용합니다.

```bash
npm install -D msw
npx msw init public/ --save
```

### 18.1 핸들러 정의

```typescript
// src/test/mocks/handlers/marketHandlers.ts
import { http, HttpResponse } from 'msw'
import { mockCollectTasks, mockStats, mockCandles } from '../fixtures/market'

export const marketHandlers = [
  // 수집 작업 목록
  http.get('/market-candle-collect-tasks', ({ request }) => {
    const url    = new URL(request.url)
    const limit  = Number(url.searchParams.get('limit') ?? 100)
    const cursor = url.searchParams.get('symbolCursor')

    const data = cursor
      ? mockCollectTasks.slice(50)   // 두 번째 페이지 시뮬레이션
      : mockCollectTasks.slice(0, limit)

    return HttpResponse.json(data)
  }),

  // 통계
  http.get('/market-candle-collect-task-status', () =>
    HttpResponse.json(mockStats)
  ),

  // 전체 재시작
  http.put('/market-candle-collect-tasks/resume-all', () =>
    new HttpResponse(null, { status: 200 })
  ),

  // 캔들 데이터
  http.get('/symbols/:symbolId/intervals/:interval/market-candles', () =>
    HttpResponse.json(mockCandles)
  ),
]
```

### 18.2 픽스처 데이터

```typescript
// src/test/mocks/fixtures/market.ts
// 실제 데이터 형태와 동일한 목 데이터 정의
export const mockCollectTasks: CollectTaskApiResponse[] = Array.from({ length: 120 }, (_, i) => ({
  identifier:         `task-${i}`,
  symbolIdentifier:   `symbol-${Math.floor(i / 12)}`,
  interval:           INTERVALS[i % 12],
  status:             randomStatus(),
  retryCount:         0,
  createdDate:        '2024-01-01T00:00:00Z',
  lastCollectedTime:  '2024-01-15T12:34:00Z',
  lastCollectedPrice: '95000000',
}))
```

### 18.3 개발 환경 활성화

```typescript
// app/index.tsx
async function enableMocking() {
  if (import.meta.env.DEV && import.meta.env.VITE_USE_MOCK === 'true') {
    const { worker } = await import('../test/mocks/browser')
    return worker.start({ onUnhandledRequest: 'warn' })
  }
}

enableMocking().then(() => {
  ReactDOM.createRoot(document.getElementById('root')!).render(<App />)
})
```

```bash
# .env.development.local (개별 개발자 로컬 설정)
VITE_USE_MOCK=true
```

---
