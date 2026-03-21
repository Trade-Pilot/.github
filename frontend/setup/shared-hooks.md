<!-- 원본: frontend/setup.md — 섹션 7 -->

# shared/hooks 공용 훅

> useDebounce, useUrlParams, useIntersectionObserver, useCandleWebSocket

---

## 7. 공용 훅 (`shared/hooks/`)

### 7.1 useDebounce

```typescript
// shared/hooks/useDebounce.ts
const useDebounce = <T>(value: T, delay = 300): T => {
  const [debouncedValue, setDebouncedValue] = useState(value)
  useEffect(() => {
    const timer = setTimeout(() => setDebouncedValue(value), delay)
    return () => clearTimeout(timer)
  }, [value, delay])
  return debouncedValue
}
```

---

### 7.2 useUrlParams

```typescript
// shared/hooks/useUrlParams.ts
// URL 검색 파라미터를 타입 안전하게 읽고 쓰는 훅
// 배열 값, 기본값, 디바운스 업데이트 지원

interface UseUrlParamsOptions {
  replace?:    boolean   // history.push vs history.replace (기본: replace)
  debounceMs?: number    // 파라미터 업데이트 디바운스 (기본: 0)
}

const useUrlParams = <T extends Record<string, any>>(
  defaultParams: T,
  options?: UseUrlParamsOptions
): {
  params:       T
  setParams:    (next: Partial<T>) => void
  resetParams:  () => void
}
```

---

### 7.3 useIntersectionObserver

```typescript
// shared/hooks/useIntersectionObserver.ts
// 무한 스크롤 트리거용

const useIntersectionObserver = (
  callback: () => void,
  options?: IntersectionObserverInit
): React.RefObject<HTMLDivElement>

// 사용:
// const triggerRef = useIntersectionObserver(fetchNextPage)
// <div ref={triggerRef} />
```

---

### 7.4 useCandleWebSocket

```typescript
// shared/hooks/useCandleWebSocket.ts
interface UseCandleWebSocketOptions {
  symbolId:   string
  interval:   MarketCandleInterval
  enabled?:   boolean
}

interface UseCandleWebSocketReturn {
  realtimeCandle: MarketCandle | null
  isConnected:    boolean
  error:          string | null
}

// 재연결 전략: 3초 후 재시도, 최대 5회, 이후 수동 재연결 필요
```

---
