import logging
import time
import yaml
from datetime import datetime, timezone

from .models import FetchResult, Observation, SearchConfig
from .extraction import extract_price_stats, extract_total_listings_count
from .providers.base import FetchProvider
from .storage import SQLiteStorage, Storage

logger = logging.getLogger("tension974.collector")
_MAX_FETCH_ATTEMPTS = 2
_RETRY_DELAY_SECONDS = 5


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


def collect_one_with_storage(search: SearchConfig, provider: FetchProvider, storage: Storage) -> Observation:
    logger.info("Collecting: %s (%s)", search.name, search.url)
    observed_at = _now_iso()

    fetch: FetchResult = _fetch_with_retry(search, provider)

    if not fetch.success:
        obs = Observation(
            search_id=search.id,
            observed_at=observed_at,
            status="failed",
            provider=fetch.provider,
            error_message=fetch.error_message,
            # Keep the served page: on an anti-bot block it is the only clue
            # ("Please enable JS and disable any ad blocker" = DataDome).
            raw_total_listings_text=fetch.content[:500] if fetch.content else None,
            credits_used=fetch.credits_used,
        )
        storage.insert_observation(obs)
        logger.warning("Collection failed for %s: %s", search.id, fetch.error_message)
        return obs

    # A successful fetch is now guaranteed to carry a count: _fetch_with_retry
    # rejects any page without one, so there is a single failure path above.
    count = extract_total_listings_count(fetch.content)
    raw_text = _find_raw_text(fetch.content)
    price_stats = extract_price_stats(fetch.content)

    obs = Observation(
        search_id=search.id,
        observed_at=observed_at,
        status="success",
        provider=fetch.provider,
        total_listings_count=count,
        raw_total_listings_text=raw_text,
        median_price=price_stats.median_price if price_stats else None,
        average_price=price_stats.average_price if price_stats else None,
        price_sample_size=price_stats.sample_size if price_stats else None,
        min_price=price_stats.min_price if price_stats else None,
        max_price=price_stats.max_price if price_stats else None,
        credits_used=fetch.credits_used,
    )
    storage.insert_observation(obs)
    if price_stats:
        logger.info(
            "Collected %d annonces for %s, median price=%d EUR, average price=%d EUR (%d prices)",
            count,
            search.id,
            price_stats.median_price,
            price_stats.average_price,
            price_stats.sample_size,
        )
    else:
        logger.info("Collected %d annonces for %s", count, search.id)
    return obs


def _fetch_with_retry(search: SearchConfig, provider: FetchProvider) -> FetchResult:
    last_result: FetchResult | None = None
    total_credits = 0
    for attempt in range(1, _MAX_FETCH_ATTEMPTS + 1):
        result = provider.fetch(search.url)
        if result.credits_used:
            total_credits += result.credits_used

        # Leboncoin's anti-bot serves its challenge page with a 200, so the
        # fetch "succeeds" while the body holds no listings count. Judging on
        # transport alone let those runs through unretried; a page without a
        # count is a failed fetch, and these blocks are intermittent enough
        # that the retry below usually clears them.
        if result.success and extract_total_listings_count(result.content) is None:
            result = FetchResult(
                success=False,
                content=result.content,
                content_type=result.content_type,
                provider=result.provider,
                status_code=result.status_code,
                error_message="No listings count found in content.",
                credits_used=result.credits_used,
                raw_metadata=result.raw_metadata,
            )

        if result.success:
            if total_credits:
                result.credits_used = total_credits
            return result

        last_result = result
        if attempt < _MAX_FETCH_ATTEMPTS:
            logger.warning(
                "Fetch failed for %s, retrying once in %ss: %s",
                search.id,
                _RETRY_DELAY_SECONDS,
                result.error_message,
            )
            time.sleep(_RETRY_DELAY_SECONDS)

    if last_result:
        if total_credits:
            last_result.credits_used = total_credits
        return last_result

    return FetchResult(
        success=False,
        provider=provider.name,
        error_message="Fetch failed without result.",
    )


def collect_one(search: SearchConfig, provider: FetchProvider, db_path: str) -> Observation:
    storage = SQLiteStorage(db_path)
    storage.initialize()
    return collect_one_with_storage(search, provider, storage)


def _find_raw_text(content: str) -> str | None:
    import re
    m = re.search(r"(\d[\d\s ]*\s*annonce[s]?)", content, re.IGNORECASE)
    return m.group(0) if m else None


def run_collection(config_path: str, db_path: str, provider: FetchProvider) -> list[Observation]:
    return run_collection_with_storage(config_path, provider, SQLiteStorage(db_path))


def run_collection_with_storage(
    config_path: str,
    provider: FetchProvider,
    storage: Storage,
) -> list[Observation]:
    storage.initialize()
    searches = load_searches(config_path)
    active = [s for s in searches if s.active]

    run_id = storage.start_run(provider.name)
    results = []
    errors = []

    try:
        for search in active:
            storage.upsert_search(search)
            obs = collect_one_with_storage(search, provider, storage)
            results.append(obs)
            if obs.status != "success":
                errors.append(obs)

        status = "success" if not errors else ("partial" if results else "failed")
        err_msg = "; ".join(o.error_message or "" for o in errors) if errors else None
        storage.finish_run(run_id, status, err_msg)
    except Exception as exc:
        storage.finish_run(run_id, "failed", str(exc))
        raise

    return results
