# TimescaleDB 설정 & 파티션 자동 생성

> 원본: `backend/database-migration.md` Section 4~5

---

## 4. Market Service — TimescaleDB 설정

### 4.1 Hypertable 변환

`market_candle` 테이블은 일반 PostgreSQL 테이블로 생성한 뒤 TimescaleDB hypertable로 변환한다.

```sql
SELECT create_hypertable('market_candle', 'time',
    chunk_time_interval => INTERVAL '1 month'
);
```

- **chunk_time_interval**: 1개월 단위로 chunk 분리
- TimescaleDB가 chunk 생성/관리를 자동으로 수행하므로 별도 파티션 관리 불필요

### 4.2 Compression 정책

7일이 지난 chunk는 자동으로 압축하여 스토리지 사용량을 절감한다.

```sql
ALTER TABLE market_candle SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'symbol_id, interval',
    timescaledb.compress_orderby = 'time DESC'
);

SELECT add_compression_policy('market_candle', INTERVAL '7 days');
```

- `compress_segmentby`: 심볼+간격별로 세그먼트를 분리하여 조회 성능 유지
- `compress_orderby`: 시간 역순으로 정렬하여 최근 데이터 조회 최적화

### 4.3 Retention 정책

2년 이상 된 데이터는 자동 삭제한다. 삭제 전 Cold Storage(S3 Glacier)로 이동하는 배치 작업이 선행되어야 한다.

```sql
SELECT add_retention_policy('market_candle', INTERVAL '2 years');
```

---

## 5. 파티션 자동 생성 (market_candle 전용)

기존 설계에서 "월별 파티션 자동 생성 스케줄러"로 계획했던 부분은 **TimescaleDB chunk 정책으로 대체**한다.

| 기존 설계 | TimescaleDB 대체 |
|-----------|-----------------|
| 월별 파티션 수동 생성 | `chunk_time_interval => INTERVAL '1 month'` (자동) |
| 파티션 생성 스케줄러 | TimescaleDB 내부 chunk 관리자 (자동) |
| 오래된 파티션 DROP | `add_retention_policy` (자동) |
| 파티션별 압축 | `add_compression_policy` (자동) |

TimescaleDB는 새 데이터 INSERT 시 해당 시간 범위의 chunk가 없으면 자동 생성하므로, 별도 파티션 생성 로직이 불필요하다.
