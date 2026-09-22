# IEUM 작업 종합 요약

기존 본문 기준일: 2026-07-29 · 최신 업데이트: 2026-09-22

## 최신 상태: 임베딩 모델 종료 대응 완료 (2026-09-22)

NVIDIA가 기존 `nvidia/llama-nemotron-embed-1b-v2` 엔드포인트를 종료해 RAG 임베딩 요청이 HTTP 410을 반환했다. `nvidia/nemotron-3-embed-1b`로 전환했고, 문서와 검색 질의 모두 실제 API에서 2048차원 벡터를 반환하는 것을 확인했다.

- 코드 기본값·환경변수 예시·Render Blueprint를 새 모델로 갱신했다. DB에 `embedding_model`을 기록하고 현재 모델의 벡터만 검색하도록 했다.
- Alembic migration, 전체 Chunk 재색인 명령, 모델별 색인 상태 조회, 임베딩 API 사전 점검, 수동 GitHub Actions 재색인 워크플로를 추가했다. 키와 DB 연결 문자열은 GitHub Secret으로 설정하고 저장소에는 기록하지 않았다.
- 로컬 Backend `86 passed, 1 skipped`; GitHub Actions에서 SQLite·Mock 테스트, PostgreSQL·pgvector 통합 테스트와 이미지 빌드가 통과했다.
- [PR #11](https://github.com/henryeffel/IEUM_ai_agent/pull/11)을 병합한 뒤 Supabase의 10개 Chunk를 새 모델로 재색인했다. [실행 기록](https://github.com/henryeffel/IEUM_ai_agent/actions/runs/35671565928)은 `reindexed_chunks=10`, `ready_for_search=True`를 보여 준다.
- 공개 Render API는 새 모델을 보고했고, 출장비 규정을 근거로 계획 생성 → 승인 → Mock To-do 2건 실행이 `SUCCEEDED`로 완료됐다. 실제 Microsoft 365 작업은 발생하지 않았다.
- 운영 결과는 [임베딩 모델 종료 및 교체 기록](./embedding-model-eol.md)에 정리했고 [문서 PR #12](https://github.com/henryeffel/IEUM_ai_agent/pull/12)로 `main`에 반영했다.

현재 공개 데모는 정상 검증됐다. 다음 모델 교체에서 검색 중단 시간을 줄이려면 별도 색인 세대에 재임베딩한 뒤 검색 대상을 전환하는 절차가 필요하다. 아래 2026-07-29 본문의 남은 작업 목록은 당시 계획이며 현재 완료 상태를 나타내지 않는다.

## 1. 프로젝트 방향

기존 IEUM 팀 프로젝트를 다음 흐름을 수행하는 업무 실행형 AI Agent
포트폴리오로 리팩터링하고 있다.

```text
회의 Transcript
→ LLM 구조화 분석
→ 조직 지식 검색(RAG)
→ 근거 기반 Action Plan 생성
→ 사용자 승인
→ Calendar·To Do·Email 실행
→ 실행 결과와 이력 저장
```

현재 개발 기준은 `ms-2nd-project-integration-ver-1`이다.
`ms-2nd-project-publish`는 과거 배포 구조 참고용 보존본이며 GitHub 게시
범위에서 제외했다.

## 2. 완료된 구현

### 저장소와 보안

- 기존 Azure 환경파일과 하드코딩 Secret을 제거했다.
- `.env.example`과 `.gitignore`를 추가했다.
- NVIDIA API 키는 Backend 환경변수로만 사용한다.
- API 키 로그, 서명된 Logic Apps URL과 기존 팀원 이메일을 제거했다.
- Mock Mode에서는 Azure Provider를 import하거나 초기화하지 않는다.
- 커밋 대상에서 Secret 후보 패턴이 발견되지 않은 것을 확인했다.

### LLM과 회의 분석

- `LLMProvider` 인터페이스를 정의했다.
- `NvidiaLLMProvider`와 `MockLLMProvider`를 구현했다.
- 한국어 회의 Transcript를 다음 Schema로 구조화한다.

```text
summary
decisions
action_items
├─ task
├─ assignee
└─ due_date
open_issues
```

- Pydantic으로 LLM JSON을 검증한다.
- 잘못된 JSON과 Schema 불일치는 HTTP 502로 처리한다.
- 실제 NVIDIA NIM 한국어 분석 호출을 검증했다.

### 상태 기반 Action Workflow

- Action Plan 생성·조회·승인·거절·실행 API를 구현했다.
- 상태 전이는 다음과 같다.

```text
PENDING_APPROVAL
├─ REJECTED
└─ APPROVED
      ↓
   EXECUTING
      ├─ SUCCEEDED
      ├─ PARTIALLY_SUCCEEDED
      └─ FAILED
```

- 승인 전 실행을 서버에서 거부한다.
- SQL 조건부 UPDATE와 `action_id` unique constraint로 중복 실행을 막는다.
- 실행 횟수, Provider, latency, 오류와 외부 리소스 ID를 저장한다.
- 일부 Action만 성공하면 `PARTIALLY_SUCCEEDED`로 기록한다.

### Productivity Provider

- `ProductivityProvider` 인터페이스를 정의했다.
- `MockMicrosoft365Provider`를 구현했다.
- Calendar, Microsoft To Do와 Email Tool을 지원한다.
- 성공, 인증 실패, timeout, 부분 실패와 중복 오류 시나리오를 재현한다.

### RAG와 pgvector

- `EmbeddingProvider`와 `VectorSearchProvider` 인터페이스를 정의했다.
- Mock/NVIDIA Embedding과 Mock/pgvector 검색 Provider를 구현했다.
- 문서 Chunk 색인, upsert, top-k, category 필터와 minimum score를 지원한다.
- 검색 결과에 Chunk ID, 문서 ID, 제목과 출처 URL을 포함한다.
- 실제 NVIDIA 2,048차원 Embedding 호출과 한국어 검색을 검증했다.
- 근거 Chunk가 없으면 외부 실행 계획 생성을 거부한다.
- Action Plan에 `evidence_chunk_ids`를 저장한다.

### Docker와 CI

- Python 3.12 기반 Backend Dockerfile을 작성했다.
- Backend를 non-root 사용자로 실행한다.
- PostgreSQL/pgvector와 Backend를 위한 `compose.yaml`을 작성했다.
- DB와 Backend health check를 구성했다.
- GitHub Actions에서 다음을 자동 검증한다.

```text
pgvector/pgvector:pg16 서비스 시작
→ Python 3.12 의존성 설치
→ SQLite·Mock 회귀 테스트
→ PostgreSQL/pgvector 통합 테스트
→ Backend Docker 이미지 빌드
```

## 3. 구현된 주요 API

```text
GET  /
GET  /health/live
GET  /health/ready

POST /api/v1/meetings/analyze
POST /analyze-meeting

POST /api/v1/knowledge/chunks
POST /api/v1/knowledge/search

POST /api/v1/action-plans
POST /api/v1/action-plans/grounded
GET  /api/v1/action-plans/{plan_id}
POST /api/v1/action-plans/{plan_id}/approve
POST /api/v1/action-plans/{plan_id}/reject
POST /api/v1/action-plans/{plan_id}/execute
```

## 4. 검증 결과

### 로컬

- SQLite·Mock 자동 테스트: `23 passed`
- Python compile 검사: 통과
- 로컬 PostgreSQL이 없을 때 통합 테스트는 명시적으로 skip
- `.env` Git 제외 확인
- 커밋 대상 Secret 후보 패턴 검사: 발견 없음

### GitHub Actions

- Backend CI: 성공
- PostgreSQL/pgvector 통합 테스트: 성공
- 2,048차원 Vector 저장·검색: 성공
- PostgreSQL 동시 실행 선점: 성공
- 동일 Action 실행 횟수 1회 유지: 성공
- Backend Docker 이미지 빌드: 성공

### Meeting-to-Action E2E

CI의 실제 PostgreSQL/pgvector 환경에서 다음 전체 흐름을 검증했다.

```text
조직 지식 Chunk 색인
→ 회의 Transcript 분석
→ pgvector 근거 검색
→ 근거 기반 To Do Action Plan 생성
→ PENDING_APPROVAL 상태 확인
→ 사용자 승인
→ Mock Microsoft 365 실행
→ SUCCEEDED 상태 확인
→ attempts=1 및 external_resource_id 확인
→ DB 재조회 결과 일치 확인
```

## 5. GitHub 상태

```text
repository: https://github.com/henryeffel/ai_agent
base branch: main
working branch: agent/add-postgres-e2e
draft PR: https://github.com/henryeffel/ai_agent/pull/1
latest documented commit: dfec000
PR CI: passed
```

주요 커밋:

```text
e7521ea  Add reproducible backend CI and agent workflow
8a4013a  Update CI actions and record verification
6d57a00  Add PostgreSQL meeting-to-action E2E test
448e8e9  Document PostgreSQL E2E verification
dfec000  Record project progress and verification status
```

GitHub 게시에서 제외한 항목:

- 팀 발표 PDF
- JD 이미지
- 루트 임시 `llm_api.py`
- `ms-2nd-project-publish` 과거 보존본
- 로컬 `.env`와 Secret

## 6. 로컬 환경 제약과 대응

로컬 PC는 약 6GB RAM 환경이다. Docker Desktop이 WSL2 VM을 생성할 때
`0x800705aa` 리소스 부족 오류로 시작되지 않았다.

- SFC 검사에서는 Windows 시스템 파일 무결성 위반이 없었다.
- Docker CLI, Compose와 WSL 패키지는 설치돼 있다.
- 로컬 Docker 재설치에 의존하지 않고 GitHub Actions runner에서 Docker,
  PostgreSQL과 pgvector를 검증하는 방식으로 전환했다.
- Compose 구성은 다른 개발 환경에서 재현할 수 있도록 저장소에 유지한다.

## 7. 현재 남은 작업

### P0 마무리

1. 전체 Git 이력 Secret scan
2. 기존 Azure 구현 위치와 Legacy API 경계 정리
3. Draft PR 검토 및 main 병합

### P1 포트폴리오 강화

1. correlation ID 기반 구조화 로그
2. LLM token·latency 기록
3. RAG 평가 질문 약 20개 작성
4. Recall@3와 출처 정확성 측정
5. README 포트폴리오 문구 및 CI 배지
6. 선택적 Microsoft Graph 실제 재연동
7. 3~5분 시연 영상

LangGraph, 멀티에이전트, STT, 화자 분리와 Reranker는 위 작업 이후에
검토한다.
