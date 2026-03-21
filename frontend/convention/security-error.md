# 보안 / 에러 처리 컨벤션

> 원본: `frontend/convention.md` Section 9~10

---

## 9. 보안 컨벤션

### 9.1 인증 토큰 관리

| 토큰 종류 | 저장 위치 | 만료 시 처리 |
|-----------|-----------|-------------|
| Access Token (AT) | Zustand 메모리 | 401 응답 시 로그아웃 |
| Refresh Token (RT) | HttpOnly Cookie | 서버 발급, JS 접근 불가 |

### 9.2 환경 변수 노출 주의

```typescript
// ✅ VITE_로 시작하는 변수만 클라이언트에 노출됨
const apiUrl = import.meta.env.VITE_API_BASE_URL

// ❌ 비밀 키를 클라이언트 env에 절대 포함 금지
VITE_SECRET_KEY=...   // 클라이언트 번들에 포함되어 노출됨
```

### 9.3 XSS 방지

```typescript
// ✅ dangerouslySetInnerHTML 사용 시 반드시 DOMPurify 적용
import DOMPurify from 'dompurify'
<div dangerouslySetInnerHTML={{ __html: DOMPurify.sanitize(userInput) }} />

// ❌ 사용자 입력을 그대로 HTML에 삽입 금지
<div dangerouslySetInnerHTML={{ __html: userInput }} />
```

---

## 10. 에러 처리 컨벤션

### 10.1 API 응답 파싱 규칙

```typescript
// shared/utils/parse.ts
// ✅ safeParse: 개발 = console.error + throw, 프로덕션 = throw
// 향후 Sentry 도입 시 captureException 추가 예정
export const parseOrThrow = <T>(schema: ZodSchema<T>, raw: unknown): T => {
  const result = schema.safeParse(raw)
  if (result.success) return result.data

  if (import.meta.env.DEV) {
    console.error('[ParseError] API 응답 스키마 불일치:', result.error, '\nraw:', raw)
  }
  throw result.error   // 항상 throw (unsafe fallback 금지)
}

// ❌ 파싱 실패 시 raw를 그대로 반환하는 것 금지
return raw as T   // 타입 안전성 붕괴
```

### 10.2 컴포넌트 에러 처리

```typescript
// ✅ 페이지 단위 ErrorBoundary 적용
<ErrorBoundary fallback={<ErrorPage />}>
  <MarketCollectionPage />
</ErrorBoundary>

// ✅ TanStack Query 에러는 isError + error 상태로 처리
if (tasksQuery.isError) {
  return <ErrorState message={tasksQuery.error.message} />
}
```

### 10.3 async/await 에러 처리

```typescript
// ✅ mutation의 에러는 onError 콜백에서 처리
useMutation({
  mutationFn: resumeTask,
  onError: (error) => {
    toast.error(`재시작 실패: ${error.message}`)
  },
})

// ✅ 독립적인 async 함수는 try/catch 사용
// ❌ 컴포넌트 이벤트 핸들러에서 unhandled rejection 발생 금지
```

### 10.4 UI 피드백 선택 기준 (Error & Feedback)

에러의 성격과 심각도에 따라 사용자에게 알리는 방식을 통일합니다.

| 방식 | 사용 시점 | 예시 |
|------|-----------|------|
| **Toast** | 일시적인 알림, 성공 피드백, 배경 작업 결과 | "저장되었습니다", "수집이 시작되었습니다" |
| **Inline Alert** | 폼 입력 오류, 특정 영역의 로드 실패 | "이메일 형식이 올바르지 않습니다", "차트 로드 실패" |
| **Modal** | 사용자 확인이 필수적인 오류, 시스템 장애, 비가역적 액션 경고 | "잔액이 부족합니다", "로그인 세션 만료", "정말 삭제하시겠습니까?" |
| **Page Error** | 페이지 전체 진입 실패 (404, 403, 500) | "존재하지 않는 페이지입니다", "접근 권한이 없습니다" |
