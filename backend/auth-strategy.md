# API Gateway / 인증-인가 전략

> API Gateway 구현 기술 선정, JWKS 캐싱, JWT 검증 흐름, Rate Limit 정책 상세 설계
> 기본 인증/인가 원칙은 [architecture.md](./architecture.md) Section 5 참조

---

## 1. API Gateway 구현 기술

**선택: Spring Cloud Gateway (SCG)**

| 기준 | 설명 |
|------|------|
| 기술 통일성 | 전체 서비스가 Kotlin + Spring Boot 기반이므로 같은 생태계에서 운영 |
| JWKS 직접 구현 | SCG 필터에서 RS256 JWT 검증 로직을 직접 구현해 외부 의존성 최소화 |
| 동적 권한 관리 | DB + Redis 기반 `EndpointPermission` 규칙을 Gateway에서 직접 평가 |
| K3s 환경 | Ingress Controller와 연동하거나 LoadBalancer Service 뒤에 단독 배치 |

> Kong, Nginx 등 별도 API Gateway 솔루션은 추가 인프라 복잡성을 높이므로 현재 단계에서는 SCG로 충분하다.

---

## 2. 배포 토폴로지

```
Client (HTTPS)
    │
    ▼
[ Ingress Controller (K3s Traefik) ]
    │ TLS 종료
    ▼
[ API Gateway (Spring Cloud Gateway) ]
    │ JWT 검증 (RS256, JWKS 캐시 사용)
    │ EndpointPermission 평가 (Redis 캐시)
    │ X-User-Id / X-User-Role 헤더 추가
    │ X-Request-Id / X-Global-Trace-Id 헤더 추가
    │ Rate Limit (IP / userIdentifier 기반)
    ▼
[ 내부 서비스들 (HTTP, 클러스터 내부망) ]
```

---

## 3. JWKS 캐싱 전략

### 문제

RS256 JWT 검증에는 User Service가 발급한 JWT의 공개키(Public Key)가 필요하다.
매 요청마다 User Service의 `/auth/.well-known/jwks.json`을 호출하면 User Service에 불필요한 부하가 생긴다.

### 해결: 인메모리 캐시 + TTL 갱신

```kotlin
@Component
class JwksCache(
    @Value("\${auth.jwks-uri}") private val jwksUri: String,
    private val webClient: WebClient,
) {
    // ConcurrentHashMap — kid (Key ID) → RSAPublicKey 매핑
    private val keyCache = ConcurrentHashMap<String, RSAPublicKey>()

    @Scheduled(fixedDelay = 600_000)  // 10분마다 갱신
    fun refresh() {
        webClient.get().uri(jwksUri)
            .retrieve()
            .bodyToMono(JwksResponse::class.java)
            .subscribe { response ->
                keyCache.clear()
                response.keys.forEach { jwk ->
                    keyCache[jwk.kid] = jwk.toRsaPublicKey()
                }
            }
    }

    fun getKey(kid: String): RSAPublicKey? = keyCache[kid]
}
```

| 항목 | 값 |
|------|-----|
| 캐시 방식 | 인메모리 `ConcurrentHashMap` (Gateway 인스턴스 로컬) |
| TTL | 10분 (`@Scheduled` 주기 갱신) |
| 최초 로딩 | `@PostConstruct` 또는 첫 요청 시 동기 로딩 |
| 키 교체 시 | `kid` 불일치 → Rate Limit 적용 후 재조회 + 캐시 갱신 |

> Gateway Pod가 재시작되면 첫 요청 전에 JWKS를 로딩한다. `@PostConstruct`로 시작 시 즉시 로딩해 Cold Start 지연을 방지한다.

### 알려지지 않은 kid 공격 방어

공격자가 조작된 JWT의 `kid`를 무작위 값으로 설정하면, Gateway가 매 요청마다 User Service에
JWKS 재조회를 시도하여 DoS 공격이 가능하다. 이를 방지하기 위해:

```kotlin
private val unknownKidCache = ConcurrentHashMap<String, Long>()  // kid → 최초 거부 시각
private val UNKNOWN_KID_TTL = 60_000L  // 1분간 동일 kid 재조회 차단

private fun refreshAndGetWithRateLimit(kid: String): RSAPublicKey? {
    val now = System.currentTimeMillis()

    // 최근 1분 내 거부된 kid → 즉시 null 반환 (재조회 안 함)
    unknownKidCache[kid]?.let { rejectedAt ->
        if (now - rejectedAt < UNKNOWN_KID_TTL) return null
    }

    // User Service JWKS 재조회
    jwksCache.refresh()
    val key = jwksCache.getKey(kid)

    if (key == null) {
        unknownKidCache[kid] = now  // 거부 캐시에 등록
    }
    return key
}
```

> `unknownKidCache`는 TTL 1분 후 자동 만료되므로, 실제 키 로테이션 시에는
> 최대 1분 후 정상 인식된다.

---

## 4. JWT 검증 필터

```kotlin
@Component
class JwtAuthenticationFilter(
    private val jwksCache: JwksCache,
) : AbstractGatewayFilterFactory<Config>() {

    override fun apply(config: Config): GatewayFilter = GatewayFilter { exchange, chain ->
        val request = exchange.request
        val token   = extractBearerToken(request) ?: return@GatewayFilter chain.filter(exchange)

        try {
            val header  = Jwts.parserBuilder().build().parseClaimsJwt(token).header
            val kid     = header["kid"] as? String
                ?: return@GatewayFilter unauthorizedResponse(exchange, "Missing kid")
            val pubKey  = jwksCache.getKey(kid)
                ?: refreshAndGetWithRateLimit(kid)       // kid 불일치 시 Rate Limit 적용 후 재조회
                ?: return@GatewayFilter unauthorizedResponse(exchange, "Unknown kid")

            val claims = Jwts.parserBuilder()
                .setSigningKey(pubKey)
                .build()
                .parseClaimsJws(token)
                .body

            val userIdentifier = claims.subject
            val role   = claims["role"] as? String ?: "USER"

            val mutated = request.mutate()
                .header("X-User-Id",   userIdentifier)
                .header("X-User-Role", role)
                .build()

            chain.filter(exchange.mutate().request(mutated).build())

        } catch (e: JwtException) {
            unauthorizedResponse(exchange, e.message)
        }
    }

    private fun extractBearerToken(request: ServerHttpRequest): String? {
        val auth = request.headers.getFirst(HttpHeaders.AUTHORIZATION) ?: return null
        return if (auth.startsWith("Bearer ")) auth.substring(7) else null
    }
}
```

---

## 5. Rate Limit 정책

### 기본 전략

```
PUBLIC 엔드포인트 (/auth/sign-up, /auth/sign-in 등)
  └── IP 기반 Rate Limit: 20 req/min per IP

USER 엔드포인트
  └── userIdentifier 기반 Rate Limit: 300 req/min per userIdentifier

ADMIN 엔드포인트
  └── Rate Limit 없음 (내부 운영 도구)
```

### Spring Cloud Gateway RequestRateLimiter 적용

```kotlin
// application.yml
spring:
  cloud:
    gateway:
      routes:
        - id: user-service
          uri: lb://user-service
          predicates:
            - Path=/auth/**,/users/**
          filters:
            - name: RequestRateLimiter
              args:
                redis-rate-limiter.replenishRate: 5     # 초당 토큰 보충
                redis-rate-limiter.burstCapacity: 20    # 순간 최대 허용
                key-resolver: "#{@userKeyResolver}"
```

```kotlin
@Bean
fun userKeyResolver(): KeyResolver = KeyResolver { exchange ->
    val userIdentifier = exchange.request.headers.getFirst("X-User-Id")
    val ip     = exchange.request.remoteAddress?.address?.hostAddress ?: "unknown"
    Mono.just(userIdentifier ?: "ip:$ip")
}
```

> Rate Limit 카운터는 Gateway 전용 Redis 인스턴스에 저장한다. (각 서비스의 Redis와 분리)

---

## 6. 요청 헤더 관리

### Gateway가 추가하는 헤더

| 헤더 | 생성 주체 | 값 | 설명 |
|------|-----------|-----|------|
| `X-User-Id` | JWT 검증 필터 | JWT `sub` 클레임 | 인증된 사용자 ID |
| `X-User-Role` | JWT 검증 필터 | JWT `role` 클레임 | 사용자 권한 |
| `X-Request-Id` | MDC 필터 | 요청별 UUID | 단일 HTTP 요청 식별자 |
| `X-Global-Trace-Id` | MDC 필터 | UUID (없으면 신규 생성) | 비즈니스 플로우 전체 식별자 |

### 보안: 내부 헤더 스푸핑 방지

클라이언트가 `X-User-Id`, `X-User-Role` 헤더를 직접 설정하는 것을 방지한다.
Gateway 필터에서 요청 수신 시 해당 헤더를 **즉시 제거**한 후, 검증된 값으로 재설정한다.

```kotlin
@Component
class SecurityHeaderFilter : GlobalFilter {
    private val internalHeaders = listOf("X-User-Id", "X-User-Role")

    override fun filter(exchange: ServerWebExchange, chain: GatewayFilterChain): Mono<Void> {
        val cleaned = exchange.request.mutate()
            .headers { headers -> internalHeaders.forEach { headers.remove(it) } }
            .build()
        return chain.filter(exchange.mutate().request(cleaned).build())
    }
}
```

---

## 7. 헬스체크 및 예외 경로

다음 경로는 JWT 검증을 건너뛴다. `EndpointPermission` DB에 `PUBLIC` 규칙으로 등록되어 있어야 한다.

| 경로 | 설명 |
|------|------|
| `POST /auth/sign-up` | 회원가입 |
| `POST /auth/sign-in` | 로그인 |
| `GET /auth/.well-known/jwks.json` | JWKS 공개키 조회 |
| `GET /actuator/health` | 서비스 헬스체크 |

---

## 8. 장애 처리

### User Service 다운 시

- JWKS는 Gateway 인메모리에 캐시되어 있으므로 User Service 다운과 무관하게 JWT 검증을 계속 수행한다.
- 캐시 만료(10분) 전까지는 영향 없음. 만료 후 재조회 실패 시 기존 캐시를 계속 사용하고 알림(경고 로그)을 남긴다.

```kotlin
@Scheduled(fixedDelay = 600_000)
fun refresh() {
    runCatching {
        // 재조회 로직
    }.onFailure { ex ->
        logger.warn("JWKS refresh failed, using stale cache: ${ex.message}")
        // 기존 캐시 유지 (keyCache 초기화 안 함)
    }
}
```

### Rate Limit Redis 다운 시

Spring Cloud Gateway의 `RequestRateLimiter`는 Redis 다운 시 기본적으로 요청을 통과시킨다(fail-open).
보안 정책상 더 엄격하게 설정하려면 `deny-empty-key: true`로 설정해 Redis 없이 Rate Limit 키를 생성할 수 없을 때 차단한다.

---

## 9. 서비스 목록 (라우팅 대상)

| 서비스 | 내부 주소 | 경로 패턴 |
|--------|-----------|-----------|
| User Service | `lb://user-service` | `/auth/**`, `/users/**` |
| Market Service | `lb://market-service` | `/market-symbols/**`, `/market-candle-collect-tasks/**` |
| Agent Service | `lb://agent-service` | `/strategies/**`, `/agents/**` |
| Simulation Service | `lb://simulation-service` | `/backtests/**` |
| VirtualTrade Service | `lb://virtual-trade-service` | `/virtual-trades/**` |
| Trade Service | `lb://trade-service` | `/trade-registrations/**` |
| Notification Service | `lb://notification-service` | `/notification-channels/**`, `/notification-preferences/**` |
| Exchange Service | `lb://exchange-service` | `/exchange-accounts/**` |
| API Gateway (자체) | — | `/admin/**` (권한 관리 Admin API) |
