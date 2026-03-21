# Trade Service — 비상 정지 및 주문 미체결 모니터링

> 이 문서는 `backend/trade/domain.md`에서 분할되었습니다.

---

## 6-1. 비상 정지 (Emergency Stop) 메커니즘

### 개요

실거래 중 예기치 않은 시장 상황(급등락, 전략 오작동, 시스템 이상)이 감지될 때
사용자 또는 관리자가 즉각적으로 거래를 중단할 수 있는 메커니즘이다.

### 비상 정지 발동 조건

| 발동 주체 | 방법 | 범위 |
|-----------|------|------|
| 사용자 | `PUT /trade-registrations/{id}/emergency-stop` | 특정 Registration |
| 관리자 | `POST /admin/trade-registrations/emergency-stop-all` | 전체 ACTIVE Registration |

### 비상 정지 처리 흐름

```
PUT /trade-registrations/{id}/emergency-stop 요청

1. TradeRegistration.emergencyStopped = true
2. TradeRegistration.status = PAUSED         (스케줄러 트리거 중단)
3. 미체결 주문 취소:
   FindOrderOutput.findAllByRegistrationIdAndActiveStatus(registrationIdentifier)
     └ status IN (PENDING, SUBMITTED, PARTIALLY_FILLED)
     └ 각 주문에 대해 CancelOrderOutput.cancel(CancelOrderCommand)
4. Notification 발행: "비상 정지 완료, {n}건 주문 취소 요청됨"
```

### 신호 처리 시 비상 정지 검증

`AnalyzeAgentReply` 수신 시 (HandleAgentReplyService):

```
1. TradeRegistration 조회 (agentIdentifier 기준)
2. registration.emergencyStopped == true → 처리 중단 (TR012 로그) + 알림 발송
3. registration.status != ACTIVE → 처리 중단 (로그)
4. 이하 정상 처리 흐름
```

### 비상 정지 해제

비상 정지 해제(`PUT /trade-registrations/{id}/emergency-resume`) 시:
- `emergencyStopped = false`
- `status = PAUSED` (자동으로 ACTIVE가 되지 않음)
- 사용자가 상황을 확인하고 직접 `activate()` 호출해야 재개됨

### trade_registration 테이블 스키마 추가

`## 8. DB 스키마` 섹션의 `trade_registration` 테이블에 `emergency_stopped` 컬럼 추가가 필요합니다.

---

## 6-2. 주문 미체결 모니터링

### 필수 메트릭

```
# 상태별 주문 수
trade_order_count{status}                           -- PENDING, SUBMITTED, PARTIALLY_FILLED 등

# 미체결 대기 시간 (SUBMITTED/PARTIALLY_FILLED 상태 주문의 경과 시간)
trade_order_pending_seconds{side, type, symbol}     -- Histogram

# 타임아웃 취소 건수
trade_order_timeout_cancelled_total{symbol}
```

### 알람 규칙

```
P1: 미체결 LIMIT 주문이 3개 이상 && 각 1시간 이상 미체결
P2: SUBMITTED 상태 주문 누적 20개 이상
P2: 타임아웃 취소 연속 5건 이상 (동일 심볼) → 전략 문제 가능성
```
