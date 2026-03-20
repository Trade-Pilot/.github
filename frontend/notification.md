# Notification - 프론트엔드 설계

> 시스템 알림 센터 및 외부 채널(Telegram, Slack) 연동 설계

---

## 1. 개요

트레이딩 봇의 활동 내역(체결, 전략 발생, 에러)을 사용자에게 실시간으로 전달하고, 브라우저를 닫은 상태에서도 중요한 정보를 놓치지 않도록 외부 알림 채널을 관리합니다.

---

## 2. 핵심 기능 설계

### 2.1 인앱 알림 센터 (Internal Center)
*   **실시간 수신**: WebSocket을 통해 새로운 알림 즉시 수신.
*   **중요도 필터**: `All`, `Orders`, `Strategy`, `System (Error/Warning)`으로 필터링 제공.
*   **일괄 읽음 처리**: "모든 알림 읽음" 및 "에러 알림 보관" 기능.

### 2.2 외부 알림 채널 연동 (External Channels)
*   **채널 목록**:
    *   **Discord**: Webhook URL을 통한 연동 (현재 지원).
    *   **향후 지원 예정**: Telegram, App Push 등 (백엔드 확장 시 추가).
*   **연동 테스트**: 설정 직후 "테스트 메시지 발송" 버튼을 통해 정상 연결 여부 확인.
*   **알림 트리거 설정**: 각 채널별로 수신할 알림 종류 선택 (예: Discord에서 에러만, 또는 모든 체결 내역).

---

## 3. UI/UX 포인트

*   **알림 소리 (Sound UI)**: 체결 시 경쾌한 소리, 에러 시 경고음을 옵션으로 제공 (Zustand 설정 저장).
*   **방해 금지 모드 (DND)**: 특정 시간대(야간 등)에는 외부 알림을 차단하는 스케줄링 UI.
*   **알림 가독성**: 긴 에러 메시지는 요약해서 보여주고, 클릭 시 상세 스택 트레이스나 감사 로그로 이동하는 링크 제공.

---

## 4. FSD 디렉토리 구조

```text
src/
├── pages/
│   └── notification-settings/      # 알림 채널 및 트리거 설정 페이지
│
├── widgets/
│   └── notification-badge/          # 헤더 알림 배지 + 드롭다운 (다중 페이지 재사용)
│
├── features/
│   ├── toggle-notification-sound/   # 알림음 온/오프
│   ├── send-test-message/           # 연동 테스트 발송
│   ├── manage-channel/              # 채널 등록/삭제/활성화 (설정 페이지 전용)
│   └── manage-preference/           # 이벤트별 수신 설정 (설정 페이지 전용)
│
└── entities/
    └── notification/               # Notification 도메인 슬라이스
        ├── api/                    # notificationApi
        └── model/                  # schemas.ts (NotificationLog, ChannelConfig)
```

> **분류 기준**: `notification-badge`만 Widget (헤더에서 모든 페이지에 표시). 나머지는 `notification-settings` 페이지 전용이므로 Feature로 분류.
