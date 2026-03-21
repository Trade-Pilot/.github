# 통합 테스트

> 원본: `backend/testing-strategy.md` Section 3

---

## 3. 통합 테스트 규칙

### 3.1 도구 및 환경

- **Testcontainers**: PostgreSQL, Kafka, Redis 실제 컨테이너를 사용한다.
- **Spring Boot Test**: `@SpringBootTest(webEnvironment = RANDOM_PORT)` 로 애플리케이션 컨텍스트를 로드한다.
- **테스트 격리**: `@DirtiesContext` 대신 **트랜잭션 롤백** 또는 **테이블 TRUNCATE** 를 사용한다. 컨텍스트 재생성 비용이 크므로 TRUNCATE 방식을 권장한다.

```kotlin
@TestInstance(TestInstance.Lifecycle.PER_CLASS)
@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT)
abstract class IntegrationTestBase {

    @Autowired
    lateinit var jdbcTemplate: JdbcTemplate

    @BeforeEach
    fun cleanUp() {
        jdbcTemplate.execute("TRUNCATE TABLE outbox, processed_events CASCADE")
        // 서비스별 테이블 추가
    }
}
```

### 3.2 DB 통합 테스트

#### Repository 테스트

```kotlin
@Test
fun `findAllByStatus_ACTIVE등록만조회`() {
    // Given: ACTIVE 2건, PAUSED 1건, STOPPED 1건 INSERT
    // When: findAllByStatus(ACTIVE) 호출
    // Then: 2건만 반환
}

@Test
fun `findTimedOutPendingOrders_타임아웃초과주문만조회`() {
    // Given: timeoutAt이 과거인 SUBMITTED 주문 1건, 미래인 주문 1건
    // When: findTimedOutPendingOrders(now) 호출
    // Then: 1건만 반환
}

@Test
fun `findActiveByAgentAndSymbol_중복주문방지인덱스확인`() {
    // Given: agentIdentifier + symbolIdentifier 조합으로 PENDING 주문 존재
    // When: findActiveByAgentAndSymbol(agentIdentifier, symbolIdentifier) 호출
    // Then: 기존 주문 반환 (부분 인덱스 idx_order_active 적중)
}
```

#### Pessimistic Lock 테스트

```kotlin
@Test
fun `PessimisticLock_동시Portfolio접근_순차처리`() {
    // Given: Portfolio (cash=10,000,000)
    // When: 2개 스레드가 동시에 findByAgentIdForUpdate() + reserveCash(6,000,000) 시도
    // Then: 첫 번째 스레드 성공 (reservedCash=6,000,000)
    //       두 번째 스레드 InsufficientCashException (가용: 4,000,000 < 요청: 6,000,000)
}

@Test
fun `PessimisticLock_lockTimeout초과_LockTimeoutException`() {
    // Given: 3초 lock timeout 설정
    // When: 첫 번째 트랜잭션이 5초간 Lock 점유, 두 번째 트랜잭션 대기
    // Then: 두 번째 트랜잭션 LockTimeoutException 발생
}
```

#### Outbox 통합 테스트

```kotlin
@Test
fun `Outbox_트랜잭션내INSERT_Relay가Kafka발행`() {
    // Given: 도메인 상태 변경 + Outbox INSERT (동일 트랜잭션)
    // When: 트랜잭션 커밋
    // Then: Outbox status == PENDING
    //       Relay 실행 후 status == PUBLISHED
    //       Kafka Consumer에서 메시지 수신 확인
}

@Test
fun `Outbox_Kafka발행실패_retryCount증가후재시도`() {
    // Given: Kafka 브로커 일시 중단
    // When: Relay 실행
    // Then: status == FAILED, retryCount += 1
    //       Kafka 브로커 복구 후 다음 Relay 사이클에서 PUBLISHED
}

@Test
fun `Outbox_3회실패_DEAD상태전환`() {
    // Given: retryCount == 2, Kafka 발행 실패
    // When: Relay 실행
    // Then: status == DEAD, retryCount == 3
    //       관리자 알림 발행 확인
}

@Test
fun `Outbox_traceId전파_KafkaConsumer에서동일traceId확인`() {
    // Given: HTTP 요청 traceId = "abc-123"
    // When: Outbox INSERT → Relay → Kafka 발행
    // Then: Kafka Consumer가 수신한 traceparent 헤더에 "abc-123" 포함
}
```

### 3.3 Kafka 통합 테스트

```kotlin
@Test
fun `Kafka_메시지발행후Consumer수신확인`() {
    // Given: AnalyzeAgentCommand 메시지
    // When: Producer가 command.agent.trade.analyze-strategy 토픽에 발행
    // Then: Consumer에서 동일 메시지 수신 (Awaitility 5초 대기)
}

@Test
fun `Kafka_멱등성_동일메시지2회소비시1회만처리`() {
    // Given: 동일 (topic, partition, offset)의 메시지
    // When: Consumer가 2회 소비 시도
    // Then: processed_events 테이블 확인 → 1회만 비즈니스 로직 실행
    //       2회차는 skip (이미 처리됨)
}

@Test
fun `Kafka_DLQ_3회실패후DeadLetterQueue이동`() {
    // Given: 처리 시 항상 예외 발생하는 Consumer
    // When: 메시지 소비 시도 (3회 재시도)
    // Then: dlq.{원본토픽명} 토픽에 메시지 존재 확인
}

@Test
fun `Kafka_CommandReply_callback토픽으로응답발행`() {
    // Given: Command에 callback = "reply.virtual-trade.agent.analyze-strategy" 설정
    // When: Agent Service Consumer가 Command 처리 완료
    // Then: callback 토픽에 Reply 메시지 발행 확인
}

@Test
fun `Kafka_KafkaEnvelope_messageIdentifier기반멱등성`() {
    // Given: 동일 messageIdentifier를 가진 KafkaEnvelope 2개
    // When: Consumer가 순차 소비
    // Then: 첫 번째만 처리, 두 번째는 중복으로 skip
}
```

### 3.4 gRPC 통합 테스트

```kotlin
@Test
fun `gRPC_GetRecentCandles_정상응답`() {
    // Given: Market Service gRPC 서버 기동, DB에 캔들 데이터 INSERT
    // When: GetRecentCandles(symbolIdentifier, interval=MINUTE_1, limit=10) 호출
    // Then: 10개 캔들 응답, 최신순 정렬
}

@Test
fun `gRPC_BacktestStrategy_스트리밍신호순서검증`() {
    // Given: Agent Service gRPC 서버 기동, 100개 캔들 데이터
    // When: BacktestStrategy 스트리밍 호출
    // Then: 시간순으로 신호 수신, 각 신호에 portfolioSnapshot 포함
}

@Test
fun `gRPC_deadline초과_DEADLINE_EXCEEDED`() {
    // Given: 의도적으로 느린 gRPC 서버 (5초 지연)
    // When: deadline 3초로 설정하고 호출
    // Then: StatusRuntimeException(DEADLINE_EXCEEDED) 발생
}

@Test
fun `gRPC_서버미기동_UNAVAILABLE`() {
    // Given: gRPC 서버 미기동 상태
    // When: GetRecentCandles 호출
    // Then: StatusRuntimeException(UNAVAILABLE) 발생
}
```

### 3.5 Redis 통합 테스트

```kotlin
@Test
fun `Redis_캐시Hit_DB조회생략`() {
    // Given: Redis에 캔들 데이터 캐싱 완료
    // When: 동일 키로 조회
    // Then: DB 쿼리 실행 없음, 캐시에서 반환
}

@Test
fun `Redis_캐시Miss_DB조회후캐싱`() {
    // Given: Redis에 해당 키 없음
    // When: 조회 요청
    // Then: DB에서 조회 → Redis에 캐싱 → 다음 조회 시 캐시 Hit
}

@Test
fun `Redis_DistributedLock_동시실행방지`() {
    // Given: Outbox Relay Lock Key = "outbox:relay:market"
    // When: 2개 인스턴스가 동시에 tryLock 시도
    // Then: 1개만 Lock 획득, 나머지는 skip (null 반환)
}

@Test
fun `Redis_TTL만료후_캐시재조회`() {
    // Given: TTL 1초로 캐싱
    // When: 2초 후 조회
    // Then: 캐시 Miss → DB 재조회 → 새 데이터 캐싱
}

@Test
fun `Redis_Lock_leaseTime초과시_자동해제`() {
    // Given: leaseTime = 5초로 Lock 획득
    // When: 6초 경과
    // Then: 다른 인스턴스가 Lock 획득 가능
}
```

