# 동시성 Lock 설계

> MSA 환경에서 동시 접근으로 인한 데이터 불일치를 방지하기 위한 Lock 전략

---

## 1. 동시성 문제 유형

Trade Pilot에서 발생 가능한 동시성 문제:

| 시나리오                            | 문제                   |
| ------------------------------- | -------------------- |
| 동일 심볼에 대해 다수 인스턴스가 동시에 수집 작업 시작 | 중복 수집, DB 레코드 충돌     |
| 동일 계좌에서 다수 주문 동시 실행             | 리스크 한도 초과, 잔고 오버드래프트 |
| 동일 RefreshToken으로 동시 갱신 요청      | 토큰 이중 발급 가능성         |
| VirtualTrade 계좌의 동시 청산/진입       | 포지션 상태 불일치           |

---

## 2. Lock 전략 선택 기준

```
단일 인스턴스 내 동시성?
  └── YES → DB Pessimistic Lock (@Lock PESSIMISTIC_WRITE)
  └── NO (다중 인스턴스) →
        작업 시간이 예측 가능하고 짧은가 (< 1초)?
          └── YES → Redis Distributed Lock (Redisson)
          └── NO  → DB-based Lock + 상태 머신
```

### 첫 번째 분기 — "단일 인스턴스 내 동시성?"

**DB Pessimistic Lock의 보호 범위는 트랜잭션 내부로 한정된다.**

`SELECT ... FOR UPDATE`는 트랜잭션이 열려 있는 동안 해당 Row에 대한 다른 트랜잭션의 접근을 차단한다.
트랜잭션이 끝나는 순간 Lock이 해제되므로, DB는 "어느 Pod가 작업 중인지"를 트랜잭션 바깥에서는 알 수 없다.

따라서 보호해야 하는 작업이 **하나의 트랜잭션 안에서 완결**된다면 DB Lock으로 충분하다.
여러 Pod가 동시에 요청하더라도 DB가 직렬화하여 처리한다.

반면 Outbox Relay나 수집 스케줄러처럼 **트랜잭션 경계 바깥에서 실행되는 작업**은 DB Lock이
"이미 다른 Pod가 실행 중"이라는 사실을 인지하지 못한다.
이 경우 Redis처럼 트랜잭션과 무관하게 인스턴스 간 공유되는 외부 저장소가 필요하다.

> 정리: **보호 범위가 트랜잭션 내부냐 외부냐**로 첫 번째 분기를 나눈다.

---

### 두 번째 분기 — "작업 시간이 예측 가능하고 짧은가?"

**Redis Distributed Lock의 핵심 리스크는 leaseTime이다.**

Redis Lock은 `leaseTime`이 지나면 작업이 끝나지 않아도 자동으로 해제된다.
이 시간을 잘못 설정하면 두 가지 문제가 생긴다.

- `leaseTime`을 **너무 짧게** 설정하면: 작업이 끝나기 전에 Lock이 해제되어 다른 Pod가 동시에 진입한다.
- `leaseTime`을 **너무 길게** 설정하면: Pod가 죽었을 때 Lock이 오래 점유된 채로 남아 다음 실행이 지연된다.

Redisson의 `WatchDog` 기능이 자동 갱신을 지원하긴 하지만, 이는 해당 스레드가 살아있을 때만 동작한다.
결국 **작업 시간을 예측할 수 없다면** leaseTime을 어떻게 설정해도 안전하지 않다.

배치성 작업(대량 정산, 장기 실행 청산 로직 등)은 소요 시간이 데이터 양에 따라 가변적이다.
이런 경우 DB에 `status = RUNNING`, `locked_by`, `locked_at` 컬럼을 두고
**상태 머신 자체를 Lock으로 활용**하는 것이 더 안전하다.
`locked_at`을 heartbeat로 주기적으로 갱신하면 Pod 비정상 종료 시에도 일정 시간 후 다른 Pod가 인계할 수 있다.

> 정리: **작업 시간이 예측 가능한 경우에만 Redis Lock을 사용한다.**
> 소요 시간이 가변적인 작업은 상태 머신이 Lock을 대신한다.

---

### Trade Pilot에서의 실제 적용 범위

세 번째 분기(`DB-based Lock + 상태 머신`)는 현재 시점에서는 Trade Service의 실주문 배치나
정산 로직이 추가될 때를 대비한 설계다. 현재 대부분의 케이스는 아래 두 가지로 해결된다.

| 실제 케이스 | 분기 결과 |
|------------|----------|
| 수집 작업 상태 전이, 포트폴리오 점유, 회원 탈퇴 | 트랜잭션 내 완결 → DB Pessimistic Lock |
| Outbox Relay (100ms), 수집 스케줄러 | 트랜잭션 외부, 수백ms 내 완결 → Redis Lock |

---

## 3. DB Pessimistic Lock (단일 인스턴스 / 트랜잭션 내)

### 사용 시나리오

동일 트랜잭션 안에서 레코드를 조회하고 즉시 업데이트하는 경우.

```kotlin
// JPA Repository
@Lock(LockModeType.PESSIMISTIC_WRITE)
@Query("SELECT c FROM MarketCandleCollectTask c WHERE c.identifier = :id")
fun findByIdForUpdate(@Param("id") id: UUID): MarketCandleCollectTask?

// 사용
@Transactional
fun startCollect(taskIdentifier: CollectTaskId) {
    val task = taskRepository.findByIdForUpdate(taskIdentifier.value)
        ?: throw CollectTaskNotFoundException()

    task.start()    // 상태 변경
    taskRepository.save(task)
}
```

**적용 대상:**
- `MarketCandleCollectTask.start()` / `collectComplete()` — 수집 작업 상태 전이
- `Portfolio.reserveCash()` / `releaseReservation()` — 신호 발생 시 현금/포지션 점유
- `User.withdraw()` — 회원 탈퇴 상태 전이

**주의사항:**
- `@Transactional` 범위 내에서만 유효
- 다중 인스턴스(K3s Pod 복수) 환경에서는 DB Lock이 각 인스턴스 간 충돌을 막아주지만
  lock wait timeout을 적절히 설정해야 한다 (기본값 50초는 너무 길다)

```kotlin
// application.yml
spring:
  jpa:
    properties:
      jakarta.persistence.lock.timeout: 3000  # 3초 후 LockTimeoutException
```

---

## 4. Redis Distributed Lock (다중 인스턴스 / 스케줄러 중복 방지)

### 사용 시나리오

스케줄러 기반 Outbox Relay, 심볼 수집 스케줄러 등 다중 인스턴스에서 중복 실행을 방지해야 하는 경우.

**의존성:**
```kotlin
// build.gradle.kts
implementation("org.redisson:redisson-spring-boot-starter:3.27.x")
```

**구현 패턴:**

```kotlin
@Component
class DistributedLockManager(
    private val redissonClient: RedissonClient,
) {
    fun <T> withLock(
        lockKey: String,
        waitTime: Long = 0,
        leaseTime: Long = 10,
        timeUnit: TimeUnit = TimeUnit.SECONDS,
        action: () -> T,
    ): T? {
        val lock = redissonClient.getLock(lockKey)
        if (!lock.tryLock(waitTime, leaseTime, timeUnit)) return null  // Lock 획득 실패 → skip
        try {
            return action()
        } finally {
            if (lock.isHeldByCurrentThread) lock.unlock()
        }
    }
}
```

**Outbox Relay 적용 예시:**

```kotlin
@Scheduled(fixedDelay = 100)
fun relay() {
    // "outbox:relay:{serviceName}" 키로 인스턴스 간 중복 실행 방지
    lockManager.withLock("outbox:relay:market", leaseTime = 5) {
        val events = outboxRepository.findPendingOrRetryable(limit = 100)
        events.forEach { publishToKafka(it) }
    }
}
```

**Lock Key 네이밍 규칙:**

```
{domain}:{operation}:{identifier}

예시:
  outbox:relay:market
  collect:symbol:KRW-BTC
  virtual-trade:close-position:{accountIdentifier}
```

**적용 대상:**
- Outbox Relay Processor (100ms 폴링, 다중 Pod 중복 방지)
- Market 심볼별 수집 스케줄러

---

## 5. Optimistic Lock (충돌 빈도가 낮은 경우)

### 사용 시나리오

동시 수정 가능성이 낮고, 충돌 시 재시도가 허용되는 경우.

```kotlin
@Entity
class RefreshToken(
    ...
    @Version
    val version: Long = 0,   // Optimistic Lock 버전 컬럼
)

// 충돌 시 OptimisticLockException 발생 → 재시도 or 409 응답
```

**적용 대상:**
- 프로필 업데이트 등 충돌 빈도가 매우 낮은 일반 업데이트 (선택적 적용)

---

## 6. Lock 전략 요약

| 시나리오 | Lock 전략 | 구현 |
|---------|-----------|------|
| 수집 작업 상태 전이 | Pessimistic Write | `@Lock(PESSIMISTIC_WRITE)` |
| 회원 탈퇴 | Pessimistic Write | `SELECT FOR UPDATE` |
| 포트폴리오 현금/포지션 점유 | Pessimistic Write | `@Lock(PESSIMISTIC_WRITE)` |
| Outbox Relay 중복 방지 | Redis Distributed Lock | Redisson `tryLock` |
| 심볼별 수집 스케줄러 | Redis Distributed Lock | Redisson `tryLock` |
| Refresh Token 갱신 | 낙관적 (isRevoked 체크) | SELECT → 비즈니스 로직 검증 |

---

## 7. 교착 상태(Deadlock) 방지 원칙

1. **Lock 획득 순서 통일**: 여러 테이블에 Lock이 필요한 경우 항상 동일한 순서로 획득
   - 예: `user` → `refresh_token` → `outbox` 순서
2. **최소 Lock 범위**: `@Transactional` 범위를 최소화하여 Lock 보유 시간 단축
3. **타임아웃 설정**: DB Lock timeout 3초, Redis Lock leaseTime 10초 이하
4. **Retry on Deadlock**: JPA Optimistic Lock 충돌 시 1회 재시도
