# Trade Pilot Documentation

Trade Pilot 프로젝트의 전체 문서입니다.

## 📚 문서 구조

### 프로젝트 개요
- **[프로젝트 개요](project-overview.md)**: Trade Pilot의 비전, 아키텍처, 주요 도메인
- **[개발 로드맵](development-roadmap.md)**: 단계별 개발 계획, KPI 지표, 리스크 관리 (Phase 1~5)

### 기능별 통합 문서 (✨ 추천)
- **[01. 데이터 수집](features/01-data-collection.md)**: 시장 데이터 수집 및 품질 관리
- **[02. 전략 구성](features/02-agent-strategy.md)**: 거래 전략 정의 및 신호 생성
- **[03. 시뮬레이션](features/03-simulation.md)**: 과거 데이터 백테스팅
- **[04. 가상 거래](features/04-virtual-trading.md)**: 실시간 Paper Trading
- **[05. 실거래](features/05-real-trading.md)**: 실제 자금 거래 실행

### 기술 스택
- **[기술 스택 개요](profile/README.md)**: Frontend, Backend, Infra 기술 스택

### Backend 설계 (상세 기술 문서)
- **[Market Service](backend/design/market-service.md)**: 시장 데이터 수집 및 관리
- **[Agent Service](backend/design/agent-service.md)**: 거래 전략 정의 및 실행
- **[Simulation Service](backend/design/simulation-service.md)**: 백테스팅 시스템
- **[VirtualTrade Service](backend/design/virtual-trade-service.md)**: 가상거래 시스템
- **[Trade Service]**: 실거래 시스템 (작성 예정)

### Infrastructure
- **[인프라 설계](infra/README.md)**: K3s, Kafka, PostgreSQL 등

---

## 🎯 빠른 시작

### 1. 프로젝트 이해하기 (초보자 추천)
Trade Pilot이 처음이라면 다음 순서로 문서를 읽어보세요:

1. **[프로젝트 개요](project-overview.md)** - 전체적인 그림 파악
2. **[개발 로드맵](development-roadmap.md)** - 어떻게 개발할 것인가
3. **기능별 통합 문서** - 각 기능의 목적과 구현 방법 이해
   - **[데이터 수집](features/01-data-collection.md)** ← Phase 1 진행 중
   - **[전략 구성](features/02-agent-strategy.md)** ← Phase 2
   - **[시뮬레이션](features/03-simulation.md)** ← Phase 2
   - **[가상 거래](features/04-virtual-trading.md)** ← Phase 3
   - **[실거래](features/05-real-trading.md)** ← Phase 4

### 2. 개발 참여하기
개발에 참여하고 싶다면:

1. **[개발 로드맵](development-roadmap.md)**에서 현재 Phase 확인
2. 현재 Phase의 **기능별 통합 문서** 읽기
3. 각 문서의 **완료 조건**, **KPI 지표**, **리스크 관리** 확인
4. Backend 상세 설계 문서 읽기 (필요 시)
5. 구현 시작

---

## 📖 주요 도메인

Trade Pilot은 5개의 핵심 도메인으로 구성됩니다:

### 1. Market (시장 데이터)
**목적**: 시장 데이터 수집 및 관리

**주요 기능**:
- 거래 심볼 관리
- OHLCV 캔들 데이터 수집
- 데이터 품질 관리 (Flat Candle)

**문서**: [market-service.md](backend/design/market-service.md)

**현재 상태**: ✅ 설계 완료 → 🔄 구현 중

---

### 2. Agent (거래 주체)
**목적**: 시장 분석 및 거래 의사결정

**주요 기능**:
- 전략 정의 (수동 → AI)
- 매수/매도 신호 생성
- 포트폴리오 관리

**문서**: [agent-service.md](backend/design/agent-service.md)

**현재 상태**: ✅ 설계 완료 → 🔜 구현 예정 (Phase 2)

---

### 3. Simulation (시뮬레이션)
**목적**: 과거 데이터 기반 백테스팅

**주요 기능**:
- Time Travel 엔진
- 성과 측정 (수익률, MDD, 샤프비율 등)
- 파라미터 최적화 (Grid Search, Walk-Forward)

**문서**: [simulation-service.md](backend/design/simulation-service.md)

**현재 상태**: ✅ 설계 완료 → 🔜 구현 예정 (Phase 2)

---

### 4. VirtualTrade (가상거래)
**목적**: 실시간 가상거래 환경

**주요 기능**:
- Paper Trading
- 리스크 관리
- 실시간 성과 모니터링

**문서**: [virtual-trade-service.md](backend/design/virtual-trade-service.md)

**현재 상태**: 🔄 설계 필요 (Phase 3)

---

### 5. Trade (실거래)
**목적**: 실제 자금으로 거래 실행

**주요 기능**:
- 거래소 주문 실행
- 포지션 관리
- 리스크 관리 강화

**문서**: 작성 예정

**현재 상태**: 🔄 설계 필요 (Phase 4)

---

## 🗓️ 개발 일정

### Phase 1: 데이터 기반 구축 (3개월) - 현재 진행 중
- ✅ Market Service 설계 완료
- 🔄 Market Service 구현 중
- 🔄 Exchange Service 구현 중
- 🔜 Frontend 수집 현황 대시보드
- 🔜 Infra 구축

### Phase 2: 전략 개발 및 검증 (2개월)
- ✅ Agent Service 설계 완료
- ✅ Simulation Service 설계 완료
- 🔜 백테스팅 엔진 구현
- 🔜 수동 전략 구현
- 🔜 Frontend 백테스팅 UI

### Phase 3: 실시간 검증 환경 (2개월)
- 🔜 VirtualTrade Service 설계
- 🔜 가상거래 엔진 구현
- 🔜 리스크 관리 시스템
- 🔜 Frontend 가상거래 대시보드

### Phase 4: 실전 투입 자동화 (2개월)
- 🔜 Trade Service 설계
- 🔜 실거래 연동
- 🔜 보안 강화
- 🔜 Frontend 실거래 대시보드

### Phase 5: AI 전략 및 확장 (장기)
- 🔜 강화학습 전략
- 🔜 주식 시장 확장
- 🔜 멀티 거래소 지원

---

## 💡 핵심 원칙

### 1. 데이터 우선 접근
충분한 데이터 수집 없이 거래 시스템을 개발하지 않습니다.

### 2. 점진적 개발
수동 전략부터 시작하여 AI 전략으로 진화합니다.

### 3. 철저한 검증
모든 전략은 시뮬레이션 → 가상거래 → 실거래 순서로 검증합니다.

### 4. 리스크 관리
손실 한도 설정 및 긴급 중단 시스템을 필수로 구현합니다.

---

## 📊 기술 스택

### Frontend
- TypeScript, React
- FSD Architecture

### Backend
- Kotlin 2.0.21
- Spring Boot 3.4.0
- DDD, Hexagonal Architecture
- JPA, QueryDSL

### Infrastructure
- Kubernetes (K3s)
- Kafka
- PostgreSQL, TimescaleDB, Redis
- Prometheus, Grafana

---

## 🔗 관련 링크

- [GitHub Repository](https://github.com/your-repo)
- [Jira Board](https://your-jira.atlassian.net)
- [Confluence](https://your-confluence.atlassian.net)

---

## 📝 문서 작성 가이드

새로운 서비스 설계 문서를 작성할 때는 다음 템플릿을 따라주세요:

### 설계 문서 구조
1. **개요**: 서비스의 목적과 핵심 개념
2. **액션 플로우**: 주요 시나리오 흐름
3. **도메인 정의**: Domain Model 상세 설명
4. **API 엔드포인트**: REST API 명세
5. **데이터베이스 스키마**: 테이블 정의
6. **시퀀스 다이어그램**: Mermaid를 사용한 플로우 시각화

---

## 📞 문의

프로젝트에 대한 문의사항이 있으시면:

- **Email**: your-email@example.com
- **Slack**: #trade-pilot

---

## 📜 라이선스

이 프로젝트는 개인 프로젝트로, 모든 권리는 프로젝트 소유자에게 있습니다.
