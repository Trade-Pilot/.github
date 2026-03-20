# Market - 프론트엔드 설계

> Market Service와 연동하는 프론트엔드 설계 문서 (재개발 기준)

---

## 1. 기술 스택

### 1.1 권장 스택

| 분류 | 기존 | 변경 | 이유 |
|------|------|------|------|
| 빌드 도구 | CRA (react-scripts) | **Vite** | Vite HMR 5~10배 빠름 |
| 스타일링 | styled-components | **Tailwind CSS** | 클래스 기반 일관된 디자인 시스템, CSS-in-JS 오버헤드 제거 |
| 서버 상태 | useEffect + useState | **TanStack Query v5** | 캐싱, 자동 리패치, 무한 스크롤 내장 |
| 클라이언트 상태 | Redux Toolkit | **Zustand** | 가벼운 전역 상태 관리 |
| 실시간 처리 | Main Thread | **Web Worker** | 시세 파싱 및 지표 계산 부하 분리 |
| 차트 | Highcharts | **Lightweight Charts** | 금융 특화, 캔버스 기반 고성능 렌더링 |

---

## 2. FSD 디렉토리 구조

(기존 구조 유지...)

---

## 6. 페이지별 상세 설계

### 6.1 수집 현황 대시보드 (`/market/collection`)
(기존 내용 유지...)

### 6.2 캔들 차트 뷰어 (`/market/chart`)

#### 실시간 데이터 엔진 (Web Worker)
메인 스레드의 UI 반응성 보장을 위해 모든 실시간 데이터 가공을 워커로 분리한다. 통신 규격은 `convention.md` 11.5절의 `WorkerCommand/Event` 표준을 따른다.

*   **Worker 책임**: WebSocket 연결 유지, 수신 데이터 JSON 파싱, 기술적 지표(MA 등) 실시간 계산, Latency 측정.
*   **메인 스레드 전달**: `WorkerEvent` 객체로 정제된 데이터와 현재 연결 지연 시간(ms) 전달.

#### Latency & Health UI
*   **Health 배지**: 
    *   `Excellent (< 100ms)`: 녹색 ●
    *   `Fair (100~500ms)`: 노란색 ●
    *   `Poor (> 500ms)`: 빨간색 ●
*   **Data Stale 경고**: 10초 이상 데이터 수신 공백 시 차트 영역에 "연결 지연으로 데이터 업데이트가 중단됨" 오버레이 노출 및 UI Grayscale 처리.

#### CandleChart 위젯 (Memory Management)
수만 개의 데이터를 다룰 때 브라우저 메모리 고갈을 방지한다.
*   **Data Windowing**: 현재 화면에 보이는 범위와 앞뒤 버퍼 데이터만 메모리에 유지하고, 범위를 벗어난 과거 데이터는 순차적으로 해제.
*   **인스턴스 관리**: 심볼 변경 시 기존 차트 인스턴스를 명시적으로 `remove()` 처리하여 메모리 릭 방지.

---

## 7. 라우팅 및 API 클라이언트 (기존 내용 유지)
