# Agent & Strategy - 프론트엔드 설계

> 전략(Strategy) 관리, 에이전트(Agent) 설정 및 포트폴리오 모니터링 설계

---

## 1. 개요

사용자가 매매 전략을 정의하고, 이를 기반으로 구동되는 자동 매매 봇(에이전트)을 생성·관리하는 핵심 도메인입니다. 전략은 순수 신호 생성 로직을 담당하며, 에이전트는 해당 전략에 리스크 관리 설정과 자본을 결합하여 실제(또는 가상) 포트폴리오를 운용합니다.

---

## 2. FSD 디렉토리 구조

```text
src/
├── pages/
│   ├── strategy-lab/               # 전략 연구소 (전략 생성/수정)
│   ├── agent-desk/                 # 에이전트 데스크 (에이전트 목록/상세)
│   └── agent-setup/                # 에이전트 신규 설정 흐름
│
├── widgets/
│   ├── strategy-form/              # 전략 파라미터 입력 폼
│   ├── agent-card/                 # 에이전트 요약 카드
│   ├── portfolio-summary/          # 자산 현황 요약 (현금, 수익률)
│   └── decision-log-table/         # 전략 결정 감사 로그 테이블
│
├── features/
│   ├── create-strategy/            # 전략 생성 액션
│   ├── deploy-agent/               # 에이전트 활성화/중지 액션
│   └── analyze-decision/           # 감사 로그 상세 분석 팝업
│
└── entities/
    └── agent/                      # Agent 도메인 슬라이스
        ├── api/                    # strategyApi, agentApi
        ├── model/                  # schemas.ts (Strategy, Agent, Portfolio 등)
        └── queries/                # useStrategiesQuery, useAgentsQuery 등
```

---

## 3. 도메인 모델 & Zod 스키마

### 3.1 전략 (Strategy)

```typescript
// entities/agent/model/enums.ts
export enum StrategyStatus {
  DRAFT     = 'DRAFT',
  VALIDATED = 'VALIDATED',
  DEPRECATED = 'DEPRECATED',
}

// entities/agent/model/schemas.ts
export const StrategySchema = z.object({
  strategyIdentifier: z.string().uuid(),
  name:        z.string().min(1, '전략 이름을 입력해주세요.'),
  description: z.string().optional(),
  type:        z.enum(['MANUAL', 'AI']),
  status:      z.nativeEnum(StrategyStatus),
  parameters:  z.record(z.any()), // 전략 종류별 동적 파라미터
  createdDate: z.string().datetime(),
});

export type Strategy = z.infer<typeof StrategySchema>;
```

### 3.2 에이전트 (Agent)

```typescript
// entities/agent/model/schemas.ts
export const AgentSchema = z.object({
  agentIdentifier:    z.string().uuid(),
  name:               z.string(),
  strategyIdentifier: z.string().uuid(),
  status:         z.enum(['INACTIVE', 'ACTIVE', 'PAUSED', 'TERMINATED']),
  initialCapital: z.string(), // Decimal.js 처리를 위해 string 유지
  riskConfig:     z.object({
    positionSizeRatio:      z.number(),
    maxConcurrentPositions: z.number().int(),
    stopLossPercent:        z.number().nullable(),
    takeProfitPercent:      z.number().nullable(),
  }),
});

export type Agent = z.infer<typeof AgentSchema>;
```

---

## 4. 핵심 페이지 설계
### 4.1 전략 연구소 (Strategy Lab)

사용자가 지표 파라미터를 조합하여 자신만의 전략을 만드는 공간입니다.

*   **Schema-driven UI**: 
    *   백엔드 API(`GET /strategies/schemas`)로부터 수집한 JSON Schema를 기반으로 폼을 동적 생성한다.
    *   새로운 지표(예: MACD)가 추가되더라도 프론트엔드 코드 수정 없이 즉시 반영 가능하다.
*   **유효성 검사**: JSON Schema의 `minimum`, `maximum`, `pattern` 속성을 `react-hook-form`과 연동하여 실시간으로 검증한다.
*   **상태 관리**:
    *   `DRAFT`: 파라미터 수정 가능.
    *   `VALIDATED`: 백테스트 성공 후 실거래 사용 가능 상태.

---
### 4.2 에이전트 데스크 (Agent Desk)

운용 중인 봇들의 상태와 성과를 한눈에 모니터링합니다.

*   **결정 감사 로그 (Decision Audit Log)**:
    *   **Time-Travel Interaction**: 로그 테이블의 특정 행을 클릭하면 상단 차트의 크로스헤어가 해당 시각으로 자동 이동한다.
    *   **Contextual Overlay**: 차트 위에 해당 시점의 지표 값(RSI 등)과 신호 결정 근거(Reason)를 팝업 툴팁으로 표시한다.
*   **성과 지표**: (기존 내용 유지)


---

## 5. 주요 컴포넌트 & 훅

### 5.1 전략 실행기 팩토리 훅

전략 파라미터 타입에 따라 적절한 입력 UI를 렌더링하기 위한 로직입니다.

```typescript
// widgets/strategy-form/model/useStrategyParams.ts
const STRATEGY_TEMPLATES = {
  MA_CROSSOVER: {
    label: '이동평균선 골든/데드크로스',
    fields: ['shortPeriod', 'longPeriod', 'interval'],
  },
  RSI: {
    label: 'RSI 상대강도지수',
    fields: ['period', 'oversold', 'overbought', 'interval'],
  }
};
```

### 5.2 자산 점유(Reservation) 시각화

백엔드 설계의 핵심인 `reservedCash`와 `reservedQuantity`를 사용자에게 명확히 전달해야 합니다.

*   **가용 자산**: `cash - reservedCash`. 실제 주문 가능한 현금 (Decimal.js 연산).
*   **점유 중**: 현재 거래소에 주문이 나가서 체결 대기 중인 금액 (`reservedCash` 필드).
*   **UI 표현**: 자산 바 차트에서 '실제 잔고' 중 일부를 '주문 대기 중' 영역으로 별도 색상 처리.
*   **WebSocket 실시간 갱신**: `portfolio:{agentIdentifier}` 채널 구독으로 체결 시 즉시 반영.
    ```typescript
    // widgets/portfolio-summary/model/usePortfolioWebSocket.ts
    const queryClient = useQueryClient()
    useWebSocketSubscription(`portfolio:${agentIdentifier}`, (data) => {
      queryClient.setQueryData(['agents', agentIdentifier, 'portfolio'], data)
    })
    ```

---

## 6. 성능 및 UX 최적화

1.  **파라미터 프리셋**: 자주 사용하는 지표 설정을 저장하고 불러오는 기능 제공.
2.  **낙관적 상태 전환**: 에이전트 `Start/Pause` 버튼 클릭 시 API 응답 전 UI를 즉시 변경하고, 실패 시 롤백(TanStack Query `onMutate` 활용).
3.  **감사 로그 무한 스크롤**: 수천 건의 결정 로그를 효율적으로 조회하기 위해 `useInfiniteQuery`와 가상 스크롤 적용.

---

## 7. 차트 연동 (Decision Overlay)

캔들 차트 위에 에이전트의 결정 로그를 오버레이합니다.
*   **신호 마커**: BUY는 캔들 하단에 `▲`(stock-up 색상), SELL은 캔들 상단에 `▼`(stock-down 색상). 마커 크기는 confidence에 비례(8~16px).
*   **지표 오버레이**: 해당 전략이 사용 중인 지표(예: MA 선)를 차트에 함께 렌더링. 색상 규칙은 `convention.md` Section 32 참조.
*   **지표 최대 개수**: 캔들 차트 오버레이 최대 3개 + 하단 패널 최대 1개.
