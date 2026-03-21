# Tailwind / CSS 토큰 컨벤션

> 원본: `frontend/convention.md` Section 5

---

## 5. Tailwind / CSS 토큰 컨벤션

### 5.1 색상 — 반드시 토큰 사용

```typescript
// ✅ 시맨틱 토큰 사용
className="bg-semantic-danger/10 text-semantic-danger"
className="bg-bg-surface border-border text-text-primary"

// ❌ 하드코딩 금지
className="bg-red-500 text-white"
className="bg-[#F04452]"
```

| 카테고리 | 토큰 접두사 | 예시 |
|----------|------------|------|
| 배경 | `bg-bg-*` | `bg-base`, `bg-surface`, `bg-elevated` |
| 텍스트 | `text-text-*` | `text-primary`, `text-secondary`, `text-tertiary` |
| 테두리 | `border-border*` | `border-border`, `border-border-strong` |
| 브랜드 | `bg-brand-*` | `bg-brand-500`, `text-brand-400` |
| 시맨틱 | `bg-semantic-*` | `bg-semantic-success`, `text-semantic-danger` |

### 5.2 투명도 수식어 (Opacity Modifier)

`semantic-*` 색상은 CSS 변수 기반(공백 분리 RGB)으로 정의되어 투명도 수식어를 지원합니다.

```typescript
// ✅ 투명도 수식어 사용 가능
className="bg-semantic-danger/10"      // rgba(220, 38, 38, 0.10)
className="bg-semantic-success/15"
className="text-semantic-info/60"

// ❌ hex 직접 정의 시 투명도 수식어 불가
// semantic-* 토큰을 hex로 재정의하지 않도록 주의
```

### 5.3 다크 모드

`darkMode: 'class'`를 사용합니다. `<html class="dark">` 전환으로 테마가 적용됩니다.

```typescript
// ✅ 토큰이 다크 모드를 자동 처리
className="bg-bg-surface text-text-primary"

// ✅ 토큰으로 처리 안 되는 값만 dark: 수식어 사용
className="bg-white dark:bg-slate-900"

// ❌ dark: 수식어로 색상 토큰 덮어쓰기 금지 (토큰이 이미 처리)
className="bg-bg-surface dark:bg-[#1C1B2E]"
```

### 5.4 boxShadow 'panel'

```typescript
// ✅ 토큰 사용 — CSS 변수 기반
className="shadow-panel"

// ❌ 직접 정의 금지 (하드코딩 hex는 테마 전환 불가)
// style={{ boxShadow: 'rgba(255,255,255,0.06) ...' }}
```

### 5.5 한국 주식 색상 컨벤션

> **주의**: 한국 주식 컨벤션은 미국/서양과 반대입니다.

| 의미 | 색상 | 토큰 |
|------|------|------|
| 상승 (양봉) | **빨강** `#F04452` | `stock-up` |
| 하락 (음봉) | **파랑** `#4066E4` | `stock-down` |

```typescript
// Lightweight Charts 설정 — 반드시 한국 컨벤션 유지
const candleSeries = chart.addCandlestickSeries({
  upColor:         '#F04452',   // 상승 = 빨강
  downColor:       '#4066E4',   // 하락 = 파랑
  borderUpColor:   '#F04452',
  borderDownColor: '#4066E4',
  wickUpColor:     '#F04452',
  wickDownColor:   '#4066E4',
})
```

### 5.6 Safe Area (iOS)

```html
<!-- index.html — viewport-fit=cover 필수 -->
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover" />
```

```typescript
// ✅ Safe Area 처리는 BottomTabBar 한 곳에서만
// body에 padding-bottom 추가 금지 (이중 패딩 발생)
className="pb-[env(safe-area-inset-bottom)]"   // BottomTabBar에서만
```

### 5.7 cn() 유틸리티

조건부 클래스 조합 시 반드시 `cn()` 사용합니다.

```typescript
// shared/utils/cn.ts
import { clsx } from 'clsx'
import { twMerge } from 'tailwind-merge'

export const cn = (...inputs: ClassValue[]) => twMerge(clsx(inputs))

// ✅ 사용
className={cn(
  'base-class',
  isActive && 'active-class',
  variant === 'danger' && 'danger-class',
)}

// ❌ 문자열 연결 금지
className={'base-class ' + (isActive ? 'active-class' : '')}
```
