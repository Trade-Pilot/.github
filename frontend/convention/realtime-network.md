<!-- 원본: frontend/convention.md — Section 29~30: WebSocket 동기화, 네트워크 장애 -->

## 29. WebSocket + TanStack Query 동기화 전략

실시간 데이터(WebSocket)와 서버 상태(TanStack Query) 간 일관성을 보장하는 규칙.

**데이터 흐름**:
```
초기 로드: TanStack Query useQuery() → API 호출 → 캐시 저장
실시간 갱신: WebSocket 메시지 수신 → queryClient.setQueryData() 직접 갱신
폴백: WebSocket 연결 끊김 → TanStack Query refetchOnWindowFocus로 복구
```

```typescript
// ✅ WebSocket 메시지로 TanStack Query 캐시 직접 갱신
const queryClient = useQueryClient()

useWebSocketSubscription('portfolio:{agentIdentifier}', (data) => {
  queryClient.setQueryData(
    ['agents', agentIdentifier, 'portfolio'],
    data
  )
})

// ✅ WebSocket 연결 끊김 시 자동 폴백
useQuery({
  queryKey: ['agents', agentIdentifier, 'portfolio'],
  queryFn: () => agentApi.getPortfolio(agentIdentifier),
  refetchInterval: isWebSocketConnected ? false : 5000,  // WS 끊기면 5초 폴링
})
```

**우선순위**:
1. WebSocket (실시간, 최우선)
2. TanStack Query 캐시 (WebSocket 갱신 반영)
3. 폴링 (WebSocket 장애 시 폴백)

**BroadcastChannel과의 관계**:
- BroadcastChannel: 로컬 탭 간 UI 상태 동기화 (예: EMERGENCY_STOP, AUTH_LOGOUT)
- WebSocket/TanStack Query: 서버 데이터 동기화
- BroadcastChannel은 서버 데이터를 전파하지 않는다 (각 탭이 독립적으로 WebSocket 구독)

## 30. 네트워크 장애 복구 전략

**Latency 경고 자동 해제**:
- Latency < 100ms가 5초 연속 유지 → Grayscale 자동 해제
- 해제 시 "연결이 복구되었습니다" 토스트 표시 (3초 후 자동 닫힘)

**주문 버튼 재활성화**:
- WebSocket 재연결 + Health Check 통과 → 자동 재활성화
- 재활성화 전 "주문 기능이 복구되었습니다" 확인 토스트

**오프라인 모드**:
- `navigator.onLine` + WebSocket 상태로 감지
- 오프라인 시: 읽기 전용 모드 (캐시된 데이터 표시), 쓰기 작업 비활성화
- 온라인 복구 시: TanStack Query invalidateQueries() 전체 갱신
