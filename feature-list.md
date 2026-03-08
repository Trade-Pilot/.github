# Trade Pilot - Feature List

> 📋 전체 개발 로드맵: [development-roadmap.md](development-roadmap.md)
> 📖 프로젝트 개요: [project-overview.md](project-overview.md)

## 진행 상태 표기
- [ ] 미시작
- [⏳] 진행중
- [✅] 완료
- [🔄] 검토중

---

## Phase 1: 데이터 기반 구축 (3개월)

### Infra
- [ ] K3s 클러스터 구성
- [ ] Helm Chart 작성
- [ ] ArgoCD 배포 자동화
- [ ] Jenkins CI/CD 파이프라인
- [ ] Nexus Repository 구성
- [ ] PostgreSQL HA 구성
- [ ] Kafka 클러스터 구성
- [ ] Monitoring Stack
  - [ ] Prometheus 설치
  - [ ] Grafana 대시보드
  - [ ] Elasticsearch + Kibana
- [ ] VPN 서버 구성

### Backend - Common
- [ ] Common 모듈 구성
  - [ ] Base Entity
  - [ ] Common Exception
  - [ ] API Response 포맷
  - [ ] Validation Utils
- [ ] Auth 모듈 구성
  - [ ] JWT 기반 인증
  - [ ] Spring Security 설정
  - [ ] User Domain

### Backend - Exchange Service
- [ ] 업비트 API 연동
  - [ ] 심볼 목록 조회
  - [ ] 캔들 데이터 조회
  - [ ] Rate Limiting 처리
  - [ ] Error Handling
- [ ] Kafka Producer 구성
  - [ ] 심볼 Reply 메시지
  - [ ] 캔들 Reply 메시지

### Backend - Market Service
- [🔄] Domain 모델 구현
  - [✅] MarketSymbol
  - [✅] MarketCandleCollectTask
  - [✅] MarketCandle
- [🔄] 데이터 수집 기능
  - [✅] 심볼 수집 스케줄러 (일 1회)
  - [✅] 캔들 수집 스케줄러 (분 1회)
  - [✅] Flat Candle 생성
  - [ ] 간격별 캔들 계산 (MIN_3 ~ MONTH)
- [ ] 데이터 저장
  - [✅] PostgreSQL 파티션 테이블
  - [ ] 파티션 자동 생성 스케줄러
- [ ] API 구현
  - [✅] 시장 심볼 조회
  - [✅] 수집 작업 조회
  - [✅] 수집 작업 제어 (시작/중지)
  - [✅] 캔들 데이터 조회
- [ ] Kafka Integration
  - [✅] 심볼 Command 발행
  - [✅] 캔들 Command 발행
  - [✅] Reply 메시지 수신
  - [✅] Domain Event 발행

### Frontend - Market
- [ ] 수집 현황 대시보드
  - [ ] 수집 작업 목록 조회
  - [ ] 수집 상태 통계
  - [ ] 수집 제어 (시작/중지/재시작)
- [ ] 캔들 차트 뷰어
  - [ ] TradingView 라이브러리 연동
  - [ ] 심볼 선택
  - [ ] 시간 간격 선택
  - [ ] 실시간 업데이트 (WebSocket)
- [ ] 심볼 관리
  - [ ] 심볼 목록 조회
  - [ ] 심볼 상태 확인

---

## Phase 2: 전략 개발 및 검증 (2개월)

### Backend - Agent Service
- [ ] Domain 모델 구현
  - [ ] Strategy (전략)
  - [ ] Signal (신호)
  - [ ] Portfolio (포트폴리오)
  - [ ] Position (포지션)
  - [ ] Trade (거래 내역)
- [ ] 기술적 지표 라이브러리
  - [ ] MA (이동평균)
  - [ ] EMA (지수 이동평균)
  - [ ] RSI (상대강도지수)
  - [ ] MACD
  - [ ] 볼린저 밴드
  - [ ] 스토캐스틱
- [ ] 전략 인터페이스
  - [ ] Strategy Interface 정의
  - [ ] Signal 생성 로직
  - [ ] 진입/청산 조건
- [ ] 수동 전략 구현
  - [ ] 이동평균 크로스오버
  - [ ] RSI 과매수/과매도
  - [ ] 볼린저 밴드 브레이크아웃
  - [ ] 전략 조합 (앙상블)
- [ ] API 구현
  - [ ] 전략 생성/수정/삭제
  - [ ] 전략 조회
  - [ ] 전략 파라미터 설정

### Backend - Simulation Service
- [ ] Domain 모델 구현
  - [ ] Simulation (시뮬레이션)
  - [ ] SimulationConfig (설정)
  - [ ] SimulationResult (결과)
  - [ ] SimulationTrade (거래 내역)
- [ ] 백테스팅 엔진
  - [ ] 과거 데이터 재생 엔진
  - [ ] 가상 주문 실행
  - [ ] 수수료 시뮬레이션
  - [ ] 슬리피지 시뮬레이션
- [ ] 성과 측정
  - [ ] 수익률 계산
  - [ ] MDD (Maximum Drawdown)
  - [ ] 샤프 비율
  - [ ] 소티노 비율
  - [ ] 승률/손익비
  - [ ] 평균 보유 기간
- [ ] 최적화 시스템
  - [ ] Grid Search
  - [ ] Walk-Forward Analysis
  - [ ] 병렬 시뮬레이션 실행
- [ ] 리포트 생성
  - [ ] 거래 내역 타임라인
  - [ ] 자산 변동 차트
  - [ ] 성과 지표 요약
  - [ ] PDF 리포트 생성
- [ ] API 구현
  - [ ] 시뮬레이션 생성/시작
  - [ ] 시뮬레이션 상태 조회
  - [ ] 시뮬레이션 결과 조회

### Frontend - Strategy & Simulation
- [ ] 전략 관리
  - [ ] 전략 목록 조회
  - [ ] 전략 생성/수정
  - [ ] 전략 파라미터 설정 UI
  - [ ] 전략 활성화/비활성화
- [ ] 백테스팅 UI
  - [ ] 시뮬레이션 설정 화면
  - [ ] 시뮬레이션 실행
  - [ ] 실시간 진행 상황
- [ ] 성과 리포트
  - [ ] 수익률 차트
  - [ ] 거래 내역 타임라인
  - [ ] 성과 지표 대시보드
  - [ ] 리포트 다운로드 (PDF/Excel)

---

## Phase 3: 실시간 검증 환경 (2개월)

### Backend - VirtualTrade Service
- [ ] Domain 모델 구현
  - [ ] VirtualAccount (가상 계좌)
  - [ ] VirtualOrder (가상 주문)
  - [ ] VirtualPosition (가상 포지션)
  - [ ] VirtualTransaction (가상 거래내역)
  - [ ] VirtualBalance (가상 잔고)
- [ ] 가상 거래 엔진
  - [ ] 실시간 시장 데이터 스트리밍
  - [ ] 전략 시그널 생성 및 실행
  - [ ] 가상 주문 체결 시뮬레이션
  - [ ] 포지션 관리
- [ ] 리스크 관리
  - [ ] 손절/익절 자동 실행
  - [ ] 포지션 크기 관리
  - [ ] 일일 손실 한도
  - [ ] 긴급 중단 시스템
- [ ] 알림 시스템
  - [ ] Slack 알림
  - [ ] Email 알림
  - [ ] 손실 한도 경고
- [ ] 성과 모니터링
  - [ ] 실시간 수익률 추적
  - [ ] 일일/주간/월간 리포트
  - [ ] 전략별 성과 비교
- [ ] API 구현
  - [ ] 가상 계좌 생성/조회
  - [ ] 전략 배포/중지
  - [ ] 포지션 조회
  - [ ] 거래 내역 조회
  - [ ] 수익률 조회

### Frontend - VirtualTrade
- [ ] 가상거래 대시보드
  - [ ] 실시간 포지션 현황
  - [ ] 자산 변동 차트
  - [ ] 전략 제어 (시작/중지)
- [ ] 거래 내역
  - [ ] 주문 내역
  - [ ] 체결 내역
  - [ ] 거래 타임라인
- [ ] 성과 분석
  - [ ] 수익률 차트
  - [ ] 전략별 성과 비교
  - [ ] 리스크 지표
- [ ] 설정
  - [ ] 리스크 한도 설정
  - [ ] 알림 설정

---

## Phase 4: 실전 투입 자동화 (2개월)

### Backend - Trade Service
- [ ] Domain 모델 구현
  - [ ] RealAccount (실계좌)
  - [ ] RealOrder (실주문)
  - [ ] RealPosition (실포지션)
  - [ ] RealTransaction (실거래내역)
  - [ ] RealBalance (실잔고)
- [ ] 실거래 연동
  - [ ] 업비트 주문 API 연동
  - [ ] 주문 실행 (시장가/지정가)
  - [ ] 주문 취소/수정
  - [ ] 체결 내역 동기화
  - [ ] 잔고 실시간 조회
- [ ] 리스크 관리 강화
  - [ ] 실계좌 손실 한도
  - [ ] 강제 청산 시스템
  - [ ] 다단계 승인 시스템
  - [ ] 거래 로그 무결성
  - [ ] 감사 로그 (Audit Log)
- [ ] 보안
  - [ ] API 키 암호화 저장
  - [ ] 2FA (2단계 인증)
  - [ ] IP 화이트리스트
  - [ ] 거래 승인 프로세스
- [ ] 모니터링
  - [ ] 실시간 거래 모니터링
  - [ ] 이상 거래 탐지
  - [ ] 긴급 알림
- [ ] API 구현
  - [ ] 실계좌 연동
  - [ ] 전략 배포/중지
  - [ ] 주문 실행/취소
  - [ ] 포지션 조회
  - [ ] 거래 내역 조회

### Frontend - Trade
- [ ] 실거래 대시보드
  - [ ] 실시간 포지션 현황
  - [ ] 자산 변동 차트
  - [ ] 수익률 대시보드
- [ ] 주문 실행
  - [ ] 수동 주문 UI
  - [ ] 주문 확인/취소
- [ ] 거래 내역
  - [ ] 주문 내역
  - [ ] 체결 내역
  - [ ] 거래 타임라인
- [ ] 리스크 관리
  - [ ] 손실 한도 설정
  - [ ] 긴급 중단 버튼
  - [ ] 알림 설정
- [ ] 보안
  - [ ] 2FA 설정
  - [ ] IP 화이트리스트 관리
  - [ ] API 키 관리

---

## Phase 5: AI 전략 및 확장 (장기)

### Backend - AI Strategy
- [ ] 강화학습 환경
  - [ ] Gym 환경 구성
  - [ ] State/Action/Reward 정의
- [ ] RL 알고리즘 구현
  - [ ] DQN
  - [ ] PPO
  - [ ] A3C
- [ ] 모델 학습
  - [ ] 학습 데이터 준비
  - [ ] 모델 학습 파이프라인
  - [ ] 하이퍼파라미터 튜닝
- [ ] 모델 배포
  - [ ] 모델 서빙
  - [ ] 모델 버전 관리
  - [ ] A/B 테스트

### Backend - Stock Market
- [ ] 한국투자증권 API 연동
  - [ ] 주식 시세 조회
  - [ ] 주문 실행
- [ ] 재무제표 데이터 수집
  - [ ] DART API 연동
  - [ ] 재무 지표 계산
- [ ] 뉴스 데이터 수집
  - [ ] 뉴스 크롤링
  - [ ] 감성 분석

### Backend - Multi Exchange
- [ ] 바이낸스 연동
- [ ] 코인원 연동
- [ ] 차익거래 전략
- [ ] 통합 주문 실행

---

## 공통 작업 (지속적)

### User Service
- [ ] 로그인/로그아웃
- [ ] 회원가입
- [ ] 사용자 프로필 관리
- [ ] 알림 설정
- [ ] 권한 관리 (RBAC)

### 테스트
- [ ] Unit Test (각 서비스별)
- [ ] Integration Test
- [ ] E2E Test
- [ ] Performance Test
- [ ] Security Test

### 문서화
- [✅] 프로젝트 개요
- [✅] 개발 로드맵
- [✅] Market Service 설계
- [ ] Agent Service 설계
- [ ] Simulation Service 설계
- [ ] VirtualTrade Service 설계
- [ ] Trade Service 설계
- [ ] API 문서 (Swagger)
- [ ] 운영 매뉴얼