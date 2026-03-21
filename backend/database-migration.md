# Flyway 데이터베이스 마이그레이션 전략

> Trade Pilot 프로젝트의 서비스별 DB 마이그레이션 관리 전략 및 초기 스키마 정의
>
> 이 문서는 목차 역할을 합니다. 상세 내용은 `database/` 하위 파일을 참조하세요.

---

## 목차

| 파일 | 섹션 | 설명 |
|------|------|------|
| [flyway-setup.md](database/flyway-setup.md) | 1~2 | Flyway 설정, 버전 네이밍 |
| [initial-migrations.md](database/initial-migrations.md) | 3 | 서비스별 초기 마이그레이션 SQL |
| [timescaledb.md](database/timescaledb.md) | 4~5 | TimescaleDB, 파티션 자동 생성 |
| [rollback-policy.md](database/rollback-policy.md) | 6~8 + 부록 | 롤백, 환경별 설정, 데이터 보관 |
