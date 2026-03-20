# Frontend Architecture - Trade Pilot

> Trade Pilot 프론트엔드 전체 시스템의 아키텍처 마스터플랜입니다.
> 전문가용 트레이딩 터미널 수준의 안정성, 정밀도, 성능을 목표로 합니다.

---

## 1. 아키텍처 목표 (Enterprise-Grade)

1.  **데이터 무결성과 정밀도**: 금융 데이터 오차 방지 및 KST/UTC 정밀 변환.
2.  **초고성능 렌더링**: Web Worker 기반 데이터 가공으로 메인 스레드 부하 최소화.
3.  **무중단 운영 안정성**: 탭 간 상태 동기화 및 네트워크 지연(Latency) 가시화.
4.  **유연한 확장성**: Schema-driven UI를 통한 동적 전략 파라미터 대응.

---

## 2. 코어 기술 스택 (고도화 반영)

| 영역 | 기술 | 채택 사유 |
|------|------|----------|
| **코어** | React 18, TypeScript 5, Vite | 빠르고 안정적인 SPA 렌더링 및 빌드. |
| **아키텍처** | **FSD (Feature-Sliced Design)** | 도메인과 UI 레이어의 명확한 분리를 통한 높은 유지보수성. |
| **상태 동기화** | **BroadcastChannel API** | 멀티 탭/윈도우 간 비상 정지 및 인증 상태 즉시 동기화. |
| **서버 상태** | TanStack Query v5 | API 캐싱, 무한 스크롤, 낙관적 업데이트 자동화. |
| **클라이언트 상태**| Zustand | 가벼운 보일러플레이트, React 외부 상태 접근 용이. |
| **동적 UI** | **JSON Schema + React Hook Form** | 백엔드 정의 스키마 기반의 전략 파라미터 폼 자동 생성. |
| **성능 최적화** | **Web Worker** | 모든 실시간 데이터(시세, 시뮬레이션) 파싱 및 지표 계산 분리. |
| **금융 연산** | Decimal.js, Day.js | 부동소수점 오차 없는 정밀한 자산 가치 계산 및 시간대 처리. |
| **차트** | Lightweight Charts | TradingView의 고성능 HTML5 캔버스 차트. |

---

## 3. FSD (Feature-Sliced Design) 도메인 매핑

```text
src/
├── app/          # 전역 설정 (Router, Providers, 글로벌 스타일)
├── pages/        # 라우트 단위의 진입점 (UI 조합 및 페이지 전용 훅)
├── widgets/      # 독립적인 재사용 블록 (예: CandleChart, AgentDashboard)
├── features/     # 특정 비즈니스 액션 (예: StartCollectTask, CreateAgent)
├── entities/     # 도메인 모델, Zod 스키마, API, Query 훅 (순수 데이터)
└── shared/       # 도메인 독립 공용 레이어 (UI, 유틸, axios 인스턴스)
```

### 3.1 Entities 매핑 (백엔드 서비스 대응)
*   `entities/user`: 인증, 세션, 권한 관리, 사용자 설정(Preferences).
*   `entities/market`: 심볼, 캔들 데이터, 수집 작업 상태.
*   `entities/agent`: 전략(Strategy), 에이전트, 포트폴리오, 시그널, 결정 감사 로그.
*   `entities/simulation`: 백테스트 설정 및 결과, 스트리밍(SSE) 진행률.
*   `entities/trade`: 거래소 계정, 실거래/가상거래 활성화, 주문 및 체결 내역.
*   `entities/notification`: 시스템 알림 내역, 외부 채널 설정.

---

## 4. 실시간성 및 신뢰성 정책

### 4.1 네트워크 지연(Latency) 및 오프라인 대응
*   **Latency 모니터링**: 서버 응답 시각과 현재 시각의 차이를 ms 단위로 상시 노출.
*   **Stale Data 경고**: 10초 경과 또는 네트워크 단절 시 UI 전체 Grayscale 처리 및 경고 노출.
*   **주문 차단**: 심각한 Latency 발생 시 실거래 주문 버튼 비활성화.

### 4.2 멀티 탭 상태 동기화 (Cross-tab Sync)
*   `BroadcastChannel`을 활용하여 `AUTH_LOGOUT`, `EMERGENCY_STOP`, `AGENT_UPDATE` 이벤트를 모든 탭에 전파.

---

## 5. 성능 및 글로벌 정책

### 5.1 Web Worker 데이터 파이프라인
*   **Sequence Guarantee**: `timestamp` 또는 `sequence`를 검증하여 데이터 역전 현상 방지.
*   **Interest-based Dispatcher**: 워커는 단일 웹소켓으로 모든 데이터를 받지만, 메인 스레드로는 컴포넌트가 구독한 토픽만 전송한다.
*   **Adaptive UI**: 프레임 레이트 저하 감지 시 차트 애니메이션 자동 하향 조정.

### 5.2 다국어 및 글로벌 표준
*   **i18next**: 다국어 키 관리.
*   **Chart Theme**: 지역 설정에 따른 상승/하락 컬러셋 토글 (KR: Red/Blue, US: Green/Red).

---

## 6. 장기 운용 및 메모리 정책

### 6.1 좀비 프로세스 방지
*   **Heartbeat Check**: 메인 스레드와 워커 간 30초마다 생존 확인.
*   **Explicit Cleanup**: 언마운트 시 리스너 해제, 차트 `destroy()`, 워커 `terminate()` 필수.

### 6.2 데이터 프리패칭
*   **Hover Prefetch**: 목록 호버 시 관련 API 미리 호출하여 체감 전환 속도 0ms 달성.

---

## 7. 요청 추적성 및 보안

### 7.1 전 구간 추적 (E2E Traceability)
*   **Correlation ID**: 모든 UI 액션 시 고유 ID 생성하여 `X-Frontend-Correlation-ID` 헤더에 부착.

### 7.2 보안 및 인증 흐름
*   **Access Token**: 메모리(Zustand) 보관.
*   **Refresh Token**: HttpOnly Cookie 보관.
*   **Standard Error Schema**: 모든 API는 `ApiErrorResponse` 표준 구조를 준수한다.
