# Simulation Service — REST API 명세

## 공통 사항

- 모든 USER 엔드포인트는 `X-User-Id` 헤더 기반으로 리소스 소유권을 검증한다.
- Simulation Service는 자체 DB를 갖지 않으며, Agent Service와 Market Service를 오케스트레이션한다.
- 백테스팅 결과는 Agent Service가 자체 DB에 저장하며, 완료 후 `GET /agents/{id}/backtests`로 조회한다.

### 공통 응답 래퍼

```json
// 에러
{ "code": "S001", "message": "...", "timestamp": "...", "path": "...", "details": null }
```

---

## 백테스팅 실행
**`POST /backtests`** | Role: USER

> SSE(Server-Sent Events) 스트림으로 실시간 백테스팅 결과를 전달한다.
> 클라이언트는 `Accept: text/event-stream` 헤더를 설정해야 한다.

**Request:**
```json
{
  "agentIdentifier": "uuid",
  "symbolIdentifier": "uuid",
  "from": "2024-01-01T00:00:00Z",
  "to": "2024-06-01T00:00:00Z",
  "interval": "HOUR_1"
}
```

| Body Field | 타입 | 필수 | 설명 |
|------------|------|------|------|
| `agentIdentifier` | UUID | Y | 백테스팅할 Agent ID |
| `symbolIdentifier` | UUID | Y | 분석 대상 심볼 ID |
| `from` | OffsetDateTime | Y | 백테스팅 시작 시점 (ISO-8601) |
| `to` | OffsetDateTime | Y | 백테스팅 종료 시점 (ISO-8601) |
| `interval` | String | Y | 캔들 주기 (`MINUTE_1`, `MINUTE_15`, `HOUR_1`, `HOUR_4`, `DAY_1`) |

**Response:** `200 OK` (`Content-Type: text/event-stream`)

### SSE 이벤트 포맷

#### `signal` 이벤트 (기본 이벤트)

각 캔들에 대한 신호 분석 결과를 실시간으로 스트리밍한다.
기본 이벤트이므로 `event:` 필드 없이 `data:` 만 전송된다.

```
data: {"signalType":"BUY","confidence":0.85,"candleOpenTime":"2024-01-15T09:00:00Z","suggestedQuantity":0.05,"cashAfter":5250000.0,"totalValueAfter":10050000.0,"reason":{"indicator":"MA_CROSSOVER","details":{"shortMA":94500000,"longMA":93000000}}}

data: {"signalType":"HOLD","confidence":0.12,"candleOpenTime":"2024-01-15T10:00:00Z","suggestedQuantity":0,"cashAfter":5250000.0,"totalValueAfter":10080000.0,"reason":{"indicator":"MA_CROSSOVER","details":{"shortMA":94800000,"longMA":93200000}}}

data: {"signalType":"SELL","confidence":0.91,"candleOpenTime":"2024-01-20T14:00:00Z","suggestedQuantity":0.05,"cashAfter":10300000.0,"totalValueAfter":10300000.0,"reason":{"indicator":"MA_CROSSOVER","details":{"shortMA":93000000,"longMA":93500000}}}
```

**signal 이벤트 필드:**

| 필드 | 타입 | 설명 |
|------|------|------|
| `signalType` | String | `BUY`, `SELL`, `HOLD` |
| `confidence` | BigDecimal | 신호 신뢰도 (0.0 ~ 1.0) |
| `candleOpenTime` | OffsetDateTime | 해당 캔들의 시작 시각 |
| `suggestedQuantity` | BigDecimal | RiskConfig 기반 산출 수량 (HOLD이면 0) |
| `cashAfter` | BigDecimal | 신호 반영 후 잔여 현금 |
| `totalValueAfter` | BigDecimal | 신호 반영 후 총자산 평가액 |
| `reason` | Object | 신호 근거 (지표명 + 세부 수치) |

#### `done` 이벤트

모든 캔들 처리가 완료되면 전송된다. 이후 SSE 연결이 종료된다.

```
event: done
data: {}
```

#### `error` 이벤트

스트리밍 도중 오류 발생 시 전송된다. 이후 SSE 연결이 종료된다.

```
event: error
data: {"code":"S003","message":"Agent Service gRPC 스트리밍 중 오류 발생"}
```

### 전체 스트림 예시

```
data: {"signalType":"BUY","confidence":0.85,"candleOpenTime":"2024-01-15T09:00:00Z","suggestedQuantity":0.05,"cashAfter":5250000.0,"totalValueAfter":10050000.0,"reason":{"indicator":"MA_CROSSOVER","details":{"shortMA":94500000,"longMA":93000000}}}

data: {"signalType":"HOLD","confidence":0.12,"candleOpenTime":"2024-01-15T10:00:00Z","suggestedQuantity":0,"cashAfter":5250000.0,"totalValueAfter":10080000.0,"reason":{"indicator":"MA_CROSSOVER","details":{"shortMA":94800000,"longMA":93200000}}}

data: {"signalType":"SELL","confidence":0.91,"candleOpenTime":"2024-01-20T14:00:00Z","suggestedQuantity":0.05,"cashAfter":10300000.0,"totalValueAfter":10300000.0,"reason":{"indicator":"MA_CROSSOVER","details":{"shortMA":93000000,"longMA":93500000}}}

event: done
data: {}
```

### 처리 흐름

```
1. POST /backtests 요청 수신
2. RunBacktestCommand 생성
3. Market Service gRPC GetHistoricalCandles 호출 (캐시 적용)
4. 캔들 수 검증 (0건이면 S001 에러)
5. Agent Service gRPC BacktestStrategy 스트리밍 호출
6. 수신된 BacktestSignalResponse를 SSE data 이벤트로 실시간 전달
7. 스트림 완료 시 done 이벤트 발행 후 연결 종료
```

### 스트림 실패 시 동작

| 실패 시점 | 동작 |
|-----------|------|
| Market gRPC 호출 실패 | `S004` 에러 즉시 반환 (SSE 시작 전, JSON 에러 응답) |
| 캔들 데이터 0건 | `S001` 에러 즉시 반환 (SSE 시작 전, JSON 에러 응답) |
| Agent gRPC 스트리밍 도중 연결 끊김 | SSE `error` 이벤트(`S003`) 발행 후 연결 종료 |
| 클라이언트 SSE 연결 끊김 | Agent gRPC 스트림 cancel 후 정리 |

**에러:**
| 코드 | 상황 |
|------|------|
| `S001` | 조회된 캔들 데이터 없음 (기간/심볼 오류) |
| `S002` | Agent Service에서 Agent 없음 |
| `S003` | Agent Service gRPC 스트리밍 중 오류 |
| `S004` | Market Service gRPC 호출 실패 |
| `S005` | `from` >= `to` 또는 미래 날짜 |

---

## 에러 코드 요약

| 코드 | 상수 | HTTP | 설명 |
|------|------|------|------|
| `S001` | `CANDLE_DATA_EMPTY` | 404 | 조회된 캔들 데이터 없음 |
| `S002` | `AGENT_NOT_FOUND` | 404 | Agent Service에서 Agent 없음 |
| `S003` | `BACKTEST_STREAM_ERROR` | 502 | Agent Service gRPC 스트리밍 중 오류 |
| `S004` | `MARKET_SERVICE_UNAVAILABLE` | 502 | Market Service gRPC 호출 실패 |
| `S005` | `INVALID_DATE_RANGE` | 400 | from >= to 또는 미래 날짜 |
