<!-- 원본: frontend/convention.md — Section 26~28: API 에러, 금융 데이터, 시간대 -->

## 26. API 에러 응답 처리 규칙

```typescript
// shared/model/apiError.ts
export const ApiErrorSchema = z.object({
  code:      z.string(),                    // 'U001', 'MS001' 등
  message:   z.string(),
  timestamp: z.string().datetime(),
  path:      z.string(),
  details:   z.record(z.string()).nullable(),
})
export type ApiError = z.infer<typeof ApiErrorSchema>
```

에러 핸들링 전략:
- 4xx: 사용자 입력 문제 → 인라인 에러 메시지 표시
- 401: 토큰 만료 → 자동 갱신 시도 → 실패 시 로그인 리다이렉트
- 403: 권한 없음 → "접근 권한이 없습니다" 토스트
- 409: 상태 충돌 → 상태에 맞는 안내 메시지 (예: "이미 활성화된 에이전트입니다")
- 429: Rate Limit → "요청이 많습니다. 잠시 후 다시 시도해주세요" 토스트
- 5xx: 서버 오류 → "일시적인 오류입니다" 토스트 + 자동 재시도 (TanStack Query retry)

Axios 인터셉터 패턴:
```typescript
// shared/api/axiosInstance.ts
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const apiError = parseOrThrow(ApiErrorSchema, error.response?.data)

    if (error.response?.status === 401) {
      // 토큰 갱신 시도
      const refreshed = await tryRefreshToken()
      if (refreshed) return api.request(error.config)
      // 실패 시 로그아웃
      useAuthStore.getState().logout()
      window.location.href = '/sign-in'
    }

    return Promise.reject(apiError)
  }
)
```

## 27. 금융 데이터 처리 규칙

**핵심 원칙**: 모든 금액/수량은 **문자열(string)** 상태로 전달받고, 연산 시에만 `Decimal.js`로 변환한다.

```typescript
// ✅ 백엔드 응답: 모든 금융 필드는 string
interface PortfolioResponse {
  cash: string           // "1000000.50"
  totalValue: string     // "2500000.75"
}

// ✅ 연산이 필요한 시점에만 Decimal 변환
import Decimal from 'decimal.js'
const cash = new Decimal(portfolio.cash)
const pnl = cash.minus(initialCapital)
const pnlPercent = pnl.div(initialCapital).mul(100).toFixed(2)

// ✅ 화면 표시
formatCurrency(portfolio.cash)  // "1,000,000.50 원"

// ❌ 절대 금지
const cash = parseFloat(portfolio.cash)      // 부동소수점 오차!
const cash = Number(portfolio.cash)          // 동일한 문제
```

Zod 스키마에서의 적용:
```typescript
// ✅ 금융 필드는 z.string()
export const PortfolioSchema = z.object({
  cash:         z.string(),   // Decimal string
  reservedCash: z.string(),
  totalValue:   z.string(),
  realizedPnl:  z.string(),
})

// ❌ z.number() 금지 (금융 데이터)
cash: z.number()  // 파싱 시 정밀도 손실
```

## 28. 시간대 처리 규칙

**원칙**: 백엔드는 UTC, 프론트엔드 표시는 KST

```typescript
// ✅ Day.js + timezone 플러그인
import dayjs from 'dayjs'
import utc from 'dayjs/plugin/utc'
import timezone from 'dayjs/plugin/timezone'
dayjs.extend(utc)
dayjs.extend(timezone)

// 백엔드 응답 (UTC)
const raw = "2024-01-15T09:00:00Z"

// KST 변환 표시
dayjs(raw).tz('Asia/Seoul').format('YYYY-MM-DD HH:mm:ss')
// → "2024-01-15 18:00:00"

// ❌ new Date() 사용 금지 (브라우저 로컬 시간대 의존)
new Date(raw).toLocaleString()  // 사용자 OS 설정에 따라 달라짐

// ❌ 시간대 없는 문자열 파싱 금지
dayjs("2024-01-15 18:00:00")  // UTC인지 KST인지 모호
```

캔들 차트에서:
```typescript
// Lightweight Charts의 time은 Unix timestamp (초 단위)
const time = dayjs(candle.time).unix()

// 차트 시간축은 UTC 기준, 표시만 KST 오프셋 적용
chart.applyOptions({
  localization: { timeFormatter: (t) => dayjs.unix(t).tz('Asia/Seoul').format('HH:mm') },
  timeScale: { timeVisible: true, secondsVisible: false },
})
```
