import argparse
from sqlalchemy import inspect

from ieum.config import get_settings
from ieum.database import get_engine, get_session_factory
from ieum.demo.maintenance import DemoMaintenanceService
from ieum.providers.vector_search import get_vector_search_provider
from ieum.providers.embedding import get_embedding_provider
from ieum.demo.reindex import reindex_all
from ieum.demo.embedding_probe import probe_embedding
from ieum.demo.index_status import get_index_status


def main():
    parser = argparse.ArgumentParser(description="IEUM public demo maintenance")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("seed", help="Upsert bundled demo knowledge")
    subparsers.add_parser("probe-embedding", help="Check embedding API without DB writes")
    subparsers.add_parser("index-status", help="Report stored chunks by embedding model")
    reindex = subparsers.add_parser("reindex", help="Re-embed all stored knowledge")
    reindex.add_argument("--confirm", action="store_true")
    cleanup = subparsers.add_parser("cleanup", help="Delete expired demo plans")
    cleanup.add_argument("--older-than-hours", type=int, default=24)
    cleanup.add_argument("--confirm", action="store_true")
    args = parser.parse_args()

    if args.command == "probe-embedding":
        print(probe_embedding(get_embedding_provider()))
        return
    if get_settings().app_mode != "demo":
        parser.error("이 명령은 APP_MODE=demo에서만 실행할 수 있습니다.")
    if args.command == "cleanup" and not args.confirm:
        parser.error("cleanup에는 데이터 삭제 확인을 위한 --confirm이 필요합니다.")
    if args.command == "reindex":
        if not args.confirm:
            parser.error("reindex에는 --confirm이 필요합니다.")
        print(f"reindexed_chunks={reindex_all(get_embedding_provider(), get_session_factory())}")
        return
    if args.command == "index-status":
        columns = {
            column["name"] for column in inspect(get_engine()).get_columns("document_chunks")
        }
        print(get_index_status(
            get_session_factory(),
            get_embedding_provider().model_id,
            schema_has_model="embedding_model" in columns,
        ))
        return
    if args.command == "seed":
        service = DemoMaintenanceService(
            get_vector_search_provider(),
            get_session_factory(),
        )
        print(f"seeded_chunks={service.seed_knowledge()}")
        return
    service = DemoMaintenanceService(None, get_session_factory())
    print(
        "deleted_demo_plans="
        f"{service.cleanup_plans(older_than_hours=args.older_than_hours)}"
    )


if __name__ == "__main__":
    main()
