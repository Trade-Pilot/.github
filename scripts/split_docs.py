#!/usr/bin/env python3
"""대형 문서 분할 스크립트 - git HEAD에서 원본을 읽고 하위 파일로 분할"""
import os
import subprocess

BASE = "/Users/sonkanghyeon/Project/side/Trade-Pilot-Documnet"

def read_from_git(src_path):
    """git HEAD에서 원본 파일 내용을 읽어온다"""
    result = subprocess.run(
        ["git", "show", f"HEAD:{src_path}"],
        capture_output=True, text=True, cwd=BASE
    )
    if result.returncode != 0:
        raise RuntimeError(f"git show failed for {src_path}: {result.stderr}")
    return result.stdout.splitlines(keepends=True)

def split_file(src_path, splits):
    lines = read_from_git(src_path)
    for start, end, dest, desc in splits:
        dest_full = os.path.join(BASE, dest)
        os.makedirs(os.path.dirname(dest_full), exist_ok=True)
        with open(dest_full, "w") as out:
            out.write(f"<!-- 원본: {src_path} — {desc} -->\n\n")
            out.writelines(lines[start-1:end])
    print(f"  {src_path}: {len(splits)} files created")

# frontend/convention.md
split_file("frontend/convention.md", [
    (38, 160, "frontend/convention/architecture.md", "Section 1~3: FSD 레이어, 디렉토리 네이밍, Import 규칙"),
    (161, 332, "frontend/convention/typescript.md", "Section 4: TypeScript 타입 컨벤션"),
    (333, 451, "frontend/convention/styling.md", "Section 5: Tailwind CSS 토큰 컨벤션"),
    (452, 585, "frontend/convention/components.md", "Section 6: 컴포넌트 작성 규칙"),
    (586, 728, "frontend/convention/state-management.md", "Section 7~8: Zustand, TanStack Query"),
    (729, 825, "frontend/convention/security-error.md", "Section 9~10: 보안, 에러 처리"),
    (826, 913, "frontend/convention/performance.md", "Section 11: 성능 최적화"),
    (914, 1131, "frontend/convention/testing-style.md", "Section 12~15: 테스트, 환경변수, ESLint/Prettier, Git"),
    (1132, 1742, "frontend/convention/design-system.md", "Section 16~24: 디자인 시스템, 타이포, 스페이싱, 반응형, z-index, 레이아웃, 아이콘"),
    (1743, 2019, "frontend/convention/workflow.md", "Section 25: 개발 워크플로우 + 부록"),
    (2020, 2140, "frontend/convention/api-financial.md", "Section 26~28: API 에러, 금융 데이터, 시간대"),
    (2141, 2195, "frontend/convention/realtime-network.md", "Section 29~30: WebSocket 동기화, 네트워크 장애"),
    (2196, 2241, "frontend/convention/responsive-chart.md", "Section 31~32: 반응형 브레이크포인트, 차트 오버레이"),
])

# backend/testing-strategy.md
split_file("backend/testing-strategy.md", [
    (1, 583, "backend/testing/unit-test.md", "Section 1~2: 테스트 피라미드, 단위 테스트"),
    (584, 890, "backend/testing/integration-test.md", "Section 3~4: 통합 테스트, E2E 테스트"),
    (891, 1228, "backend/testing/mock-coverage.md", "Section 5~9: Mock 전략, 커버리지, 네이밍, CI, 데이터 관리"),
])

# backend/code-convention.md
split_file("backend/code-convention.md", [
    (1, 62, "backend/convention/structure.md", "Section 1~2: 기술 스택, 프로젝트 구조"),
    (63, 193, "backend/convention/naming.md", "Section 3: 네이밍 규칙"),
    (194, 290, "backend/convention/domain-layer.md", "Section 4: 도메인 모델 규칙"),
    (291, 539, "backend/convention/app-infra-layer.md", "Section 5~6: Application/Infrastructure 계층"),
    (540, 793, "backend/convention/error-tx-logging.md", "Section 7~10: 예외, 트랜잭션, 동시성, 로깅"),
    (794, 1009, "backend/convention/test-style.md", "Section 11~부록: 테스트, 코드 스타일, 공통 모듈, 체크리스트"),
])

# backend/business-logic.md
split_file("backend/business-logic.md", [
    (1, 347, "backend/business-logic/indicators.md", "Section 1: 기술적 지표"),
    (348, 559, "backend/business-logic/signals.md", "Section 2: 전략 신호 생성"),
    (560, 720, "backend/business-logic/risk-management.md", "Section 3: 리스크 관리"),
    (721, 968, "backend/business-logic/performance-metrics.md", "Section 4 + 부록: 성과 지표, 공통 상수"),
])

# backend/database-migration.md
split_file("backend/database-migration.md", [
    (1, 79, "backend/database/flyway-setup.md", "Section 1~2: Flyway 설정, 버전 네이밍"),
    (80, 736, "backend/database/initial-migrations.md", "Section 3: 서비스별 초기 마이그레이션 SQL"),
    (737, 793, "backend/database/timescaledb.md", "Section 4~5: TimescaleDB, 파티션 자동 생성"),
    (794, 951, "backend/database/rollback-policy.md", "Section 6~8 + 부록: 롤백, 환경별 설정, 데이터 보관"),
])

print("\nAll sub-files created!")
