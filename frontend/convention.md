# Frontend Convention — Trade Pilot

> 이 문서는 Trade Pilot 프론트엔드 전체에 적용되는 코드 컨벤션을 정의합니다.
> 새 기능 추가/코드 리뷰/온보딩 시 이 문서를 기준으로 삼습니다.
>
> 이 문서는 목차 역할을 합니다. 상세 내용은 `convention/` 하위 파일을 참조하세요.

---

## 목차

| 파일 | 섹션 | 설명 |
|------|------|------|
| [architecture.md](convention/architecture.md) | 1~3 | FSD 레이어, 디렉토리 네이밍, Import 규칙 |
| [typescript.md](convention/typescript.md) | 4 | TypeScript 타입 컨벤션 (Zod, Enum, PK, 날짜) |
| [styling.md](convention/styling.md) | 5 | Tailwind CSS 토큰 (색상, 다크모드, 주식색상, Safe Area) |
| [components.md](convention/components.md) | 6 | 컴포넌트 작성 규칙 (memo, Router, 핸들러, 폼) |
| [state-management.md](convention/state-management.md) | 7~8 | Zustand, TanStack Query |
| [security-error.md](convention/security-error.md) | 9~10 | 보안, 에러 처리 |
| [performance.md](convention/performance.md) | 11 | 성능 최적화 (Web Worker, SSE, 디바운스) |
| [testing-style.md](convention/testing-style.md) | 12~15 | 테스트, 환경변수, ESLint/Prettier, Git |
| [design-system.md](convention/design-system.md) | 16~24 | 디자인 시스템, 타이포, 스페이싱, 반응형, z-index, 레이아웃, 아이콘 |
| [workflow.md](convention/workflow.md) | 25 + 부록 | 개발 워크플로우, 빠른 참조 |
| [api-financial.md](convention/api-financial.md) | 26~28 | API 에러, 금융 데이터, 시간대 |
| [realtime-network.md](convention/realtime-network.md) | 29~30 | WebSocket 동기화, 네트워크 장애 |
| [responsive-chart.md](convention/responsive-chart.md) | 31~32 | 반응형 브레이크포인트, 차트 오버레이 |
