# Agent Service — Domain 설계

> 이 문서는 목차 역할을 합니다. 각 섹션의 상세 내용은 아래 하위 문서를 참조하세요.

---

## 문서 구성

| 파일 | 내용 |
|------|------|
| [model.md](./model.md) | Bounded Context, 헥사고날 아키텍처 레이어, 도메인 모델 (Aggregate, Value Objects, Enums, 생명주기) |
| [service.md](./service.md) | 도메인 포트, 도메인 서비스 (AgentRiskManager, PortfolioUpdater, Reconciliation, DecisionLogging, PortfolioHistory) |
| [kafka.md](./kafka.md) | Kafka 인터페이스 (AnalyzeAgentCommand, ExecutionConfirmed, OrderFailed, AgentTerminated, UserWithdrawn) |
| [grpc.md](./grpc.md) | gRPC 인터페이스 (Simulation→Agent 백테스팅, Agent→Market 캔들/심볼 조회) |
| [schema.md](./schema.md) | Redis 캐시 전략, DB 스키마, API 엔드포인트, 에러 코드 |
| [api-spec.md](./api-spec.md) | API 상세 스펙 (별도 문서) |
