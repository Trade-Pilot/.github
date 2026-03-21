# 롤백 정책, 환경별 설정, 데이터 보관

> 원본: `backend/database-migration.md` Section 6~8 + 부록

---

---

## 6. 롤백 정책

### 6.1 Flyway 롤백 제약

Flyway Community Edition은 자동 롤백을 지원하지 않는다 (Teams/Enterprise 에디션에서만 `flyway undo` 사용 가능).

### 6.2 수동 롤백 전략

롤백이 필요한 경우 다음 버전의 마이그레이션 파일로 역방향 변경을 수행한다.

```
V20260320_001__create_user_table.sql       (원본)
V20260321_001__rollback_drop_user_table.sql (롤백 — 실제로는 사용 지양)
```

### 6.3 파괴적 변경의 2단계 분리

컬럼 삭제, 테이블 삭제 등 파괴적 변경은 2단계로 나누어 안전하게 수행한다.

**예시: `user` 테이블에서 `nickname` 컬럼 제거**

```
단계 1 — 코드에서 사용 중단 (릴리스 N)
  - nickname 컬럼 읽기/쓰기 코드 제거
  - 코드 배포 후 nickname 컬럼은 미사용 상태

단계 2 — 실제 컬럼 삭제 (릴리스 N+1)
  V20260401_001__drop_nickname_from_user.sql
  ALTER TABLE "user" DROP COLUMN nickname;
```

이 방식으로 롤링 업데이트 중 신/구 버전 인스턴스가 공존하는 상황에서도 스키마 불일치 오류를 방지한다.

### 6.4 테이블 이름 변경

테이블 이름 변경도 2단계로 분리한다.

```
단계 1 — 뷰 또는 Alias 생성 (릴리스 N)
  CREATE VIEW old_name AS SELECT * FROM new_name;

단계 2 — 뷰 제거 (릴리스 N+1)
  DROP VIEW old_name;
```

---

## 7. 환경별 설정

### 7.1 dev (개발 환경)

```yaml
spring:
  flyway:
    enabled: true
    clean-disabled: false  # dev에서만 clean 허용
    locations:
      - classpath:db/migration
      - classpath:db/seed    # 테스트 데이터 시드
```

- `flyway clean` 허용 — 스키마 초기화 후 재생성 가능
- `db/seed` 디렉토리에 테스트 데이터 INSERT 스크립트 배치

### 7.2 stg (스테이징 환경)

```yaml
spring:
  flyway:
    enabled: true
    clean-disabled: true   # clean 금지
    locations:
      - classpath:db/migration
```

- `flyway clean` 금지 — 프로덕션과 동일한 스키마 유지
- 프로덕션 스키마를 복제하여 마이그레이션 사전 검증

### 7.3 prod (프로덕션 환경)

```yaml
spring:
  flyway:
    enabled: true
    clean-disabled: true   # clean 절대 금지
    validate-on-migrate: true
    locations:
      - classpath:db/migration
```

- `flyway clean` 절대 금지
- 마이그레이션만 허용, 수동 DDL 실행 금지
- `validate-on-migrate: true`로 체크섬 검증 활성화

---

## 8. 데이터 보관 정책 연동

architecture.md Section 9의 데이터 보관 정책과 연동하여 만료 데이터를 정리한다.

### 8.1 정리 대상

| 대상 | 보관 기간 | 정리 방식 |
|------|----------|----------|
| `processed_events` | 처리 후 7일 | 배치 삭제 스케줄러 |
| `outbox` (PUBLISHED) | 발행 성공 후 7일 | 배치 삭제 스케줄러 |
| `refresh_token` (만료) | 만료 후 30일 | 배치 삭제 스케줄러 |
| `strategy_decision_log` | 3개월 | BigQuery 이동 후 삭제 |
| `portfolio_history` (SIGNAL) | 3개월 | BigQuery 이동 후 삭제 |
| `notification_log` | 3개월 | BigQuery 이동 후 삭제 |
| `market_candle` | 2년 | TimescaleDB retention policy 자동 삭제 |

### 8.2 배치 삭제 스케줄러

각 서비스는 만료 데이터를 정리하는 스케줄러를 운영한다. 대량 삭제 시 테이블 락을 방지하기 위해 배치 단위로 삭제한다.

```kotlin
@Scheduled(cron = "0 0 3 * * *")  // 매일 새벽 3시
fun cleanupExpiredData() {
    // 1000건씩 반복 삭제
    do {
        val deleted = jdbcTemplate.update("""
            DELETE FROM processed_events
            WHERE consumed_at < NOW() - INTERVAL '7 days'
            LIMIT 1000
        """)
    } while (deleted > 0)
}
```

### 8.3 Repeatable Migration 활용

인덱스 재생성 등 반복 가능한 작업은 Repeatable Migration으로 관리한다.

#### R__cleanup_policies.sql (참고용 — 실제 삭제는 스케줄러가 수행)
```sql
-- 이 파일은 정리 정책을 문서화하는 용도
-- 실제 삭제는 애플리케이션 스케줄러에서 수행

-- processed_events: 7일 후 삭제
-- outbox (PUBLISHED): 7일 후 삭제
-- refresh_token (만료 + 30일): 삭제
```

---

## 부록: 서비스별 마이그레이션 파일 요약

| 서비스 | 마이그레이션 파일 수 | 주요 테이블 |
|--------|---------------------|------------|
| User Service | 3 | user, refresh_token, outbox |
| Exchange Service | 1 | exchange_account |
| Market Service | 6 | market_symbol, market_candle (hypertable), market_candle_collect_task, outbox, TimescaleDB 설정 |
| Agent Service | 10 | strategy, agent, signal, portfolio, position, portfolio_history, backtest_result, strategy_decision_log, outbox, processed_events |
| Simulation Service | 0 | 자체 DB 없음 (Redis 캐시만) |
| VirtualTrade Service | 3 | virtual_trade_registration, outbox, processed_events |
| Trade Service | 6 | trade_registration, trade_order, execution, outbox, processed_events, account_reconciliation_log |
| Notification Service | 5 | notification_channel, notification_preference, notification_log, notification_template, processed_events |
