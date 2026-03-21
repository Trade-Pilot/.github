# Trade Service — Domain 설계

> 이 문서는 목차 역할을 합니다. 각 섹션의 상세 내용은 아래 하위 문서를 참조하세요.

---

## 문서 구성

| 파일 | 내용 |
|------|------|
| [model.md](./model.md) | Bounded Context, 헥사고날 아키텍처 레이어, 도메인 모델 (Aggregate, Value Objects, 상태 전이) |
| [service.md](./service.md) | 도메인 포트, 스케줄러 (TradeScheduler, OrderTimeoutScheduler), Account Reconciliation |
| [kafka.md](./kafka.md) | Kafka 인터페이스 (신호 요청/응답, 주문 제출/취소, 체결 확정, 이벤트 수신) |
| [emergency.md](./emergency.md) | 비상 정지 (Emergency Stop) 메커니즘, 주문 미체결 모니터링 |
| [schema.md](./schema.md) | gRPC 인터페이스, DB 스키마, API 엔드포인트, 에러 코드 |
| [api-spec.md](./api-spec.md) | API 상세 스펙 (별도 문서) |
