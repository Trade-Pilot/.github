# Market Service - 도메인 설계

> 이 문서는 목차 역할을 합니다. 각 섹션의 상세 내용은 아래 하위 문서를 참조하세요.

---

## 문서 구성

| 파일 | 내용 |
|------|------|
| [model.md](./model.md) | Aggregate Root (MarketSymbol, MarketCandleCollectTask), Entity (MarketCandle), Value Object, Enum |
| [service.md](./service.md) | Domain Service (MarketCandleIntervalCalculator), Domain Event |
| [factory.md](./factory.md) | Factory (MarketSymbolFactory, MarketCandleCollectTaskFactory, MarketCandleFactory) |
| [usecase.md](./usecase.md) | Exception, 도메인 관계, Use Case (심볼 수집, 캔들 수집, 수집 샤딩) |
| [grpc.md](./grpc.md) | 핵심 비즈니스 규칙, gRPC 인터페이스 (Proto 정의, 서버 구현, 타임아웃/성능) |
| [schema.md](./schema.md) | gRPC 클라이언트 예시, 보안 (mTLS), Use Case 추가 (심볼 조회) |
| [api-spec.md](./api-spec.md) | API 상세 스펙 (별도 문서) |
