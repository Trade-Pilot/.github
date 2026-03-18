# Market - 프론트엔드 설계

> Market Service와 연동하는 프론트엔드 설계 문서 (재개발 기준)

---

## 1. 기술 스택

### 1.1 권장 스택

| 분류 | 기존 | 변경 | 이유 |
|------|------|------|------|
| 빌드 도구 | CRA (react-scripts) | **Vite** | CRA 공식 deprecated, Vite HMR 5~10배 빠름 |
| 스타일링 | styled-components | **Tailwind CSS** | 클래스 기반으로 일관된 디자인 시스템 구축, CSS-in-JS 런타임 오버헤드 제거 |
| 서버 상태 | useEffect + useState | **TanStack Query v5** | 캐싱, 자동 리패치, 무한 스크롤, 낙관적 업데이트 내장. 반복 보일러플레이트 제거 |
| 클라이언트 상태 | Redux Toolkit | **Zustand** | 인증 등 전역 상태는 단순. Redux는 이 규모에 과함 |
| 차트 | Highcharts | **Lightweight Charts (TradingView)** | 금융 차트 특화 라이브러리, Highcharts 대비 성능 우수, 라이선스 무료 |
| HTTP | Axios | **Axios** (유지) | - |
| 라우터 | react-router-dom v6 | **react-router-dom v6** (유지) | - |
| 언어 | TypeScript | **TypeScript** (유지) | - |

### 1.2 주요 패키지

```json
{
  "dependencies": {
    "react": "^18.3.1",
    "react-dom": "^18.3.1",
    "typescript": "^5.x",
    "react-router-dom": "^6.x",
    "axios": "^1.x",
    "@tanstack/react-query": "^5.x",
    "zustand": "^4.x",
    "lightweight-charts": "^4.x",
    "react-icons": "^5.x"
  },
  "devDependencies": {
    "vite": "^5.x",
    "@vitejs/plugin-react": "^4.x",
    "tailwindcss": "^3.x",
    "autoprefixer": "^10.x",
    "postcss": "^8.x"
  }
}
```

---

## 2. FSD 디렉토리 구조

```
src/
├── app/
│   ├── router.tsx                  # React Router 설정
│   ├── providers.tsx               # QueryClientProvider, 전역 프로바이더
│   └── index.tsx
│
├── pages/
│   ├── market-collection/          # 수집 현황 대시보드
│   │   ├── index.tsx               # 페이지 진입점
│   │   ├── ui/
│   │   │   ├── MarketCollectionPage.tsx
│   │   │   ├── CollectionHeader.tsx
│   │   │   ├── CollectionSidebar.tsx
│   │   │   └── CollectionTaskTable.tsx
│   │   └── model/
│   │       └── useCollectionPage.ts    # 페이지 통합 훅
│   │
│   ├── market-chart/               # 캔들 차트 뷰어
│   │   ├── index.tsx
│   │   ├── ui/
│   │   │   ├── MarketChartPage.tsx
│   │   │   ├── ChartHeader.tsx
│   │   │   ├── ChartSidebar.tsx
│   │   │   └── CandleChartView.tsx
│   │   └── model/
│   │       └── useChartPage.ts
│   │
│   └── market-symbols/             # 심볼 관리
│       ├── index.tsx
│       ├── ui/
│       │   ├── MarketSymbolsPage.tsx
│       │   ├── SymbolsHeader.tsx
│       │   └── SymbolsTable.tsx
│       └── model/
│           └── useSymbolsPage.ts
│
├── widgets/
│   ├── candle-chart/               # 재사용 캔들 차트 위젯
│   │   ├── ui/CandleChart.tsx      # Lightweight Charts 래퍼
│   │   └── index.ts
│   └── task-table/                 # 재사용 수집 작업 테이블
│       ├── ui/TaskTable.tsx
│       └── index.ts
│
├── features/
│   └── market-collection-control/  # 수집 제어 기능 (resume/pause)
│       ├── ui/
│       │   ├── ResumeAllButton.tsx
│       │   ├── PauseAllButton.tsx
│       │   └── TaskActionButtons.tsx
│       └── model/
│           ├── useResumeAll.ts
│           ├── usePauseAll.ts
│           └── useTaskAction.ts
│
├── entities/
│   └── market/
│       ├── api/
│       │   ├── symbolApi.ts        # 심볼 REST API
│       │   ├── collectTaskApi.ts   # 수집 작업 REST API
│       │   └── candleApi.ts        # 캔들 REST API
│       ├── model/
│       │   ├── enums.ts            # Enum 정의 (MarketType, MarketCandleCollectStatus 등)
│       │   ├── schemas.ts          # Zod 스키마 + z.infer 타입 export (단일 진실 공급원)
│       │   └── parsers.ts          # API 응답 → 도메인 모델 변환
│       ├── queries/
│       │   ├── useSymbolsQuery.ts          # TanStack Query: 심볼 목록
│       │   ├── useCollectTasksQuery.ts     # TanStack Query: 수집 작업 (무한)
│       │   ├── useCollectTaskStatsQuery.ts # TanStack Query: 통계
│       │   └── useCandlesQuery.ts          # TanStack Query: 캔들 (무한)
│       └── index.ts
│
└── shared/
    ├── api/
    │   ├── client.ts               # Axios 인스턴스 (인터셉터 포함)
    │   └── types.ts                # API 공통 타입, Enum
    ├── store/
    │   └── authStore.ts            # Zustand: 인증 상태
    ├── hooks/
    │   ├── useUrlParams.ts         # URL 파라미터 상태
    │   └── useCandleWebSocket.ts   # WebSocket 실시간 캔들
    ├── ui/
    │   ├── Spinner.tsx
    │   ├── Badge.tsx               # 상태 배지
    │   ├── EmptyState.tsx
    │   └── ErrorBoundary.tsx
    └── constants/
        └── market.ts               # INTERVAL_LABELS 등 공통 상수
```

---

## 3. 공통 도메인 타입

> **단일 스키마 원칙**: 도메인 모델 타입은 `interface`로 이중 선언하지 않습니다.
> Zod 스키마 하나에서 런타임 검증과 TypeScript 타입을 함께 얻습니다.

### 3.1 Enum (`entities/market/model/enums.ts`)

Enum은 Zod `z.nativeEnum()`과 함께 사용되므로 별도 파일에 유지합니다.
JavaScript 런타임 값이 필요하기 때문에 `z.infer`로 대체할 수 없습니다.

```typescript
// entities/market/model/enums.ts
export enum MarketType {
  COIN  = 'COIN',
  STOCK = 'STOCK',
}

export enum MarketSymbolStatus {
  LISTED         = 'LISTED',
  WARNING        = 'WARNING',
  CAUTION        = 'CAUTION',
  TRADING_HALTED = 'TRADING_HALTED',
  DELISTED       = 'DELISTED',
}

export enum MarketCandleInterval {
  MIN_1   = 'MIN_1',
  MIN_3   = 'MIN_3',
  MIN_5   = 'MIN_5',
  MIN_10  = 'MIN_10',
  MIN_15  = 'MIN_15',
  MIN_30  = 'MIN_30',
  MIN_60  = 'MIN_60',
  MIN_120 = 'MIN_120',
  MIN_180 = 'MIN_180',
  DAY     = 'DAY',
  WEEK    = 'WEEK',
  MONTH   = 'MONTH',
}

export enum MarketCandleCollectStatus {
  CREATED    = 'CREATED',
  COLLECTING = 'COLLECTING',
  COLLECTED  = 'COLLECTED',
  ERROR      = 'ERROR',
  PAUSED     = 'PAUSED',
  DELISTED   = 'DELISTED',
}
```

### 3.2 도메인 모델 스키마 (`entities/market/model/schemas.ts`)

`interface` 선언 없이 Zod 스키마에서 `z.infer`로 타입을 추출합니다.
스키마와 타입이 항상 동기화되어 불일치 버그가 구조적으로 불가능합니다.

```typescript
// entities/market/model/schemas.ts
import { z } from 'zod'
import {
  MarketCandleCollectStatus,
  MarketCandleInterval,
  MarketSymbolStatus,
  MarketType,
} from './enums'

// ── 심볼 ──────────────────────────────────────────────────────
export const MarketSymbolSchema = z.object({
  identifier:   z.string().uuid(),
  code:         z.string().regex(/^[A-Z]+-[A-Z]+$/),  // 예: KRW-BTC
  name:         z.string(),
  market:       z.nativeEnum(MarketType),
  status:       z.nativeEnum(MarketSymbolStatus),
  createdDate:  z.string().datetime(),
  modifiedDate: z.string().datetime(),
})

// interface 선언 없이 스키마에서 타입 추출 — 단일 진실 공급원
export type MarketSymbol = z.infer<typeof MarketSymbolSchema>

// ── 수집 작업 ────────────────────────────────────────────────
export const CollectTaskSchema = z.object({
  identifier:         z.string().uuid(),
  symbolIdentifier:   z.string().uuid(),                 // FK → MarketSymbol.identifier
  symbol:             MarketSymbolSchema.optional(),      // JOIN 시 포함
  interval:           z.nativeEnum(MarketCandleInterval),
  status:             z.nativeEnum(MarketCandleCollectStatus),
  retryCount:         z.number().int().min(0),
  createdDate:        z.string().datetime(),
  lastCollectedTime:  z.string().datetime().nullable(),  // ← lastCollectedAt 아님
  lastCollectedPrice: z.string().nullable(),             // BigDecimal → string
})

export type MarketCandleCollectTask = z.infer<typeof CollectTaskSchema>

// ── 캔들 ──────────────────────────────────────────────────────
export const MarketCandleSchema = z.object({
  symbolIdentifier: z.string().uuid(),
  interval:         z.nativeEnum(MarketCandleInterval),
  time:             z.string().datetime(),
  open:             z.string(),   // BigDecimal → string (정밀도 손실 방지)
  high:             z.string(),
  low:              z.string(),
  close:            z.string(),
  volume:           z.string(),
  amount:           z.string(),
  isFlat:           z.boolean(),  // volume === 0: Flat Candle 여부
})

export type MarketCandle = z.infer<typeof MarketCandleSchema>

// ── 통계 ──────────────────────────────────────────────────────
export const CollectTaskStatsSchema = z.object({
  total:       z.number().int(),
  byStatus:    z.record(z.nativeEnum(MarketCandleCollectStatus), z.number()),
  byMarketType: z.record(z.nativeEnum(MarketType), z.number()),
})

export type CollectTaskStats = z.infer<typeof CollectTaskStatsSchema>
```

### 3.3 API 파라미터 타입 (`entities/market/model/params.ts`)

요청 파라미터는 API 응답이 아니므로 런타임 검증이 불필요합니다.
`interface`를 그대로 사용합니다.

```typescript
// entities/market/model/params.ts
import type { MarketCandleCollectStatus, MarketCandleInterval, MarketType } from './enums'

export interface CollectTaskListParams {
  keyword?:        string
  statuses?:       MarketCandleCollectStatus[]
  market?:         MarketType[]
  intervals?:      MarketCandleInterval[]
  symbolCursor?:   string
  intervalCursor?: MarketCandleInterval
  limit?:          number
}

export interface CandleListParams {
  symbolId:   string
  interval:   MarketCandleInterval
  cursor?:    string           // ISO 8601 timestamp
  limit?:     number           // 기본값: 200
  orderBy?:   'ASC' | 'DESC'
}
```

---

## 4. TanStack Query 설계 (`entities/market/queries/`)

### 4.1 Query Key 구조

```typescript
// entities/market/queries/queryKeys.ts
export const marketQueryKeys = {
  symbols:              (market?: MarketType) =>
                          ['market', 'symbols', market] as const,
  collectTaskStats:     () =>
                          ['market', 'collect-tasks', 'stats'] as const,
  collectTasks:         (params: CollectTaskListParams) =>
                          ['market', 'collect-tasks', params] as const,
  candles:              (symbolId: string, interval: MarketCandleInterval) =>
                          ['market', 'candles', symbolId, interval] as const,
}
```

### 4.2 심볼 목록 쿼리

```typescript
// useSymbolsQuery.ts
export const useSymbolsQuery = (market?: MarketType) =>
  useQuery({
    queryKey: marketQueryKeys.symbols(market),
    queryFn:  () => symbolApi.getSymbols(market),
    staleTime: 5 * 60 * 1000,        // 5분 캐시 (심볼은 자주 바뀌지 않음)
  })
```

### 4.3 수집 작업 통계 쿼리

```typescript
// useCollectTaskStatsQuery.ts
export const useCollectTaskStatsQuery = () =>
  useQuery({
    queryKey:       marketQueryKeys.collectTaskStats(),
    queryFn:        () => collectTaskApi.getStats(),
    refetchInterval: 30_000,          // 30초 자동 리패치 (기존 setInterval 대체)
  })
```

### 4.4 수집 작업 목록 쿼리 (무한 스크롤)

```typescript
// useCollectTasksQuery.ts
export const useCollectTasksInfiniteQuery = (params: CollectTaskListParams) =>
  useInfiniteQuery({
    queryKey: marketQueryKeys.collectTasks(params),
    queryFn: ({ pageParam }) =>
      collectTaskApi.getTasks({ ...params, symbolCursor: pageParam }),
    initialPageParam: undefined as string | undefined,
    getNextPageParam: (lastPage) => {
      // 마지막 페이지의 데이터가 limit 미만이면 다음 페이지 없음
      if (lastPage.length < (params.limit ?? 100)) return undefined
      const last = lastPage[lastPage.length - 1]
      return last.symbol?.code        // 다음 cursor = 마지막 심볼 코드
    },
    refetchInterval: 30_000,
  })
```

### 4.5 캔들 쿼리 (무한 스크롤 - 과거 방향)

```typescript
// useCandlesQuery.ts
export const useCandlesInfiniteQuery = (symbolId: string, interval: MarketCandleInterval) =>
  useInfiniteQuery({
    queryKey: marketQueryKeys.candles(symbolId, interval),
    queryFn:  ({ pageParam }) =>
      candleApi.getCandles({ symbolId, interval, cursor: pageParam, orderBy: 'DESC' }),
    initialPageParam: undefined as string | undefined,
    getNextPageParam: (lastPage) => {
      // 차트 좌측 스크롤 시 과거 데이터 추가 로드
      if (lastPage.length < 200) return undefined
      const oldest = lastPage[lastPage.length - 1]
      return oldest.time.toISOString()
    },
    select: (data) => ({
      ...data,
      // 페이지를 합쳐 시간 ASC 정렬 후 차트에 전달
      candles: data.pages.flat().reverse(),
    }),
    enabled: !!symbolId,
  })
```

### 4.6 Mutation (수집 제어)

```typescript
// features/market-collection-control/model/useResumeAll.ts
export const useResumeAllMutation = () => {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: () => collectTaskApi.resumeAll(),
    onSuccess: () => {
      // 관련 쿼리 무효화 → 자동 리패치
      queryClient.invalidateQueries({ queryKey: ['market', 'collect-tasks'] })
    },
  })
}

// useTaskActionMutation.ts (개별 resume/pause)
export const useTaskActionMutation = () => {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ taskId, action }: { taskId: string; action: 'resume' | 'pause' }) =>
      action === 'resume'
        ? collectTaskApi.resumeTask(taskId)
        : collectTaskApi.pauseTask(taskId),
    onMutate: async ({ taskId, action }) => {
      // 낙관적 업데이트: API 응답 전에 UI 즉시 반영
      await queryClient.cancelQueries({ queryKey: ['market', 'collect-tasks'] })
      const targetStatus = action === 'resume'
        ? MarketCandleCollectStatus.COLLECTED
        : MarketCandleCollectStatus.PAUSED
      queryClient.setQueriesData<InfiniteData<MarketCandleCollectTask[]>>(
        { queryKey: ['market', 'collect-tasks'] },
        (old) => patchTaskStatus(old, taskId, targetStatus)
      )
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ['market', 'collect-tasks'] })
    },
  })
}
```

---

## 5. 전역 상태 관리 (`shared/store/authStore.ts`)

```typescript
// Zustand: Redux 대체 (인증 전역 상태만 관리)
interface AuthState {
  token: string | null
  user: User | null
  isAuthenticated: boolean
  setToken: (token: string) => void
  logout: () => void
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      token: null,
      user: null,
      isAuthenticated: false,
      setToken: (token) => set({ token, isAuthenticated: true }),
      logout: () => set({ token: null, user: null, isAuthenticated: false }),
    }),
    {
      name: 'auth-storage',
      // ⚠️ 보안 정책: AT(Access Token)은 절대 localStorage에 저장하지 않음 (XSS 탈취 위험)
      // token은 Zustand 메모리에만 유지 — 페이지 새로고침 시 재로그인 필요
      partialize: (state) => ({ user: state.user }),  // user 정보만 persist, token 제외
    }
  )
)
```

---

## 6. 페이지별 상세 설계

### 6.1 수집 현황 대시보드 (`/market/collection`)

#### 화면 구성

```
┌──────────────────────────────────────────────────────────────┐
│ CollectionHeader                                              │
│  수집 현황   ○ 30초 전 업데이트   [전체 재시작] [전체 정지] [↺] │
└──────────────────────────────────────────────────────────────┘
┌─────────────┬────────────────────────────────────────────────┐
│CollectionSidebar│ CollectionTaskTable                        │
│             │                                                │
│ ┌─────────┐ │  [검색: 심볼명 입력...]                         │
│ │ 전체    │ │                                                │
│ │  1,200  │ │  Symbol   간격    상태        마지막 수집   제어 │
│ └─────────┘ │  ────────────────────────────────────────────  │
│ ┌─────────┐ │  KRW-BTC  MIN_1  ● 수집중    12:34:01    ⏸    │
│ │ 수집중  │ │  KRW-BTC  MIN_3  ● 완료      12:33:00    ⏸    │
│ │    800  │ │  KRW-ETH  MIN_1  ● 오류(2)   12:30:00    ▶ ⏸  │
│ └─────────┘ │  KRW-ETH  MIN_3  ● 정지      -           ▶    │
│ ┌─────────┐ │  ...                                           │
│ │ 완료    │ │                                                │
│ │    380  │ │  [로딩 스피너 / 더 불러오기 트리거]              │
│ └─────────┘ │                                                │
│ ┌─────────┐ │                                                │
│ │ 오류    │ │                                                │
│ │     20  │ │                                                │
│ └─────────┘ │                                                │
│             │                                                │
│ [필터]      │                                                │
│ 상태 체크박스│                                                │
│ 간격 체크박스│                                                │
└─────────────┴────────────────────────────────────────────────┘
```

#### 컴포넌트 트리

```
MarketCollectionPage
├── CollectionHeader
│   ├── LastUpdatedBadge          # "N초 전 업데이트" 표시
│   ├── ResumeAllButton           # (features/market-collection-control)
│   ├── PauseAllButton
│   └── RefreshButton
├── CollectionSidebar
│   ├── StatsCard × N             # 상태별 카운트 카드 (클릭 시 필터 적용)
│   └── FiltersPanel
│       ├── StatusFilter          # 체크박스 멀티 선택
│       └── IntervalFilter        # 체크박스 멀티 선택
└── CollectionTaskTable           # (widgets/task-table)
    ├── SearchInput               # 심볼 검색 (디바운스 300ms)
    ├── TableHeader
    ├── TaskRow × N
    │   ├── SymbolCell
    │   ├── IntervalBadge
    │   ├── StatusBadge           # 색상 + retryCount 표시
    │   ├── LastCollectedCell
    │   └── TaskActionButtons     # (features/market-collection-control)
    └── InfiniteScrollTrigger     # IntersectionObserver
```

#### 페이지 모델 훅

```typescript
// pages/market-collection/model/useCollectionPage.ts
const useCollectionPage = () => {
  // URL 파라미터에서 필터 읽기
  const [searchParams, setSearchParams] = useSearchParams()
  const filters = parseFiltersFromUrl(searchParams)

  // TanStack Query
  const statsQuery = useCollectTaskStatsQuery()
  const tasksQuery = useCollectTasksInfiniteQuery(filters)

  // 필터 변경 → URL 업데이트
  const setFilters = (next: Partial<CollectTaskListParams>) => {
    setSearchParams(buildUrlParams(next), { replace: true })
  }

  return {
    stats:        statsQuery.data,
    tasks:        tasksQuery.data?.pages.flat() ?? [],
    isLoading:    tasksQuery.isLoading,
    isFetchingNextPage: tasksQuery.isFetchingNextPage,
    hasNextPage:  tasksQuery.hasNextPage,
    fetchNextPage: tasksQuery.fetchNextPage,
    filters,
    setFilters,
  }
}
```

#### 상태별 스타일

| 상태 | Tailwind 클래스 (토큰 시스템) | 설명 |
|------|-------------------------------|------|
| `CREATED`    | `bg-bg-elevated text-text-tertiary`                          | 수집 전 |
| `COLLECTING` | `bg-semantic-info/15 text-semantic-info animate-pulse`       | 수집 중 |
| `COLLECTED`  | `bg-semantic-success/15 text-semantic-success`               | 완료 |
| `ERROR`      | `bg-semantic-danger/15 text-semantic-danger`                 | 실패 (retryCount 표시) |
| `PAUSED`     | `bg-semantic-warning/15 text-semantic-warning`               | 정지 |
| `DELISTED`   | `bg-bg-elevated text-text-disabled`                          | 폐지 |

> `semantic-*` 토큰은 `tailwind.config.ts` Section 4의 `semantic` 섹션에 정의됩니다.
> 투명도 수식어(`/15`)를 사용하려면 hex 값 대신 RGB CSS 변수 형식이어야 합니다.
> setup.md Section 4의 tailwind.config.ts `semantic` 항목을 CSS 변수 형식으로 유지하세요.

---

### 6.2 캔들 차트 뷰어 (`/market/chart`)

#### 화면 구성

```
┌──────────────────────────────────────────────────────────────┐
│ ChartHeader                                                   │
│  [KRW-BTC ▼ 검색...]  [1분][3분][5분][15분][1시][1일][1주]   │
│                        ● WS 연결됨   현재가: 95,000,000 KRW  │
└────────────────┬─────────────────────────────────────────────┘
│ ChartSidebar   │ CandleChartView                              │
│                │                                              │
│ [검색...]      │  ┌──────────────────────────────────────┐   │
│                │  │                                      │   │
│ 즐겨찾기 ★     │  │   Lightweight Charts                 │   │
│  BTC           │  │   캔들스틱 + 이동평균선               │   │
│  ETH           │  │                                      │   │
│                │  │                                      │   │
│ 전체 심볼      │  └──────────────────────────────────────┘   │
│  SOL           │  ┌──────────────────────────────────────┐   │
│  XRP           │  │   거래량 (Volume)                    │   │
│  ADA           │  └──────────────────────────────────────┘   │
│  ...           │                                              │
│                │  OHLCV: O 94,800,000 H 95,200,000           │
│                │         L 94,500,000 C 95,000,000 V 12.4    │
└────────────────┴─────────────────────────────────────────────┘
```

#### 컴포넌트 트리

```
MarketChartPage
├── ChartHeader
│   ├── SymbolSelector             # 심볼 드롭다운 (검색 지원)
│   ├── IntervalSelector           # 간격 버튼 그룹 (12개)
│   ├── WebSocketStatus            # ● 연결됨 / ✕ 끊김
│   └── CurrentPriceBadge          # 실시간 현재가
├── ChartSidebar
│   ├── SearchInput
│   ├── FavoriteSymbols            # Zustand 즐겨찾기 목록
│   └── SymbolList                 # 전체 심볼 목록 (가상 스크롤)
└── CandleChartView
    ├── CandleChart                # (widgets/candle-chart) Lightweight Charts
    └── OHLCVTooltip               # 호버 시 OHLCV 상세 표시
```

#### CandleChart 위젯 설계

```typescript
// widgets/candle-chart/ui/CandleChart.tsx
interface CandleChartProps {
  candles:        MarketCandle[]
  realtimeCandle?: MarketCandle     // WebSocket 실시간 캔들
  interval:       MarketCandleInterval
  isLoading:      boolean
  onLoadMore:     () => void        // 차트 좌측 스크롤 시 과거 데이터 요청
}

// Lightweight Charts 구성
// ⚠️ Lightweight Charts는 CSS 변수를 직접 지원하지 않으므로
//    현재 테마에 맞는 색상을 JS로 읽어 적용
const isDark = document.documentElement.classList.contains('dark')

const chart = createChart(containerRef.current, {
  layout: {
    background: { color: isDark ? '#1C1B2E' : '#FFFFFF' },  // bg-surface
    textColor:  isDark ? '#9490B5'  : '#4D4975',             // text-secondary
  },
  grid: {
    vertLines: { color: isDark ? '#252440' : '#E4E1F8' },    // border
    horzLines: { color: isDark ? '#252440' : '#E4E1F8' },
  },
  crosshair: { mode: CrosshairMode.Normal },
})

// ⚠️ 한국 주식 컨벤션: 빨강 = 상승(양봉), 파랑 = 하락(음봉)
//    setup.md Section 5.1 색상 토큰과 반드시 일치시킬 것
const candleSeries = chart.addCandlestickSeries({
  upColor:         '#F04452',   // 상승봉 ← 빨강 (한국)
  downColor:       '#4066E4',   // 하락봉 ← 파랑 (한국)
  borderUpColor:   '#F04452',
  borderDownColor: '#4066E4',
  wickUpColor:     '#F04452',
  wickDownColor:   '#4066E4',
})

const volumeSeries = chart.addHistogramSeries({
  priceFormat: { type: 'volume' },
  priceScaleId: 'volume',
})

// 과거 데이터 로드 트리거 (차트 좌측 스크롤)
chart.timeScale().subscribeVisibleLogicalRangeChange((range) => {
  if (range && range.from < 10) {
    onLoadMore()
  }
})
```

#### 실시간 WebSocket 훅

```typescript
// shared/hooks/useCandleWebSocket.ts
interface UseCandleWebSocketReturn {
  realtimeCandle: MarketCandle | null
  isConnected:    boolean
}

const useCandleWebSocket = (
  symbolId: string,
  interval: MarketCandleInterval
): UseCandleWebSocketReturn => {
  // 심볼/간격 변경 시 재연결
  useEffect(() => {
    const ws = new WebSocket(
      `${WS_BASE_URL}/market/candles/stream?symbolId=${symbolId}&interval=${interval}`
    )
    ws.onmessage = (e) => {
      const candle = parseWebSocketCandle(JSON.parse(e.data))
      setRealtimeCandle(candle)
    }
    ws.onclose = () => {
      setIsConnected(false)
      // 자동 재연결 (3초 후, 최대 5회)
      if (retryCount < 5) {
        setTimeout(() => retryCount++, 3000)
      }
    }
    return () => ws.close()
  }, [symbolId, interval])
}
```

#### 페이지 모델 훅

```typescript
// pages/market-chart/model/useChartPage.ts
const useChartPage = () => {
  // URL 파라미터로 선택 상태 유지
  const [searchParams, setSearchParams] = useSearchParams()
  const symbolId = searchParams.get('symbolId') ?? ''
  const interval = (searchParams.get('interval') as MarketCandleInterval) ?? MarketCandleInterval.MIN_1

  const symbolsQuery       = useSymbolsQuery()
  const candlesQuery       = useCandlesInfiniteQuery(symbolId, interval)
  const { realtimeCandle, isConnected } = useCandleWebSocket(symbolId, interval)

  // ✅ MarketSymbol의 PK 필드명은 'identifier' (id 아님)
  const selectedSymbol = symbolsQuery.data?.find(s => s.identifier === symbolId)

  const changeSymbol = (symbol: MarketSymbol) => {
    setSearchParams({ symbolId: symbol.identifier, interval }, { replace: true })
  }

  const changeInterval = (next: MarketCandleInterval) => {
    setSearchParams({ symbolId, interval: next }, { replace: true })
  }

  return {
    symbols:        symbolsQuery.data ?? [],
    selectedSymbol,
    interval,
    // InfiniteQuery는 pages 배열 구조 — flatMap으로 단일 배열로 펼침
    candles:        candlesQuery.data?.pages.flatMap(page => page) ?? [],
    isLoadingCandles: candlesQuery.isLoading,
    hasMoreCandles: candlesQuery.hasNextPage,
    loadMoreCandles: candlesQuery.fetchNextPage,
    realtimeCandle,
    isConnected,
    changeSymbol,
    changeInterval,
  }
}
```

---

### 6.3 심볼 관리 (`/market/symbols`)

#### 화면 구성

```
┌──────────────────────────────────────────────────────────────┐
│ SymbolsHeader                                                 │
│  심볼 관리   총 152개   [심볼 수동 수집]                        │
└──────────────────────────────────────────────────────────────┘
┌──────────────────────────────────────────────────────────────┐
│ [검색: 심볼명/코드 입력...]   [전체 ▼]  [LISTED ▼]           │
└──────────────────────────────────────────────────────────────┘
┌──────────────────────────────────────────────────────────────┐
│  코드       이름        시장   상태          수집 작업   등록일  │
│  ────────────────────────────────────────────────────────── │
│  KRW-BTC   비트코인    COIN  ● LISTED       12/12 수집중  ...  │
│  KRW-ETH   이더리움    COIN  ● LISTED       12/12 완료    ...  │
│  KRW-XRP   리플        COIN  ⚠ WARNING      12/12 오류    ...  │
│  KRW-ABC   ABC코인     COIN  ✕ DELISTED     0/12  -       ...  │
│  ...                                                         │
└──────────────────────────────────────────────────────────────┘
```

#### 컴포넌트 트리

```
MarketSymbolsPage
├── SymbolsHeader
│   ├── TotalCountBadge
│   └── CollectSymbolsButton       # POST /market-symbols/collect (수동 수집 트리거)
├── SymbolsFilterBar
│   ├── SearchInput                # 디바운스 300ms
│   ├── MarketTypeSelect           # COIN / STOCK
│   └── StatusSelect               # LISTED / WARNING / ... 멀티 선택
└── SymbolsTable
    ├── TableHeader
    ├── SymbolRow × N
    │   ├── CodeCell               # KRW-BTC
    │   ├── NameCell               # 비트코인
    │   ├── MarketBadge            # COIN / STOCK
    │   ├── SymbolStatusBadge      # LISTED / DELISTED 등
    │   ├── TaskProgressCell       # "12/12 수집중" (완료/전체, 상태 요약)
    │   └── CreatedAtCell
    └── Pagination                 # 심볼은 많지 않으므로 일반 페이지네이션
```

#### 심볼 수집 Mutation

```typescript
// pages/market-symbols/model/useSymbolsPage.ts
const useCollectSymbolsMutation = () => {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: () => symbolApi.collectSymbols(),  // POST /market-symbols/collect
    onSuccess: () => {
      // 202 Accepted: 비동기 처리이므로 2초 후 심볼 목록 재조회
      setTimeout(() => {
        queryClient.invalidateQueries({ queryKey: ['market', 'symbols'] })
      }, 2000)
    },
  })
}
```

---

## 7. 라우팅 (`app/router.tsx`)

```typescript
export const router = createBrowserRouter([
  {
    path: '/',
    element: <RootLayout />,          // 공통 레이아웃 (사이드바 네비게이션)
    children: [
      { index: true, element: <Navigate to="/market/collection" replace /> },
      {
        path: 'market',
        children: [
          { path: 'collection', element: <MarketCollectionPage /> },
          { path: 'chart',      element: <MarketChartPage /> },
          { path: 'symbols',    element: <MarketSymbolsPage /> },
        ],
      },
    ],
  },
  { path: '/login', element: <LoginPage /> },
])
```

---

## 8. API 클라이언트 (`shared/api/client.ts`)

```typescript
export const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL,
  timeout: 10_000,
})

// 요청 인터셉터: 토큰 자동 주입
apiClient.interceptors.request.use((config) => {
  const token = useAuthStore.getState().token
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

// 응답 인터셉터: 401 → 로그아웃 + 리다이렉트
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

## 9. 개발 우선순위

### Phase 1: 프로젝트 초기 설정
- [ ] Vite + React 18 + TypeScript 프로젝트 생성
- [ ] Tailwind CSS 설정
- [ ] TanStack Query, Zustand 설치 및 Provider 설정
- [ ] Axios 클라이언트 (인터셉터) 설정
- [ ] React Router 라우팅 기본 구조
- [ ] FSD 디렉토리 구조 생성

### Phase 2: 공통 레이어
- [ ] `entities/market/model/enums.ts`: Enum 정의
- [ ] `entities/market/model/schemas.ts`: Zod 스키마 + z.infer 타입 export
- [ ] `entities/market/model/params.ts`: 요청 파라미터 interface
- [ ] `shared/store/authStore.ts`: Zustand 인증 상태
- [ ] `shared/ui`: Spinner, Badge, EmptyState, ErrorBoundary
- [ ] `entities/market/api/`: REST API 함수 (symbolApi, collectTaskApi, candleApi)
- [ ] `entities/market/queries/`: TanStack Query 훅 4개

### Phase 3: 수집 현황 대시보드
- [ ] `features/market-collection-control/`: resume/pause mutation 훅
- [ ] `widgets/task-table/`: CollectTaskTable 위젯
- [ ] `pages/market-collection/`: 페이지 조립

### Phase 4: 캔들 차트 뷰어
- [ ] `shared/hooks/useCandleWebSocket.ts`
- [ ] `widgets/candle-chart/`: Lightweight Charts 위젯
- [ ] `pages/market-chart/`: 페이지 조립

### Phase 5: 심볼 관리
- [ ] `pages/market-symbols/`: 심볼 관리 페이지 조립

---

## 참고

- **백엔드 도메인 설계**: [`backend/market/domain.md`](../backend/market/domain.md)
- **시퀀스 다이어그램**: [`backend/market/sequence-diagram.md`](../backend/market/sequence-diagram.md)
- **기능 명세**: [`features/01-data-collection.md`](../features/01-data-collection.md)
