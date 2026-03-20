# Trade Pilot - 로컬 개발 환경 설정

> 백엔드 및 프론트엔드 로컬 개발 환경을 구성하고, 서비스를 실행하는 가이드

---

## 1. 사전 요구사항

| 도구 | 버전 | 비고 |
|------|------|------|
| JDK | 21 (Eclipse Temurin) | `java -version` 으로 확인 |
| Kotlin | 2.0.21 | Gradle 플러그인으로 관리 |
| Gradle | 8.x | Wrapper 사용 (`./gradlew`) |
| Node.js | 20 LTS | 프론트엔드 빌드용 |
| Docker Desktop | Docker Compose v2 포함 | `docker compose version` 으로 확인 |
| IDE | IntelliJ IDEA Ultimate (권장) | Spring Boot, Kotlin 지원 |

```bash
# 버전 확인
java -version          # openjdk 21.x.x (Eclipse Temurin)
node -v                # v20.x.x
docker compose version # Docker Compose v2.x.x
```

---

## 2. Docker Compose 인프라 스택

로컬 개발에 필요한 인프라(PostgreSQL, Kafka, Redis)를 단일 `docker-compose.yml`로 관리한다.

### docker-compose.yml

```yaml
services:
  # PostgreSQL (단일 인스턴스, 서비스별 다중 데이터베이스)
  postgres:
    image: timescale/timescaledb:latest-pg16
    container_name: tradepilot-postgres
    ports: ["5432:5432"]
    environment:
      POSTGRES_USER: tradepilot
      POSTGRES_PASSWORD: tradepilot
    volumes:
      - postgres-data:/var/lib/postgresql/data
      - ./init-db.sql:/docker-entrypoint-initdb.d/init-db.sql

  # Kafka (KRaft 모드 — Zookeeper 없음)
  kafka:
    image: confluentinc/cp-kafka:7.6.0
    container_name: tradepilot-kafka
    ports: ["9092:9092"]
    environment:
      KAFKA_NODE_ID: 1
      KAFKA_PROCESS_ROLES: broker,controller
      KAFKA_CONTROLLER_QUORUM_VOTERS: 1@kafka:29093
      KAFKA_LISTENERS: PLAINTEXT://0.0.0.0:9092,CONTROLLER://0.0.0.0:29093
      KAFKA_ADVERTISED_LISTENERS: PLAINTEXT://localhost:9092
      KAFKA_CONTROLLER_LISTENER_NAMES: CONTROLLER
      KAFKA_LISTENER_SECURITY_PROTOCOL_MAP: CONTROLLER:PLAINTEXT,PLAINTEXT:PLAINTEXT
      KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR: 1
      KAFKA_AUTO_CREATE_TOPICS_ENABLE: "true"
      CLUSTER_ID: "local-dev-cluster"

  # Redis
  redis:
    image: redis:7-alpine
    container_name: tradepilot-redis
    ports: ["6379:6379"]

  # Kafka UI (토픽/메시지 모니터링)
  kafka-ui:
    image: provectuslabs/kafka-ui:latest
    container_name: tradepilot-kafka-ui
    ports: ["8090:8080"]
    environment:
      KAFKA_CLUSTERS_0_NAME: local
      KAFKA_CLUSTERS_0_BOOTSTRAPSERVERS: kafka:9092
    depends_on: [kafka]

volumes:
  postgres-data:
```

### init-db.sql (다중 데이터베이스 초기화)

PostgreSQL 컨테이너 최초 실행 시 자동으로 서비스별 데이터베이스를 생성한다.

```sql
-- 서비스별 데이터베이스 생성
CREATE DATABASE user_service;
CREATE DATABASE exchange_service;
CREATE DATABASE market_service;
CREATE DATABASE agent_service;
CREATE DATABASE virtual_trade_service;
CREATE DATABASE trade_service;
CREATE DATABASE notification_service;

-- TimescaleDB 확장 활성화 (Market Service — 시계열 캔들 데이터)
\c market_service;
CREATE EXTENSION IF NOT EXISTS timescaledb;
```

---

## 3. 서비스별 application-local.yml 설정

각 서비스의 `src/main/resources/application-local.yml`에 로컬 개발 프로파일을 정의한다.

### 공통 설정 패턴

```yaml
spring:
  profiles:
    active: local
  datasource:
    url: jdbc:postgresql://localhost:5432/{서비스_db명}
    username: tradepilot
    password: tradepilot
  jpa:
    hibernate:
      ddl-auto: validate  # 스키마는 Flyway가 관리
    properties:
      hibernate:
        dialect: org.hibernate.dialect.PostgreSQLDialect
        jdbc.batch_size: 100
  flyway:
    enabled: true
    locations: classpath:db/migration
  kafka:
    bootstrap-servers: localhost:9092
  data:
    redis:
      host: localhost
      port: 6379

# gRPC 설정
grpc:
  server:
    port: {서비스별 gRPC 포트}
  client:
    market-service:
      address: static://localhost:9090
      negotiationType: plaintext  # 로컬은 TLS 미사용
```

### 서비스별 포트 매핑

| 서비스 | HTTP 포트 | gRPC 포트 | DB명 |
|--------|----------|----------|------|
| API Gateway | 8080 | — | — |
| User Service | 8081 | — | user_service |
| Exchange Service | 8082 | — | exchange_service |
| Market Service | 8083 | 9090 | market_service |
| Agent Service | 8084 | 9091 | agent_service |
| Simulation Service | 8085 | — | — |
| VirtualTrade Service | 8086 | — | virtual_trade_service |
| Trade Service | 8087 | — | trade_service |
| Notification Service | 8088 | — | notification_service |

---

## 4. 빠른 시작 가이드

### 4.1 인프라 실행

```bash
# 인프라 컨테이너 실행
docker compose up -d

# 컨테이너 상태 확인
docker compose ps

# DB 초기화 확인 (서비스별 데이터베이스 목록)
docker exec -it tradepilot-postgres psql -U tradepilot -l
```

### 4.2 백엔드 서비스 실행

```bash
# 개별 서비스 실행 (예: Market Service)
cd market-service
./gradlew bootRun --args='--spring.profiles.active=local'

# 또는 환경 변수로 프로파일 지정
SPRING_PROFILES_ACTIVE=local ./gradlew bootRun
```

### 4.3 프론트엔드 실행

```bash
cd trade-pilot-web
npm install
npm run dev
```

> Vite 개발 서버가 기본적으로 `http://localhost:5173`에서 실행된다.

---

## 5. 개발용 테스트 데이터 시드

각 서비스의 `src/main/resources/db/seed/` 디렉토리에 로컬 개발용 테스트 데이터 SQL을 배치한다.
`local` 프로파일에서만 자동 실행되도록 구성한다.

### 시드 데이터 예시

| 서비스 | 데이터 | 설명 |
|--------|--------|------|
| User Service | `admin@tradepilot.com` / `test1234!` | ADMIN 역할 테스트 계정 |
| Market Service | KRW-BTC, KRW-ETH 등 | 주요 심볼 10개 |
| Notification Service | VIRTUAL_ORDER_FILLED, REAL_ORDER_FILLED 등 | 기본 알림 템플릿 |

### application-local.yml 시드 설정

```yaml
spring:
  sql:
    init:
      mode: always
      data-locations: classpath:db/seed/data-local.sql
```

---

## 6. 개발 도구 및 디버깅

### Kafka UI

토픽 목록, 메시지 내용, Consumer Group 상태를 브라우저에서 확인할 수 있다.

- **URL**: http://localhost:8090

### PostgreSQL 접속

```bash
# 특정 서비스 DB에 접속
docker exec -it tradepilot-postgres psql -U tradepilot -d market_service

# 테이블 목록 확인
\dt

# 쿼리 실행
SELECT * FROM market_symbol LIMIT 10;
```

### Redis CLI

```bash
docker exec -it tradepilot-redis redis-cli

# 키 목록 조회
KEYS *

# 특정 키 조회
GET cache:market:candle:KRW-BTC
```

### API Gateway 없이 직접 호출

로컬 개발 시 API Gateway를 거치지 않고 각 서비스에 직접 요청할 수 있다.
Gateway가 주입하는 `X-User-Id` 헤더를 수동으로 설정해야 한다.

```bash
# Agent Service에 직접 요청
curl -H "X-User-Id: test-user-uuid" http://localhost:8084/agents

# Market Service에 직접 요청
curl http://localhost:8083/market-symbols
```

---

## 7. IntelliJ IDEA 설정

### Multi-module 프로젝트 구조

```
trade-pilot/
├── api-gateway/
├── user-service/
├── exchange-service/
├── market-service/
├── agent-service/
├── simulation-service/
├── virtual-trade-service/
├── trade-service/
├── notification-service/
├── shared-kernel/            # 공통 모듈 (KafkaEnvelope, ApiErrorResponse 등)
├── proto/                    # gRPC proto 파일 공유
├── docker-compose.yml
├── init-db.sql
└── settings.gradle.kts
```

### Run Configuration 설정

각 서비스별 Spring Boot Run Configuration을 생성한다.

1. **Run/Debug Configurations** > **Add** > **Spring Boot**
2. **Main class**: `{서비스}.ApplicationKt`
3. **Active profiles**: `local`
4. **Environment variables**: `SPRING_PROFILES_ACTIVE=local`

### Compound Run Configuration (멀티 서비스 동시 실행)

IntelliJ의 Compound Run Configuration을 사용하여 필요한 서비스만 선택적으로 동시 실행한다.

| 개발 대상 | 최소 실행 조합 |
|-----------|---------------|
| Market 개발 | API Gateway + Market Service |
| Agent 개발 | API Gateway + Market Service + Agent Service |
| Trade 개발 | API Gateway + Market Service + Agent Service + Trade Service + Exchange Service |
| VirtualTrade 개발 | API Gateway + Market Service + Agent Service + VirtualTrade Service |
| 전체 통합 테스트 | 전체 서비스 |

### Compound 설정 방법

1. **Run/Debug Configurations** > **Add** > **Compound**
2. 이름 입력 (예: `[Trade 개발]`)
3. 필요한 서비스의 Run Configuration 선택 후 추가

---

## 8. 트러블슈팅

| 증상 | 원인 | 해결 |
|------|------|------|
| Kafka 연결 실패 | Docker 미실행 | `docker compose up -d` |
| DB 마이그레이션 실패 | 이전 스키마 충돌 | `docker compose down -v` 후 재시작 |
| gRPC 연결 거부 | 대상 서비스 미실행 | 의존 서비스를 먼저 실행 |
| Port already in use | 이전 프로세스 잔존 | `lsof -i :{포트}` 로 PID 확인 후 `kill {PID}` |
| TimescaleDB 확장 미설치 | init-db.sql 미실행 | `docker compose down -v` 후 재시작 |
| Kafka 토픽 생성 안 됨 | Kafka 브로커 미준비 | `docker compose logs kafka` 로 상태 확인, 재시작 |
| Redis 연결 거부 | Redis 컨테이너 미실행 | `docker compose up -d redis` |

### 인프라 전체 초기화

데이터를 포함한 완전한 초기화가 필요한 경우:

```bash
# 볼륨 포함 전체 제거
docker compose down -v

# 재시작
docker compose up -d

# DB 초기화 확인
docker exec -it tradepilot-postgres psql -U tradepilot -l
```

### 로그 확인

```bash
# 특정 서비스 로그 확인
docker compose logs -f kafka
docker compose logs -f postgres

# 전체 인프라 로그
docker compose logs -f
```
