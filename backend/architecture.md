# Trade Pilot - 백엔드 아키텍처

> 이 문서는 목차 역할을 합니다. 각 섹션의 상세 내용은 아래 하위 문서를 참조하세요.

---

## 문서 구성

| 파일 | 내용 |
|------|------|
| [architecture/service-overview.md](./architecture/service-overview.md) | 서비스 구성 (전체 구조도, 서비스 목록), 보안 전략, 성능/확장성 전략 |
| [architecture/communication.md](./architecture/communication.md) | 데이터 인터페이스 표준, 서비스 간 통신 원칙 (gRPC, Kafka, REST, 탈퇴 사용자 차단) |
| [architecture/kafka-standard.md](./architecture/kafka-standard.md) | Kafka 토픽 명명 규칙, 메시지 Envelope, Command/Reply 패턴, 멱등성 보장 |
| [architecture/observability.md](./architecture/observability.md) | 옵저빌리티 (Health Check, Metrics, Distributed Tracing, Logging, 알람 정책) |
| [architecture/error-retry.md](./architecture/error-retry.md) | 재시도/에러 처리 전략, Circuit Breaker, 에러 코드 체계 |
| [architecture/data-policy.md](./architecture/data-policy.md) | 데이터 보관 정책, API Gateway 상세, 보안 체크리스트, 배포/운영, 서비스 의존성 매트릭스 |
