#!/usr/bin/env python3
"""Collecte manuelle — mode direct par défaut (0 crédit Firecrawl)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from tension974.settings import (
    get_firecrawl_api_key, get_database_path,
    get_searches_config_path, get_log_level, get_log_file,
)
from tension974.logging_config import setup_logging
from tension974.collector import run_collection
from tension974.providers.simple_http_provider import SimpleHttpProvider
from tension974.providers.firecrawl_provider import FirecrawlProvider

if __name__ == "__main__":
    logger = setup_logging(get_log_level(), get_log_file())

    # Mode direct par défaut — passer --firecrawl pour forcer Firecrawl
    use_firecrawl = "--firecrawl" in sys.argv

    if use_firecrawl:
        api_key = get_firecrawl_api_key()
        if not api_key:
            logger.error("FIRECRAWL_API_KEY manquante dans .env")
            print("ERROR: FIRECRAWL_API_KEY manquante.")
            sys.exit(1)
        provider = FirecrawlProvider(api_key=api_key)
        logger.info("Mode : Firecrawl")
    else:
        provider = SimpleHttpProvider()
        logger.info("Mode : Direct HTTP (0 crédit)")

    db_path = get_database_path()
    config_path = get_searches_config_path()

    results = run_collection(config_path, db_path, provider)

    for obs in results:
        if obs.status == "success":
            credits_info = f" [{obs.credits_used} crédit(s)]" if obs.credits_used else " [0 crédit]"
            print(f"[OK] {obs.search_id}: {obs.total_listings_count} annonces{credits_info}")
        else:
            print(f"[FAIL] {obs.search_id}: {obs.error_message}")
