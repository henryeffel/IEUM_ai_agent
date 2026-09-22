# IEUM 포트폴리오 개발 문서

최신 공개 배포 결과는 [공개 배포 및 검증 기록](./deployment-verification.md)에서 확인할 수 있다.

이 폴더는 IEUM 프로젝트를 AI Agent 개발자 JD에 부합하는 포트폴리오로 발전시키기 위한 실행 계획을 정리한다.

## 문서

- [임베딩 모델 종료 및 교체 기록](./embedding-model-eol.md)
- [P0 제출 전 Release Checklist](./p0-release-checklist.md)
- [작업 종합 요약](./work-summary.md)
- [구현 진행 기록](./implementation-progress.md)
- [Agentic Coding 사례](./agentic-development-case-study.md)
- [재현 가능한 데모](./demo.md)
- [Copilot Studio 연동 준비](./copilot-studio-integration.md)
- [Microsoft Graph Provider](./microsoft-graph-provider.md)
- [공개 데모 배포 계획](./open-demo-deployment-plan.md)
- [포트폴리오 개발 계획](./portfolio-development-plan.md)
- [개발 작업 로그](./development-log.md)
- [현재 개발 현황](./current-status.md)
- [Docker 설치 및 검증 준비](./docker-setup.md)

## 프로젝트 목표

IEUM을 새로 만드는 대신 기존 구현을 업무 실행형 AI Agent로 제품화·리팩터링한다.

> 회의 기록 → 조직 지식 검색(RAG) → 실행 계획 생성 → 사용자 승인 → 일정·메일·To-do 실행 → 실행 이력 관리

Azure 구독이 만료된 현재 환경에서는 NVIDIA NIM, PostgreSQL/pgvector와 Mock Microsoft 365 Provider로 재현 가능한 데모를 제공한다. 기존 Azure 구현은 과거 실제 사용 경험의 근거로 보존한다.

## 범위 원칙

- P0: Secret 제거, NVIDIA LLM, 상태 기반 Workflow, 승인, 멱등성, Mock Microsoft 365, RAG, Docker, 핵심 테스트
- P1: 구조화 로그, RAG 평가, 선택적 Microsoft Graph 재연동, CI 및 시연 영상
- 후순위: LangGraph, 멀티에이전트, IaC, STT, 화자 분리, Reranker

P0가 완료되기 전에는 후순위 기능을 추가하지 않는다.
