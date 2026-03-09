# 실거래 (Real Trading)

> 💸 실제 자금 거래 실행 기능

---

## 개요

### 목적
검증된 전략을 실제 자금으로 거래하여 수익을 창출합니다.

### 핵심 가치
- **안전 제일**: 철저한 검증 후에만 실거래 허용
- **점진적 투입**: 소액부터 시작하여 단계적 확대
- **엄격한 리스크 관리**: 손실 한도 필수 준수
- **투명한 기록**: 모든 거래 로그 무결성 보장

### ⚠️ 중요 주의사항
```
실거래는 실제 자금 손실 위험이 있습니다.

필수 선행 조건:
  1. 백테스팅 승률 > 60%
  2. 가상거래 1개월 이상 검증
  3. 월평균 수익률 > 3%
  4. MDD < 15%
  5. 손실 한도 위반 0건
  6. 보안 감사 통과
  7. 법률 및 세무 자문 완료

위 조건을 모두 충족해야만 실거래를 시작할 수 있습니다.
```

---

## 주요 기능

### 1. 실계좌 연동
```
기능: 거래소 실계좌 API 연동
거래소: 업비트 (Phase 4)
확장: 바이낸스, 코인원 (Phase 5)
```

**연동 프로세스**:
```
1. API 키 발급 (거래소)
2. API 키 암호화 저장 (AES-256)
3. Kubernetes Secret 관리
4. 환경 변수 주입
5. 연결 테스트
6. 권한 확인 (거래 권한만, 출금 권한 제외)
7. IP 화이트리스트 설정
8. 2FA 활성화 확인
```

### 2. 실주문 실행
```
기능: 실제 거래소에 주문 전송
타입: 시장가, 지정가
```

**주문 실행 프로세스**:
```
1. 전략에서 신호 생성 (BUY/SELL)
2. 주문 크기 계산
3. 리스크 검증
   - 포지션 크기 제한 확인
   - 일일 손실 한도 확인
   - 자금 충분성 확인
4. 주문 생성
5. 거래소 API 호출
6. 주문 체결 대기
7. 체결 확인
8. 포트폴리오 업데이트
9. 거래 내역 기록 (감사 로그)
10. Slack 알림 발송
```

**주문 실행 코드**:
```kotlin
fun executeRealOrder(signal: Signal): OrderResult {
    // 1. 리스크 검증
    val riskCheck = validateRisk(signal)
    if (!riskCheck.passed) {
        return OrderResult.REJECTED(riskCheck.reason)
    }

    // 2. 주문 크기 계산
    val orderSize = calculateOrderSize(signal)

    // 3. 거래소 주문 실행
    val order = when (signal.type) {
        SignalType.BUY -> {
            upbitApiClient.buyMarketOrder(
                market = signal.symbolCode,
                price = orderSize * signal.price
            )
        }
        SignalType.SELL -> {
            upbitApiClient.sellMarketOrder(
                market = signal.symbolCode,
                volume = orderSize
            )
        }
        else -> return OrderResult.SKIPPED
    }

    // 4. 체결 확인
    val filled = waitForFill(order.uuid, timeout = 30.seconds)
    if (!filled.success) {
        return OrderResult.FAILED(filled.reason)
    }

    // 5. 포트폴리오 업데이트
    updatePortfolio(filled)

    // 6. 거래 로그 기록
    auditLog.record(filled)

    // 7. 알림
    slackNotifier.send("주문 체결: ${signal.type} ${orderSize} @ ${filled.price}")

    return OrderResult.SUCCESS(filled)
}
```

### 3. 리스크 관리 강화

#### 실계좌 손실 한도
```kotlin
data class RealTradeLossLimit(
    val dailyLossLimit: BigDecimal = BigDecimal("3"),   // 3%
    val weeklyLossLimit: BigDecimal = BigDecimal("7"),  // 7%
    val monthlyLossLimit: BigDecimal = BigDecimal("15") // 15%
)

fun checkLossLimit(): LossLimitStatus {
    val dailyLoss = calculateTodayLoss()
    val weeklyLoss = calculateWeeklyLoss()
    val monthlyLoss = calculateMonthlyLoss()

    return when {
        dailyLoss >= 3.0 -> {
            account.pause()
            LossLimitStatus.DAILY_EXCEEDED
        }
        weeklyLoss >= 7.0 -> {
            account.pause()
            LossLimitStatus.WEEKLY_EXCEEDED
        }
        monthlyLoss >= 15.0 -> {
            account.stop()
            LossLimitStatus.MONTHLY_EXCEEDED
        }
        else -> LossLimitStatus.SAFE
    }
}
```

#### 강제 청산 시스템
```kotlin
fun emergencyLiquidation() {
    // 긴급 전량 청산
    val positions = realAccount.getPositions()

    positions.forEach { position ->
        try {
            // 시장가로 즉시 전량 매도
            upbitApiClient.sellMarketOrder(
                market = position.symbol,
                volume = position.quantity
            )

            slackNotifier.send("""
                [긴급 청산] ${position.symbol}
                수량: ${position.quantity}
                평균가: ${position.averagePrice}
                손익: ${position.unrealizedPnL}
            """)
        } catch (e: Exception) {
            errorLog.critical("긴급 청산 실패: ${position.symbol}", e)
        }
    }

    // 계좌 중단
    realAccount.stop()
}
```

#### 다단계 승인 시스템
```kotlin
@Service
class TradingApprovalSystem {
    /**
     * 실거래 주문은 다단계 승인 필요
     */
    fun requestApproval(order: RealOrder): ApprovalRequest {
        val request = ApprovalRequest.create(order)

        // Level 1: 자동 리스크 검증
        val riskCheck = validateRisk(order)
        if (!riskCheck.passed) {
            return request.reject(riskCheck.reason)
        }

        // Level 2: 일일 한도 체크
        val dailyLimit = checkDailyLimit(order)
        if (!dailyLimit.passed) {
            return request.reject(dailyLimit.reason)
        }

        // Level 3: 수동 승인 (고액 거래)
        if (order.totalAmount > 1_000_000) {
            request.requireManualApproval()
            slackNotifier.send("수동 승인 필요: ${order.totalAmount}원")
        } else {
            request.autoApprove()
        }

        return request
    }
}
```

### 4. 보안

#### API 키 암호화
```kotlin
@Service
class ApiKeyEncryptionService {
    private val algorithm = "AES/GCM/NoPadding"
    private val keySize = 256

    fun encrypt(apiKey: String, secretKey: String): EncryptedApiKey {
        val cipher = Cipher.getInstance(algorithm)
        val gcmParameterSpec = GCMParameterSpec(128, generateIV())
        val masterKey = getMasterKey() // Kubernetes Secret

        cipher.init(Cipher.ENCRYPT_MODE, masterKey, gcmParameterSpec)

        val encryptedKey = cipher.doFinal(apiKey.toByteArray())
        val encryptedSecret = cipher.doFinal(secretKey.toByteArray())

        return EncryptedApiKey(
            encryptedKey = Base64.encode(encryptedKey),
            encryptedSecret = Base64.encode(encryptedSecret),
            iv = Base64.encode(gcmParameterSpec.iv)
        )
    }

    fun decrypt(encrypted: EncryptedApiKey): ApiKey {
        // 복호화 로직
    }
}
```

#### 2FA (2단계 인증)
```
필수 활성화:
  - 거래소 계정 2FA
  - Trade Pilot 관리자 2FA
  - API 키 발급 시 2FA

검증 주기:
  - 실거래 시작 시
  - 설정 변경 시
  - 대량 거래 시
```

#### IP 화이트리스트
```
설정:
  - K3s 클러스터 Egress IP만 허용
  - VPN 서버 IP 허용
  - 개발자 IP 허용 (필요 시)

모니터링:
  - 비정상 IP 접근 감지 시 즉시 차단
  - 접근 로그 실시간 모니터링
```

### 5. 감사 로그 (Audit Log)
```
목적: 모든 거래 기록의 무결성 보장
방법: 해시 체인으로 변조 방지
```

**감사 로그 구조**:
```kotlin
data class AuditLog(
    val id: UUID,
    val timestamp: Instant,
    val userId: UUID,
    val action: String,          // ORDER_CREATE, ORDER_FILL, POSITION_UPDATE
    val details: Map<String, Any>,
    val previousHash: String,    // 이전 로그의 해시
    val currentHash: String      // 현재 로그의 해시
) {
    fun calculateHash(): String {
        val data = "$id|$timestamp|$userId|$action|$details|$previousHash"
        return SHA256.hash(data)
    }

    fun verifyIntegrity(): Boolean {
        return currentHash == calculateHash()
    }
}
```

---

## 개발 로드맵

### Phase 1: 기본 구조 (2주)
- [ ] Domain 모델
  - [ ] RealAccount
  - [ ] RealOrder
  - [ ] RealPosition
  - [ ] RealTransaction
- [ ] 데이터베이스 스키마
- [ ] 감사 로그 시스템

### Phase 2: 거래소 연동 (3주)
- [ ] 업비트 API 연동
  - [ ] 주문 실행 (시장가/지정가)
  - [ ] 주문 취소/수정
  - [ ] 체결 내역 동기화
  - [ ] 잔고 실시간 조회
- [ ] API 키 암호화 저장
- [ ] Rate Limiting 처리

### Phase 3: 리스크 관리 강화 (2주)
- [ ] 실계좌 손실 한도
- [ ] 강제 청산 시스템
- [ ] 다단계 승인 시스템
- [ ] 거래 로그 무결성

### Phase 4: 보안 강화 (2주)
- [ ] 2FA (2단계 인증)
- [ ] IP 화이트리스트
- [ ] API 키 권한 제한
- [ ] 접근 제어 (RBAC)

### Phase 5: 모니터링 (1주)
- [ ] 실시간 거래 모니터링
- [ ] 이상 거래 탐지
- [ ] 긴급 알림 시스템

### Phase 6: API 및 Frontend (2주)
- [ ] REST API 구현
- [ ] 실거래 대시보드
- [ ] 수동 주문 UI
- [ ] 긴급 중단 버튼

---

## 기술 설계

### API 엔드포인트

```http
POST /real-accounts
→ 실계좌 연동

GET /real-accounts/{accountId}
→ 계좌 조회

PUT /real-accounts/{accountId}/deploy
→ 전략 배포 (실거래 시작)

PUT /real-accounts/{accountId}/stop
→ 전략 중단

POST /real-accounts/{accountId}/orders
→ 수동 주문 실행

GET /real-accounts/{accountId}/orders
→ 주문 내역 조회

GET /real-accounts/{accountId}/positions
→ 포지션 조회

GET /real-accounts/{accountId}/transactions
→ 거래 내역 조회

POST /real-accounts/{accountId}/emergency-stop
→ 긴급 전량 청산
```

### 데이터베이스 스키마

```sql
CREATE TABLE real_account (
    identifier          UUID PRIMARY KEY,
    name                VARCHAR NOT NULL,
    strategy_identifier UUID NOT NULL,
    exchange            VARCHAR NOT NULL,
    api_key_encrypted   TEXT NOT NULL,
    secret_encrypted    TEXT NOT NULL,
    status              VARCHAR NOT NULL,
    created_date        TIMESTAMP WITH TIME ZONE
);

CREATE TABLE audit_log (
    id             UUID PRIMARY KEY,
    timestamp      TIMESTAMP WITH TIME ZONE,
    user_id        UUID NOT NULL,
    action         VARCHAR NOT NULL,
    details        JSONB NOT NULL,
    previous_hash  VARCHAR,
    current_hash   VARCHAR NOT NULL
);
```

---

## KPI 지표

### 실거래 성과
| 지표 | 목표값 | 측정 주기 |
|------|--------|-----------|
| 월평균 수익률 | > 5% | 월 1회 |
| BTC 대비 초과 수익 | > +5% | 월 1회 |
| 연환산 수익률 | > 60% | 분기 1회 |
| 최대 낙폭 (MDD) | < 15% | 실시간 |
| 샤프 비율 | > 2.0 | 월 1회 |

### 리스크 준수
| 지표 | 목표값 | 측정 주기 |
|------|--------|-----------|
| 손실 한도 준수율 | 100% | 실시간 |
| 일일 손실 한도 위반 | 0건 | 일 1회 |
| 주간 손실 한도 위반 | 0건 | 주 1회 |
| 긴급 중단 오작동 | 0건 | 월 1회 |

### 보안 지표
| 지표 | 목표값 | 측정 주기 |
|------|--------|-----------|
| 보안 패치 적용 시간 | < 24시간 | 발견 시 |
| 침투 테스트 통과율 | 100% | 분기 1회 |
| API 키 유출 사고 | 0건 | 실시간 |
| 비정상 접근 탐지 | < 1시간 | 실시간 |

---

## 리스크 관리

### 1. 자금 손실 리스크
**예방**:
- 점진적 자금 투입 (10% → 20% → 50%)
- 손실 한도 엄격 준수
- 2주 연속 손실 시 즉시 중단

**대응**:
- 손실 한도 도달 시 자동 중단
- 긴급 청산 버튼
- 보험 자금 별도 확보

### 2. API 키 유출 리스크
**예방**:
- AES-256 암호화
- Kubernetes Secret 관리
- IP 화이트리스트

**대응**:
- 비정상 접근 감지 시 API 키 즉시 폐기
- 거래소 계정 일시 중지
- 새 API 키 발급

### 3. 규제 변경 리스크
**예방**:
- 분기 법률 자문
- 규제 모니터링

**대응**:
- 규제 변경 시 즉시 거래 중단
- 법률 자문 요청
- 백업 플랜 실행

---

## 완료 조건

### 필수 조건
- ✅ 실거래 시스템 안정적 운영
- ✅ 보안 감사 통과 (침투 테스트)
- ✅ 리스크 관리 시스템 검증
- ✅ 최소 3개월 실거래 성과 확보
- ✅ 월평균 수익률 > 5%
- ✅ BTC 대비 초과 수익 > +5%
- ✅ 손실 한도 준수율 100%
- ✅ 법률 및 세무 자문 완료

### 권장 조건
- ✅ 2FA 활성화
- ✅ 감사 로그 무결성 100%
- ✅ 긴급 중단 시스템 정상 작동

---

## 점진적 자금 투입 전략

```
Week 1-2:  총 자금의 10% (100만원)
  목표: 시스템 안정성 확인
  조건: 손실 없이 2주 운영

Week 3-4:  총 자금의 20% (200만원)
  목표: 수익률 > 3%
  조건: MDD < 10%

Week 5-8:  총 자금의 30% (300만원)
  목표: 수익률 > 5%
  조건: MDD < 15%

Week 9-12: 총 자금의 50% (500만원)
  목표: 안정적 운영
  조건: 손실 한도 위반 0건

※ 어느 단계에서든 2주 연속 손실 시 이전 단계로 회귀
```

---

## 다음 단계

실거래 완료 후:
1. **Phase 5-1: 주식 시장 확장**
2. **Phase 5-2: 멀티 거래소**
3. **Phase 5-3: AI 전략**

---

## 참고 문서
- [데이터 수집](01-data-collection.md)
- [전략 구성](02-agent-strategy.md)
- [시뮬레이션](03-simulation.md)
- [가상 거래](04-virtual-trading.md)
- [KPI 측정 지표](../kpi-metrics.md)
- [리스크 관리 계획](../risk-management-plan.md)
