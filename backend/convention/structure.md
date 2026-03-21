# 기술 스택 & 프로젝트 구조

> 원본: `backend/code-convention.md` Section 1~2

---

## 1. 기술 스택 요약

| 분류 | 기술 | 버전 |
|------|------|------|
| 언어 | Kotlin | 2.0.21 |
| 프레임워크 | Spring Boot | 3.4.0 |
| JDK | Eclipse Temurin | 21 |
| ORM | JPA, QueryDSL | - |
| 빌드 | Gradle (Kotlin DSL) | 8.x |
| 데이터베이스 | PostgreSQL | 16 |
| 시계열 DB | TimescaleDB (Market Service) | - |
| 캐시 | Redis | 7 |
| 메시징 | Apache Kafka (KRaft) | 7.6.0 |
| 동기 통신 | gRPC | - |
| 컨테이너 | Kubernetes (K3s) | - |

---

## 2. 프로젝트 구조 — 헥사고날 아키텍처

### 2.1 패키지 구조

각 서비스는 아래의 표준 패키지 구조를 따른다.

```
com.tradepilot.{서비스명}/
├── domain/
│   ├── model/         # Aggregate Root, Entity, Value Object, Enum
│   ├── service/       # 도메인 서비스 (AgentRiskManager, PortfolioUpdater 등)
│   └── port/
│       ├── in/        # Input Port (UseCase 인터페이스, Command 객체)
│       └── out/       # Output Port (Repository, 외부 서비스 인터페이스)
├── application/
│   └── usecase/       # UseCase 구현체 (Input Port implements)
└── infrastructure/
    ├── persistence/   # JPA Entity, JPA Repository, Entity ↔ Domain Mapper
    ├── kafka/         # Producer, Consumer
    ├── grpc/          # gRPC Server, Client Adapter
    ├── redis/         # Redis 캐시 어댑터
    └── web/           # REST Controller, Request/Response DTO
```

### 2.2 계층 간 의존성 규칙

```
domain  ← 외부 의존성 없음 (Spring, JPA, Jackson 어노테이션 금지)
application ← domain만 의존
infrastructure ← domain + application + 외부 라이브러리 (Spring, JPA, Kafka, gRPC 등)
```

- **domain 레이어**: 순수 Kotlin 코드만 허용. `@Entity`, `@Service`, `@Transactional` 등 프레임워크 어노테이션 사용 금지.
- **application 레이어**: `@Service`, `@Transactional` 허용. infrastructure 레이어에 직접 의존하지 않고 Output Port를 통해 접근.
- **infrastructure 레이어**: 프레임워크 어노테이션 자유롭게 사용. Output Port를 구현하여 domain/application에 주입.
