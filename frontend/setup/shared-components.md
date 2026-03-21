<!-- 원본: frontend/setup.md — 섹션 6 -->

# shared/ui 공용 컴포넌트

> Button, Badge, Input, Modal, Toast, Table 등 공용 UI 컴포넌트 정의

---

## 6. 공용 컴포넌트 (`shared/ui/`)

### 6.1 Button

```typescript
// shared/ui/Button.tsx
// ✅ 아이콘은 shared/ui/icons/index.ts에 등록된 것을 사용 (convention.md 24절 참조)
import { IconName } from '@shared/ui/icons'

type ButtonVariant = 'primary' | 'secondary' | 'danger' | 'ghost'
type ButtonSize    = 'sm' | 'md' | 'lg'

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?:  ButtonVariant
  size?:     ButtonSize
  loading?:  boolean
  leftIcon?: React.ReactNode // 아이콘 레지스트리 컴포넌트 사용 권장
}
```

const variantClass: Record<ButtonVariant, string> = {
  primary:   'bg-brand-500 hover:bg-brand-600 active:bg-brand-700 text-white shadow-sm',
  secondary: 'bg-bg-surface hover:bg-bg-elevated active:bg-bg-overlay text-text-primary border border-border hover:border-border-strong',
  danger:    'bg-semantic-danger hover:bg-semantic-danger/90 active:bg-semantic-danger/80 text-white',
  ghost:     'hover:bg-bg-elevated active:bg-bg-overlay text-text-secondary hover:text-text-primary',
}

const sizeClass: Record<ButtonSize, string> = {
  sm: 'h-7  px-2.5 text-xs  gap-1.5',
  md: 'h-9  px-3.5 text-sm  gap-2',
  lg: 'h-11 px-5   text-base gap-2.5',
}
```

**사용 예시**:
```tsx
<Button variant="primary"    size="md">전체 재시작</Button>
<Button variant="danger"     size="sm">전체 정지</Button>
<Button variant="secondary"  size="md" leftIcon={<FiRefreshCw />}>새로고침</Button>
<Button variant="ghost"      size="sm" loading>저장 중...</Button>
```

---

### 6.2 Badge

```typescript
// shared/ui/Badge.tsx
type BadgeVariant = 'default' | 'success' | 'error' | 'warning' | 'info' | 'neutral'

interface BadgeProps {
  variant?:  BadgeVariant
  dot?:      boolean    // 앞에 점(●) 표시 여부
  children:  React.ReactNode
}

const variantClass: Record<BadgeVariant, string> = {
  // semantic-* CSS 변수 토큰 사용 — 테마별 색상 자동 전환 + 투명도 수식어 지원
  default: 'bg-bg-elevated                   text-text-secondary',
  success: 'bg-semantic-success/10           text-semantic-success',
  error:   'bg-semantic-danger/10            text-semantic-danger',
  warning: 'bg-semantic-warning/10           text-semantic-warning',
  info:    'bg-semantic-info/10              text-semantic-info',
  neutral: 'bg-bg-surface                   text-text-tertiary',
}
```

**사용 예시**:
```tsx
<Badge variant="success" dot>COLLECTED</Badge>
<Badge variant="error"   dot>ERROR (2)</Badge>
<Badge variant="info"    dot>COLLECTING</Badge>
<Badge variant="warning" dot>PAUSED</Badge>
```

---

### 6.3 StatusBadge (수집 상태 전용)

```typescript
// shared/ui/StatusBadge.tsx
// MarketCandleCollectStatus를 Badge variant로 자동 매핑
const STATUS_CONFIG: Record<MarketCandleCollectStatus, {
  variant: BadgeVariant
  label:   string
}> = {
  CREATED:    { variant: 'neutral',  label: '대기'     },
  COLLECTING: { variant: 'info',     label: '수집중'   },
  COLLECTED:  { variant: 'success',  label: '완료'     },
  ERROR:      { variant: 'error',    label: '오류'     },
  PAUSED:     { variant: 'warning',  label: '정지'     },
  DELISTED:   { variant: 'neutral',  label: '폐지'     },
}

interface StatusBadgeProps {
  status:     MarketCandleCollectStatus
  retryCount?: number    // ERROR 상태일 때 "(2/3)" 형태로 표시
}
```

---

### 6.4 Input / SearchInput

```typescript
// shared/ui/Input.tsx
interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?:      string
  error?:      string
  leftIcon?:   React.ReactNode
  rightIcon?:  React.ReactNode
}

// 기본 클래스
// bg-bg-input border border-border rounded text-text-primary text-sm
// focus:border-brand-500 focus:ring-2 focus:ring-brand-500/20
// placeholder:text-text-tertiary
// error: border-semantic-danger focus:ring-semantic-danger/20

// shared/ui/SearchInput.tsx
interface SearchInputProps {
  value:       string
  onChange:    (value: string) => void
  placeholder?: string
  debounceMs?: number   // 기본값: 300ms
}
```

---

### 6.5 Spinner / Skeleton

```typescript
// shared/ui/Spinner.tsx
type SpinnerSize = 'sm' | 'md' | 'lg'

// shared/ui/Skeleton.tsx
interface SkeletonProps {
  className?: string  // width, height를 Tailwind로 지정
}
// 사용: <Skeleton className="h-4 w-32" />
// animate-pulse bg-bg-elevated rounded

// shared/ui/TableSkeleton.tsx  (테이블 로딩 상태 전용)
interface TableSkeletonProps {
  rows?:    number   // 기본값: 10
  columns?: number   // 기본값: 5
}
```

---

### 6.6 EmptyState

```typescript
// shared/ui/EmptyState.tsx
interface EmptyStateProps {
  icon?:        React.ReactNode
  title:        string
  description?: string
  action?:      React.ReactNode  // 버튼 등
}
```

**사용 예시**:
```tsx
<EmptyState
  icon={<FiDatabase className="text-text-tertiary w-8 h-8" />}
  title="수집된 데이터가 없습니다"
  description="필터 조건을 변경하거나 수집을 시작해주세요."
  action={<Button variant="primary">수집 시작</Button>}
/>
```

---

### 6.7 ErrorBoundary

```typescript
// shared/ui/ErrorBoundary.tsx
interface ErrorBoundaryProps {
  children:  React.ReactNode
  fallback?: React.ReactNode  // 미제공 시 기본 에러 UI 표시
  onError?:  (error: Error) => void
}

// 기본 에러 UI: 에러 메시지 + "새로고침" 버튼
```

---

### 6.8 Modal

```typescript
// shared/ui/Modal.tsx
interface ModalProps {
  isOpen:    boolean
  onClose:   () => void
  title?:    string
  size?:     'sm' | 'md' | 'lg'
  children:  React.ReactNode
  footer?:   React.ReactNode
}

// 구현: createPortal + backdrop blur
// animate-fade-in + animate-slide-up
```

---

### 6.9 Toast (알림)

```typescript
// shared/ui/toast.ts
// 전역 함수 방식으로 제공 (import 없이 호출 가능)

toast.success('전체 수집 작업이 재시작되었습니다.')
toast.error('오류가 발생했습니다: ' + message)
toast.info('수집이 시작되었습니다.')
toast.warning('일부 작업을 일시정지했습니다.')

// 구현: Zustand로 toast 목록 관리
// 위치: 우하단 고정 (fixed bottom-4 right-4)
// 자동 소멸: 3초 후 (setTimeout)
```

---

### 6.10 Table

```typescript
// shared/ui/Table.tsx
// 스타일만 제공하는 Headless 컴포넌트

export const Table    = ...  // <table>  래퍼
export const Thead    = ...  // <thead>  래퍼
export const Tbody    = ...  // <tbody>  래퍼
export const Th       = ...  // <th>     래퍼 (정렬 아이콘 포함)
export const Td       = ...  // <td>     래퍼
export const TableRow = ...  // <tr>     래퍼 (hover 상태 포함)

// 기본 스타일
// table:    w-full text-sm
// th:       px-4 py-3 text-left text-text-tertiary font-medium text-xs uppercase tracking-wider
// td:       px-4 py-3 text-text-primary
// TableRow: hover:bg-bg-elevated transition-colors cursor-default
```

---

### 6.11 공용 컴포넌트 index.ts

```typescript
// shared/ui/index.ts
export { Button }        from './Button'
export { Badge }         from './Badge'
export { StatusBadge }   from './StatusBadge'
export { Input }         from './Input'
export { SearchInput }   from './SearchInput'
export { Spinner }       from './Spinner'
export { Skeleton, TableSkeleton } from './Skeleton'
export { EmptyState }    from './EmptyState'
export { ErrorBoundary } from './ErrorBoundary'
export { Modal }         from './Modal'
export { toast }         from './toast'
export { Table, Thead, Tbody, Th, Td, TableRow } from './Table'
```

---
