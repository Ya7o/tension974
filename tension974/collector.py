import logging
import yaml
from datetime import datetime, timezone
from pathlib import Path

from .models import FetchResult, Observation, SearchConfig
from .extraction import extract_total_listings_count
from .database import (
    init_db, upsert_search, insert_observation,
    start_collection_run, finish_collection_run,
)
from .providers.base import FetchProvider

logger = logging.getLogger("tension974.collector")


def load_searches(config_path: str) -> list[SearchConfig]:
    with open(config_path, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    searches = []
    for item in data.get("searches", []):
        searches.append(SearchConfig(
            id=item["id"],
            name=item["name"],
            platform=item["platform"],
            url=item["url"],
            location=item.get("location", ""),
            property_type=item.get("property_type", ""),
            metric=item.get("metric", "total_listings_count"),
            active=item.get("active", True),
        ))
    return searches


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def collect_one(search: SearchConfig, provider: FetchProvider, db_path: str) -> Observation:
    logger.info("Collecting: %s (%s)", search.name, search.url)
    observed_at = _now_iso()

    fetch: FetchResult = provider.fetch(search.url)

    if not fetch.success:
        obs = Observation(
            search_id=search.id,
            observed_at=observed_at,
            status="failed",
            provider=fetch.provider,
            error_message=fetch.error_message,
            credits_used=fetch.credits_used,
        )
        insert_observation(db_path, obs)
        logger.warning("Collection failed for %s: %s", search.id, fetch.error_message)
        return obs

    count = extract_total_listings_count(fetch.content)
    raw_text = _find_raw_text(fetch.content)

    if count is None:
        obs = Observation(
            search_id=search.id,
            observed_at=observed_at,
            status="failed",
            provider=fetch.provider,
            error_message="No listings count found in content.",
            raw_total_listings_text=fetch.content[:500] if fetch.content else None,
            credits_used=fetch.credits_used,
        )
        insert_observation(db_path, obs)
        logger.warning("Could not extract count for %s", search.id)
        return obs

    obs = Observation(
        search_id=search.id,
        observed_at=observed_at,
        status="success",
        provider=fetch.provider,
        total_listings_count=count,
        raw_total_listings_text=raw_text,
        credits_used=fetch.credits_used,
    )
    insert_observation(db_path, obs)
    logger.info("Collected %d annonces for %s", count, search.id)
    return obs


def _find_raw_text(content: str) -> str | None:
    import re
    m = re.search(r"(\d[\d\s ]*\s*annonce[s]?)", content, re.IGNORECASE)
    return m.group(0) if m else None


def run_collection(config_path: str, db_path: str, provider: FetchProvider) -> list[Observation]:
    init_db(db_path)
    searches = load_searches(config_path)
    active = [s for s in searches if s.active]

    run_id = start_collection_run(db_path, provider.name)
    results = []
    errors = []

    for search in active:
        upsert_search(db_path, search)
        obs = collect_one(search, provider, db_path)
        results.append(obs)
        if obs.status != "success":
            errors.append(obs)

    status = "success" if not errors else ("partial" if results else "failed")
    err_msg = "; ".join(o.error_message or "" for o in errors) if errors else None
    finish_collection_run(db_path, run_id, status, err_msg)

    return results
