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

### 3.2 Streaming POST 기반 SSE

백테스팅은 `POST /backtests` 호출 시 즉시 SSE 스트림으로 응답한다.
별도의 task ID 기반 재연결은 지원하지 않는다.

*   **실행 흐름**:
    1. 사용자가 설정 완료 후 "백테스트 시작" 클릭
    2. `POST /backtests` 호출 (Accept: text/event-stream)
    3. 응답을 Fetch API ReadableStream으로 수신하며 SSE 이벤트를 파싱
    4. 각 이벤트(signal, done, error)를 UI에 실시간 반영
    5. 컴포넌트 언마운트 시 `AbortController.abort()`로 스트림 중단

*   **구현 패턴**:
    ```typescript
    // entities/simulation/api/backtestApi.ts
    export async function* streamBacktest(
      config: RunBacktestCommand,
      signal: AbortSignal,
    ): AsyncGenerator<BacktestSignalResult> {
      const response = await fetch('/backtests', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Accept': 'text/event-stream' },
        body: JSON.stringify(config),
        signal,
      })

      const reader = response.body!.getReader()
      const decoder = new TextDecoder()

      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        const text = decoder.decode(value)
        for (const event of parseSSEEvents(text)) {
          if (event.type === 'done') return
          if (event.type === 'error') throw new BacktestError(event.data)
          yield parseOrThrow(BacktestSignalResultSchema, JSON.parse(event.data))
        }
      }
    }
    ```

*   **페이지 이탈 시 처리**:
    - `AbortController`로 Fetch 요청 취소 → 서버 측 gRPC 스트림도 자동 종료
    - 백테스팅 결과는 Agent Service에 저장되므로, 완료된 결과는 `GET /agents/{id}/backtests`로 조회 가능

*   **Background Notification**: 백테스팅이 완료되면 브라우저 알림 센터를 통해 "백테스팅 완료" 메시지를 띄워 사용자가 결과를 확인하도록 유도한다.

---

## 4. 성능 및 메모리 관리 (Memory Management) (기존 내용 유지)

수만 개의 백테스트 결과를 장시간 켜두어도 브라우저가 느려지지 않도록 관리한다.

*   **Chart Data Windowing**: 전체 신호 이력은 워커의 메모리에 보관하고, 메인 스레드의 차트에는 현재 뷰포트 영역의 데이터만 공급한다.
*   **Virtual Scroll**: 수천 건의 체결 내역 리스트는 `TanStack Virtual`을 사용하여 DOM 점유율을 최소화한다.
*   **리소스 해제**: 페이지 이탈(`unmount`) 시 `EventSource` 연결 해제 및 워커 종료를 강제하여 잔여 메모리를 정리한다.

---

## 5. UI/UX 포인트 (기존 내용 유지)
