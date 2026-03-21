# 개발 워크플로우

> 원본: `frontend/convention.md` Section 25 + 부록

---

## 25. 개발 워크플로우

> PR을 올리기 전 아래 4단계를 순서대로 완료해야 합니다.
> CI에서도 동일한 단계가 자동 실행되므로, 로컬에서 통과하지 못하면 CI도 실패합니다.

```
개발 → 테스트 코드 작성 → 린트 검증 → 코드 검증
```

---

### 25.1 개발

#### 시작 전 체크리스트

```
□ 브랜치를 develop에서 분기했는가?
  git checkout develop && git pull
  git checkout -b feat/TP-{번호}-{간략설명}

□ 구현할 컴포넌트가 shared/ui에 있는가?
  없으면 먼저 공통 컴포넌트를 만들고 시작

□ FSD 레이어 규칙을 확인했는가?
  구현 위치: pages / widgets / features / entities / shared 중 어디?
```

#### 개발 서버 실행

```bash
npm run dev          # Vite 개발 서버 (http://localhost:5173)
```

#### 새 기능 구현 순서

```
1. entities/   — 타입 정의, Zod 스키마, API 함수, Query 훅
2. features/   — mutation 훅, 비즈니스 로직
3. widgets/    — 재사용 UI 블록 (필요 시)
4. pages/      — model/ 훅으로 데이터 연결, ui/ 컴포넌트 조립
5. shared/ui/  — 신규 공통 컴포넌트 (필요 시 먼저 추가)
```

#### 개발 중 지켜야 할 규칙

```
□ 날 HTML 태그 대신 shared/ui 컴포넌트 사용 (Section 16)
□ 색상·간격은 Tailwind 토큰 사용, 하드코딩 금지 (Section 5, 18)
□ import 경로는 @shared / @entities 등 앨리어스 사용 (Section 3)
□ any 타입 사용 금지 — TypeScript 엄격 모드 (Section 4)
□ console.log 프로덕션 코드에 남기지 않기
```

---

### 25.2 테스트 코드 작성

#### 테스트 실행 명령어

```bash
npm run test           # vitest watch 모드 (개발 중 실시간)
npm run test:run       # 단일 실행 (CI용)
npm run test:coverage  # 커버리지 리포트 생성
```

#### 작성 대상 및 우선순위

| 우선순위 | 대상 | 예시 |
|---------|------|------|
| **필수** | `shared/utils/` 유틸 함수 | `formatPrice`, `formatRelativeTime`, `cn` |
| **필수** | `entities/*/model/` 파서·스키마 | Zod 스키마 검증, 파서 변환 |
| **권장** | `features/*/model/` 훅 비즈니스 로직 | mutation 성공·실패 케이스 |
| **선택** | `shared/ui/` 핵심 컴포넌트 | `Button` variant, `Badge` 렌더링 |

#### 테스트 작성 원칙

```typescript
// ✅ 테스트 파일은 대상 파일 옆에 위치
// shared/utils/formatPrice.ts
// shared/utils/formatPrice.test.ts

// ✅ 정상 케이스 + 엣지 케이스 + 경계값 모두 작성
describe('formatPrice', () => {
  // 정상
  it('천 단위 쉼표를 붙인다', () => {
    expect(formatPrice(1000000)).toBe('1,000,000')
  })
  // 엣지 케이스
  it('null이면 "-"를 반환한다', () => {
    expect(formatPrice(null)).toBe('-')
  })
  // 경계값
  it('0은 "0"을 반환한다', () => {
    expect(formatPrice(0)).toBe('0')
  })
})

// ✅ Zod 스키마 — 유효/무효 데이터 모두 검증
describe('MarketSymbolSchema', () => {
  it('올바른 데이터는 파싱에 성공한다', () => {
    const result = MarketSymbolSchema.safeParse(validFixture)
    expect(result.success).toBe(true)
  })
  it('identifier가 UUID 형식이 아니면 실패한다', () => {
    const result = MarketSymbolSchema.safeParse({ ...validFixture, identifier: 'not-uuid' })
    expect(result.success).toBe(false)
  })
})

// ❌ 구현 세부사항을 테스트하지 않음 (내부 상태, private 변수)
// ❌ 외부 API를 실제로 호출하는 테스트 금지 — msw로 모킹
```

#### 커버리지 기준

| 레이어 | 목표 | 미달 시 |
|--------|------|---------|
| `shared/utils` | 90% | PR 블로킹 |
| `entities/*/model` | 80% | PR 블로킹 |
| `features/*/model` | 70% | 경고 후 머지 가능 |
| `shared/ui` | 주요 컴포넌트 | 권장 |

---

### 25.3 린트 검증

#### 실행 명령어

```bash
npm run lint           # ESLint 검사
npm run lint:fix       # ESLint 자동 수정
npm run format         # Prettier 포맷팅 적용
npm run format:check   # Prettier 포맷팅 검사 (CI용)
```

#### package.json scripts 정의

```json
{
  "scripts": {
    "dev":            "vite",
    "build":          "tsc && vite build",
    "lint":           "eslint src --ext .ts,.tsx --report-unused-disable-directives",
    "lint:fix":       "eslint src --ext .ts,.tsx --fix",
    "format":         "prettier --write src",
    "format:check":   "prettier --check src",
    "test":           "vitest",
    "test:run":       "vitest run",
    "test:coverage":  "vitest run --coverage",
    "type-check":     "tsc --noEmit"
  }
}
```

#### 린트에서 반드시 통과해야 하는 규칙

```
□ @typescript-eslint/no-explicit-any    — any 사용 금지
□ @typescript-eslint/no-unused-vars     — 미사용 변수 금지
□ react-hooks/rules-of-hooks            — 훅 규칙 위반 금지
□ react-hooks/exhaustive-deps           — useEffect 의존성 누락 경고
□ import/no-cycle                        — 순환 의존성 금지
□ no-console                             — console.log 프로덕션 금지
```

#### 린트 오류 처리 원칙

```typescript
// ✅ 오류를 근본적으로 수정
const data: SymbolData = response.data   // any 대신 구체적 타입

// eslint-disable은 불가피한 경우에만, 이유를 반드시 주석으로 명시
// eslint-disable-next-line @typescript-eslint/no-explicit-any
const legacy: any = window.__LEGACY_DATA__   // 레거시 전역 변수 접근 불가피

// ❌ 이유 없는 eslint-disable 금지 — 코드 리뷰에서 반려
// eslint-disable-next-line @typescript-eslint/no-explicit-any
const foo: any = bar
```

---

### 25.4 코드 검증

#### 실행 명령어

```bash
npm run type-check     # TypeScript 타입 검사 (tsc --noEmit)
npm run build          # 프로덕션 빌드 검증 (tsc + vite build)
```

#### 타입 검사 원칙

```bash
# ✅ 타입 에러 0건 상태에서 PR 제출
npm run type-check
# Found 0 errors ← 이 상태여야 함

# 타입 에러 예시 및 수정 방향
# Error: Property 'identifier' does not exist on type 'MarketSymbol'
# → 타입 정의 확인, 'id' 대신 'identifier' 사용
```

#### 빌드 검증

```bash
npm run build
# ✅ dist/ 폴더 생성 및 경고 없이 완료되어야 함
# 번들 크기 경고(500kb 이상) 발생 시 코드 스플리팅 검토
```

#### PR 제출 전 최종 체크리스트

```
개발
□ 날 HTML 태그를 쓰지 않고 디자인 시스템 컴포넌트를 사용했는가?
□ 색상·간격에 하드코딩된 값이 없는가?
□ FSD 레이어 경계를 넘는 import가 없는가?
□ console.log가 남아 있지 않은가?
□ any 타입을 사용하지 않았는가?

테스트
□ 새로 추가한 유틸·파서에 테스트를 작성했는가?
□ npm run test:run 전체 통과했는가?
□ 커버리지 기준을 충족하는가?

린트
□ npm run lint 오류 0건인가?
□ npm run format:check 통과했는가?

코드 검증
□ npm run type-check 에러 0건인가?
□ npm run build 성공했는가?
□ 셀프 리뷰를 완료했는가? (변경된 파일 전체 diff 확인)
```

#### CI 파이프라인 구성 (참고)

```yaml
# .github/workflows/ci.yml (예시)
jobs:
  verify:
    steps:
      - run: npm run type-check   # 1. 타입 검사
      - run: npm run lint         # 2. 린트
      - run: npm run format:check # 3. 포맷 검사
      - run: npm run test:run     # 4. 테스트
      - run: npm run build        # 5. 빌드
```

> CI의 모든 단계는 로컬 명령어와 동일합니다.
> 로컬에서 전부 통과하면 CI도 통과합니다. CI에서만 실패하는 경우는 없어야 합니다.

---

## 부록 — 빠른 참조

### 자주 헷갈리는 필드명

| 잘못된 이름 | 올바른 이름 | 근거 |
|--------------|--------------|------|
| `id` | `identifier` | 백엔드 PK 필드명 통일 |
| `symbolId` | `symbolIdentifier` | FK도 동일 규칙 |
| `createdAt` | `createdDate` | 백엔드 네이밍 통일 |
| `lastCollectedAt` | `lastCollectedTime` | 백엔드 네이밍 통일 |
| `isActive` | `status === 'COLLECTING'` | 해당 필드 없음 |

### 존재하지 않는 Enum 값

| 잘못된 값 | 올바른 값 |
|-------------|------------|
| `'RUNNING'` | `'COLLECTING'` |
| `'ACTIVE'`  | `'COLLECTING'` |
| `'STOPPED'` | `'PAUSED'` |
