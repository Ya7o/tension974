import argparse
import sys

from .collector import run_collection_with_storage
from .logging_config import setup_logging
from .providers.firecrawl_provider import FirecrawlProvider
from .providers.simple_http_provider import SimpleHttpProvider
from .settings import (
    get_data_dir,
    get_database_path,
    get_firecrawl_api_key,
    get_log_file,
    get_log_level,
    get_searches_config_path,
)
from .storage import JsonlStorage, SQLiteStorage, StorageError


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Collecte tension974")
    parser.add_argument(
        "--storage",
        choices=("sqlite", "jsonl"),
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

    if args.firecrawl:
        _report_credits(provider, logger)

    # Une collecte intégralement en échec doit faire échouer le job appelant
    # (collect.yml) au lieu de le laisser vert : les observations d'échec sont
    # déjà écrites dans le stockage, rien n'est perdu, mais le signal remonte.
    failures = [o for o in results if o.status != "success"]
    if results and len(failures) == len(results):
        print("ERROR: toutes les recherches ont échoué.", file=sys.stderr)
        logger.error("Toutes les recherches ont échoué (%d/%d).", len(failures), len(results))
        return 1

    return 0


# ~15-30 crédits consommés par semaine (retry compris) : en dessous de ce
# seuil, il reste moins d'un mois de collecte.
_LOW_CREDITS_THRESHOLD = 120


def _report_credits(provider, logger) -> None:
    credits = provider.get_account_credits()
    remaining = credits.get("remaining_credits") if isinstance(credits, dict) else None
    if remaining is None:
        logger.warning(
            "Solde de crédits Firecrawl indisponible : %s",
            credits.get("error", "réponse inattendue") if isinstance(credits, dict) else credits,
        )
        return
    print(f"[CREDITS] {remaining} crédit(s) Firecrawl restant(s)")
    if remaining < _LOW_CREDITS_THRESHOLD:
        logger.warning(
            "Solde Firecrawl bas : %s crédits restants (seuil %s) — moins d'un mois de collecte.",
            remaining,
            _LOW_CREDITS_THRESHOLD,
        )


def _build_storage(name: str):
    if name == "sqlite":
        return SQLiteStorage(get_database_path())
    if name == "jsonl":
        return JsonlStorage(get_data_dir())
    raise StorageError(f"Storage inconnu: {name}")


if __name__ == "__main__":
    raise SystemExit(main())
