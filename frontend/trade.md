# Trade - 프론트엔드 설계

> 거래소 연동, 실거래 집행 관리 및 비상 정지 제어 설계

---

## 1. 개요

사용자가 등록한 에이전트를 실제 거래소 계좌와 연결하여 매매를 수행하는 도메인입니다. 1개의 실계좌를 여러 가상 에이전트가 공유하여 자산을 효율적으로 배분하고 운영할 수 있습니다.

---

## 2. FSD 디렉토리 구조

(기존 구조 유지...)

---

## 3. 핵심 기능 설계

### 3.1 거래소 계정 및 에이전트 할당 (Allocation)

*   **Account-level Dashboard**: 등록된 실계좌별로 현재 어떤 에이전트들이 할당되어 있는지 트리(Tree) 구조로 표시한다.
*   **Asset Allocation UI**: 
    *   **Allocation Slider**: 계좌의 가용 잔고를 각 에이전트에게 % 또는 절대 금액으로 배분한다.
    *   **Dynamic Rebalancing**: 에이전트 가동 중에도 할당량을 조정할 수 있으나, 현재 포지션 평가액보다 낮은 할당은 차단한다.
    *   **Over-allocation Warning**: 할당량 합계가 100%를 초과할 경우 시각적 경고를 노출한다.
*   **Cascade Impact Policy**: 계좌 삭제 시 연결된 에이전트 일괄 `STOPPED` 처리 및 사전 경고 노출.

### 3.2 실거래 및 가상거래 제어 (Trade & Virtual)

*   **Environment Switcher**: `Real-mode`와 `Virtual-mode` 스위칭.
*   **Virtual Balance Management**: 가상 잔고 초기화 및 재설정 UI.
*   **비상 정지 (Emergency Stop)**: 
    *   전역 또는 에이전트별 비상 정지 버튼 제공.
    *   탭 동기화를 통한 즉각적인 UI 잠금.

### 3.3 실시간 주문 상태 및 잔고 트래킹

*   **Dual-Balance View**:
    *   **System View**: 에이전트 가상 장부 잔고.
    *   **Exchange View**: 거래소 실제 잔고.
    *   **Drift Indicator**: 두 잔고 간 오차 발생 시 대조(Reconciliation) 아이콘 노출.
*   **Execution Feedback**: 체결 진행률 프로그레스바 및 실패 사유 툴팁.

---

## 4. 데이터 일관성 및 운영 안정성

*   **Safety Lock**: 고지연(Latency > 1s) 또는 오프라인 시 주문 버튼 비활성화.
*   **Action Confirmation**: 실거래 주문 시 2중 확인 팝업 강제.
