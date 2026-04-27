#!/usr/bin/env python3
"""Smoke test: real Firecrawl call against Leboncoin."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from tension974.settings import (
    get_firecrawl_api_key, get_database_path,
    get_searches_config_path, get_log_level, get_log_file,
)
from tension974.logging_config import setup_logging
from tension974.extraction import extract_total_listings_count
from tension974.collector import run_collection
from tension974.providers.firecrawl_provider import FirecrawlProvider

if __name__ == "__main__":
    logger = setup_logging(get_log_level(), get_log_file())

    api_key = get_firecrawl_api_key()
    if not api_key:
        print("SKIP: FIRECRAWL_API_KEY is not set. Cannot run smoke test.")
        print("To run the smoke test: add FIRECRAWL_API_KEY=your_key in .env")
        sys.exit(0)

    print("Running Firecrawl smoke test...")
    provider = FirecrawlProvider(api_key=api_key)

    url = "https://www.leboncoin.fr/recherche?text=t3&locations=Saint-Denis_97400__-20.89076_55.45851_5000_1000&from=rs"
    result = provider.fetch(url)

    print(f"Provider: {result.provider}")
    print(f"Success: {result.success}")
    print(f"Content type: {result.content_type}")
    print(f"Content length: {len(result.content)} chars")

    if not result.success:
        print(f"ERROR: {result.error_message}")
        sys.exit(1)

    print("\n--- Content preview (first 500 chars) ---")
    print(result.content[:500])
    print("---")

    count = extract_total_listings_count(result.content)
    if count is not None:
        print(f"\nExtracted count: {count} annonces")
    else:
        print("\nWARNING: Could not extract count from content.")

    # Store result in DB
    db_path = get_database_path()
    config_path = get_searches_config_path()
    observations = run_collection(config_path, db_path, provider)
    for obs in observations:
        if obs.status == "success":
            print(f"[STORED] {obs.search_id}: {obs.total_listings_count} annonces at {obs.observed_at}")
        else:
            print(f"[FAILED] {obs.search_id}: {obs.error_message}")
