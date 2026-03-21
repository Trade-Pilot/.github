# TypeScript 타입 컨벤션

> 원본: `frontend/convention.md` Section 4

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
