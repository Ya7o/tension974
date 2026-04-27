import argparse
import sys

from .collector import run_collection_with_storage
from .logging_config import setup_logging
from .providers.firecrawl_provider import FirecrawlProvider
from .providers.simple_http_provider import SimpleHttpProvider
from .settings import (
    get_database_path,
    get_firecrawl_api_key,
    get_google_service_account_json,
    get_google_sheet_id,
    get_log_file,
    get_log_level,
    get_searches_config_path,
)
from .storage import GoogleSheetsStorage, SQLiteStorage, StorageError


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Collecte tension974")
    parser.add_argument(
        "--storage",
        choices=("sqlite", "google_sheets"),
        default="sqlite",
        help="Backend de stockage.",
    )
    parser.add_argument(
        "--firecrawl",
        action="store_true",
        help="Utilise Firecrawl au lieu du mode HTTP direct.",
    )
    args = parser.parse_args(argv)

    logger = setup_logging(get_log_level(), get_log_file())

    if args.firecrawl:
        api_key = get_firecrawl_api_key()
        if not api_key:
            print("ERROR: FIRECRAWL_API_KEY est manquant.", file=sys.stderr)
            logger.error("FIRECRAWL_API_KEY est manquant.")
            return 1
        provider = FirecrawlProvider(api_key=api_key)
        logger.info("Mode provider : Firecrawl")
    else:
        provider = SimpleHttpProvider()
        logger.info("Mode provider : Direct HTTP")

    try:
        storage = _build_storage(args.storage)
        results = run_collection_with_storage(
            get_searches_config_path(),
            provider,
            storage,
        )
    except StorageError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        logger.error("%s", exc)
        return 1

    for obs in results:
        if obs.status == "success":
            credits_info = f" [{obs.credits_used} crédit(s)]" if obs.credits_used else " [0 crédit]"
            print(f"[OK] {obs.search_id}: {obs.total_listings_count} annonces{credits_info}")
        else:
            print(f"[FAIL] {obs.search_id}: {obs.error_message}")

    return 0


def _build_storage(name: str):
    if name == "sqlite":
        return SQLiteStorage(get_database_path())
    if name == "google_sheets":
        return GoogleSheetsStorage(
            get_google_service_account_json(),
            get_google_sheet_id(),
        )
    raise StorageError(f"Storage inconnu: {name}")


if __name__ == "__main__":
    raise SystemExit(main())
