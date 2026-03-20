# Frontend - 프로젝트 초기 세팅

> Trade Pilot 프론트엔드 재개발 초기 세팅 가이드

---

## 1. 프로젝트 생성

```bash
# Vite + React + TypeScript
npm create vite@latest trade-pilot-web -- --template react-ts

cd trade-pilot-web

# 의존성 설치
npm install \
  ... (기존 라이브러리) ...
  i18next \
  react-i18next

# 개발 의존성
npm install -D \
  ... (기존 도구) ...
  @storybook/react \
  chromatic \
  loki

# Tailwind 초기화
npx tailwindcss init -p
```

---

## 2. 디렉토리 구조

```
src/
├── app/                          # 앱 초기화 레이어
│   ├── providers.tsx             # 전역 프로바이더 조립
│   ├── router.tsx                # 라우팅 정의
│   └── index.tsx                 # App 루트
│
├── pages/                        # 페이지 (라우트 단위)
│   └── [도메인]-[기능]/
│       ├── index.tsx             # 페이지 진입점 (export만)
│       ├── ui/                   # UI 컴포넌트
│       └── model/                # 페이지 전용 훅/로직
│
├── widgets/                      # 독립 블록 컴포넌트 (여러 페이지에서 재사용)
│   └── [위젯명]/
│       ├── ui/
│       └── index.ts
│
├── features/                     # 사용자 인터랙션 단위 기능
│   └── [기능명]/
│       ├── ui/
│       └── model/
│
├── entities/                     # 도메인 엔티티 (API + 타입 + Query)
│   └── [도메인]/
│       ├── api/                  # REST API 함수
│       ├── model/                # 타입, 파서
│       ├── queries/              # TanStack Query 훅
│       └── index.ts
│
└── shared/                       # 도메인 독립 공용 레이어
    ├── api/                      # Axios 클라이언트
    ├── store/                    # Zustand 전역 상태
    ├── hooks/                    # 공용 커스텀 훅
    ├── ui/                       # 공용 UI 컴포넌트
    ├── utils/                    # 유틸 함수
    ├── constants/                # 공용 상수
    └── types/                    # 공용 타입
```

### FSD 레이어 규칙

- **상위 레이어는 하위 레이어를 import 할 수 있지만 역방향은 금지**
- `pages` → `widgets` → `features` → `entities` → `shared` 순서
- **같은 레이어 내 cross-import 금지** (예: `entities/market`이 `entities/user`를 직접 import 불가)
- 각 레이어의 `index.ts`를 통해서만 외부에 노출 (public API)

---

## 3. 환경 변수 (`.env`)

```bash
# .env.development
VITE_API_BASE_URL=http://localhost:8080
VITE_WS_BASE_URL=ws://localhost:8080

# .env.production
VITE_API_BASE_URL=https://api.trade-pilot.com
VITE_WS_BASE_URL=wss://api.trade-pilot.com
```

```typescript
// shared/config/env.ts
export const env = {
  API_BASE_URL: import.meta.env.VITE_API_BASE_URL as string,
  WS_BASE_URL:  import.meta.env.VITE_WS_BASE_URL as string,
}
```

---

## 4. Tailwind CSS 설정

> **컬러 철학**: 소프트 바이올렛 — 라이트/다크 모두 지원하는 듀얼 테마.
> 브랜드 컬러(`#7C6EF5`)는 양쪽 테마에서 동일하게 사용하고,
> 배경·텍스트·보더는 CSS 변수(Custom Properties)로 분리해 테마 전환 시 즉시 반영됩니다.

```typescript
// tailwind.config.ts
import type { Config } from 'tailwindcss'

export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  darkMode: 'class',   // <html class="dark"> 로 테마 전환
  theme: {
    extend: {
      colors: {
        // ── 브랜드 (라이트/다크 공통 — 고정값) ─────────────────────
        brand: {
          50:  '#F0EEFF',
          100: '#DDD8FC',
          400: '#A99AF8',
          500: '#7C6EF5',   // ★ 메인 브랜드 컬러
          600: '#6557E8',
          700: '#5143CF',
        },

        // ── 테마별 변화 토큰 → CSS 변수 참조 ────────────────────────
        // 실제 값은 index.css :root(라이트) / .dark(다크) 에서 정의
        bg: {
          base:    'rgb(var(--bg-base) / <alpha-value>)',
          surface: 'rgb(var(--bg-surface) / <alpha-value>)',
          elevated:'rgb(var(--bg-elevated) / <alpha-value>)',
          input:   'rgb(var(--bg-input) / <alpha-value>)',
          overlay: 'rgb(var(--bg-overlay) / <alpha-value>)',
        },
        text: {
          primary:   'rgb(var(--text-primary) / <alpha-value>)',
          secondary: 'rgb(var(--text-secondary) / <alpha-value>)',
          tertiary:  'rgb(var(--text-tertiary) / <alpha-value>)',
          disabled:  'rgb(var(--text-disabled) / <alpha-value>)',
        },
        border: {
          DEFAULT: 'rgb(var(--border) / <alpha-value>)',
          strong:  'rgb(var(--border-strong) / <alpha-value>)',
        },

        // ── 시맨틱 (CSS 변수 기반 — 테마별 밝기 자동 조절, 투명도 수식어 지원) ────
        semantic: {
          success: 'rgb(var(--semantic-success) / <alpha-value>)',
          warning: 'rgb(var(--semantic-warning) / <alpha-value>)',
          danger:  'rgb(var(--semantic-danger)  / <alpha-value>)',
          info:    'rgb(var(--semantic-info)     / <alpha-value>)',
        },

        // ── 상승/하락 (한국 주식 컨벤션 — 공통) ─────────────────────
        // ⚠️  빨강 = 상승(양봉), 파랑 = 하락(음봉)
        //     Lightweight Charts: upColor: '#F04452', downColor: '#4066E4'
        up:   '#F04452',
        down: '#4066E4',

        // ── 수집 상태 (공통) ──────────────────────────────────────────
        status: {
          created:    '#9490B5',   // text-secondary 수준 (중립)
          collecting: '#7C6EF5',
          collected:  '#06C270',
          error:      '#F04452',
          paused:     '#F5A623',
          delisted:   'rgb(var(--text-disabled) / 1)',
        },
      },

      fontFamily: {
        sans: ['Pretendard', 'Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'monospace'],
      },
      fontSize: {
        '2xs': ['0.625rem', { lineHeight: '0.875rem' }],
      },
      animation: {
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'fade-in':    'fadeIn 0.15s ease-out',
        'slide-up':   'slideUp 0.2s ease-out',
        'slide-down': 'slideDown 0.2s ease-out',
      },
      keyframes: {
        fadeIn:    { from: { opacity: '0' },                               to: { opacity: '1' } },
        slideUp:   { from: { transform: 'translateY(6px)', opacity: '0' }, to: { transform: 'translateY(0)', opacity: '1' } },
        slideDown: { from: { transform: 'translateY(-6px)', opacity: '0'}, to: { transform: 'translateY(0)', opacity: '1' } },
      },
      zIndex: {
        sticky:   '10',
        dropdown: '20',
        modal:    '30',
        toast:    '40',
      },
      boxShadow: {
        // CSS 변수는 'R G B' 형식이므로 rgb(var(--x) / alpha) 문법 사용
        // ❌ rgba(var(--x), alpha) — CSS 변수가 단일 값일 때만 동작
        // ✅ rgb(var(--x) / alpha)  — space-separated RGB 변수에서 정상 동작
        'panel': '0 0 0 1px rgb(var(--border-strong) / 0.6), 0 8px 24px rgb(var(--shadow-color) / 0.35)',
        'focus': '0 0 0 3px rgb(124 110 245 / 0.35)',
      },
    },
  },
  plugins: [],
} satisfies Config
```

```css
/* src/index.css */
@import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/variable/pretendardvariable-dynamic-subset.css');

@tailwind base;
@tailwind components;
@tailwind utilities;

/* ══════════════════════════════════════════════
   라이트 테마 (기본)
   배경: 보라빛이 스며든 따뜻한 화이트
   텍스트: 딥 퍼플 계열 다크
   ══════════════════════════════════════════════ */
:root {
  --bg-base:    242 241 255;   /* #F2F1FF */
  --bg-surface: 255 255 255;   /* #FFFFFF */
  --bg-elevated:238 235 255;   /* #EEEAFF */
  --bg-input:   248 247 255;   /* #F8F7FF */
  --bg-overlay: 233 230 255;   /* #E9E6FF */

  --text-primary:   24 22 46;    /* #18162E */
  --text-secondary: 77 73 117;   /* #4D4975 */
  --text-tertiary:  140 136 176; /* #8C88B0 */
  --text-disabled:  192 189 224; /* #C0BDE0 */

  --border:       228 225 248;   /* #E4E1F8 */
  --border-strong:206 204 240;   /* #CECCF0 */

  --shadow-color: 90 80 180;     /* 보라빛 그림자 */

  /* 시맨틱 — 라이트: 채도 높은 원색 */
  --semantic-success: 22 163 74;    /* green-600  #16A34A */
  --semantic-warning: 202 138   4;  /* yellow-600 #CA8A04 */
  --semantic-danger:  220  38  38;  /* red-600    #DC2626 */
  --semantic-info:    124 110 245;  /* brand-500  #7C6EF5 */

  color-scheme: light;
}

/* ══════════════════════════════════════════════
   다크 테마
   배경: 딥 퍼플 다크
   텍스트: 보라빛 화이트 계열
   ══════════════════════════════════════════════ */
.dark {
  --bg-base:    18 17 26;    /* #12111A */
  --bg-surface: 28 27 46;    /* #1C1B2E */
  --bg-elevated:37 36 64;    /* #252440 */
  --bg-input:   24 23 40;    /* #181728 */
  --bg-overlay: 45 44 74;    /* #2D2C4A */

  --text-primary:   238 237 248; /* #EEEDF8 */
  --text-secondary: 148 144 181; /* #9490B5 */
  --text-tertiary:  97 93 130;   /* #615D82 */
  --text-disabled:  64 61 94;    /* #403D5E */

  --border:       37 36 64;      /* #252440 = bg-elevated */
  --border-strong:51 48 99;      /* #333063 */

  --shadow-color: 0 0 0;         /* 다크는 순수 블랙 그림자 */

  /* 시맨틱 — 다크: 밝은 파스텔 계열 (대비 확보) */
  --semantic-success:  74 222 128;  /* green-400  #4ADE80 */
  --semantic-warning: 250 204  21;  /* yellow-400 #FACC15 */
  --semantic-danger:  248 113 113;  /* red-400    #F87171 */
  --semantic-info:    169 154 248;  /* brand-400  #A99AF8 */

  color-scheme: dark;
}

@layer base {
  body {
    @apply bg-bg-base text-text-primary font-sans antialiased;
    transition: background-color 0.2s ease, color 0.2s ease;
  }

  /* 포커스 링 */
  :focus-visible {
    @apply outline-none ring-2 ring-brand-500/40 ring-offset-2 ring-offset-bg-base;
  }

  /* 스크롤바 */
  ::-webkit-scrollbar       { @apply w-1.5; }
  ::-webkit-scrollbar-track { @apply bg-bg-base; }
  ::-webkit-scrollbar-thumb { @apply bg-bg-overlay rounded-full; }
  ::-webkit-scrollbar-thumb:hover { @apply bg-border-strong; }
}

@layer utilities {
  .scrollbar-none { scrollbar-width: none; }
  .scrollbar-none::-webkit-scrollbar { display: none; }
}
```

---

## 5. 디자인 시스템

### 5.1 색상 토큰 사용 원칙

> 토큰 이름은 라이트/다크 어느 쪽에서도 동일하게 사용합니다.
> 실제 색상값은 `index.css`의 CSS 변수가 테마에 따라 자동으로 교체합니다.

#### 배경 계층 (밝을수록 앞으로 나옴)

```
토큰            라이트         다크         용도
bg-base         #F2F1FF        #12111A      페이지 전체 배경 (최하단)
bg-surface      #FFFFFF        #1C1B2E      카드, 패널, 사이드바 (Level 1)
bg-elevated     #EEEAFF        #252440      호버, 선택 항목 (Level 2)
bg-input        #F8F7FF        #181728      인풋 필드 (오목한 느낌)
bg-overlay      #E9E6FF        #2D2C4A      드롭다운, 모달 패널 (Level 3)
```

#### 텍스트 계층 (읽기 중요도에 따라)

```
토큰              라이트         다크         용도
text-primary      #18162E        #EEEDF8      제목, 가격, 핵심 수치 (강조)
text-secondary    #4D4975        #9490B5      레이블, 설명, 서브 정보 (기본)
text-tertiary     #8C88B0        #615D82      플레이스홀더, 힌트, 타임스탬프
text-disabled     #C0BDE0        #403D5E      비활성 항목
```

#### 브랜드 컬러 사용 기준

```
brand-500 #7C6EF5  → CTA 버튼, 링크, 활성 탭, 포커스 링 기준색 (소프트 바이올렛)
brand-600 #6557E8  → 버튼 hover
brand-700 #5143CF  → 버튼 active (눌림)
brand-50  #F0EEFF  → 선택된 행 배경 틴트, 알림 배경
brand-100 #DDD8FC  → 강조 텍스트 배경
brand-400 #A99AF8  → 비활성 상태의 브랜드 컬러 (loading 중 아이콘 등)
```

#### 시맨틱 컬러

CSS 변수 기반으로 테마별 밝기가 자동 조절됩니다. 투명도 수식어(`/15` 등)도 지원합니다.

```
토큰                    라이트          다크            용도
semantic-success        green-600       green-400       수집 완료, 연결 성공
semantic-warning        yellow-600      yellow-400      일시정지, 재시도 대기
semantic-danger         red-600         red-400         오류, 실패, 삭제 액션
semantic-info           brand-500       brand-400       안내, 수집 진행 중

사용 예시:
  text-semantic-success
  bg-semantic-danger/15     ← 투명 배경 (StatusBadge 등)
```

#### 상승/하락 컬러 (한국 주식 컨벤션)

```
up   #F04452  빨강 = 상승(양봉)  ← 한국 관습 (서양과 반대)
down #4066E4  파랑 = 하락(음봉)

⚠️  Lightweight Charts candlestick 설정 시 반드시 동일하게 맞출 것:
    upColor:   '#F04452', wickUpColor:   '#F04452'
    downColor: '#4066E4', wickDownColor: '#4066E4'
```

#### 보더 사용 기준

```
토큰              라이트         다크         용도
border            #E4E1F8        #252440      카드 외곽선, 섹션 구분 (subtle)
border-strong     #CECCF0        #333063      인풋 포커스, 드롭다운, 모달 테두리
```

### 5.2 타이포그래피

```
제목 (Heading)
  h1: text-2xl font-bold   → 페이지 제목
  h2: text-xl  font-bold   → 섹션 제목
  h3: text-lg  font-semibold → 카드 제목

본문 (Body)
  text-sm  → 기본 본문, 테이블 내용
  text-xs  → 보조 정보, 배지, 타임스탬프
  text-2xs → 최소 크기 (간격 레이블 등)

숫자 (Mono)
  font-mono → 가격, 거래량, 수익률 등 금융 숫자
```

### 5.3 스페이싱 원칙

```
컴포넌트 내부 패딩: p-3 (12px) ~ p-4 (16px)
카드 패딩:          p-4 (16px) ~ p-6 (24px)
컴포넌트 간 갭:     gap-3 (12px) ~ gap-4 (16px)
섹션 간 간격:       gap-6 (24px) ~ gap-8 (32px)
```

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

## 8. 공용 유틸 (`shared/utils/`)

### 8.1 숫자 포맷 (`formatNumber.ts`)

```typescript
// 가격 (KRW)
formatPrice(95_000_000)        // → "95,000,000"
formatPrice(95_000_000, 'KRW') // → "95,000,000 KRW"
formatPriceCompact(95_000_000) // → "9500만" (대시보드 요약용)

// 거래량
formatVolume(12.45678)         // → "12.4568" (소수 4자리)
formatVolume(0)                // → "0" (Flat Candle)

// 수익률
formatRate(0.0512)             // → "+5.12%"  (양수: + 접두, 초록)
formatRate(-0.0215)            // → "-2.15%"  (음수: 빨강)

// 개수
formatCount(1_200)             // → "1,200"

// 날짜/시간
formatDateTime(date)           // → "2024-01-15 12:34:56"
formatRelativeTime(date)       // → "3분 전", "방금 전"
formatCandleTime(date, interval) // → 간격별 포맷
                                  //   MIN_1: "12:34"
                                  //   DAY:   "01-15"
                                  //   WEEK:  "01/03주"
                                  //   MONTH: "2024-01"
```

### 8.2 클래스 유틸 (`cn.ts`)

```typescript
// clsx + tailwind-merge 래퍼
// 조건부 클래스 + Tailwind 충돌 자동 해결

import { clsx, type ClassValue } from 'clsx'
import { twMerge } from 'tailwind-merge'

export const cn = (...inputs: ClassValue[]) => twMerge(clsx(inputs))

// 사용:
// cn('px-4 py-2', isActive && 'bg-brand-600', className)
```

---

## 9. API 클라이언트 (`shared/api/`)

### 9.1 Axios 인스턴스

```typescript
// shared/api/client.ts
export const apiClient = axios.create({
  baseURL: env.API_BASE_URL,
  timeout: 10_000,
  headers: { 'Content-Type': 'application/json' },
})

// 요청 인터셉터: Bearer 토큰 자동 주입
apiClient.interceptors.request.use((config) => {
  const token = useAuthStore.getState().token
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

// 응답 인터셉터: 공통 에러 처리
apiClient.interceptors.response.use(
  (res) => res.data,   // data만 반환
  (err) => {
    const status = err.response?.status
    if (status === 401) {
      useAuthStore.getState().logout()
      window.location.replace('/login')
    }
    // 에러 메시지 표준화
    const message = err.response?.data?.message ?? err.message ?? '알 수 없는 오류'
    return Promise.reject(new ApiError(status, message))
  }
)
```

### 9.2 공통 에러 타입

```typescript
// shared/api/errors.ts
export class ApiError extends Error {
  constructor(
    public status:  number,
    public message: string,
  ) {
    super(message)
    this.name = 'ApiError'
  }
}

export const isApiError    = (e: unknown): e is ApiError => e instanceof ApiError
export const isUnauthorized = (e: unknown) => isApiError(e) && e.status === 401
export const isNotFound     = (e: unknown) => isApiError(e) && e.status === 404
```

### 9.3 API 응답 공통 타입

```typescript
// shared/api/types.ts
// 페이지네이션 응답 래퍼 (백엔드 형식에 맞게 조정)
export interface PageResponse<T> {
  content:  T[]
  hasNext:  boolean
  cursor?:  string
}

// 에러 응답
export interface ApiErrorResponse {
  code:    string
  message: string
  details?: Record<string, string>
}
```

---

## 10. 전역 상태 (`shared/store/`)

### 10.1 인증 스토어

```typescript
// shared/store/authStore.ts
interface AuthState {
  token:           string | null
  user:            User | null
  isAuthenticated: boolean

  setAuth:  (token: string, user: User) => void
  logout:   () => void
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      token:           null,
      user:            null,
      isAuthenticated: false,
      setAuth:  (token, user) => set({ token, user, isAuthenticated: true }),
      logout:   ()            => set({ token: null, user: null, isAuthenticated: false }),
    }),
    {
      name:    'trade-pilot-auth',
      // ⚠️ 보안 정책: AT(Access Token)은 절대 localStorage에 저장하지 않음 (XSS 탈취 위험)
      // token은 Zustand 메모리에만 유지 — 페이지 새로고침 시 재로그인 필요
      partialize: (state) => ({ user: state.user }),    // user 정보만 persist, token 제외
    }
  )
)
```

### 10.2 테마 스토어

```typescript
// shared/store/themeStore.ts
type Theme = 'light' | 'dark' | 'system'

interface ThemeState {
  theme:          Theme
  resolvedTheme:  'light' | 'dark'   // system일 때 실제 적용된 값
  setTheme:       (theme: Theme) => void
}

export const useThemeStore = create<ThemeState>()(
  persist(
    (set, get) => ({
      theme:         'dark',   // 기본값: 다크
      resolvedTheme: 'dark',

      setTheme: (theme) => {
        const resolved = theme === 'system'
          ? (window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light')
          : theme

        // <html> 클래스 전환 → Tailwind darkMode: 'class' 트리거
        document.documentElement.classList.toggle('dark', resolved === 'dark')
        set({ theme, resolvedTheme: resolved })
      },
    }),
    { name: 'trade-pilot-theme', partialize: (s) => ({ theme: s.theme }) }
  )
)

// app/providers.tsx에서 앱 시작 시 테마 초기화
export const initTheme = () => {
  const { theme, setTheme } = useThemeStore.getState()
  setTheme(theme)   // 저장된 값 또는 기본값 적용

  // system 선택 시 OS 테마 변경 감지
  if (theme === 'system') {
    window.matchMedia('(prefers-color-scheme: dark)')
      .addEventListener('change', (e) =>
        document.documentElement.classList.toggle('dark', e.matches)
      )
  }
}
```

**테마 토글 버튼 예시**:
```tsx
// 헤더 or 사이드바 하단에 배치
const ThemeToggle = () => {
  const { resolvedTheme, setTheme } = useThemeStore()

  return (
    <button
      onClick={() => setTheme(resolvedTheme === 'dark' ? 'light' : 'dark')}
      className="p-2 rounded-md hover:bg-bg-elevated text-text-secondary hover:text-text-primary transition-colors"
    >
      {resolvedTheme === 'dark' ? <IconSun /> : <IconMoon />}
    </button>
  )
}
```

---

### 10.3 UI 스토어 (토스트, 모달)

```typescript
// shared/store/uiStore.ts
interface Toast {
  id:      string
  type:    'success' | 'error' | 'info' | 'warning'
  message: string
}

interface UIState {
  toasts: Toast[]
  addToast:    (toast: Omit<Toast, 'id'>) => void
  removeToast: (id: string) => void
}

export const useUIStore = create<UIState>((set) => ({
  toasts: [],
  addToast: (toast) =>
    set((s) => ({ toasts: [...s.toasts, { ...toast, id: crypto.randomUUID() }] })),
  removeToast: (id) =>
    set((s) => ({ toasts: s.toasts.filter(t => t.id !== id) })),
}))
```

---

## 11. TanStack Query 설정 (`app/providers.tsx`)

```typescript
// app/providers.tsx
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime:          30_000,   // 30초 (기본 캐시 신선도)
      gcTime:             5 * 60_000, // 5분 (캐시 유지)
      retry:              2,
      refetchOnWindowFocus: true,   // 탭 포커스 시 자동 리패치
      throwOnError:       false,    // 에러는 컴포넌트에서 처리
    },
    mutations: {
      retry: 0,
    },
  },
})

export const Providers = ({ children }: { children: React.ReactNode }) => (
  <QueryClientProvider client={queryClient}>
    {children}
    {import.meta.env.DEV && <ReactQueryDevtools buttonPosition="bottom-right" />}
  </QueryClientProvider>
)
```

---

## 12. 라우팅 (`app/router.tsx`)

```typescript
// app/router.tsx
export const router = createBrowserRouter([
  {
    path:    '/',
    element: <RootLayout />,          // 공통 레이아웃 (사이드바 + 상단 바)
    errorElement: <ErrorPage />,
    children: [
      { index: true, element: <Navigate to="/market/collection" replace /> },
      {
        path: 'market',
        children: [
          { path: 'collection', element: <MarketCollectionPage />, },
          { path: 'chart',      element: <MarketChartPage />, },
          { path: 'symbols',    element: <MarketSymbolsPage />, },
        ],
      },
      // 이후 Phase
      // { path: 'agent',      ... }
      // { path: 'simulation', ... }
      // { path: 'trade',      ... }
      // { path: 'settings',   element: <SettingsPage /> }  ← Phase 2: BottomTabBar Settings 탭과 연동 시 추가
    ],
  },
  {
    path:    '/login',
    element: <LoginPage />,
  },
])
```

### 공통 레이아웃 구조

```
RootLayout
├── Sidebar (좌측 고정 네비게이션)
│   ├── Logo
│   ├── NavItem: 수집 현황  (/market/collection)
│   ├── NavItem: 캔들 차트  (/market/chart)
│   ├── NavItem: 심볼 관리  (/market/symbols)
│   └── UserMenu (하단 고정)
└── MainArea
    ├── TopBar (선택적: 브레드크럼, 알림 등)
    └── <Outlet />       ← 페이지 컴포넌트 렌더링
```

---

## 13. 코드 컨벤션

### 13.1 ESLint 설정 (`.eslintrc.cjs`)

```js
module.exports = {
  root: true,
  parser: '@typescript-eslint/parser',
  plugins: ['@typescript-eslint', 'react-hooks'],
  extends: [
    'eslint:recommended',
    'plugin:@typescript-eslint/recommended',
    'plugin:react-hooks/recommended',
  ],
  rules: {
    '@typescript-eslint/no-explicit-any':        'warn',
    '@typescript-eslint/no-unused-vars':         ['warn', { argsIgnorePattern: '^_' }],
    'react-hooks/rules-of-hooks':                'error',
    'react-hooks/exhaustive-deps':               'warn',
    'no-console':                                ['warn', { allow: ['warn', 'error'] }],
  },
}
```

### 13.2 Prettier 설정 (`.prettierrc`)

```json
{
  "semi":            false,
  "singleQuote":     true,
  "trailingComma":   "es5",
  "printWidth":      100,
  "tabWidth":        2,
  "plugins":         ["prettier-plugin-tailwindcss"]
}
```

### 13.3 파일/컴포넌트 네이밍

```
컴포넌트 파일:  PascalCase.tsx          (CollectTaskTable.tsx)
훅 파일:        camelCase.ts            (useMarketCollection.ts)
유틸 파일:      camelCase.ts            (formatNumber.ts)
상수 파일:      camelCase.ts            (market.ts)
타입 파일:      types.ts or camelCase.ts
스타일 없음:    Tailwind 클래스 직접 사용 (별도 CSS 파일 지양)
```

### 13.4 컴포넌트 구조 순서

```typescript
// 1. imports
// 2. 타입/인터페이스 정의
// 3. 상수 정의 (컴포넌트 외부)
// 4. 컴포넌트 선언
//    a. hooks (useState, useRef, useContext, 커스텀 훅)
//    b. 파생 상태 (useMemo, useCallback)
//    c. 이펙트 (useEffect)
//    d. 이벤트 핸들러
//    e. return JSX
// 5. export
```

---

## 14. vite.config.ts

```typescript
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      // 절대 경로 import 지원
      '@app':      path.resolve(__dirname, 'src/app'),
      '@pages':    path.resolve(__dirname, 'src/pages'),
      '@widgets':  path.resolve(__dirname, 'src/widgets'),
      '@features': path.resolve(__dirname, 'src/features'),
      '@entities': path.resolve(__dirname, 'src/entities'),
      '@shared':   path.resolve(__dirname, 'src/shared'),
    },
  },
  server: {
    port: 3000,
    proxy: {
      // 개발 환경 CORS 우회
      '/api': {
        target:    'http://localhost:8080',
        changeOrigin: true,
        rewrite:   (path) => path.replace(/^\/api/, ''),
      },
    },
  },
})
```

### tsconfig.json paths 동기화

```json
{
  "compilerOptions": {
    "baseUrl": ".",
    "paths": {
      "@app/*":      ["src/app/*"],
      "@pages/*":    ["src/pages/*"],
      "@widgets/*":  ["src/widgets/*"],
      "@features/*": ["src/features/*"],
      "@entities/*": ["src/entities/*"],
      "@shared/*":   ["src/shared/*"]
    }
  }
}
```

---

## 15. 개발 착수 체크리스트

### 프로젝트 초기화

- [ ] `npm create vite@latest` 실행
- [ ] 의존성 설치
- [ ] `tailwind.config.ts` 색상 시스템 설정
- [ ] `vite.config.ts` alias 설정
- [ ] `.env.development` / `.env.production` 작성
- [ ] ESLint + Prettier 설정

### 공용 레이어 구현

- [ ] `shared/api/client.ts`: Axios 인스턴스 + 인터셉터
- [ ] `shared/api/errors.ts`: ApiError 클래스
- [ ] `shared/store/authStore.ts`: Zustand 인증 상태
- [ ] `shared/store/uiStore.ts`: Toast 상태
- [ ] `shared/utils/cn.ts`: 클래스 유틸
- [ ] `shared/utils/formatNumber.ts`: 숫자/날짜 포맷
- [ ] `shared/hooks/useDebounce.ts`
- [ ] `shared/hooks/useUrlParams.ts`
- [ ] `shared/hooks/useIntersectionObserver.ts`

### 공용 UI 구현

- [ ] Button, Badge, StatusBadge
- [ ] Input, SearchInput
- [ ] Spinner, Skeleton, TableSkeleton
- [ ] EmptyState, ErrorBoundary
- [ ] Modal
- [ ] Toast + ToastContainer
- [ ] Table, Th, Td, TableRow

### 앱 조립

- [ ] `app/providers.tsx`: QueryClient Provider
- [ ] `app/router.tsx`: 라우팅 구조
- [ ] `RootLayout`: 사이드바 + 메인 영역

---

## 16. API 타입 자동 생성 & 런타임 검증

### 16.1 openapi-typescript (백엔드 스펙 → 타입 자동 생성)

백엔드 Swagger 스펙으로부터 API 요청/응답 타입을 자동 생성합니다. 수동으로 타입을 유지하는 비용을 제거하고, 백엔드 변경 시 타입 오류를 컴파일 타임에 즉시 감지합니다.

```bash
npm install -D openapi-typescript
```

```json
// package.json scripts
{
  "generate:api": "openapi-typescript http://localhost:8080/v3/api-docs -o src/shared/api/schema.d.ts"
}
```

```typescript
// 생성된 schema.d.ts를 기반으로 타입 추출
// shared/api/types.ts
import type { paths } from './schema'

// 경로별 응답 타입 추출
type CollectTaskListResponse =
  paths['/market-candle-collect-tasks']['get']['responses']['200']['content']['application/json']

type CollectTaskStatusResponse =
  paths['/market-candle-collect-task-status']['get']['responses']['200']['content']['application/json']
```

**운영 방식**: 백엔드 API 변경 시 `npm run generate:api` 실행 → 타입 오류 확인 → 수정

---

### 16.2 Zod — 단일 스키마 원칙 (런타임 검증 + 타입 추론)

TypeScript 타입은 컴파일 타임에만 존재합니다. 백엔드가 예상치 못한 형태의 응답을 보내도 런타임에서는 감지할 수 없습니다.

**기존 방식의 문제**: `types.ts`(interface)와 `schemas.ts`(Zod)를 따로 두면 두 곳이 불일치할 수 있습니다. 실제로 이 프로젝트에서 `lastCollectedAt` vs `lastCollectedTime` 불일치 버그가 이 구조에서 발생했습니다.

**단일 스키마 원칙**: Zod 스키마 하나에서 `z.infer`로 TypeScript 타입까지 추출합니다. 스키마와 타입의 단일 진실 공급원(Single Source of Truth)을 유지합니다.

```bash
npm install zod
```

#### 파일 구조

```
entities/market/model/
├── enums.ts     # Enum만 (z.nativeEnum과 함께 쓰이므로 별도 유지)
├── schemas.ts   # Zod 스키마 + z.infer 타입 export ← 핵심
└── params.ts    # 요청 파라미터 interface (런타임 검증 불필요)
```

```typescript
// entities/market/model/enums.ts
// Enum은 런타임 JS 값이 필요하므로 z.infer 대체 불가 — 별도 파일 유지
export enum MarketType               { COIN = 'COIN', STOCK = 'STOCK' }
export enum MarketSymbolStatus       { LISTED = 'LISTED', /* ... */ }
export enum MarketCandleInterval     { MIN_1 = 'MIN_1', /* ... */ }
export enum MarketCandleCollectStatus { CREATED = 'CREATED', COLLECTING = 'COLLECTING', /* ... */ }
```

```typescript
// entities/market/model/schemas.ts
import { z } from 'zod'
import {
  MarketCandleCollectStatus,
  MarketCandleInterval,
  MarketSymbolStatus,
  MarketType,
} from './enums'

// ── 스키마 정의 ────────────────────────────────────────────────

export const MarketSymbolSchema = z.object({
  identifier:   z.string().uuid(),
  code:         z.string().regex(/^[A-Z]+-[A-Z]+$/),
  name:         z.string(),
  market:       z.nativeEnum(MarketType),
  status:       z.nativeEnum(MarketSymbolStatus),
  createdDate:  z.string().datetime(),
  modifiedDate: z.string().datetime(),
})

export const CollectTaskSchema = z.object({
  identifier:         z.string().uuid(),
  symbolIdentifier:   z.string().uuid(),
  symbol:             MarketSymbolSchema.optional(),
  interval:           z.nativeEnum(MarketCandleInterval),
  status:             z.nativeEnum(MarketCandleCollectStatus),
  retryCount:         z.number().int().min(0),
  createdDate:        z.string().datetime(),
  lastCollectedTime:  z.string().datetime().nullable(),
  lastCollectedPrice: z.string().nullable(),
})

export const MarketCandleSchema = z.object({
  symbolIdentifier: z.string().uuid(),
  interval:         z.nativeEnum(MarketCandleInterval),
  time:             z.string().datetime(),
  open:             z.string(),
  high:             z.string(),
  low:              z.string(),
  close:            z.string(),
  volume:           z.string(),
  amount:           z.string(),
  isFlat:           z.boolean(),
})

export const CollectTaskStatsSchema = z.object({
  total:        z.number().int(),
  byStatus:     z.record(z.nativeEnum(MarketCandleCollectStatus), z.number()),
  byMarketType: z.record(z.nativeEnum(MarketType), z.number()),
})

// ── 타입 추출 (interface 이중 선언 없음) ────────────────────────
// z.infer가 스키마로부터 TypeScript 타입을 자동 생성
// 스키마 수정 → 타입 자동 반영 → 불일치 버그 구조적 불가능

export type MarketSymbol            = z.infer<typeof MarketSymbolSchema>
export type MarketCandleCollectTask = z.infer<typeof CollectTaskSchema>
export type MarketCandle            = z.infer<typeof MarketCandleSchema>
export type CollectTaskStats        = z.infer<typeof CollectTaskStatsSchema>
```

```typescript
// entities/market/model/params.ts
// 요청 파라미터는 API 응답이 아니므로 런타임 검증 불필요 → interface 사용
import type { MarketCandleCollectStatus, MarketCandleInterval, MarketType } from './enums'

export interface CollectTaskListParams {
  keyword?: string; statuses?: MarketCandleCollectStatus[]
  market?: MarketType[]; intervals?: MarketCandleInterval[]
  symbolCursor?: string; intervalCursor?: MarketCandleInterval; limit?: number
}

export interface CandleListParams {
  symbolId: string; interval: MarketCandleInterval
  cursor?: string; limit?: number; orderBy?: 'ASC' | 'DESC'
}
```

**검증 전략**: `parseOrThrow()` (`shared/utils/parse.ts`) 사용. 개발 환경은 `console.error`로 원인 출력 후 throw, 프로덕션은 그냥 throw. 향후 모니터링 도구 도입 시 해당 함수만 수정.

---

## 17. 테스트 전략

금융 앱이므로 버그가 실제 손실로 이어질 수 있습니다. 레이어별로 테스트 범위를 명확히 합니다.

```bash
npm install -D \
  vitest \
  @vitest/ui \
  @testing-library/react \
  @testing-library/user-event \
  @testing-library/jest-dom \
  jsdom \
  playwright \
  @playwright/test \
  msw   # 17절 MSW와 공유
```

### 17.1 테스트 레이어 구분

```
테스트 피라미드:

        /\
       /E2E\         playwright (핵심 사용자 시나리오)
      /──────\
     /통합테스트\      RTL + MSW (페이지 단위, API 모킹)
    /────────────\
   /  단위 테스트  \   Vitest (유틸, 훅, 도메인 로직)
  /────────────────\
```

| 대상 | 도구 | 범위 |
|------|------|------|
| 유틸 함수 (`formatNumber`, `cn` 등) | Vitest | 100% 커버리지 목표 |
| 도메인 로직 (parsers, Zod schemas) | Vitest | 100% 커버리지 목표 |
| 커스텀 훅 | Vitest + renderHook | 주요 시나리오 |
| 공용 컴포넌트 (shared/ui) | RTL | 인터랙션 위주 |
| 페이지 통합 | RTL + MSW | 핵심 플로우 |
| E2E | Playwright | 수집 제어, 차트 로딩 등 |

### 17.2 Vitest 설정

```typescript
// vitest.config.ts
import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'
import path from 'path'

export default defineConfig({
  plugins: [react()],
  test: {
    globals:     true,
    environment: 'jsdom',
    setupFiles:  ['./src/test/setup.ts'],
    alias: {
      // vite.config.ts의 alias와 동일하게 유지 (누락 시 테스트에서 import 오류 발생)
      '@app':      path.resolve(__dirname, 'src/app'),
      '@pages':    path.resolve(__dirname, 'src/pages'),
      '@widgets':  path.resolve(__dirname, 'src/widgets'),
      '@features': path.resolve(__dirname, 'src/features'),
      '@entities': path.resolve(__dirname, 'src/entities'),
      '@shared':   path.resolve(__dirname, 'src/shared'),
    },
  },
})
```

```typescript
// src/test/setup.ts
import '@testing-library/jest-dom'
import { server } from './mocks/server'    // MSW 서버

beforeAll(()  => server.listen())
afterEach(()  => server.resetHandlers())
afterAll(()   => server.close())
```

### 17.3 단위 테스트 예시 (유틸)

```typescript
// shared/utils/formatNumber.test.ts
describe('formatPrice', () => {
  it('천 단위 구분자를 붙인다', () => {
    expect(formatPrice(95_000_000)).toBe('95,000,000')
  })
  it('0은 0으로 표시한다', () => {
    expect(formatPrice(0)).toBe('0')
  })
})

describe('formatRate', () => {
  it('양수에는 + 접두사를 붙인다', () => {
    expect(formatRate(0.0512)).toBe('+5.12%')
  })
  it('음수는 그대로 표시한다', () => {
    expect(formatRate(-0.0215)).toBe('-2.15%')
  })
})
```

### 17.4 훅 테스트 예시

```typescript
// entities/market/queries/useCollectTasksQuery.test.ts
describe('useCollectTasksInfiniteQuery', () => {
  it('초기 로드 시 첫 페이지 데이터를 반환한다', async () => {
    const { result } = renderHook(
      () => useCollectTasksInfiniteQuery({}),
      { wrapper: QueryClientWrapper }
    )
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data?.pages[0]).toHaveLength(100)
  })

  it('hasNextPage가 false이면 fetchNextPage를 호출해도 추가 요청이 없다', async () => {
    // ...
  })
})
```

### 17.5 테스트 파일 위치 규칙

```
컴포넌트/훅과 같은 디렉토리에 배치:
  shared/utils/formatNumber.ts
  shared/utils/formatNumber.test.ts

  entities/market/queries/useCollectTasksQuery.ts
  entities/market/queries/useCollectTasksQuery.test.ts

E2E는 별도 디렉토리:
  e2e/
  ├── market-collection.spec.ts
  ├── market-chart.spec.ts
  └── auth.spec.ts
```

---

## 18. 개발 API 모킹 (MSW)

백엔드 API가 완성되기 전에도 프론트엔드 개발을 병렬로 진행할 수 있습니다. 테스트에서도 동일한 핸들러를 재사용합니다.

```bash
npm install -D msw
npx msw init public/ --save
```

### 18.1 핸들러 정의

```typescript
// src/test/mocks/handlers/marketHandlers.ts
import { http, HttpResponse } from 'msw'
import { mockCollectTasks, mockStats, mockCandles } from '../fixtures/market'

export const marketHandlers = [
  // 수집 작업 목록
  http.get('/market-candle-collect-tasks', ({ request }) => {
    const url    = new URL(request.url)
    const limit  = Number(url.searchParams.get('limit') ?? 100)
    const cursor = url.searchParams.get('symbolCursor')

    const data = cursor
      ? mockCollectTasks.slice(50)   // 두 번째 페이지 시뮬레이션
      : mockCollectTasks.slice(0, limit)

    return HttpResponse.json(data)
  }),

  // 통계
  http.get('/market-candle-collect-task-status', () =>
    HttpResponse.json(mockStats)
  ),

  // 전체 재시작
  http.put('/market-candle-collect-tasks/resume-all', () =>
    new HttpResponse(null, { status: 200 })
  ),

  // 캔들 데이터
  http.get('/symbols/:symbolId/intervals/:interval/market-candles', () =>
    HttpResponse.json(mockCandles)
  ),
]
```

### 18.2 픽스처 데이터

```typescript
// src/test/mocks/fixtures/market.ts
// 실제 데이터 형태와 동일한 목 데이터 정의
export const mockCollectTasks: CollectTaskApiResponse[] = Array.from({ length: 120 }, (_, i) => ({
  identifier:         `task-${i}`,
  symbolIdentifier:   `symbol-${Math.floor(i / 12)}`,
  interval:           INTERVALS[i % 12],
  status:             randomStatus(),
  retryCount:         0,
  createdDate:        '2024-01-01T00:00:00Z',
  lastCollectedTime:  '2024-01-15T12:34:00Z',
  lastCollectedPrice: '95000000',
}))
```

### 18.3 개발 환경 활성화

```typescript
// app/index.tsx
async function enableMocking() {
  if (import.meta.env.DEV && import.meta.env.VITE_USE_MOCK === 'true') {
    const { worker } = await import('../test/mocks/browser')
    return worker.start({ onUnhandledRequest: 'warn' })
  }
}

enableMocking().then(() => {
  ReactDOM.createRoot(document.getElementById('root')!).render(<App />)
})
```

```bash
# .env.development.local (개별 개발자 로컬 설정)
VITE_USE_MOCK=true
```

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

## 24. 디자인 시스템 보완

> Section 5에서 정의한 색상·타이포그래피·스페이싱 이외의 나머지 토큰과 컴포넌트를 정의합니다.

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
