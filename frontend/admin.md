# Admin - 프론트엔드 설계

> 시스템 운영, 모니터링 및 전역 제어를 위한 관리자 전용 설계

---

## 1. 개요

시스템 관리자가 전체 서비스의 상태를 파악하고, 이상 징후 발생 시 즉각적인 조치(전체 비상 정지, 수집 강제 재시작 등)를 취할 수 있는 관제 센터입니다.

---

## 2. 핵심 기능 설계

### 2.1 시스템 헬스 보드 (System Health)
*   **Service Status**: 각 마이크로서비스(User, Market, Agent 등)의 생존 여부 및 gRPC/Kafka 연결 상태 시각화.
*   **Circuit Breaker Monitor**: 현재 오픈된 서킷 브레이커 목록 및 실시간 에러율 그래프 노출.
*   **Kafka Lag Monitor**: 주요 토픽의 컨슈머 랙(Lag) 상태를 모니터링하여 병목 지점 파악.

### 2.2 운영 장애 복구 (Incident Recovery)
*   **Dead Letter Queue (DLQ) 관리**: 
    *   `processed_events` 실패 이력 및 Outbox `DEAD` 레코드 목록 조회.
    *   **Manual Retry**: 특정 메시지를 선택하여 강제로 재발행하거나 상태를 복구하는 기능.
*   **Emergency stop-all**: 전 서비스의 실거래 등록을 일괄 `PAUSED` 처리하고 모든 주문을 취소하는 강력한 제어 버튼.

### 2.3 데이터 수집 관제 (Market Admin)
*   **Sharding Status**: 현재 수집 워커(Pod)별로 할당된 심볼 수와 부하 분산 상태 확인.
*   **Force Collect**: 특정 심볼이나 기간에 대해 수집 스케줄러와 무관하게 즉시 수집을 명령하는 기능.

### 2.3.1 Force Collect 모달

특정 심볼에 대해 수집 스케줄러와 무관하게 즉시 수집을 명령한다.

*   **UI 컴포넌트**: `features/force-collect/ui/ForceCollectModal.tsx`
*   **흐름**:
    1. "즉시 수집" 버튼 클릭 → 모달 오픈
    2. 대상 심볼 선택 (검색 가능 드롭다운, 복수 선택)
    3. "수집 시작" 클릭 → `POST /market-symbols/collect` 호출 (202 Accepted)
    4. 토스트: "수집이 시작되었습니다. 완료 시 알림을 받습니다."
    5. 수집 완료/실패 시 Notification 알림으로 결과 수신

### 2.4 감사 로그 (Audit Log)

관리자가 수행한 모든 제어 액션 이력을 조회한다.

*   **UI 컴포넌트**: `widgets/audit-log-table/ui/AuditLogTable.tsx`
*   **컬럼**:
    | 컬럼 | 타입 | 설명 |
    |------|------|------|
    | 시각 | datetime | 액션 실행 시각 (KST) |
    | 관리자 | string | 실행한 관리자 이름 |
    | 액션 | badge | EMERGENCY_STOP, MANUAL_RETRY, FORCE_COLLECT 등 |
    | 대상 | string | 에이전트/심볼/주문 식별자 |
    | 결과 | badge | SUCCESS, FAILED, IN_PROGRESS |
    | Correlation ID | link | 분산 트레이싱 연결 |
*   **필터**: 기간, 액션 타입, 결과 상태
*   **페이지네이션**: TanStack Query `useInfiniteQuery` + 가상 스크롤

---

## 3. UI/UX 제어

*   **Role-based Access**: `PermissionGate`를 통해 `ADMIN` 권한자에게만 메뉴 노출.
*   **Action Log**: 관리자가 수행한 모든 제어 액션(비상 정지, DLQ 재시도 등)은 별도의 감사 로그(Audit Log)로 기록 및 조회 가능. 모든 액션에는 추적을 위한 고유 식별자(Correlation Identifier)가 부여된다.
*   **Destructive Action Guard**: "전체 비상 정지"와 같은 파괴적인 액션은 반드시 2단계 확인(비밀번호 재입력 등)을 거치도록 설계.

---

## 4. FSD 디렉토리 구조

```text
src/
├── pages/
│   └── admin-dashboard/            # 관리자 메인 관제 페이지
│
├── widgets/
│   ├── service-health-grid/        # 서비스별 상태 카드 그리드
│   ├── outbox-dead-table/          # Outbox DEAD 레코드 관리 테이블
│   └── worker-load-chart/          # 수집 워커 부하 차트
│
├── features/
│   ├── retry-outbox-message/       # DEAD 레코드 재시도 액션
│   └── global-emergency-stop/      # 시스템 전체 비상 정지 기능
│
└── entities/
    └── admin/                      # Admin 전용 도메인 (Health, Metrics 등)
```
