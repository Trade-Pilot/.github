<!-- 원본: frontend/setup.md — 섹션 2 (디렉토리 구조) -->

# FSD 디렉토리 구조

> Trade Pilot 프론트엔드 Feature-Sliced Design 기반 디렉토리 구조

---

## 디렉토리 구조

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
