<!-- 원본: frontend/setup.md — 섹션 1~3 -->

# 프로젝트 생성, 의존성, 환경 변수

> Trade Pilot 프론트엔드 초기 프로젝트 생성 및 기본 설정

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

## 2. 환경 변수 (`.env`)

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
