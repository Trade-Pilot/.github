# 디자인 시스템 — 컴포넌트, 타이포, 스페이싱, 반응형, 애니메이션, Z-index, 레이아웃, 아이콘

> 원본: `frontend/convention.md` Section 16~24

---

## 16. 디자인 시스템 컴포넌트 사용 규칙

> **핵심 원칙**: 화면을 구성할 때 **날 HTML 태그를 직접 쓰지 않습니다.**
> `shared/ui`에 정의된 디자인 시스템 컴포넌트를 반드시 사용합니다.
> 필요한 컴포넌트가 없으면 먼저 `shared/ui`에 추가한 뒤 사용합니다.

### 16.1 HTML 태그 → 디자인 시스템 컴포넌트 대응표

| 날 HTML 태그 | 디자인 시스템 컴포넌트 | 위치 |
|----------------|--------------------------|------|
| `<button>` | `<Button>` | `shared/ui/Button` |
| `<input type="checkbox">` | `<Checkbox>` | `shared/ui/Checkbox` |
| `<input type="text">` | `<Input>` | `shared/ui/Input` |
| `<select>` | `<Select>` | `shared/ui/Select` |
| `<span class="badge">` | `<Badge>` | `shared/ui/Badge` |
| `<span class="status">` | `<StatusBadge>` | `shared/ui/StatusBadge` |
| `<input type="range">` / 온오프 토글 | `<Toggle>` | `shared/ui/Toggle` |
| `<div class="tooltip">` | `<Tooltip>` | `shared/ui/Tooltip` |
| `<div class="popover">` | `<Popover>` | `shared/ui/Popover` |
| `<svg>` / `<img>` (아이콘) | `<IconPlay>` 등 | `shared/ui/icons` |
| `<div class="spinner">` | `<Spinner>` | `shared/ui/Spinner` |
| `<div class="empty">` | `<EmptyState>` | `shared/ui/EmptyState` |

### 16.2 사용 예시

```tsx
// ✅ 디자인 시스템 컴포넌트 사용
import { Button, Badge, Toggle, Checkbox } from '@shared/ui'
import { IconPlay, IconPause }             from '@shared/ui/icons'

<Button variant="primary" size="md" onClick={handleResume}>
  재시작
</Button>

<Badge variant="success">완료</Badge>

<Toggle
  checked={task.status === 'COLLECTING'}
  onChange={(v) => v ? onResume(task.identifier) : onPause(task.identifier)}
  size="sm"
/>

<Checkbox
  checked={isSelected}
  onChange={(v) => toggleSelect(symbol.identifier, v)}
/>
```

```tsx
// ❌ 날 HTML 태그 직접 사용 금지
<button onClick={handleResume} className="bg-brand-500 text-white px-4 py-2 rounded">
  재시작
</button>

<span className="bg-green-100 text-green-700 px-2 py-0.5 rounded text-xs">완료</span>

<input
  type="checkbox"
  checked={isSelected}
  onChange={(e) => toggleSelect(symbol.identifier, e.target.checked)}
/>
```

### 16.3 예외 — 날 태그 허용 케이스

아래 경우에만 날 HTML 태그 사용이 허용됩니다.

| 케이스 | 이유 |
|--------|------|
| 디자인 시스템 컴포넌트 **내부 구현** | `Button.tsx` 내부에서 `<button>` 사용 |
| 시맨틱 마크업 구조 (`<main>`, `<aside>`, `<section>`, `<article>`) | 레이아웃 의미 부여, 스타일 컴포넌트 없음 |
| 텍스트 구조 (`<h1>`~`<h6>`, `<p>`, `<ul>`, `<li>`) | 콘텐츠 계층 표현 (Typography 토큰 적용 필수) |
| `<form>` | form 제출 의미 구조 |

```tsx
// ✅ 허용 — 레이아웃 구조 태그
<main className="flex-1 overflow-y-auto">
  <section className="p-4">
    <h2 className="text-lg font-semibold text-text-primary">수집 현황</h2>
    <p className="text-sm text-text-secondary mt-1">실시간 업데이트</p>
  </section>
</main>

// ✅ 허용 — Button 컴포넌트 내부 구현
// shared/ui/Button.tsx
export const Button = ({ children, ...props }: ButtonProps) => (
  <button className={cn(baseClass, variantClass[variant])} {...props}>
    {children}
  </button>
)
```

### 16.4 새 컴포넌트 추가 절차

필요한 UI 요소가 디자인 시스템에 없을 때 날 태그를 쓰지 말고 컴포넌트를 먼저 만듭니다.

```
1. shared/ui/[ComponentName].tsx 생성
2. Props 인터페이스 정의 (variant, size, disabled 등)
3. 디자인 토큰 기반으로 스타일 구현 (cn() 사용)
4. shared/ui/index.ts에 export 추가
5. 사용처에서 import 후 사용

### 16.5 접근성(A11y) 필수 규칙

*   **Interactive Elements**: 모든 버튼과 링크는 키보드로 포커스 가능해야 하며(`Tab`), `focus-visible` 스타일이 명확해야 합니다.
*   **Labeling**: 아이콘만 있는 버튼은 반드시 `aria-label`을 제공합니다.
    *   `<Button aria-label="닫기"><IconX /></Button>`
*   **Contrast**: 텍스트와 배경의 대비는 WCAG AA 등급(4.5:1) 이상을 유지합니다. (디자인 시스템 토큰 사용 시 자동 보장)
*   **Alt Text**: 의미 있는 이미지는 `alt` 속성을, 장식용 아이콘은 `aria-hidden="true"`를 부여합니다.
*   **Status Announcements**: 실시간 상태 변화나 에러 메시지는 시각 장애 사용자를 위해 `role="status"` 또는 `aria-live="polite"`를 고려합니다.
```

---

## 17. 타이포그래피 규칙

### 17.1 폰트 사이즈 스케일

Tailwind의 기본 스케일을 사용합니다. 임의의 값(`text-[13px]`)은 금지합니다.

| 용도 | 클래스 | 크기 |
|------|--------|------|
| 페이지 제목 | `text-xl font-semibold` | 20px |
| 섹션 제목 | `text-lg font-semibold` | 18px |
| 카드 제목 / 강조 텍스트 | `text-base font-semibold` | 16px |
| 본문 (기본) | `text-sm` | 14px |
| 보조 텍스트 / 레이블 | `text-xs` | 12px |
| 숫자 데이터 (가격·수량) | `text-sm font-mono` | 14px (고정폭) |

```tsx
// ✅ 스케일 준수
<h1 className="text-xl font-semibold text-text-primary">수집 현황</h1>
<p  className="text-sm text-text-secondary">실시간으로 업데이트됩니다</p>
<span className="text-xs text-text-tertiary">12:34:01</span>
<span className="font-mono text-sm text-text-primary">{formatPrice(price)}</span>

// ❌ 임의 크기 금지
<p className="text-[13px]">...</p>
<p style={{ fontSize: '13px' }}>...</p>
```

### 17.2 폰트 웨이트

| 용도 | 클래스 |
|------|--------|
| 제목·강조 | `font-semibold` (600) |
| 중간 강조 | `font-medium` (500) |
| 본문 | `font-normal` (400, 기본값) |
| 숫자·코드 | `font-mono` (고정폭) |

> `font-bold`(700)는 특별한 강조가 필요한 경우에만 제한적으로 사용합니다.

### 17.3 텍스트 색상

텍스트 색상은 반드시 `text-text-*` 토큰을 사용합니다.

| 토큰 | 용도 |
|------|------|
| `text-text-primary` | 제목, 핵심 데이터 |
| `text-text-secondary` | 본문, 일반 설명 |
| `text-text-tertiary` | 보조 정보, 타임스탬프 |
| `text-text-disabled` | 비활성 항목 |

### 17.4 줄바꿈·말줄임

```tsx
// ✅ 단일 행 말줄임
<p className="truncate">긴 텍스트...</p>

// ✅ 다중 행 말줄임 (2줄)
<p className="line-clamp-2">긴 텍스트...</p>

// ✅ 줄바꿈 방지 (심볼 코드, 배지 등)
<span className="whitespace-nowrap">KRW-BTC</span>
```

---

## 18. 스페이싱 규칙

### 18.1 4px 그리드 시스템

모든 여백·크기는 **4px 단위(Tailwind 기본 단위)** 를 사용합니다.

```
1 unit = 4px

p-1  = 4px    p-2  = 8px    p-3  = 12px
p-4  = 16px   p-5  = 20px   p-6  = 24px
p-8  = 32px   p-10 = 40px   p-12 = 48px
```

```tsx
// ✅ 4px 단위 준수
<div className="p-4 gap-3">...</div>

// ❌ 임의 값 금지
<div className="p-[14px] gap-[7px]">...</div>
```

### 18.2 컴포넌트 내부 패딩 기준

| 컴포넌트 크기 | 패딩 |
|-------------|------|
| 버튼 sm | `px-3 py-1.5` |
| 버튼 md | `px-4 py-2` |
| 버튼 lg | `px-5 py-2.5` |
| 카드 | `p-4` |
| 테이블 셀 | `px-4 py-3` |
| 페이지 콘텐츠 | `p-4 sm:p-5 lg:p-6` (반응형) |
| 모달 | `p-6` |

### 18.3 간격(gap) 기준

| 용도 | 클래스 |
|------|--------|
| 인라인 아이콘·텍스트 간격 | `gap-1.5` (6px) |
| 폼 필드 간 간격 | `gap-3` (12px) |
| 카드 사이 간격 | `gap-3` ~ `gap-4` |
| 섹션 사이 간격 | `gap-6` ~ `gap-8` |

---

## 19. 컴포넌트 Variant 선택 기준

### 19.1 Button

| Variant | 사용 시점 | 예시 |
|---------|-----------|------|
| `primary` | 페이지당 1개, 핵심 CTA | 저장, 확인, 재시작 |
| `secondary` | 보조 액션 | 취소, 이전 |
| `ghost` | 테이블·카드 내 인라인 액션 | 재시작, 정지 |
| `danger` | 비가역적 삭제·경고 액션 | 삭제, 초기화 |

```tsx
// ✅ 수집 작업 개별 제어 → ghost (테이블 인라인)
<Button variant="ghost" size="sm" onClick={() => onPause(task.identifier)}>
  <IconPause />
</Button>

// ✅ 페이지 핵심 액션 → primary
<Button variant="primary" onClick={handleResumeAll}>
  전체 재시작
</Button>

// ✅ 위험 액션 → danger
<Button variant="danger" onClick={handleDelete}>
  수집 작업 삭제
</Button>
```

### 19.2 Badge / StatusBadge

```tsx
// StatusBadge — 수집 상태 표시 (MarketCandleCollectStatus 전용)
<StatusBadge status={task.status} retryCount={task.retryCount} />

// Badge — 일반 레이블 (상태 외 용도)
<Badge variant="info">COIN</Badge>      // 마켓 타입
<Badge variant="success">LISTED</Badge>  // 심볼 상태
<Badge variant="error">DELISTED</Badge>
```

| Variant | 색상 | 사용 시점 |
|---------|------|----------|
| `default` | 회색 | 중립, 기본 레이블 |
| `success` | 초록 | 정상·완료·활성 |
| `error` | 빨강 | 실패·오류·비활성 |
| `warning` | 노랑 | 경고·주의 |
| `info` | 보라(브랜드) | 정보·진행 중 |
| `neutral` | 연회색 | 폐지·무관 |

### 19.3 Toggle vs Button(ghost)

```tsx
// Toggle — 즉시 반영되는 on/off 상태 전환 (낙관적 업데이트)
<Toggle
  checked={task.status === 'COLLECTING'}
  onChange={(v) => v ? onResume(task.identifier) : onPause(task.identifier)}
/>

// Button ghost — 명시적 액션 (클릭 → API → UI 반영)
<Button variant="ghost" size="sm" onClick={() => onResume(task.identifier)}>
  <IconPlay />
</Button>
```

> Toggle은 "현재 상태 표시 + 전환"이 동시에 필요할 때 사용합니다.
> 단순 액션 트리거는 Button을 사용합니다.

### 19.4 Select vs 체크박스 필터

```tsx
// Select — 단일 선택 필터 (마켓 타입, 인터벌)
<Select
  value={marketType}
  onChange={setMarketType}
  options={[
    { value: 'COIN',  label: 'COIN' },
    { value: 'STOCK', label: 'STOCK' },
  ]}
/>

// Checkbox 그룹 — 복수 선택 필터 (상태, 인터벌 멀티 선택)
{STATUS_OPTIONS.map(opt => (
  <Checkbox
    key={opt.value}
    label={opt.label}
    checked={filters.statuses.includes(opt.value)}
    onChange={(v) => toggleStatusFilter(opt.value, v)}
  />
))}
```

---

## 20. 반응형 브레이크포인트 규칙

### 20.1 브레이크포인트 정의

Tailwind 기본값을 그대로 사용합니다.

| 접두사 | 기준 | 대상 기기 |
|--------|------|----------|
| (없음) | 0px ~ | 모바일 (기본) |
| `sm:` | 640px ~ | 태블릿 세로 |
| `lg:` | 1024px ~ | 데스크탑 |
| `xl:` | 1280px ~ | 넓은 데스크탑 |

> `md:`(768px)는 사용하지 않습니다. 분기점을 단순화하기 위해 `sm` / `lg` 두 단계만 사용합니다.

### 20.2 레이아웃 분기 기준

| 요소 | 모바일 (기본) | 태블릿+ (`sm:`) | 데스크탑 (`lg:`) |
|------|-------------|----------------|----------------|
| 네비게이션 | BottomTabBar | 사이드바 (아이콘) | 사이드바 (아이콘+텍스트) |
| 사이드바 너비 | 없음 | `w-16` | `w-60` |
| 수집 현황 목록 | 카드 뷰 (`TaskCardList`) | 테이블 (`TaskTable`) | 테이블 |
| 차트 컨트롤 | 하단 스크롤 바 | 하단 스크롤 바 | 우측 사이드 패널 |
| 페이지 패딩 | `p-4` | `p-5` | `p-6` |

### 20.3 반응형 작성 순서 — Mobile First

```tsx
// ✅ 모바일 기본값 → sm → lg 순으로 작성
className="flex flex-col sm:flex-row lg:gap-6"
className="text-sm lg:text-base"
className="w-full sm:w-auto"

// ❌ 데스크탑 기준으로 작성 후 모바일 덮어쓰기 금지
className="flex-row sm:flex-col"  // 의도가 뒤집혀 가독성 저하
```

### 20.4 JS 분기 — `useIsMobile` 사용 기준

CSS만으로 처리할 수 없는 경우(가상화 행 높이 계산, 조건부 렌더링)에만 사용합니다.

```tsx
// ✅ JS 분기가 필요한 경우
const isMobile = useIsMobile()
return isMobile
  ? <TaskCardList tasks={tasks} onResume={onResume} onPause={onPause} />
  : <TaskTable tasks={tasks} />

// ✅ CSS로 처리 가능한 경우 — useIsMobile 사용 금지
<div className="hidden sm:block">...</div>   // 태블릿+ 전용
<div className="sm:hidden">...</div>         // 모바일 전용
```

---

## 21. 애니메이션 / 트랜지션 규칙

### 21.1 트랜지션 기본 원칙

```tsx
// ✅ 모든 인터랙티브 요소에 transition 적용
className="transition-colors duration-150"   // 색상 변화 (버튼 hover)
className="transition-all duration-200"      // 레이아웃 변화 (사이드바 너비)
className="transition-opacity duration-150"  // 나타남/사라짐

// ❌ transition 없는 즉각 색상 변화 금지 (눈에 거슬림)
className="hover:bg-brand-600"   // transition 없으면 딱딱한 느낌
```

### 21.2 duration 기준

| 용도 | duration | 클래스 |
|------|----------|--------|
| 버튼 hover, 색상 전환 | 150ms | `duration-150` |
| 토글, 체크박스 | 200ms | `duration-200` |
| 사이드바 너비 변화 | 200ms | `duration-200` |
| 모달·드로어 진입 | 150ms | `duration-150` |
| 페이지 전환 | 150ms | `duration-150` |

> 300ms 이상은 사용자가 느리다고 느낍니다. 복잡한 애니메이션이 아니면 200ms를 넘지 않습니다.

### 21.3 easing 기준

```tsx
// ✅ 기본값 — ease-in-out (자연스러운 가속·감속)
className="transition-all duration-200 ease-in-out"

// ✅ 토글 thumb 이동
className="transition-transform duration-200 ease-in-out"

// ❌ linear는 기계적으로 느껴짐 — 색상 전환에만 사용
```

### 21.4 애니메이션 토큰

```tsx
// tailwind.config.ts에 정의된 커스텀 애니메이션
className="animate-fade-in"     // 요소 진입 (opacity 0→1, 0.15s)
className="animate-pulse"       // 수집 중 상태 점멸 (Tailwind 기본)
className="animate-spin"        // 로딩 스피너 (Tailwind 기본)

// 사용 예시
<StatusBadge
  className={task.status === 'COLLECTING' ? 'animate-pulse' : ''}
/>
```

> `animate-*`를 제외한 커스텀 `@keyframes`는 `tailwind.config.ts`에 등록 후 사용합니다.
> 컴포넌트 파일 내 인라인 `@keyframes` 정의는 금지합니다.

---

## 22. Z-index 계층 규칙

### 22.1 계층 정의

`shared/config/zIndex.ts`에 정의된 값만 사용합니다. 임의 숫자 직접 입력은 금지합니다.

```typescript
// shared/config/zIndex.ts
export const Z_INDEX = {
  base:     0,    // 일반 콘텐츠
  sticky:   10,   // 고정 헤더, 사이드바
  dropdown: 20,   // 드롭다운, Select 메뉴
  modal:    30,   // 모달 오버레이 + 패널
  toast:    40,   // 토스트 알림 (최상단)
}
```

```typescript
// tailwind.config.ts — zIndex 토큰으로 등록
zIndex: {
  'sticky':   '10',
  'dropdown': '20',
  'modal':    '30',
  'toast':    '40',
}
```

### 22.2 사용 규칙

```tsx
// ✅ Tailwind 토큰 사용
className="z-dropdown"   // Select, Popover 드롭다운
className="z-modal"      // 모달 오버레이
className="z-toast"      // 토스트 메시지

// ❌ 임의 숫자 금지
className="z-[999]"
style={{ zIndex: 9999 }}
```

> Popover, Select, Tooltip 등 Portal로 렌더링되는 컴포넌트는 `z-dropdown`을 기본으로 사용합니다.
> 모달이 Popover 위에 떠야 할 경우 `z-modal`을 사용합니다.

---

## 23. 레이아웃 패턴 선택 기준

### 23.1 데이터 표시 패턴

| 패턴 | 사용 시점 | 컴포넌트 |
|------|-----------|---------|
| **테이블** | 행이 많고 컬럼 비교가 중요할 때, 데스크탑 | `TaskTable`, `SymbolsTable` |
| **카드 리스트** | 모바일, 항목당 정보가 많아 테이블이 좁을 때 | `TaskCardList`, `TaskCard` |
| **통계 카드** | 숫자 요약, 대시보드 상단 | `StatsCard` |
| **사이드바 + 메인** | 필터·탐색 + 콘텐츠 분리가 필요할 때 | `CollectionSidebar + TaskTable` |

### 23.2 모달 vs 페이지 이동 vs 드로어

| 패턴 | 사용 시점 |
|------|-----------|
| **페이지 이동** | 독립적인 콘텐츠, URL이 필요할 때 |
| **모달** | 간단한 확인·입력, 현재 컨텍스트 유지 필요 시 |
| **드로어 (하단)** | 모바일에서 보조 정보나 액션 목록 표시 |
| **Popover** | 인라인 추가 정보, 클릭 대상 주변에 띄울 때 |
| **Tooltip** | 호버 시 짧은 설명 (1줄 이내) |

### 23.3 빈 상태 / 로딩 / 에러 패턴

```tsx
// 모든 비동기 데이터 영역은 세 가지 상태를 처리합니다
if (query.isLoading) return <Spinner />         // ← Spinner 컴포넌트
if (query.isError)   return <ErrorState />      // ← ErrorState 컴포넌트
if (!data.length)    return <EmptyState />      // ← EmptyState 컴포넌트

return <TaskTable tasks={data} />
```

> 로딩 중에 레이아웃이 뚝뚝 변하는 CLS(Cumulative Layout Shift)를 방지하려면
> Spinner는 실제 콘텐츠와 동일한 높이 영역 안에 렌더링합니다.

### 23.4 스크롤 처리

```tsx
// ✅ 스크롤바 숨김 (가로 스크롤 탭 등)
className="overflow-x-auto scrollbar-none"

// ✅ 콘텐츠 영역 세로 스크롤
className="overflow-y-auto"

// ✅ 무한 스크롤 트리거 — IntersectionObserver
<div ref={infiniteScrollRef} className="h-1" />   // 하단 감지 sentinel

// ❌ 스크롤 이벤트 직접 바인딩 금지 (성능 저하)
window.addEventListener('scroll', handleScroll)
```

---

## 24. 아이콘 사용 규칙

### 24.1 아이콘 소스

모든 아이콘은 `react-icons`의 **Feather Icons (`Fi` 접두사)** 를 사용합니다.
`shared/ui/icons/index.ts`에 등록된 아이콘만 사용합니다.

```typescript
// shared/ui/icons/index.ts — 등록된 아이콘 목록
export { FiPlay     as IconPlay    } from 'react-icons/fi'
export { FiPause    as IconPause   } from 'react-icons/fi'
export { FiRefreshCw as IconRefresh } from 'react-icons/fi'
export { FiSearch   as IconSearch  } from 'react-icons/fi'
export { FiSettings as IconSettings } from 'react-icons/fi'
export { FiBarChart2 as IconChart  } from 'react-icons/fi'
export { FiList     as IconList    } from 'react-icons/fi'
export { FiSun      as IconSun     } from 'react-icons/fi'
export { FiMoon     as IconMoon    } from 'react-icons/fi'
export { FiChevronDown as IconChevronDown } from 'react-icons/fi'
export { FiX        as IconX       } from 'react-icons/fi'
export { FiCheck    as IconCheck   } from 'react-icons/fi'
export { FiAlertCircle as IconAlert } from 'react-icons/fi'
```

### 24.2 사용 규칙

```tsx
// ✅ icons/index.ts에서 import
import { IconPlay, IconPause, IconRefresh } from '@shared/ui/icons'

<Button variant="ghost" size="sm">
  <IconPlay className="text-base" />
</Button>

// ❌ react-icons에서 직접 import 금지 (아이콘 분산 관리)
import { FiPlay } from 'react-icons/fi'

// ❌ 새 아이콘을 icons/index.ts에 등록하지 않고 사용 금지
import { FiStar } from 'react-icons/fi'   // 등록 후 사용할 것
```

### 24.3 아이콘 크기 기준

```tsx
// ✅ 텍스트 기준 상대 크기 사용
className="text-sm"     // 14px — 버튼 내 아이콘 (sm 버튼)
className="text-base"   // 16px — 버튼 내 아이콘 (md 버튼), 인라인 아이콘
className="text-lg"     // 18px — 사이드바 네비게이션 아이콘
className="text-xl"     // 20px — 강조 아이콘

// ❌ 픽셀 직접 지정 금지
style={{ fontSize: '16px' }}
className="text-[16px]"
```

### 24.4 아이콘 + 텍스트 정렬

```tsx
// ✅ items-center + gap으로 정렬
<span className="flex items-center gap-1.5">
  <IconSearch className="text-base shrink-0" />
  <span>검색</span>
</span>

// ✅ 아이콘만 있는 버튼은 aria-label 필수
<Button variant="ghost" size="sm" aria-label="새로고침">
  <IconRefresh className="text-base" />
</Button>
```

### 24.5 새 아이콘 추가 절차

```
1. Feather Icons에서 적합한 아이콘 선택 (https://feathericons.com)
2. shared/ui/icons/index.ts에 Icon* 형식으로 등록
3. 팀 공유 후 사용
```

> 다른 아이콘 라이브러리 (`Heroicons`, `Lucide` 등) 혼용 금지.
> 디자인 일관성을 위해 Feather Icons 단일 소스를 유지합니다.
