# Trade Pilot — 데이터 보관, API Gateway, 보안 체크리스트, 배포/운영

> 이 문서는 `backend/architecture.md`에서 분할되었습니다.

---

## 9. 데이터 보관 정책

### 9.1 보관 기간

**Hot Storage (PostgreSQL)**:
```
이벤트 로그:        3개월
  - StrategyDecisionLog
  - PortfolioHistory (SIGNAL 타입)
  - NotificationLog

실행 이력:          1년
  - Order
  - Execution
  - Signal

운영 데이터:        30일 후 Hard Delete
  - ProcessedEvents
  - Outbox (발행 성공 후 7일)
  - RefreshToken (만료 30일 후)

마스터 데이터:      영구
  - User
  - Strategy
  - Agent
  - Portfolio
  - MarketSymbol
```

**Warm Storage (BigQuery / S3 Parquet)**:
```
3개월~2년:
  - 모든 이벤트 로그
  - 집계 분석용 데이터
```

**Cold Storage (S3 Glacier)**:
```
2년~:
  - 규제 준수용 감사 데이터
  - 압축 아카이브
```

### 9.2 데이터 아카이빙 스케줄

**매월 1일 실행**:
```sql
-- 3개월 이전 데이터를 BigQuery로 이동
INSERT INTO bigquery.strategy_decision_log
SELECT * FROM strategy_decision_log
WHERE created_at < NOW() - INTERVAL '3 months';

DELETE FROM strategy_decision_log
WHERE created_at < NOW() - INTERVAL '3 months';
```

**매년 1월 1일 실행**:
```
- BigQuery → S3 Parquet 변환
- 2년 이전 데이터 Glacier 이동
```

### 9.3 데이터 삭제 정책

**Soft Delete** (논리 삭제):
```
- User (회원 탈퇴)
- NotificationChannel
- NotificationPreference
- ExchangeAccount

※ 감사 목적으로 데이터는 보존, isDeleted=true 플래그로 비활성화
```

**Hard Delete** (물리 삭제):
```
- RefreshToken (만료 30일 후)
- Outbox (발행 성공 후 7일)
- ProcessedEvents (처리 후 7일)
```

---

## 10. API Gateway 상세

### 10.1 인증 및 인가

**JWT 검증**:
```yaml
알고리즘: RS256
Public Key: User Service에서 제공 (/auth/public-key)
검증 항목:
  - 서명 유효성
  - 만료 시간 (exp)
  - 발급자 (iss = "trade-pilot")
```

**헤더 주입**:
```
검증 성공 시:
  X-User-Id: {userIdentifier}
  X-User-Role: {role}

내부 서비스는 이 헤더를 신뢰하고 사용
```

### 10.2 Rate Limiting

**사용자별 Rate Limit**:
```yaml
인증 사용자 (USER):
  - 300 req/min (userIdentifier 기준)

인증 사용자 (ADMIN):
  - Rate Limit 없음 (내부 운영 도구)

미인증 (PUBLIC):
  - 20 req/min (IP 기준)
```

**엔드포인트별 Rate Limit**:
```yaml
POST /auth/sign-up:     20 req/min (IP 기준)
POST /auth/sign-in:     20 req/min (IP 기준, 무차별 대입 방지)
POST /orders:           100 req/min
GET /*:                 300 req/min
```

### 10.3 라우팅 규칙

```nginx
/auth/**                          → User Service
/users/**                         → User Service
/exchange-accounts/**             → Exchange Service
/market-symbols/**                → Market Service
/market-candle-collect-tasks/**   → Market Service
/strategies/**                    → Agent Service
/agents/**                        → Agent Service
/backtests/**                     → Simulation Service
/virtual-trades/**                → VirtualTrade Service
/trade-registrations/**           → Trade Service
/notification-channels/**        → Notification Service
/notification-preferences/**     → Notification Service
/notification-logs/**            → Notification Service
/notification-templates/**       → Notification Service (ADMIN)
/admin/**                         → API Gateway (자체, 권한 관리)
```

### 10.4 CORS 설정

```yaml
allowed-origins:
  - https://trade-pilot.com
  - https://*.trade-pilot.com
allowed-methods: GET, POST, PUT, DELETE, OPTIONS
allowed-headers: Authorization, Content-Type
max-age: 3600
```

---

## 11. 보안 체크리스트

### 11.1 인증/인가
- [x] JWT RS256 사용
- [x] Refresh Token DB 저장 및 무효화 가능
- [x] API Gateway에서 JWT 검증
- [x] 서비스 간 mTLS 적용
- [x] Kafka SASL/SCRAM 인증

### 11.2 암호화
- [x] 민감 정보 AES-256-GCM 암호화 (Exchange API Key)
- [x] HTTPS 강제 (HTTP → HTTPS 리다이렉트)
- [x] DB 연결 암호화 (SSL/TLS)
- [ ] 암호화 키 로테이션 정책 (TODO)

### 11.3 입력 검증
- [x] DTO Validation (@Valid, JSR-303)
- [x] SQL Injection 방지 (JPA Prepared Statement)
- [x] XSS 방지 (Response Encoding)
- [x] CSRF 방지 (SameSite Cookie, CORS)

### 11.4 권한 검증
- [x] 사용자별 리소스 소유권 검증 (userIdentifier 일치 확인)
- [x] ADMIN 전용 API 분리
- [x] Kafka ACL (토픽별 접근 제어)

---

## 12. 배포 및 운영

### 12.1 컨테이너화

**Dockerfile 표준**:
```dockerfile
FROM eclipse-temurin:21-jre-alpine
WORKDIR /app
COPY build/libs/*.jar app.jar
EXPOSE 8080
ENTRYPOINT ["java", "-jar", "app.jar"]
```

**리소스 제한**:
```yaml
resources:
  requests:
    memory: 512Mi
    cpu: 500m
  limits:
    memory: 1Gi
    cpu: 1000m
```

### 12.2 환경별 설정

```
dev:  개발 환경 (로컬 Docker Compose)
stg:  스테이징 (프로덕션 데이터 복제본)
prod: 프로덕션
```

**환경 변수 관리**:
```yaml
DB 연결: Kubernetes Secret
Kafka: ConfigMap
암호화 키: Vault / AWS Secrets Manager
```

### 12.3 롤링 업데이트

```yaml
strategy:
  type: RollingUpdate
  rollingUpdate:
    maxSurge: 1        # 동시에 추가 가능한 Pod 수
    maxUnavailable: 0  # 업데이트 중 중단 가능한 Pod 수
```

**배포 절차**:
1. Health Check 통과 확인
2. 카나리 배포 (10% 트래픽)
3. 메트릭 모니터링 (에러율, 레이턴시)
4. 점진적 확대 (50% → 100%)
5. 롤백 준비 (이전 이미지 보관)

---

## 부록: 서비스 의존성 매트릭스

| 서비스 | User | Exchange | Market | Agent | Simulation | VirtualTrade | Trade | Notification |
|--------|------|----------|--------|-------|------------|--------------|-------|--------------|
| User | - | - | - | - | - | - | - | ✅ Event |
| Exchange | - | - | - | - | - | - | ✅ Command | - |
| Market | - | ✅ Command | - | - | - | - | - | ✅ Event |
| Agent | - | - | ✅ gRPC | - | - | ✅ Command | ✅ Command | - |
| Simulation | - | - | ✅ gRPC | ✅ gRPC | - | - | - | - |
| VirtualTrade | - | - | ✅ gRPC | ✅ Command | - | - | - | ✅ Command |
| Trade | - | ✅ Command | ✅ gRPC | ✅ Command | - | - | - | ✅ Command |
| Notification | - | - | - | - | - | - | - | - |

**범례**:
- ✅ Command: Kafka Command/Reply
- ✅ Event: Kafka Event (단방향)
- ✅ gRPC: 동기 호출
