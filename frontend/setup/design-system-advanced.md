<!-- 원본: frontend/setup.md — 섹션 24~25 -->

# 디자인 시스템 보완

> Z-Index, Border Radius, Elevation, Form 컴포넌트, Tooltip/Popover, 아이콘, 반응형 전략

---

## 24. 디자인 시스템 보완

> Section 5에서 정의한 색상/타이포그래피/스페이싱 이외의 나머지 토큰과 컴포넌트를 정의합니다.

---

### 24.1 Z-Index 레이어 시스템

레이어 충돌을 방지하기 위해 Z-index 값을 토큰으로 고정합니다.

```typescript
// shared/config/zIndex.ts
export const Z_INDEX = {
  base:     0,   // 일반 콘텐츠
  sticky:   10,  // 고정 헤더, 사이드바
  dropdown: 20,  // 드롭다운, 셀렉트 메뉴
  modal:    30,  // 모달 오버레이 + 패널
  toast:    40,  // 토스트 알림 (최상단)
} as const
```

```typescript
// tailwind.config.ts에 추가
theme: {
  extend: {
    zIndex: {
      sticky:   '10',
      dropdown: '20',
      modal:    '30',
      toast:    '40',
    },
  },
}
```

```
레이어 계층:
  toast    (z-40)  ← 토스트 / 알림
  modal    (z-30)  ← 모달 dim + 패널
  dropdown (z-20)  ← Select 드롭다운, Popover, Tooltip
  sticky   (z-10)  ← 고정 사이드바, 테이블 헤더
  base     (z-0)   ← 일반 카드, 콘텐츠
```

**주의사항**:
- Modal 내부의 Dropdown은 Modal 밖 `z-dropdown`을 그대로 쓰면 Modal 아래로 내려갑니다.
  Modal 내부에서는 Portal로 `document.body`에 마운트해 stacking context를 탈출시킵니다.
- Toast는 항상 `document.body`에 Portal로 마운트합니다.

---

### 24.2 Border Radius 토큰

```
사용 기준 (Tailwind 기본값 활용):
  rounded-sm   (2px)  → 배지(Badge), 코드 인라인
  rounded      (4px)  → 버튼(sm), 인풋, 셀렉트 트리거
  rounded-md   (6px)  → 버튼(md/lg), 드롭다운 아이템
  rounded-lg   (8px)  → 카드, 모달, 패널, 툴팁
  rounded-xl   (12px) → 모달 대형, 사이드바 영역
  rounded-full        → 아바타, 토글 트랙, 스피너
```

---

### 24.3 Elevation (다크 테마 깊이 표현)

> 다크 테마에서는 `box-shadow`보다 **배경색 계층 + border**로 깊이(depth)를 표현합니다.
> 밝은 테마의 그림자 전략과 반대 방향입니다.

```
Elevation 레벨:
  Level 0 → bg-bg-base     + border 없음        (페이지 배경)
  Level 1 → bg-bg-surface  + border-border       (카드, 패널)
  Level 2 → bg-bg-elevated + border-border-strong (드롭다운, 호버)
  Level 3 → bg-bg-overlay  + shadow-panel        (모달: 예외적으로 shadow 사용)
```

```typescript
// tailwind.config.ts에 추가
theme: {
  extend: {
    boxShadow: {
      // ✅ CSS 변수 기반 — Section 4 boxShadow 'panel'과 동일한 값 사용
      // rgb(var(--x) / alpha) 문법: CSS 커스텀 프로퍼티(공백 구분 RGB)에서 투명도 수식어 사용 가능
      'panel': '0 0 0 1px rgb(var(--border-strong) / 0.6), 0 8px 24px rgb(var(--shadow-color) / 0.35)',
    },
  },
}
```

```tsx
// 컴포넌트별 적용 예시
// 카드:   className="bg-bg-surface border border-border rounded-lg"
// 드롭:   className="bg-bg-elevated border border-border-strong rounded-lg shadow-panel"
// 모달:   className="bg-bg-surface border border-border-strong rounded-xl shadow-panel"
```

---

### 24.4 Form 컴포넌트

#### Select

```typescript
// shared/ui/Select.tsx
interface SelectOption<T extends string = string> {
  value:     T
  label:     string
  disabled?: boolean
}

interface SelectProps<T extends string = string> {
  options:      SelectOption<T>[]
  value:        T
  onChange:     (value: T) => void
  placeholder?: string
  disabled?:    boolean
  size?:        'sm' | 'md'
}

// 스타일 기준:
// trigger: bg-bg-surface border border-border rounded px-3 h-9 text-sm
//          hover:border-border-strong
//          focus:border-brand-500 focus:ring-1 focus:ring-brand-500/30
// dropdown: Portal → body / bg-bg-elevated border border-border-strong
//           rounded-lg shadow-panel z-dropdown min-w-[trigger width]
// option:   px-3 py-2 text-sm hover:bg-bg-surface cursor-pointer rounded-md
// selected: text-brand-400 font-medium
```

**사용 예시**:
```tsx
<Select
  options={INTERVAL_OPTIONS}
  value={interval}
  onChange={setInterval}
/>

const INTERVAL_OPTIONS = [
  { value: 'MIN_1',  label: '1분'  },
  { value: 'MIN_5',  label: '5분'  },
  { value: 'MIN_15', label: '15분' },
  { value: 'MIN_60', label: '1시간' },
]
```

---

#### Checkbox

```typescript
// shared/ui/Checkbox.tsx
interface CheckboxProps {
  checked:        boolean
  onChange:       (checked: boolean) => void
  label?:         string
  disabled?:      boolean
  indeterminate?: boolean   // 전체 선택 부분 상태 (일부만 선택됨)
}

// 스타일 기준:
// box:   w-4 h-4 rounded-sm border border-border-strong bg-bg-surface
//        checked:     bg-brand-600 border-brand-600
//        indeterminate: bg-brand-600/60 border-brand-600
//        disabled:    opacity-40 cursor-not-allowed
// label: text-sm text-text-primary ml-2 cursor-pointer select-none
```

**사용 예시**:
```tsx
// 행 단건 선택
<Checkbox
  checked={isSelected}
  onChange={(v) => toggleSelect(symbol.identifier, v)}
/>

// 전체 선택 (indeterminate 상태 포함)
<Checkbox
  checked={isAllSelected}
  indeterminate={isPartialSelected}
  onChange={toggleSelectAll}
  label="전체 선택"
/>
```

---

#### Toggle

```typescript
// shared/ui/Toggle.tsx
interface ToggleProps {
  checked:   boolean
  onChange:  (checked: boolean) => void
  label?:    string
  size?:     'sm' | 'md'
  disabled?: boolean
}

// 스타일 기준:
// track (sm): w-8  h-4  rounded-full  off: bg-bg-elevated  on: bg-brand-600
// track (md): w-11 h-6  rounded-full  off: bg-bg-elevated  on: bg-brand-600
// thumb (sm): w-3  h-3  rounded-full  bg-white  off: translate-x-0.5  on: translate-x-4
// thumb (md): w-5  h-5  rounded-full  bg-white  off: translate-x-0.5  on: translate-x-5
// transition: transition-all duration-200 ease-in-out
```

**사용 예시**:
```tsx
// 수집 작업 즉시 토글 — status 필드로 on/off 판단 (isActive 필드 없음)
// ✅ 'COLLECTING'이 활성 상태 — 'RUNNING'은 MarketCandleCollectStatus에 없는 값
<Toggle
  checked={task.status === 'COLLECTING'}
  onChange={(v) => v ? onResume(task.identifier) : onPause(task.identifier)}
  size="sm"
/>
```

---

### 24.5 Tooltip / Popover

#### Tooltip

```typescript
// shared/ui/Tooltip.tsx
// 마우스 호버 시 짧은 텍스트 설명 → Portal(body) 마운트, z-dropdown

interface TooltipProps {
  content:    React.ReactNode
  placement?: 'top' | 'bottom' | 'left' | 'right'  // 기본: 'top'
  delay?:     number        // 표시 딜레이 ms (기본: 300)
  children:   React.ReactElement
}

// 스타일:
// bg-bg-overlay text-text-primary text-xs rounded-lg px-2.5 py-1.5
// shadow-panel max-w-xs whitespace-pre-line animate-fade-in
// arrow: 4px 삼각형, placement에 따라 방향 결정
```

**사용 예시**:
```tsx
// 상태 뱃지에 상세 설명 추가
<Tooltip content="3회 실패 후 자동 복구 중단. 수동 재시작 필요">
  <StatusBadge status="ERROR" />
</Tooltip>

// 아이콘 버튼 레이블
<Tooltip content="데이터 새로고침">
  <Button variant="ghost" size="sm"><IconRefresh /></Button>
</Tooltip>
```

---

#### Popover

```typescript
// shared/ui/Popover.tsx
// 클릭으로 열리는 작은 패널 (Tooltip보다 풍부한 콘텐츠)
// Portal(body) 마운트, z-dropdown, 외부 클릭 시 자동 닫힘

interface PopoverProps {
  trigger:        React.ReactElement
  content:        React.ReactNode
  placement?:     'top' | 'bottom' | 'left' | 'right'  // 기본: 'bottom'
  onOpenChange?:  (open: boolean) => void
}

// 스타일:
// bg-bg-elevated border border-border-strong rounded-lg shadow-panel p-3
// min-w-[200px] max-w-[320px] animate-fade-in
```

**사용 예시**:
```tsx
// 필터 옵션 패널
<Popover
  trigger={<Button variant="secondary" size="sm">필터 <IconChevronDown /></Button>}
  content={<FilterPanel onApply={handleFilter} />}
  placement="bottom"
/>
```

---

### 24.6 아이콘 시스템

`react-icons/fi` (Feather Icons) 서브셋을 고정하여 번들 크기를 제어합니다.

```typescript
// shared/ui/icons/index.ts
// ✅ 이 파일을 통해서만 임포트 — 직접 react-icons 임포트 금지

// 네비게이션
export { FiBarChart2  as IconDashboard   } from 'react-icons/fi'
export { FiTrendingUp as IconChart       } from 'react-icons/fi'
export { FiList       as IconSymbols     } from 'react-icons/fi'
export { FiSettings   as IconSettings    } from 'react-icons/fi'

// 액션
export { FiPlay       as IconPlay        } from 'react-icons/fi'
export { FiPause      as IconPause       } from 'react-icons/fi'
export { FiRefreshCw  as IconRefresh     } from 'react-icons/fi'
export { FiSearch     as IconSearch      } from 'react-icons/fi'
export { FiFilter     as IconFilter      } from 'react-icons/fi'
export { FiPlus       as IconPlus        } from 'react-icons/fi'
export { FiTrash2     as IconTrash       } from 'react-icons/fi'
export { FiEdit2      as IconEdit        } from 'react-icons/fi'

// 방향
export { FiChevronDown  as IconChevronDown  } from 'react-icons/fi'
export { FiChevronUp    as IconChevronUp    } from 'react-icons/fi'
export { FiChevronLeft  as IconChevronLeft  } from 'react-icons/fi'
export { FiChevronRight as IconChevronRight } from 'react-icons/fi'
export { FiArrowUp      as IconArrowUp      } from 'react-icons/fi'
export { FiArrowDown    as IconArrowDown    } from 'react-icons/fi'

// 상태 / 피드백
export { FiAlertCircle as IconAlert   } from 'react-icons/fi'
export { FiCheckCircle as IconCheck   } from 'react-icons/fi'
export { FiXCircle     as IconError   } from 'react-icons/fi'
export { FiInfo        as IconInfo    } from 'react-icons/fi'
export { FiX           as IconClose   } from 'react-icons/fi'

// 테마 전환
export { FiSun      as IconSun      } from 'react-icons/fi'
export { FiMoon     as IconMoon     } from 'react-icons/fi'

// 데이터 / 기타
export { FiClock    as IconClock    } from 'react-icons/fi'
export { FiDatabase as IconDatabase } from 'react-icons/fi'
export { FiActivity as IconActivity } from 'react-icons/fi'
export { FiWifi     as IconWifi     } from 'react-icons/fi'
export { FiWifiOff  as IconWifiOff  } from 'react-icons/fi'
```

**크기 기준**:
```
text-xs   (12px) → 배지 내부
text-sm   (14px) → 버튼(sm), 테이블 셀
text-base (16px) → 버튼(md), 인풋 우측
text-lg   (18px) → 사이드바 아이콘
text-2xl  (24px) → EmptyState 보조 아이콘
text-4xl  (36px) → 에러 페이지 아이콘
```

---

### 24.7 반응형 전략

Trade Pilot은 **모바일 포함 전체 화면 대응**을 목표로 합니다.
화면 크기에 따라 레이아웃과 네비게이션 방식이 달라집니다.

```
브레이크포인트 (Tailwind 기본값 사용):
  모바일:  ~ 639px   (기본, sm 미만)   → 하단 탭 바 네비게이션
  태블릿:  640 ~ 1023px (sm ~ lg 미만) → 축소 사이드바 (icon-only)
  데스크탑:1024px ~  (lg 이상)         → 풀 사이드바 (텍스트 포함)
  와이드:  1280px ~  (xl 이상)         → 4열 그리드 확장
```

---

#### 레이아웃 구조

```
모바일 (~ 639px)                태블릿 (640 ~ 1023px)           데스크탑 (1024px+)
┌──────────────────┐           ┌────┬───────────────────┐       ┌──────────┬──────────────────────┐
│   헤더 (타이틀)   │           │ ┃  │                   │       │          │                      │
├──────────────────┤           │아이│   메인 콘텐츠      │       │ 풀 사이드 │    메인 콘텐츠         │
│                  │           │콘  │                   │       │ 바 (240) │                      │
│   메인 콘텐츠     │           │전용│                   │       │          │                      │
│                  │           │(64)│                   │       │          │                      │
├──────────────────┤           └────┴───────────────────┘       └──────────┴──────────────────────┘
│  하단 탭 바 (고정) │
└──────────────────┘
```

---

#### 네비게이션 — RootLayout

```tsx
// app/RootLayout.tsx
// 화면 크기에 따라 사이드바 ↔ 하단 탭 바 자동 전환

// ✅ React Router v6 중첩 라우트: 자식 페이지는 <Outlet />으로 렌더링
// {children} prop 방식은 React Router v6에서 동작하지 않음
import { Outlet } from 'react-router-dom'

export const RootLayout = () => (
  <div className="flex h-dvh bg-bg-base overflow-hidden">

    {/* 사이드바: 태블릿(sm) 이상에서만 표시 */}
    <aside className="hidden sm:flex flex-col
                      w-16 lg:w-60
                      shrink-0
                      bg-bg-surface border-r border-border
                      transition-[width] duration-200">
      <SidebarContent />
    </aside>

    {/* 메인 콘텐츠: <Outlet />이 중첩된 자식 라우트(페이지)를 렌더링 */}
    <main className="flex-1 min-w-0 overflow-y-auto
                     pb-20 sm:pb-0">   {/* 모바일: 하단 탭 바 높이만큼 패딩 */}
      <Outlet />
    </main>

    {/* 하단 탭 바: 모바일(sm 미만)에서만 표시 */}
    <BottomTabBar className="sm:hidden" />
  </div>
)
```

---

#### 하단 탭 바 (모바일 전용)

```tsx
// shared/ui/BottomTabBar.tsx
// ⚠️ 경로는 app/router.tsx의 실제 라우트와 반드시 일치해야 함
const NAV_ITEMS = [
  { path: '/market/collection', icon: IconDashboard, label: '현황' },
  { path: '/market/chart',      icon: IconChart,     label: '차트' },
  { path: '/market/symbols',    icon: IconSymbols,   label: '심볼' },
  // Settings는 이후 Phase에서 라우트 추가 후 활성화
  // { path: '/settings', icon: IconSettings, label: '설정' },
]

export const BottomTabBar = ({ className }: { className?: string }) => {
  const location = useLocation()

  return (
    <nav className={cn(
      'fixed bottom-0 inset-x-0 z-sticky',
      'bg-bg-surface border-t border-border',
      'flex items-stretch',
      // Safe area 대응 (iPhone 홈바)
      'pb-[env(safe-area-inset-bottom)]',
      className
    )}>
      {NAV_ITEMS.map(({ path, icon: Icon, label }) => {
        const isActive = location.pathname.startsWith(path)
        return (
          <Link key={path} to={path}
                className={cn(
                  'flex-1 flex flex-col items-center justify-center gap-1 pt-2 pb-1',
                  'text-xs transition-colors',
                  isActive
                    ? 'text-brand-500'
                    : 'text-text-tertiary hover:text-text-secondary'
                )}>
            <Icon className={cn('text-xl', isActive && 'scale-110 transition-transform')} />
            <span className="font-medium">{label}</span>
          </Link>
        )
      })}
    </nav>
  )
}
```

---

#### 사이드바 (태블릿/데스크탑)

```tsx
// shared/ui/SidebarContent.tsx
// NAV_ITEMS는 BottomTabBar와 동일한 상수를 공유 (shared/config/nav.ts 등으로 분리 권장)
export const SidebarContent = () => {
  const location = useLocation()

  return (
    <>
      {/* 로고 */}
      <div className="h-14 flex items-center px-4 border-b border-border shrink-0">
        <IconActivity className="text-brand-500 text-xl shrink-0" />
        <span className="hidden lg:block ml-2.5 font-bold text-sm tracking-tight">
          Trade Pilot
        </span>
      </div>

      {/* 메뉴 */}
      <nav className="flex-1 p-2 space-y-0.5 overflow-y-auto">
        {NAV_ITEMS.map(({ path, icon: Icon, label }) => {
          const isActive = location.pathname.startsWith(path)
          return (
            <Link key={path} to={path}
                  className={cn(
                    'flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm',
                    'transition-colors',
                    isActive
                      ? 'bg-brand-500/10 text-brand-500 font-medium'
                      : 'text-text-secondary hover:bg-bg-elevated hover:text-text-primary'
                  )}>
              <Icon className="text-lg shrink-0" />
              <span className="hidden lg:block truncate">{label}</span>
            </Link>
          )
        })}
      </nav>

      {/* 하단: 테마 토글 */}
      <div className="p-2 border-t border-border shrink-0">
        <ThemeToggle />
      </div>
    </>
  )
}
```

---

#### 그리드 시스템 (화면별)

```tsx
// 대시보드 Stats 카드
<div className="grid grid-cols-2 sm:grid-cols-2 lg:grid-cols-2 xl:grid-cols-4 gap-3 lg:gap-4">
  <StatsCard />
</div>

// 수집 현황 테이블 — 모바일에서 카드뷰로 전환
{isMobile
  ? <TaskCardList tasks={tasks} onResume={onResume} onPause={onPause} />  // 모바일: 카드 리스트
  : <TaskTable    tasks={tasks} />                                         // 태블릿+: 테이블
}

// 페이지 패딩
<div className="p-4 sm:p-5 lg:p-6">
  {/* 콘텐츠 */}
</div>
```

---

#### 모바일 테이블 대안 — 카드 뷰

```tsx
// 테이블이 모바일에서 너무 좁을 때 카드 형태로 대체
// shared/ui/TaskCard.tsx

export const TaskCard = ({ task, onResume, onPause }: {
  task:     MarketCandleCollectTask
  onResume: (id: string) => void
  onPause:  (id: string) => void
}) => (
  <div className="bg-bg-surface border border-border rounded-xl p-4 space-y-3">

    {/* 상단: 심볼코드 + 인터벌 + 상태 배지 */}
    <div className="flex items-center justify-between">
      <div>
        <p className="font-semibold text-text-primary">{task.symbol?.code ?? task.symbolIdentifier}</p>
        <p className="text-xs text-text-tertiary mt-0.5">{task.interval}</p>
      </div>
      <StatusBadge status={task.status} retryCount={task.retryCount} />
    </div>

    {/* 중단: 마지막 수집 가격 */}
    {task.lastCollectedPrice && (
      <div className="flex items-baseline gap-2">
        <span className="font-mono font-semibold text-text-primary">
          {formatPrice(task.lastCollectedPrice)}
        </span>
      </div>
    )}

    {/* 하단: 마지막 수집 시간 + 액션 버튼 */}
    <div className="flex items-center justify-between pt-1 border-t border-border">
      <span className="text-xs text-text-tertiary">
        {task.lastCollectedTime
          ? formatRelativeTime(new Date(task.lastCollectedTime))
          : '수집 대기 중'}
      </span>
      <div className="flex gap-2">
        {/* status 필드로 판단 — isActive 같은 필드 없음 */}
        {task.status === 'PAUSED' || task.status === 'ERROR'
          ? <Button variant="ghost" size="sm" onClick={() => onResume(task.identifier)}><IconPlay /></Button>
          : <Button variant="ghost" size="sm" onClick={() => onPause(task.identifier)}><IconPause /></Button>
        }
      </div>
    </div>
  </div>
)
```

---

#### 모바일 차트 뷰 조정

```tsx
// 차트 페이지: 모바일에서 컨트롤 패널을 하단 드로어로 이동
// features/chart/ui/ChartPage.tsx

// 데스크탑: 좌측 컨트롤 패널 + 우측 차트
// 모바일:   전체 너비 차트 + 하단 인터벌 선택 바

<div className="flex flex-col lg:flex-row h-full">

  {/* 차트 영역: 모바일에서 전체 너비 */}
  <div className="flex-1 min-h-0">
    <CandleChart />
  </div>

  {/* 컨트롤: 모바일에서 수평 스크롤 바 */}
  <div className="lg:hidden flex items-center gap-2 px-4 py-2 overflow-x-auto scrollbar-none
                  bg-bg-surface border-t border-border">
    {INTERVALS.map(iv => (
      <button key={iv}
              onClick={() => setInterval(iv)}
              className={cn(
                'shrink-0 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors',
                interval === iv
                  ? 'bg-brand-500 text-white'
                  : 'bg-bg-elevated text-text-secondary'
              )}>
        {iv}
      </button>
    ))}
  </div>

  {/* 컨트롤 패널: 데스크탑 전용 */}
  <aside className="hidden lg:flex flex-col w-64 border-l border-border">
    <ChartControlPanel />
  </aside>

</div>
```

---

#### Safe Area 대응 (iOS)

> **주의**: `body`의 `padding-bottom`과 BottomTabBar의 `pb-[env(...)]`를 **동시에 적용하면
> 홈바 영역이 두 배로 늘어납니다.** Safe Area 처리는 BottomTabBar 컴포넌트 한 곳에서만 합니다.

```css
/* src/index.css — body에는 적용하지 않음 */
@layer base {
  /* Safe Area는 BottomTabBar에서 pb-[env(safe-area-inset-bottom)]로 처리하므로
     여기서는 body padding 없이 meta viewport만 설정 */
  /* viewport-fit=cover는 index.html <meta name="viewport">에서 설정 */
}
```

```html
<!-- index.html -->
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover" />
```

```typescript
// tailwind.config.ts에 추가
theme: {
  extend: {
    spacing: {
      'safe-bottom': 'env(safe-area-inset-bottom)',
      'safe-top':    'env(safe-area-inset-top)',
    },
  },
}
```

---

#### useIsMobile 훅

```typescript
// shared/hooks/useIsMobile.ts
// 컴포넌트에서 JS로 분기가 필요할 때 사용
// (CSS만으로 처리 불가한 경우: 가상화 행 높이, 차트 크기 계산 등)

export const useIsMobile = (breakpoint = 640): boolean => {
  // ✅ matchMedia로 초기화 — window.innerWidth와 달리 이벤트 리스너와 동일한 기준 사용
  const [isMobile, setIsMobile] = useState(
    () => window.matchMedia(`(max-width: ${breakpoint - 1}px)`).matches
  )

  useEffect(() => {
    const mq = window.matchMedia(`(max-width: ${breakpoint - 1}px)`)
    const handler = (e: MediaQueryListEvent) => setIsMobile(e.matches)
    mq.addEventListener('change', handler)
    return () => mq.removeEventListener('change', handler)
  }, [breakpoint])

  return isMobile
}

// 사용 예시
const isMobile = useIsMobile()
return isMobile ? <TaskCardList tasks={tasks} onResume={onResume} onPause={onPause} /> : <TaskTable tasks={tasks} />
```

---

#### useClickOutside 훅

```typescript
// shared/hooks/useClickOutside.ts
// Popover / Dropdown 외부 클릭 감지용

import { useEffect, RefObject } from 'react'

export const useClickOutside = <T extends HTMLElement>(
  ref: RefObject<T>,
  handler: () => void,
  enabled = true,
): void => {
  useEffect(() => {
    if (!enabled) return

    const listener = (e: MouseEvent | TouchEvent) => {
      if (!ref.current || ref.current.contains(e.target as Node)) return
      handler()
    }

    document.addEventListener('mousedown', listener)
    document.addEventListener('touchstart', listener)
    return () => {
      document.removeEventListener('mousedown', listener)
      document.removeEventListener('touchstart', listener)
    }
  }, [ref, handler, enabled])
}
```

---

#### ThemeToggle 컴포넌트

```tsx
// shared/ui/ThemeToggle.tsx
// 사이드바 하단에 배치되는 라이트/다크 전환 버튼

import { useThemeStore } from '@shared/store/themeStore'
import { IconSun, IconMoon } from '@shared/ui/icons'   // fi 아이콘 추가 필요 (FiSun, FiMoon)
import { cn } from '@shared/utils/cn'

export const ThemeToggle = () => {
  const { resolvedTheme, setTheme } = useThemeStore()
  const isDark = resolvedTheme === 'dark'

  return (
    <button
      onClick={() => setTheme(isDark ? 'light' : 'dark')}
      className={cn(
        'w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm',
        'text-text-secondary hover:bg-bg-elevated hover:text-text-primary transition-colors',
      )}
      aria-label={isDark ? '라이트 모드로 전환' : '다크 모드로 전환'}
    >
      {isDark
        ? <IconSun  className="text-lg shrink-0" />
        : <IconMoon className="text-lg shrink-0" />
      }
      <span className="hidden lg:block truncate">
        {isDark ? '라이트 모드' : '다크 모드'}
      </span>
    </button>
  )
}
```

> `icons/index.ts`에 `FiSun as IconSun`, `FiMoon as IconMoon` 추가 필요

---

#### TaskCardList 컴포넌트

```tsx
// shared/ui/TaskCardList.tsx
// TaskCard를 세로로 나열하는 모바일용 래퍼

import { TaskCard } from './TaskCard'
import type { MarketCandleCollectTask } from '@entities/market'

interface TaskCardListProps {
  tasks:    MarketCandleCollectTask[]
  onResume: (id: string) => void
  onPause:  (id: string) => void
}

export const TaskCardList = ({ tasks, onResume, onPause }: TaskCardListProps) => (
  <div className="flex flex-col gap-3 p-4">
    {tasks.map((task) => (
      <TaskCard
        key={task.identifier}
        task={task}
        onResume={onResume}
        onPause={onPause}
      />
    ))}
  </div>
)
```

---

## 25. 업데이트된 착수 체크리스트 (디자인 시스템 보완)

- [ ] `tailwind.config.ts`에 `zIndex`, `boxShadow('panel')` 토큰 추가
- [ ] `shared/config/zIndex.ts` 파일 생성
- [ ] `shared/ui/Select.tsx` 구현 (Portal 드롭다운, 제네릭 타입)
- [ ] `shared/ui/Checkbox.tsx` 구현 (indeterminate 상태 포함)
- [ ] `shared/ui/Toggle.tsx` 구현 (sm/md 사이즈)
- [ ] `shared/ui/Tooltip.tsx` 구현 (Portal + delay + placement)
- [ ] `shared/ui/Popover.tsx` 구현 (Portal + useClickOutside)
- [ ] `shared/ui/icons/index.ts` 생성 및 서브셋 정의
- [ ] `shared/ui/BottomTabBar.tsx` 구현 (모바일 하단 탭 바)
- [ ] `shared/ui/SidebarContent.tsx` 구현 (태블릿/데스크탑 사이드바)
- [ ] `app/RootLayout.tsx` 반응형 레이아웃 구현 (사이드바 + 하단 탭 분기)
- [ ] `shared/hooks/useIsMobile.ts` 구현
- [ ] `tailwind.config.ts`에 `safe-bottom`, `safe-top` spacing 추가
- [ ] `index.css`에 `env(safe-area-inset-bottom)` safe area 추가
- [ ] 수집 현황 페이지: 모바일 카드뷰 / 데스크탑 테이블 분기 구현
- [ ] 차트 페이지: 모바일 하단 인터벌 바 / 데스크탑 사이드 패널 분기 구현
- [ ] `shared/ui/index.ts`에 신규 컴포넌트 export 추가
