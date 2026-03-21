# Notification Service - 도메인 설계

> 이 문서는 목차 역할을 합니다. 각 섹션의 상세 내용은 아래 하위 문서를 참조하세요.

---

## 문서 구성

| 파일 | 내용 |
|------|------|
| [model.md](./model.md) | 서비스 책임, Aggregate Root (Channel, Preference), Entity (Log, Template), Value Object, Enum |
| [service.md](./service.md) | Notification Command, Domain Service (Dispatcher, TemplateRenderer, UserWithdrawnHandler), Preference 초기화 |
| [kafka.md](./kafka.md) | Kafka 이벤트 소비 플로우 (시퀀스 다이어그램) |
| [schema.md](./schema.md) | Use Case, API 엔드포인트, DB 스키마, 예외, 도메인 관계 |
| [api-spec.md](./api-spec.md) | API 상세 스펙 (별도 문서) |
