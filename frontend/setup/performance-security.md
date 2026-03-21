<!-- 원본: frontend/setup.md — 섹션 19~23 -->

# 성능 최적화, 금융 특화 처리, 에러 모니터링, 보안

> 코드 스플리팅, 실시간 데이터 렌더링, 시간대/고정밀 숫자, 토큰 저장 전략

---

## 19. 성능 최적화

실시간 데이터가 초 단위로 갱신되는 트레이딩 앱 특성상 불필요한 리렌더링이 성능 병목이 됩니다.

### 19.1 코드 스플리팅 (Lazy Loading)

```typescript
// app/router.tsx
// 각 페이지를 동적 import로 분리 → 초기 번들 크기 감소
const MarketCollectionPage = lazy(() => import('@pages/market-collection'))
const MarketChartPage      = lazy(() => import('@pages/market-chart'))
const MarketSymbolsPage    = lazy(() => import('@pages/market-symbols'))

// Suspense로 로딩 처리
{
  element: (
    <Suspense fallback={<PageLoadingSpinner />}>
      <Outlet />
    </Suspense>
  ),
  children: [...]
}
```

### 19.2 실시간 데이터 렌더링 최적화

```typescript
// 문제: WebSocket 메시지가 초당 여러 번 오면 그만큼 리렌더링 발생
// 해결: throttle로 렌더링 빈도를 제한

// shared/hooks/useCandleWebSocket.ts
import { throttle } from '@shared/utils/throttle'

const handleMessage = throttle((data: MessageEvent) => {
  const candle = parseWebSocketCandle(JSON.parse(data.data))
  setRealtimeCandle(candle)
}, 500)  // 500ms 이하 업데이트는 무시 (시각적으로 충분)
```

```typescript
// 문제: CollectTaskTable이 30초마다 1,200개 Task를 전체 리렌더링
// 해결: React.memo + 안정적인 key + 개별 Task 컴포넌트 분리

const TaskRow = React.memo(
  ({ task, onResume, onPause }: TaskRowProps) => { ... },
  (prev, next) =>
    prev.task.status     === next.task.status &&
    prev.task.retryCount === next.task.retryCount &&
    prev.task.lastCollectedTime === next.task.lastCollectedTime
)
```

### 19.3 가상 스크롤 (대용량 목록)

심볼 수가 늘어날 경우 (주식 확장 시 수천 개), DOM에 전체 행을 렌더링하면 성능이 저하됩니다.

```bash
npm install @tanstack/react-virtual
```

```typescript
// 적용 기준: 행 수 > 200개인 목록
// CollectTaskTable: 심볼 × 12간격 → 100심볼 = 1,200행 → 가상 스크롤 필요

const rowVirtualizer = useVirtualizer({
  count:          tasks.length,
  getScrollElement: () => scrollRef.current,
  estimateSize:   () => 52,        // 행 높이 (px)
  overscan:       10,              // 스크롤 밖 예비 렌더링 수
})
```

### 19.4 번들 크기 최적화

```typescript
// vite.config.ts - 청크 분리 전략
export default defineConfig({
  build: {
    rollupOptions: {
      output: {
        manualChunks: {
          // 큰 라이브러리를 별도 청크로 분리
          'vendor-react':   ['react', 'react-dom', 'react-router-dom'],
          'vendor-query':   ['@tanstack/react-query'],
          'vendor-charts':  ['lightweight-charts'],
          'vendor-utils':   ['axios', 'zustand', 'zod'],
        },
      },
    },
    // 번들 크기 경고 임계값
    chunkSizeWarningLimit: 500,  // 500KB
  },
})
```

```bash
# 번들 분석 (빌드 후)
npm install -D rollup-plugin-visualizer

# 결과: dist/stats.html 에서 번들 구성 시각화
```

---

## 20. 금융 특화 처리

### 20.1 시간대 처리 (UTC ↔ KST)

백엔드는 UTC `OffsetDateTime`으로 저장하지만, 사용자는 KST(UTC+9)로 표시해야 합니다. 특히 일봉/주봉/월봉은 KST 기준 날짜 경계를 따라야 합니다.

```bash
npm install dayjs
# dayjs는 번들 크기가 작고 플러그인 방식으로 필요한 것만 추가
```

```typescript
// shared/utils/time.ts
import dayjs from 'dayjs'
import utc from 'dayjs/plugin/utc'
import timezone from 'dayjs/plugin/timezone'
import weekOfYear from 'dayjs/plugin/weekOfYear'  // d.week() 사용을 위해 필수

dayjs.extend(utc)
dayjs.extend(timezone)
dayjs.extend(weekOfYear)

const KST = 'Asia/Seoul'

// API 응답 시간 → KST로 파싱
export const parseApiTime = (iso: string): Date =>
  dayjs.utc(iso).tz(KST).toDate()

// 차트 표시용 KST 포맷
export const formatCandleTime = (date: Date, interval: MarketCandleInterval): string => {
  const d = dayjs(date).tz(KST)
  switch (interval) {
    case 'MIN_1':  case 'MIN_3':  case 'MIN_5':
    case 'MIN_10': case 'MIN_15': case 'MIN_30':
      return d.format('HH:mm')
    case 'MIN_60': case 'MIN_120': case 'MIN_180':
      return d.format('MM-DD HH:mm')
    case 'DAY':
      return d.format('MM-DD')
    case 'WEEK':
      return d.format('YY/MM') + ` ${d.week()}주`
    case 'MONTH':
      return d.format('YYYY-MM')
  }
}

// 스케줄러 시간 표시 ("방금 전", "3분 전")
export const formatRelativeTime = (date: Date): string => {
  const diff = dayjs().diff(dayjs(date), 'second')
  if (diff < 10)  return '방금 전'
  if (diff < 60)  return `${diff}초 전`
  if (diff < 3600) return `${Math.floor(diff / 60)}분 전`
  return dayjs(date).tz(KST).format('HH:mm:ss')
}
```

### 20.2 고정밀 숫자 처리 (Decimal.js)

자바스크립트의 부동소수점 문제(`0.1 + 0.2 = 0.30000000000000004`)는 가격 계산 시 오류를 유발합니다. 백엔드에서 BigDecimal을 String으로 내려주는 이유도 이 때문입니다.

```bash
npm install decimal.js
```

```typescript
// shared/utils/decimal.ts
import Decimal from 'decimal.js'

Decimal.set({ precision: 20, rounding: Decimal.ROUND_HALF_UP })

// 수익률 계산
export const calcProfitRate = (entry: string, current: string): string => {
  const rate = new Decimal(current).minus(entry).div(entry).mul(100)
  return rate.toFixed(2)  // "5.12"
}

// 표시용 포맷 (Decimal → string)
export const formatDecimalPrice = (value: string): string =>
  new Decimal(value).toFormat()    // "95,000,000"

// 주의: UI 표시 전용으로만 사용
//       계산은 항상 Decimal 객체로 유지 (string 변환은 마지막에)
```

### 20.3 MarketCandle 파서에서 적용

```typescript
// entities/market/model/parsers.ts
export const parseCandle = (raw: CandleApiResponse): MarketCandle => ({
  symbolId: raw.symbolIdentifier,
  interval: raw.interval,
  time:     parseApiTime(raw.time),     // UTC → KST Date
  open:     raw.open,                   // string 유지 (BigDecimal)
  high:     raw.high,
  low:      raw.low,
  close:    raw.close,
  volume:   raw.volume,
  amount:   raw.amount,
  isFlat:   new Decimal(raw.volume).isZero(),
})

// Lightweight Charts에 전달 시 number 변환 (표시 전용)
const toChartData = (candle: MarketCandle) => ({
  time:  candle.time.getTime() / 1000,  // Unix timestamp (seconds)
  open:  Number(candle.open),
  high:  Number(candle.high),
  low:   Number(candle.low),
  close: Number(candle.close),
})
```

---

## 21. 에러 모니터링

> 현재는 Sentry를 사용하지 않습니다. 향후 프로덕션 모니터링 도구 도입 시 이 섹션을 업데이트합니다.

### API 응답 파싱 에러 처리

```typescript
// shared/utils/parse.ts
// 향후 모니터링 도구 연동이 필요할 때 이 함수 내부만 수정하면 됨
export const parseOrThrow = <T>(schema: z.ZodSchema<T>, raw: unknown): T => {
  const result = schema.safeParse(raw)
  if (!result.success) {
    if (import.meta.env.DEV) {
      console.error('[ParseError] API 응답 스키마 불일치:', result.error, '\nraw:', raw)
    }
    // ✅ 항상 throw — unknown 타입을 T로 단언하는 unsafe fallback 금지
    throw result.error
  }
  return result.data
}
```

### ErrorBoundary

```typescript
// shared/ui/ErrorBoundary.tsx — React 기본 ErrorBoundary 사용
export const ErrorBoundary = ({ children, fallback }: ErrorBoundaryProps) => (
  <ReactErrorBoundary FallbackComponent={fallback ?? ErrorFallbackPage}>
    {children}
  </ReactErrorBoundary>
)
```

---

## 22. 보안

### 22.1 토큰 저장 전략

```
저장 위치별 비교:

localStorage   → XSS 취약 (JS로 접근 가능)
sessionStorage → XSS 취약, 탭 닫으면 소멸
Memory (Zustand) → XSS 안전, 새로고침 시 소멸 → 재로그인 필요
httpOnly Cookie  → XSS 안전, CSRF 취약 → SameSite=Strict로 완화

Trade Pilot 선택: Memory (Zustand) + Refresh Token은 httpOnly Cookie
- Access Token: 15분 만료, Zustand memory에만 보관
- Refresh Token: 7일 만료, httpOnly Cookie (백엔드에서 발급)
- 페이지 새로고침 시: Refresh Token으로 Access Token 재발급 (자동)
```

```typescript
// shared/api/auth.ts
export const refreshAccessToken = async (): Promise<string> => {
  // httpOnly Cookie는 자동 전송되므로 별도 처리 불필요
  const res = await apiClient.post<{ token: string }>('/auth/refresh')
  useAuthStore.getState().setAuth(res.token, res.user)
  return res.token
}

// Axios 인터셉터에서 401 시 자동 갱신
apiClient.interceptors.response.use(
  (res) => res,
  async (err) => {
    if (err.response?.status === 401 && !err.config._retry) {
      err.config._retry = true
      const newToken = await refreshAccessToken()
      err.config.headers.Authorization = `Bearer ${newToken}`
      return apiClient(err.config)  // 원래 요청 재시도
    }
    return Promise.reject(err)
  }
)
```

### 22.2 XSS 방어

```typescript
// 사용자 입력을 dangerouslySetInnerHTML에 사용 금지
// 심볼 코드, 이름 등은 반드시 텍스트로만 렌더링

// ❌ 잘못된 예
<div dangerouslySetInnerHTML={{ __html: symbol.name }} />

// ✅ 올바른 예
<div>{symbol.name}</div>
```

```typescript
// Content Security Policy (index.html)
// <meta http-equiv="Content-Security-Policy"
//   content="default-src 'self';
//            script-src 'self';
//            connect-src 'self' wss://api.trade-pilot.com https://api.trade-pilot.com;
//            img-src 'self' data:;
//            style-src 'self' 'unsafe-inline' https://fonts.googleapis.com;">
```

### 22.3 민감 정보 노출 방지

```typescript
// 환경 변수 중 VITE_ 접두사가 붙은 것은 번들에 포함됨 → 주의
// ❌ 클라이언트에 노출되면 안 되는 것
VITE_DB_PASSWORD=...        // 절대 금지
VITE_SECRET_KEY=...         // 절대 금지

// ✅ 클라이언트에 노출 가능한 것
VITE_API_BASE_URL=...       // 공개 API 주소
VITE_SENTRY_DSN=...         // 공개 DSN
```

---

## 23. 업데이트된 착수 체크리스트

### 추가 항목

- [ ] `openapi-typescript` 설치 및 `generate:api` 스크립트 추가
- [ ] `zod` 설치 및 핵심 엔티티 Schema 정의 (Market, CollectTask, Candle)
- [ ] `vitest` + RTL 설정 (`vitest.config.ts`, `test/setup.ts`)
- [ ] MSW 초기화 (`public/mockServiceWorker.js`) 및 핸들러 작성
- [ ] `dayjs` 설치 및 `shared/utils/time.ts` 작성 (UTC/KST 변환)
- [ ] `decimal.js` 설치 및 `shared/utils/decimal.ts` 작성
- [ ] 에러 모니터링 도구 도입 시 `shared/utils/parse.ts`의 `parseOrThrow` 함수 업데이트 (현재 Sentry 미사용)
- [ ] Refresh Token 자동 갱신 인터셉터 추가
- [ ] `vite.config.ts` manualChunks 청크 분리 설정
- [ ] CSP 메타 태그 추가 (`index.html`)
- [ ] `.env.development.local` gitignore 등록 확인

---
