# 컴포넌트 작성 규칙

> 원본: `frontend/convention.md` Section 6

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

### 6.6 표준 폼(Form) 패턴

`react-hook-form`과 `zod`를 조합하여 폼을 구현합니다.

```typescript
// ✅ 표준 폼 구조
const schema = z.object({
  name: z.string().min(1, '이름을 입력해주세요.'),
})
type FormValues = z.infer<typeof schema>

export const AgentForm = () => {
  const { register, handleSubmit, formState: { errors, isSubmitting } } = useForm<FormValues>({
    resolver: zodResolver(schema)
  })

  const onValid = (data: FormValues) => {
    // 폼 제출 로직
  }

  return (
    <form onSubmit={handleSubmit(onValid)} className="flex flex-col gap-4">
      <Input
        {...register('name')}
        label="에이전트 이름"
        error={errors.name?.message}    // 에러 메시지 자동 노출
        disabled={isSubmitting}
      />
      <Button type="submit" loading={isSubmitting}>저장</Button>
    </form>
  )
}
```
```
