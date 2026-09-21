# 임베딩 모델 종료 및 교체 기록

기록일: 2026-09-22

## 장애

NVIDIA 임베딩 요청이 HTTP 410 `Gone`을 반환했다. 응답은 `nvidia/llama-nemotron-embed-1b-v2`가 2026-08-25 09:00 UTC에 수명을 마쳐 더 이상 제공되지 않는다고 명시한다. 검색 질의와 문서 시드 모두 이 모델에 의존하므로 공개 RAG 흐름이 중단된다.

NVIDIA [모델 페이지](https://build.nvidia.com/nvidia/llama-nemotron-embed-1b-v2)는 해당 엔드포인트를 Deprecated로 표시한다. 대체 후보인 [`nvidia/nemotron-3-embed-1b`](https://build.nvidia.com/nvidia/nemotron-3-embed-1b)는 현재 제공되는 텍스트 임베딩 모델이다. [NVIDIA API 문서](https://docs.nvidia.com/nim/nemo-retriever/embedding/2.2/reference.html)에 따르면 출력은 기존 DB 컬럼과 같은 2048차원이다.

## 이번 변경과 운영 절차

코드 기본값과 두 환경변수 예시를 새 모델로 변경했다. `NVIDIA_EMBEDDING_MODEL`을 이미 지정한 Render 및 로컬 환경은 **별도로 변경**해야 한다. 기본값 변경만으로 운영 설정은 바뀌지 않는다.

2048차원 일치는 DB 타입 호환성만 뜻한다. 두 모델의 벡터를 같은 검색 공간에서 섞으면 검색 품질을 보장할 수 없다. 운영 전환 절차:

1. `EMBEDDING_PROVIDER=nvidia`, `NVIDIA_EMBEDDING_MODEL=nvidia/nemotron-3-embed-1b`, `NVIDIA_API_KEY`를 설정한 뒤 Backend 디렉터리에서 `python -m ieum.demo probe-embedding`을 실행한다. 출력의 `provider=nvidia_embedding`, 모델명과 2048차원을 확인한다. 이 명령은 `passage`와 `query`를 각각 호출하며 DB를 읽거나 쓰지 않는다.
2. Supabase 운영 DB를 백업하고 기존 Chunk의 본문·개수를 확인한다. 번들 Demo 시드 10개 외에 사용자 문서가 있는지 확인한다. `scripts/verify_supabase.py`는 테이블을 downgrade/recreate하는 전용 테스트 DB 도구이므로 운영 DB에 실행하지 않는다.
3. 코드를 배포하고 Render의 `NVIDIA_EMBEDDING_MODEL`이 새 값인지 확인한다. `render.yaml`에도 새 모델을 지정했다. 서비스 시작 시 Alembic migration 후 Demo 시드가 upsert된다. 이때 기존 행의 모델 ID는 비어 있고 검색 결과가 일부 또는 전부 비어 있을 수 있으므로 점검 시간에 진행한다.
4. 배포된 코드와 Supabase 운영 DB 연결을 갖춘 운영자 환경에서 `python -m ieum.demo index-status`로 모델별 Chunk 수를 확인한다. 이어서 `python -m ieum.demo reindex --confirm`으로 모든 Chunk를 새 모델로 재임베딩한다. 두 명령은 Render shell 또는 Supabase `DATABASE_URL`을 환경변수로 설정한 로컬 Backend에서 실행할 수 있다. 연결 문자열과 비밀번호는 출력하거나 저장소에 기록하지 않는다.
5. `index-status`를 다시 실행해 `ready_for_search=True`이고 다른 모델 또는 `<unlabeled>` Chunk가 없는지 확인한다. 한국어 질의의 Top 1~3, 점수 분포, `min_score` 통과 여부도 확인한다. 기존 0.04 기준은 새 모델에서 다시 측정한다.
6. 공개 `/health/ready`에서 `embedding_model=nvidia/nemotron-3-embed-1b`인지 확인하고, 공개 검색과 `PENDING_APPROVAL → APPROVED → SUCCEEDED` 흐름을 확인한다.

저장소에는 `embedding_model` 컬럼과 `python -m ieum.demo reindex --confirm` 명령을 추가했다. 이 명령은 DB에 남아 있는 모든 Chunk 본문을 읽고, 전체 임베딩 API 호출이 끝난 뒤 하나의 트랜잭션으로 벡터와 모델 ID를 갱신한다. 검색은 현재 설정된 모델 ID의 행만 반환한다. Alembic migration 이후 기존 행은 모델 ID가 비어 있어 재색인 전까지 검색에서 제외된다. 따라서 **migration·모델 전환·재색인 사이에는 공개 검색이 비어 있을 수 있으므로 운영 점검 시간에 실행**한다. 재색인 도중 문서 내용이 변경되면 중단한다.

이번 저장소 변경은 **운영 DB 재색인·배포를 수행하지 않았다**. 운영 데이터 전체와 백업을 확인한 뒤 실행해야 한다.

## 2026-09-22 로컬 검증

- Backend `85 passed, 1 skipped`; SQLite migration에 `embedding_model` 컬럼이 생기는 것을 확인했다.
- 임베딩 API 실패 시 재색인 쓰기 트랜잭션에 들어가지 않는 테스트를 통과했다.
- 전용 PostgreSQL DB에서 기존 모델 검색 차단 → 전체 재색인 → 새 모델 검색 성공을 확인하는 통합 테스트를 추가했다. GitHub Actions [Backend CI 실행](https://github.com/henryeffel/IEUM_ai_agent/actions/runs/35668388324)에서 pgvector 서비스 기반 통합 테스트 4건과 SQLite·Mock 테스트 85건, 백엔드 이미지 빌드가 통과했다. 이 결과는 Supabase 운영 DB 검증을 대신하지 않는다. 운영 DB에는 파괴적인 통합 테스트를 실행하지 않는다.
- 초기에는 로컬 API 키가 없어 실제 모델 응답을 확인하지 못했다. 이후 키를 설정한 뒤 `probe-embedding`을 실행했고, `nvidia/nemotron-3-embed-1b`의 passage·query 요청이 모두 성공하여 각각 2048차원을 반환했다. 운영 DB 연결 설정은 없어 재색인은 아직 실행하지 않았다.
- DB 쓰기 없는 임베딩 API 사전 점검 명령과 결과 차원 검증을 추가했다.
- `python -m scripts.probe_demo_retrieval`로 실제 Demo 시드와 동일한 10개 Chunk를 새 모델로 임베딩했다. 기본 한국어 회의록 질의의 Top 1은 `demo-travel-policy-0001`(출장비 규정, score `0.5335`)이었다. 전체 순위는 구매 승인 규정 `0.3103`, 구매 승인 규정 `0.2820`, 출장비 규정 `0.2718`, 회의실 운영 규정 `0.2095` 순이었다. 현재 UI의 `category=policy`, `top_k=1`, `min_score=0.04`에서는 목표 규정이 통과한다. 한 샘플 결과이므로 임계값은 아직 변경하지 않았다.
- DB 읽기 전용 `index-status` 명령을 추가했다. 전체 Chunk 중 현재 모델로 색인된 수와 모델별 분포를 보여 주며, 비어 있거나 혼합된 색인은 `ready_for_search=False`로 표시한다. 운영 DB 연결이 없어 실행 결과는 아직 없다.
- `/health/ready` 응답에 현재 임베딩 Provider와 모델명을 추가했다. 배포 후 설정이 실제 프로세스에 반영됐는지 공개 GET 요청으로 확인할 수 있다.

## 재발 방지 작업

- 저장 벡터에 임베딩 모델 ID와 색인 세대를 기록한다.
- 새 세대에 전체 문서를 적재·검증한 뒤 검색 대상을 전환한다.
- 모델 종료 공지를 감시하고, 모델 교체 시 한국어 검색 평가를 반복한다.
- 원본 Chunk와 재색인 명령을 유지한다. 같은 2048차원 모델로 바꾸더라도 재색인은 필수다.
