<!-- 원본: frontend/setup.md — 섹션 4~5 -->

# 다크/라이트 테마, CSS 토큰, 색상 정의

> Tailwind CSS 설정 및 디자인 시스템 색상 토큰

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
