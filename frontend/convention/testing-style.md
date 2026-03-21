# 테스트, 환경변수, ESLint/Prettier, Git 컨벤션

> 원본: `frontend/convention.md` Section 12~15

---

## 12. 테스트 컨벤션

### 12.1 테스트 파일 위치

```
src/
└── shared/
    └── utils/
        ├── cn.ts
        └── cn.test.ts     # 테스트 파일은 대상 파일 옆에 위치
```

### 12.2 테스트 명명 규칙

```typescript
// vitest 사용
describe('formatPrice', () => {
  it('1000 이상은 쉼표 구분자 포함', () => {
    expect(formatPrice(1000000)).toBe('1,000,000')
  })

  it('null 입력 시 "-" 반환', () => {
    expect(formatPrice(null)).toBe('-')
  })
})
```

### 12.3 vitest 경로 앨리어스

```typescript
// vitest.config.ts — vite.config.ts와 동일한 앨리어스 6개 모두 등록
resolve: {
  alias: {
    '@app':      resolve(__dirname, 'src/app'),
    '@pages':    resolve(__dirname, 'src/pages'),
    '@widgets':  resolve(__dirname, 'src/widgets'),
    '@features': resolve(__dirname, 'src/features'),
    '@entities': resolve(__dirname, 'src/entities'),
    '@shared':   resolve(__dirname, 'src/shared'),
  },
}
```

### 12.4 테스트 커버리지 기준

| 레이어 | 목표 커버리지 | 우선 대상 |
|--------|-------------|-----------|
| `shared/utils` | 90% 이상 | formatPrice, formatRelativeTime, cn |
| `entities/*/model` | 80% 이상 | 파서, Zod 스키마 |
| `features/*/model` | 70% 이상 | mutation 훅, 비즈니스 로직 |
| `shared/ui` | 주요 컴포넌트 | Button, Badge, Toggle |

### 12.5 시각적 회귀 테스트 (Visual Regression)

UI 컴포넌트의 의도치 않은 스타일 변화를 방지합니다.

*   **Loki**: 로컬 환경에서 스토리북과 연동하여 스냅샷 비교.
*   **Chromatic**: CI 환경에서 PR별 UI 변경 내역 리뷰 및 승인.
*   **수행 시점**: `shared/ui` 컴포넌트 수정 시 반드시 로컬에서 `npm run test:visual` 실행 후 스냅샷 갱신.

### 12.6 도메인별 테스트 시나리오 예시

*   **Happy Path**: "정상적인 입력 시 에이전트가 성공적으로 생성되어 목록으로 이동한다."
*   **Error Case**: "API 서버가 500 에러를 반환할 경우, Modal 에러 팝업을 띄우고 폼 데이터를 유지한다."
*   **Edge Case**: "시세 데이터가 10초 이상 중단될 경우, 차트를 회색조로 변경하고 경고 오버레이를 표시한다."

---

## 13. 환경 변수 규칙

```bash
# .env.local (git에 커밋하지 않음)
VITE_API_BASE_URL=http://localhost:8080
VITE_WS_BASE_URL=ws://localhost:8080

# .env.example (git에 커밋, 실제 값 제외)
VITE_API_BASE_URL=
VITE_WS_BASE_URL=
```

```typescript
// shared/config/env.ts — 접근 일원화 + 타입 보장
export const env = {
  apiBaseUrl: import.meta.env.VITE_API_BASE_URL as string,
  wsBaseUrl:  import.meta.env.VITE_WS_BASE_URL  as string,
}

// ✅ 컴포넌트에서 직접 import.meta.env 접근 금지
// import { env } from '@shared/config/env' 로 통일
```

### 13.2 i18n 키 네이밍 컨벤션

`i18next` 사용 시 번역 키는 하이브리드 계층 구조(공통/페이지)를 따릅니다.

*   **구조**: `[namespace].[scope].[component].[element]`
*   **공통 키 (`common`)**: 여러 페이지에서 재사용되는 단어/문구
    *   `common.button.save`, `common.label.confirm`, `common.status.success`
*   **페이지 전용 키 (`pages`)**: 특정 페이지에서만 사용되는 문구
    *   `pages.market.chart.title`, `pages.agent.setup.description`
*   **변수 삽입 (Interpolation)**: `{{ }}`를 사용
    *   `msg.error.retry`: "오류 발생 (재시도 {{count}}회)"

---

## 14. 코드 스타일 (ESLint / Prettier)

### 14.1 Prettier 설정

```json
// .prettierrc
{
  "semi": false,
  "singleQuote": true,
  "trailingComma": "es5",
  "printWidth": 100,
  "tabWidth": 2,
  "plugins": ["prettier-plugin-tailwindcss"]
}
```

> `prettier-plugin-tailwindcss`: Tailwind 클래스를 자동으로 권장 순서로 정렬합니다.

### 14.2 ESLint 핵심 규칙

```json
{
  "rules": {
    "react-hooks/rules-of-hooks":  "error",    // 훅 규칙 강제
    "react-hooks/exhaustive-deps": "warn",     // useEffect 의존성 경고
    "@typescript-eslint/no-explicit-any": "error",   // any 금지
    "@typescript-eslint/no-unused-vars":  "error",   // 미사용 변수 금지
    "import/no-cycle": "error"                 // 순환 의존성 금지 (FSD 위반 감지)
  }
}
```

### 14.3 금지 패턴

```typescript
// ❌ any 사용 금지 — unknown 또는 구체적 타입 사용
const data: any = response.data

// ✅ 대안
const data: unknown = response.data
const result = schema.parse(data)    // Zod로 타입 좁히기

// ❌ console.log 프로덕션 코드에 남기지 않음 (eslint no-console)
console.log('debug:', task)

// ✅ 디버깅 후 반드시 제거 (프로덕션 빌드 전 ESLint no-console으로 확인)
// 향후 모니터링 도구 도입 시 console.log 대신 전용 logger 유틸로 교체 예정
```

---

## 15. Git / 커밋 컨벤션

### 15.1 브랜치 네이밍

```
main          # 배포 브랜치 (직접 push 금지)
develop       # 통합 개발 브랜치
feat/<ticket>-<desc>    # 기능 개발
fix/<ticket>-<desc>     # 버그 수정
refactor/<desc>         # 리팩토링
chore/<desc>            # 빌드/설정 변경
```

예시:
```
feat/TP-42-candle-chart-widget
fix/TP-101-ws-reconnect
refactor/auth-store-security
```

### 15.2 커밋 메시지 — Conventional Commits

```
<type>(<scope>): <subject>

[body]

[footer]
```

| type | 용도 |
|------|------|
| `feat` | 새 기능 |
| `fix` | 버그 수정 |
| `refactor` | 기능 변화 없는 코드 개선 |
| `style` | 포맷팅 (로직 변화 없음) |
| `test` | 테스트 추가·수정 |
| `chore` | 빌드·설정·패키지 변경 |
| `docs` | 문서 수정 |
| `perf` | 성능 개선 |

예시:
```
feat(chart): add Korean stock color convention to CandleChart

upColor/downColor을 한국 주식 컨벤션(빨강=상승, 파랑=하락)으로 변경
Lightweight Charts의 기본값(서양 컨벤션)과 반대이므로 명시적 설정 필수

Closes #42
```

### 15.3 PR 규칙

- 하나의 PR = 하나의 기능/수정 (범위 최소화)
- 셀프 리뷰 후 팀원 1인 이상 리뷰 승인 필요
- `main` 브랜치에 직접 push 금지 — PR + CI 통과 후 머지
- 스쿼시 머지 권장 (커밋 히스토리 단순화)
