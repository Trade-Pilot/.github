# 성능 최적화 컨벤션

> 원본: `frontend/convention.md` Section 11

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

### 11.5 Web Worker & SSE 통신 프로토콜

비동기 실시간 데이터 처리를 위해 통신 객체 구조를 통일합니다.

#### Web Worker 메시지 포맷 (Command/Event)

```typescript
// ✅ Worker로 보내는 메시지 (Command)
type WorkerCommand =
  | { type: 'CONNECT';    payload: { url: string, topics: string[] } }
  | { type: 'DISCONNECT' }
  | { type: 'SUBSCRIBE';  payload: { topic: string } }

// ✅ Worker에서 받는 메시지 (Event)
type WorkerEvent =
  | { type: 'CONNECTED' }
  | { type: 'DATA';       payload: { topic: string; data: any } }
  | { type: 'ERROR';      payload: { message: string } }
  | { type: 'HEALTH';     payload: { latency: number } }
```

#### SSE (Server-Sent Events) 처리 표준

*   **훅 사용**: 도메인별 `useSSE` 커스텀 훅을 만들어 연결 관리(`EventSource`)를 캡슐화합니다.
*   **Life Cycle**: 컴포넌트 언마운트 시 반드시 `eventSource.close()`를 호출합니다.
*   **메시지 파싱**: `data` 필드는 항상 JSON으로 파싱하며, Zod 스키마로 검증 후 상태에 반영합니다.
