# Flyway 설정 & 버전 네이밍 규칙

> 원본: `backend/database-migration.md` Section 1~2

---

## 1. Flyway 설정

### 1.1 Gradle 의존성

```kotlin
// build.gradle.kts
dependencies {
    implementation("org.flywaydb:flyway-core")
    implementation("org.flywaydb:flyway-database-postgresql")
    runtimeOnly("org.postgresql:postgresql")
}
```

### 1.2 application.yml 설정

```yaml
spring:
  flyway:
    enabled: true
    locations: classpath:db/migration
    baseline-on-migrate: true
    baseline-version: "0"
    validate-on-migrate: true
    out-of-order: false
    table: flyway_schema_history
    clean-disabled: true  # prod/stg 환경에서는 반드시 true
```

### 1.3 마이그레이션 파일 위치

```
src/main/resources/db/migration/
├── V20260320_001__create_user_table.sql
├── V20260320_002__create_refresh_token_table.sql
├── V20260320_003__create_outbox_table.sql
└── R__cleanup_expired_data.sql
```

---

## 2. 버전 네이밍 규칙

### 2.1 Versioned Migration

**패턴**: `V{YYYYMMDD}_{순번}__{설명}.sql`

- `YYYYMMDD`: 작성 날짜
- `순번`: 해당 날짜 내 순서 (001, 002, ...)
- `설명`: 변경 내용을 snake_case로 기술

**예시**:
```
V20260320_001__create_user_table.sql
V20260320_002__create_refresh_token_table.sql
V20260321_001__add_nickname_to_user.sql
V20260401_001__rollback_remove_nickname.sql
```

### 2.2 Repeatable Migration

**패턴**: `R__{설명}.sql`

- 파일 내용이 변경될 때마다 재실행됨
- 인덱스 재생성, 뷰 갱신, 데이터 정리 작업에 사용

**예시**:
```
R__create_indexes.sql
R__cleanup_expired_data.sql
```

