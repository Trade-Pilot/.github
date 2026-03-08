# Trade-Pilot Infrastructure Documentation

## 현재 클러스터 구성 현황

### 노드 구성
| 역할       | 호스트명     | IP 주소        | 상태      | 설치일        |
| -------- | -------- | ------------ | ------- | ---------- |
| Master1  | master1  | 192.168.0.34 | Running | 2025-07-31 |
| Master2  | master2  | 192.168.0.37 | Running | 2025-07-31 |
| Master3  | master3  | 192.168.0.39 | Running | 2025-07-31 |
| Service1 | service1 | 192.168.0.33 | Running | 2025-07-31 |
| Service2 | service2 | 192.168.0.36 | Running | 2025-07-31 |
| Service3 | service3 | 192.168.0.38 | Running | 2025-07-31 |
| Service4 | service4 | 192.168.0.35 | Running | 2025-07-31 |
| Data     | data     | 192.168.0.29 | Running | 2025-07-31 |
| Infra    | infra    | 192.168.0.12 | Running | 2025-07-31 |


### 클러스터 정보
- **클러스터 타입**: K3s HA 클러스터
- **총 노드 수**: 9개 (마스터 3개, 워커 4개, 데이터 1개, 인프라 1개)
- **K3s 버전**: v1.28.x+k3s1
- **설치 완료일**: 2025년 7월 31일

## 설치된 구성 요소

### 핵심 인프라
- ✅ **K3s**: 경량 Kubernetes 배포
- ✅ **Helm**: Kubernetes 패키지 매니저
- ✅ **ArgoCD**: GitOps 기반 CD 도구
