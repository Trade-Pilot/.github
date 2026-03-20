# Storybook 설계 — Trade Pilot

> 디자인 시스템 컴포넌트 카탈로그, 스토리 작성 규칙, 설정 가이드

---

## 1. 개요

Storybook은 Trade Pilot의 **공용 컴포넌트(shared/ui)**, **위젯(widgets)**, **피처(features)**를 독립적으로 개발·문서화·테스트하는 도구이다.

**목적**:
- 디자인 시스템 컴포넌트의 시각적 카탈로그
- Props 조합별 상태를 독립적으로 검증
- 다크 모드, 반응형 뷰포트별 렌더링 확인
- Chromatic 연동으로 시각적 회귀 테스트 자동화

---

## 2. 설치 및 설정

### 2.1 의존성

```bash
npm install -D \
  @storybook/react-vite \
  @storybook/addon-essentials \
  @storybook/addon-a11y \
  @storybook/addon-themes \
  @storybook/addon-viewport \
  @storybook/test \
  chromatic
```

### 2.2 설정 파일

```typescript
// .storybook/main.ts
import type { StorybookConfig } from '@storybook/react-vite'

const config: StorybookConfig = {
  stories: [
    '../src/shared/**/*.stories.@(ts|tsx)',
    '../src/widgets/**/*.stories.@(ts|tsx)',
    '../src/features/**/*.stories.@(ts|tsx)',
  ],
  addons: [
    '@storybook/addon-essentials',
    '@storybook/addon-a11y',
    '@storybook/addon-themes',
    '@storybook/addon-viewport',
  ],
  framework: {
    name: '@storybook/react-vite',
    options: {},
  },
}

export default config
```

```typescript
// .storybook/preview.ts
import type { Preview } from '@storybook/react'
import '../src/app/globals.css'  // Tailwind 전역 스타일

const preview: Preview = {
  parameters: {
    layout: 'centered',
    backgrounds: {
      default: 'dark',
      values: [
        { name: 'dark', value: '#0D0C1D' },
        { name: 'light', value: '#FFFFFF' },
      ],
    },
    viewport: {
      viewports: {
        mobile:  { name: 'Mobile',  styles: { width: '375px',  height: '812px' } },
        tablet:  { name: 'Tablet',  styles: { width: '768px',  height: '1024px' } },
        desktop: { name: 'Desktop', styles: { width: '1280px', height: '800px' } },
        wide:    { name: 'Wide',    styles: { width: '1920px', height: '1080px' } },
      },
    },
  },
  decorators: [
    (Story) => (
      <div className="dark font-sans">
        <Story />
      </div>
    ),
  ],
}

export default preview
```

### 2.3 스크립트

```json
{
  "scripts": {
    "storybook": "storybook dev -p 6006",
    "build-storybook": "storybook build",
    "chromatic": "chromatic --project-token=${CHROMATIC_TOKEN}"
  }
}
```

---

## 3. 스토리 작성 규칙

### 3.1 파일 위치

```
컴포넌트 파일과 같은 디렉토리에 배치:

shared/ui/
├── Button.tsx
├── Button.stories.tsx     ← 여기
├── Badge.tsx
├── Badge.stories.tsx
└── ...

widgets/candle-chart/
├── ui/
│   ├── CandleChart.tsx
│   └── CandleChart.stories.tsx
└── ...
```

### 3.2 네이밍 규칙

```typescript
// 카테고리/서브카테고리 패턴
export default {
  title: 'shared/Button',        // shared/ 접두사
  // title: 'widgets/CandleChart',   // widgets/ 접두사
  // title: 'features/EmergencyStop', // features/ 접두사
  component: Button,
} satisfies Meta<typeof Button>
```

**사이드바 구조**:
```
shared/
├── Button
├── Badge
├── StatusBadge
├── Input
├── SearchInput
├── Spinner
├── Skeleton
├── EmptyState
├── Modal
├── Toast
├── Table
└── ErrorBoundary

widgets/
├── CandleChart
├── AgentCard
├── PortfolioSummary
├── DecisionLogTable
├── BacktestConfigPanel
├── BacktestProgressBar
├── BacktestResultReport
├── AccountTree
├── AllocationSlider
├── OrderBook
├── DualBalanceView
├── EmergencyStopButton
├── NotificationBadge
├── ServiceHealthGrid
├── OutboxDeadTable
└── AuditLogTable

features/
├── SignIn
├── SignUp
├── CreateStrategy
├── DeployAgent
├── RunBacktest
├── RegisterTrade
├── EmergencyStop
├── CancelOrder
└── ManageChannel
```

### 3.3 스토리 구조 표준

```typescript
import type { Meta, StoryObj } from '@storybook/react'
import { Button } from './Button'

const meta = {
  title: 'shared/Button',
  component: Button,
  tags: ['autodocs'],              // 자동 문서 생성
  argTypes: {
    variant: {
      control: 'select',
      options: ['primary', 'secondary', 'danger', 'ghost'],
    },
    size: {
      control: 'select',
      options: ['sm', 'md', 'lg'],
    },
    loading: { control: 'boolean' },
    disabled: { control: 'boolean' },
  },
} satisfies Meta<typeof Button>

export default meta
type Story = StoryObj<typeof meta>

// 기본 상태 (필수)
export const Default: Story = {
  args: {
    children: '버튼',
    variant: 'primary',
    size: 'md',
  },
}

// 모든 Variant 나열 (필수)
export const AllVariants: Story = {
  render: () => (
    <div className="flex gap-3">
      <Button variant="primary">Primary</Button>
      <Button variant="secondary">Secondary</Button>
      <Button variant="danger">Danger</Button>
      <Button variant="ghost">Ghost</Button>
    </div>
  ),
}

// 인터랙션 상태 (필수)
export const Loading: Story = {
  args: { children: '저장 중...', variant: 'primary', loading: true },
}

export const Disabled: Story = {
  args: { children: '비활성', variant: 'primary', disabled: true },
}
```

### 3.4 필수 스토리 체크리스트

모든 컴포넌트에 대해 최소한 아래 스토리를 작성한다:

| 스토리 | 설명 | 필수 |
|--------|------|------|
| `Default` | 기본 Props 상태 | **필수** |
| `AllVariants` | 모든 variant를 한 화면에 나열 | **필수** |
| `Sizes` | 모든 size를 한 화면에 나열 | variant/size가 있으면 필수 |
| `Loading` | 로딩 상태 | loading prop이 있으면 필수 |
| `Disabled` | 비활성 상태 | disabled prop이 있으면 필수 |
| `Error` | 에러 상태 (validation 등) | error prop이 있으면 필수 |
| `Empty` | 데이터 없음 상태 | 목록/테이블 컴포넌트 필수 |
| `DarkMode` | 다크 모드 렌더링 | 색상 관련 컴포넌트 |
| `Mobile` | 모바일 뷰포트 | 반응형 컴포넌트 |

---

## 4. shared/ui 스토리 명세

### 4.1 Button

```typescript
// shared/ui/Button.stories.tsx
title: 'shared/Button'

stories:
  Default          — variant: primary, size: md
  AllVariants      — primary, secondary, danger, ghost 나열
  AllSizes         — sm, md, lg 나열
  WithLeftIcon     — leftIcon: <FiRefreshCw />
  Loading          — loading: true (Spinner 표시)
  Disabled         — disabled: true (opacity 처리)
  FullWidth        — className: 'w-full'

argTypes:
  variant:  select ['primary', 'secondary', 'danger', 'ghost']
  size:     select ['sm', 'md', 'lg']
  loading:  boolean
  disabled: boolean
```

### 4.2 Badge

```typescript
// shared/ui/Badge.stories.tsx
title: 'shared/Badge'

stories:
  Default          — variant: default
  AllVariants      — default, success, error, warning, info, neutral 나열
  WithDot          — dot: true (각 variant별)
  LongText         — children: '매우 긴 상태 메시지 텍스트'

argTypes:
  variant: select ['default', 'success', 'error', 'warning', 'info', 'neutral']
  dot:     boolean
```

### 4.3 StatusBadge

```typescript
// shared/ui/StatusBadge.stories.tsx
title: 'shared/StatusBadge'

stories:
  AllStatuses       — CREATED, COLLECTING, COLLECTED, ERROR, PAUSED, DELISTED 나열
  ErrorWithRetry    — status: ERROR, retryCount: 2 → "오류 (2/3)"
  ErrorMaxRetry     — status: ERROR, retryCount: 3 → "오류 (3/3) - 수동 복구 필요"

argTypes:
  status:     select [MarketCandleCollectStatus values]
  retryCount: number
```

### 4.4 Input / SearchInput

```typescript
// shared/ui/Input.stories.tsx
title: 'shared/Input'

stories:
  Default          — label: '이메일', placeholder: 'email@example.com'
  WithError        — error: '이메일 형식이 올바르지 않습니다'
  WithIcons        — leftIcon: <FiSearch />, rightIcon: <FiX />
  Disabled         — disabled: true
  Password         — type: 'password'

// shared/ui/SearchInput.stories.tsx
title: 'shared/SearchInput'

stories:
  Default          — placeholder: '심볼 검색...'
  WithValue        — value: 'KRW-BTC'
  Debounced        — debounceMs: 500 (입력 지연 시각화)
```

### 4.5 Spinner / Skeleton

```typescript
// shared/ui/Spinner.stories.tsx
title: 'shared/Spinner'

stories:
  AllSizes — sm, md, lg 나열

// shared/ui/Skeleton.stories.tsx
title: 'shared/Skeleton'

stories:
  TextLine         — className: 'h-4 w-48'
  Card             — className: 'h-32 w-64 rounded-lg'
  TableSkeleton    — rows: 5, columns: 4
```

### 4.6 EmptyState

```typescript
// shared/ui/EmptyState.stories.tsx
title: 'shared/EmptyState'

stories:
  Default          — title: '데이터가 없습니다'
  WithDescription  — title + description
  WithAction       — title + description + <Button>추가</Button>
  WithIcon         — icon: <FiDatabase />
```

### 4.7 Modal

```typescript
// shared/ui/Modal.stories.tsx
title: 'shared/Modal'

stories:
  Default          — isOpen: true, title: '확인', size: md
  Small            — size: sm
  Large            — size: lg
  WithFooter       — footer: <Button>확인</Button><Button variant="ghost">취소</Button>
  DestructiveConfirm — title: '정말 삭제하시겠습니까?', footer: <Button variant="danger">삭제</Button>

interaction:
  - "닫기" 버튼 클릭 → onClose 호출 확인
  - Backdrop 클릭 → onClose 호출 확인
  - ESC 키 → onClose 호출 확인
```

### 4.8 Toast

```typescript
// shared/ui/Toast.stories.tsx
title: 'shared/Toast'

stories:
  Success     — toast.success('저장되었습니다')
  Error       — toast.error('오류가 발생했습니다')
  Info        — toast.info('수집이 시작되었습니다')
  Warning     — toast.warning('일부 작업이 정지되었습니다')
  AutoDismiss — 3초 후 자동 소멸 확인
  Stack       — 여러 토스트 동시 표시 (최대 5개)
```

### 4.9 Table

```typescript
// shared/ui/Table.stories.tsx
title: 'shared/Table'

stories:
  Default          — 5행 3열 기본 테이블
  WithSortable     — Th 클릭 시 정렬 아이콘 변경
  Loading          — <TableSkeleton rows={5} columns={3} />
  Empty            — <EmptyState title="데이터가 없습니다" />
  VirtualScroll    — 1000행 가상 스크롤 (TanStack Virtual)
```

---

## 5. widgets 스토리 명세

### 5.1 CandleChart

```typescript
// widgets/candle-chart/ui/CandleChart.stories.tsx
title: 'widgets/CandleChart'

stories:
  Default            — 100개 캔들 데이터, KRW-BTC, MIN_1
  WithIndicators     — MA(20), MA(60) 오버레이
  WithSignalMarkers  — BUY/SELL 마커 5개
  Loading            — 데이터 로딩 중 Skeleton
  Empty              — 캔들 데이터 없음
  StaleData          — Grayscale + "연결 지연" 오버레이
  Mobile             — 375px 뷰포트, 터치 인터랙션

decorators:
  - 고정 크기 컨테이너 (800×400)

mock data:
  - 캔들: 랜덤 OHLCV 생성 유틸 사용
  - 지표: MA 계산값 포함
  - 신호: { type: 'BUY', confidence: 0.85, candleIndex: 50 }
```

### 5.2 AgentCard

```typescript
// widgets/agent-card/ui/AgentCard.stories.tsx
title: 'widgets/AgentCard'

stories:
  Inactive       — status: INACTIVE, 비활성 상태
  Active         — status: ACTIVE, 수익률 +5.2%
  Paused         — status: PAUSED, 일시정지 아이콘
  Terminated     — status: TERMINATED, 회색 처리
  WithProfit     — realizedPnl: +150,000 (녹색)
  WithLoss       — realizedPnl: -30,000 (빨간색)

argTypes:
  status: select ['INACTIVE', 'ACTIVE', 'PAUSED', 'TERMINATED']
```

### 5.3 PortfolioSummary

```typescript
// widgets/portfolio-summary/ui/PortfolioSummary.stories.tsx
title: 'widgets/PortfolioSummary'

stories:
  Default            — cash: 1,000,000, totalValue: 2,500,000
  WithReservation    — reservedCash: 500,000 (바 차트에서 점유 영역 표시)
  NoPositions        — positions: [] (현금만)
  HighPnl            — realizedPnl: +1,200,000 (강조)
  NegativePnl        — realizedPnl: -300,000 (경고)
  Loading            — 데이터 로딩 중

mock data:
  - cash, reservedCash, totalValue: Decimal string
  - positions: [{ symbolIdentifier, quantity, reservedQuantity, averagePrice, currentPrice }]
```

### 5.4 DecisionLogTable

```typescript
// widgets/decision-log-table/ui/DecisionLogTable.stories.tsx
title: 'widgets/DecisionLogTable'

stories:
  Default            — 20행 결정 로그
  WithBuySignal      — signalType: BUY 강조 (녹색)
  WithSellSignal     — signalType: SELL 강조 (빨간색)
  WithHoldSignal     — signalType: HOLD (회색)
  WithError          — evaluationStatus: ERROR (빨간 배경)
  Loading            — TableSkeleton
  Empty              — EmptyState
  InfiniteScroll     — 1000건 가상 스크롤

interaction:
  - 행 클릭 → 차트 크로스헤어 이동 시뮬레이션
```

### 5.5 BacktestProgressBar

```typescript
// widgets/backtest-progress-bar/ui/BacktestProgressBar.stories.tsx
title: 'widgets/BacktestProgressBar'

stories:
  NotStarted     — progress: 0%
  InProgress     — progress: 45% (애니메이션)
  NearComplete   — progress: 95%
  Completed      — progress: 100% + "완료" 배지
  Error          — 에러 상태 + 에러 메시지

argTypes:
  progress: range [0, 100]
```

### 5.6 BacktestResultReport

```typescript
// widgets/backtest-result-report/ui/BacktestResultReport.stories.tsx
title: 'widgets/BacktestResultReport'

stories:
  Profitable     — 수익률 +15%, MDD -8%, Sharpe 2.1
  Unprofitable   — 수익률 -5%, MDD -22%, Sharpe 0.3
  HighVolatility — 수익률 +25%, MDD -30%

mock data:
  - 수익률 곡선 (시계열 데이터)
  - 통계 지표: return, mdd, sharpe, sortino, winRate
  - 신호 스냅샷 목록
```

### 5.7 EmergencyStopButton

```typescript
// widgets/emergency-stop-button/ui/EmergencyStopButton.stories.tsx
title: 'widgets/EmergencyStopButton'

stories:
  Default          — 빨간 버튼 "비상 정지"
  Confirming       — 2단계 확인 모달 오픈 상태
  Stopped          — emergencyStopped: true → "비상 정지 해제" 버튼
  GlobalStop       — ADMIN 전체 비상 정지 (파괴적 액션 가드)

interaction:
  - 클릭 → 확인 모달 표시
  - 확인 → onEmergencyStop 호출
```

### 5.8 DualBalanceView

```typescript
// widgets/dual-balance-view/ui/DualBalanceView.stories.tsx
title: 'widgets/DualBalanceView'

stories:
  Synced           — System View = Exchange View (정상)
  Drifted          — 차이 발생 → Drift Indicator 아이콘
  Loading          — Exchange 잔고 조회 중
  Offline          — Exchange 연결 실패 → 경고

mock data:
  - systemBalance: { cash: '1,000,000', positions: [...] }
  - exchangeBalance: { cash: '998,500', positions: [...] }
  - driftAmount: '1,500'
```

### 5.9 NotificationBadge

```typescript
// widgets/notification-badge/ui/NotificationBadge.stories.tsx
title: 'widgets/NotificationBadge'

stories:
  NoNotifications  — count: 0 (배지 미표시)
  Few              — count: 3 (숫자 표시)
  Many             — count: 99+ (99+ 표시)
  WithDropdown     — 클릭 시 드롭다운 알림 목록

interaction:
  - 클릭 → 드롭다운 토글
  - 외부 클릭 → 드롭다운 닫힘
```

### 5.10 OrderBook

```typescript
// widgets/order-book/ui/OrderBook.stories.tsx
title: 'widgets/OrderBook'

stories:
  Default          — PENDING 2건, SUBMITTED 3건, FILLED 5건
  WithPartialFill  — PARTIALLY_FILLED 주문 (프로그레스바)
  AllCancelled     — 모든 주문 CANCELLED
  Empty            — 주문 없음
  Realtime         — WebSocket 이벤트로 상태 변경 시뮬레이션

mock data:
  - orders: [{ orderIdentifier, side, type, requestedQuantity, executedQuantity, status, ... }]
```

---

## 6. features 스토리 명세

### 6.1 SignIn / SignUp

```typescript
// features/sign-in/ui/SignInForm.stories.tsx
title: 'features/SignIn'

stories:
  Default          — 빈 폼
  FilledValid      — 유효한 입력값
  InvalidEmail     — 이메일 형식 오류 (인라인 에러)
  WrongPassword    — 서버 에러 U003 (토스트)
  AccountSuspended — 서버 에러 U004 (토스트)
  Loading          — 로그인 진행 중 (버튼 로딩)

// features/sign-up/ui/SignUpForm.stories.tsx
title: 'features/SignUp'

stories:
  Default          — 빈 폼
  PasswordWeak     — 비밀번호 규칙 미충족 (인라인 에러)
  EmailDuplicate   — 서버 에러 U002 (인라인 에러)
  Success          — 가입 성공 → 토스트 + 리다이렉트
```

### 6.2 CreateStrategy

```typescript
// features/create-strategy/ui/StrategyForm.stories.tsx
title: 'features/CreateStrategy'

stories:
  MACrossover      — strategyKind: MA_CROSSOVER, shortPeriod/longPeriod 슬라이더
  RSI              — strategyKind: RSI, period/oversold/overbought 슬라이더
  BollingerBreakout — strategyKind: BOLLINGER_BREAKOUT, period/multiplier
  ValidationError  — 파라미터 범위 초과 (인라인 에러)
```

### 6.3 EmergencyStop

```typescript
// features/emergency-stop/ui/EmergencyStopAction.stories.tsx
title: 'features/EmergencyStop'

stories:
  SingleAgent      — 특정 Registration 비상 정지
  GlobalStop       — ADMIN 전체 비상 정지 (비밀번호 재입력)
  AlreadyStopped   — emergencyStopped: true → 해제 버튼
```

---

## 7. Mock 데이터 관리

### 7.1 Mock 파일 위치

```
.storybook/
├── mocks/
│   ├── candles.ts          — 랜덤 OHLCV 생성
│   ├── agents.ts           — Agent/Strategy/Portfolio 목 데이터
│   ├── orders.ts           — Order/Execution 목 데이터
│   ├── notifications.ts    — NotificationLog 목 데이터
│   └── factory.ts          — 공통 팩토리 함수
└── decorators/
    ├── withQueryClient.tsx  — TanStack Query Provider
    ├── withRouter.tsx       — React Router Provider
    └── withAuth.tsx         — 인증 상태 Provider
```

### 7.2 캔들 데이터 생성기

```typescript
// .storybook/mocks/candles.ts
export function generateCandles(count: number, basePrice = 50000000): CandleData[] {
  let price = basePrice
  return Array.from({ length: count }, (_, i) => {
    const change = (Math.random() - 0.48) * price * 0.02
    price += change
    const high = price * (1 + Math.random() * 0.005)
    const low = price * (1 - Math.random() * 0.005)
    return {
      time: dayjs().subtract(count - i, 'minute').toISOString(),
      open: String(price - change / 2),
      high: String(high),
      low: String(low),
      close: String(price),
      volume: String(Math.random() * 10),
      amount: String(Math.random() * 500000000),
    }
  })
}
```

### 7.3 공통 Decorator

```typescript
// .storybook/decorators/withQueryClient.tsx
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'

const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: false, staleTime: Infinity } },
})

export const withQueryClient = (Story: React.FC) => (
  <QueryClientProvider client={queryClient}>
    <Story />
  </QueryClientProvider>
)
```

---

## 8. 테마 테스트

### 8.1 다크/라이트 모드 전환

```typescript
// .storybook/preview.ts
import { withThemeByClassName } from '@storybook/addon-themes'

decorators: [
  withThemeByClassName({
    themes: {
      dark:  'dark',
      light: '',
    },
    defaultTheme: 'dark',
  }),
]
```

### 8.2 한국 주식 색상 검증

캔들 차트 관련 스토리에서 반드시 확인:
- 상승(양봉): **빨간색** `#F04452` (`stock-up`)
- 하락(음봉): **파란색** `#4066E4` (`stock-down`)

```typescript
// widgets/candle-chart/ui/CandleChart.stories.tsx
export const KoreanColorConvention: Story = {
  name: '한국 주식 색상 확인',
  args: {
    candles: [
      { ...baseCandle, close: '51000000' },  // 양봉 → 빨간색
      { ...baseCandle, close: '49000000' },  // 음봉 → 파란색
    ],
  },
}
```

---

## 9. 접근성(A11y) 테스트

### 9.1 자동 검사

`@storybook/addon-a11y`로 각 스토리의 접근성을 자동 검사한다.

**필수 통과 기준**:
- 색상 대비: WCAG 2.1 AA (최소 4.5:1)
- 터치 타겟: 최소 44px × 44px (convention.md Section 31)
- 키보드 네비게이션: Tab/Enter/ESC 동작
- ARIA 레이블: 아이콘 버튼에 `aria-label` 필수

### 9.2 포커스 순서 검증

```typescript
// Modal, Dropdown 등 오버레이 컴포넌트에서 필수
export const FocusTrap: Story = {
  name: '포커스 트랩 확인',
  play: async ({ canvasElement }) => {
    const modal = within(canvasElement).getByRole('dialog')
    // Tab 키로 모달 내부에서만 포커스 순환 확인
    await userEvent.tab()
    expect(document.activeElement).toBeWithin(modal)
  },
}
```

---

## 10. CI 연동

### 10.1 Chromatic (시각적 회귀 테스트)

```yaml
# .github/workflows/chromatic.yml
name: Chromatic
on: push
jobs:
  chromatic:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with: { fetch-depth: 0 }
      - uses: actions/setup-node@v4
      - run: npm ci
      - run: npx chromatic --project-token=${{ secrets.CHROMATIC_TOKEN }}
```

**검토 기준**:
- 1px 이상 차이 → Chromatic에서 경고
- 레이아웃 변경 → 반드시 디자이너 승인 후 머지

### 10.2 Storybook 빌드 검증

```yaml
# PR 시 Storybook 빌드 실패하면 머지 차단
- run: npm run build-storybook
```

---

## 11. 컴포넌트 카탈로그 전체 목록

### shared/ui (11개)

| 컴포넌트 | 스토리 수 | Variant | 상태 |
|---------|----------|---------|------|
| Button | 7 | primary/secondary/danger/ghost × sm/md/lg | 설계 완료 |
| Badge | 4 | default/success/error/warning/info/neutral | 설계 완료 |
| StatusBadge | 3 | MarketCandleCollectStatus 6종 | 설계 완료 |
| Input | 5 | label/error/icons/disabled/password | 설계 완료 |
| SearchInput | 3 | default/withValue/debounced | 설계 완료 |
| Spinner | 1 | sm/md/lg | 설계 완료 |
| Skeleton | 3 | textLine/card/tableSkeleton | 설계 완료 |
| EmptyState | 4 | default/description/action/icon | 설계 완료 |
| Modal | 5 | sm/md/lg/footer/destructive | 설계 완료 |
| Toast | 6 | success/error/info/warning/autoDismiss/stack | 설계 완료 |
| Table | 5 | default/sortable/loading/empty/virtualScroll | 설계 완료 |

### widgets (10개)

| 컴포넌트 | 스토리 수 | 핵심 상태 |
|---------|----------|----------|
| CandleChart | 7 | 기본/지표/신호/로딩/비어있음/지연경고/모바일 |
| AgentCard | 6 | INACTIVE/ACTIVE/PAUSED/TERMINATED/수익/손실 |
| PortfolioSummary | 6 | 기본/점유/포지션없음/수익/손실/로딩 |
| DecisionLogTable | 8 | BUY/SELL/HOLD/ERROR/로딩/비어있음/무한스크롤/행클릭 |
| BacktestProgressBar | 5 | 시작전/진행중/거의완료/완료/에러 |
| BacktestResultReport | 3 | 수익/손실/고변동성 |
| EmergencyStopButton | 4 | 기본/확인중/정지됨/전체정지 |
| DualBalanceView | 4 | 동기화/편차/로딩/오프라인 |
| NotificationBadge | 4 | 없음/소량/다량/드롭다운 |
| OrderBook | 5 | 기본/부분체결/전체취소/비어있음/실시간 |

### features (4개)

| 컴포넌트 | 스토리 수 | 핵심 상태 |
|---------|----------|----------|
| SignIn/SignUp | 10 | 빈 폼/유효/무효/서버에러/로딩 |
| CreateStrategy | 4 | MA/RSI/Bollinger/유효성에러 |
| EmergencyStop | 3 | 단일/전체/해제 |
| CancelOrder | 2 | 기본/확인모달 |

**전체: 25개 컴포넌트, 약 100개 스토리**
