# Simulation - 프론트엔드 설계

> 과거 데이터를 활용한 전략 백테스팅 및 결과 시각화 설계

---

## 1. 개요

Simulation 서비스는 과거 캔들 데이터를 사용하여 특정 전략(Agent)의 성능을 검증합니다. 프론트엔드는 백테스팅 파라미터 설정, 실시간 진행률 표시(SSE), 그리고 최종 결과(수익률 곡선, MDD 등)의 시각화를 담당합니다.

---

## 2. FSD 디렉토리 구조

```text
src/
├── pages/
│   └── simulation-runner/          # 백테스트 실행 및 결과 페이지
│
├── widgets/
│   ├── backtest-config-panel/      # 기간, 자본금 등 설정 패널
│   ├── backtest-progress-bar/      # 실시간 진행률 (SSE 연동)
│   └── backtest-result-report/     # 수익률 곡선, 통계 지표 리포트
│
├── features/
│   ├── run-backtest/               # 백테스트 시작/중지 액션
│   └── export-backtest-result/     # 결과 CSV/PDF 내보내기
│
└── entities/
    └── simulation/                 # Simulation 도메인 슬라이스
        ├── api/                    # backtestApi (SSE 전용 함수 포함)
        ├── model/                  # schemas.ts (BacktestSignal, ResultStats 등)
        └── queries/                # useBacktestResultsQuery
```

---

## 3. 핵심 기능 설계

### 3.1 백테스트 설정 (Config)

사용자가 백테스트를 수행할 환경을 정의합니다.
*   **대상 에이전트 선택**: `entities/agent`에서 관리되는 에이전트 목록 중 선택.
*   **심볼 및 기간**: 특정 거래 심볼과 과거 날짜 범위(`from`, `to`) 선택.
*   **초기 자본금**: 에이전트 설정값을 기본으로 하되, 시뮬레이션 시 일시적 변경 가능.

### 3.2 비동기 작업 추적 및 SSE 합류 (Task-based SSE)

백테스팅은 백그라운드에서 실행되므로, 사용자가 페이지를 새로고침하거나 나중에 다시 진입해도 진행 상황을 복구할 수 있어야 한다. SSE 처리 방식은 `convention.md` 11.5절의 표준을 따른다.

*   **Task Persistence**: 백테스팅 시작 시 발급받은 `taskId`를 Zustand 또는 URL 파라미터에 저장한다.
*   **Resume Flow (useSSE Hook)**: 
    1. 페이지 진입 시 실행 중인 `taskId`가 있는지 확인한다.
    2. 있다면 `GET /backtests/{taskId}/stream`에 연결하여 실시간 데이터를 수신한다.
    3. 컴포넌트 언마운트 시 반드시 `eventSource.close()`를 실행한다.
*   **Background Notification**: 백테스팅이 완료되면 브라우저 알림 센터를 통해 "백테스팅 완료" 메시지를 띄워 사용자가 결과를 확인하도록 유도한다.

---

## 4. 성능 및 메모리 관리 (Memory Management) (기존 내용 유지)

수만 개의 백테스트 결과를 장시간 켜두어도 브라우저가 느려지지 않도록 관리한다.

*   **Chart Data Windowing**: 전체 신호 이력은 워커의 메모리에 보관하고, 메인 스레드의 차트에는 현재 뷰포트 영역의 데이터만 공급한다.
*   **Virtual Scroll**: 수천 건의 체결 내역 리스트는 `TanStack Virtual`을 사용하여 DOM 점유율을 최소화한다.
*   **리소스 해제**: 페이지 이탈(`unmount`) 시 `EventSource` 연결 해제 및 워커 종료를 강제하여 잔여 메모리를 정리한다.

---

## 5. UI/UX 포인트 (기존 내용 유지)
