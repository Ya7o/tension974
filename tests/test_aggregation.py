import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from tension974.aggregation import (
    build_search_timeseries,
    compute_health,
    compute_kpis,
    merge_runs,
)

NOW = datetime(2026, 4, 27, 12, 0, tzinfo=timezone.utc)


def _obs(days_ago, count, status="success", median_price=None, error_message=None):
    dt = NOW.replace(hour=0) - __import__("datetime").timedelta(days=days_ago)
    return {
        "search_id": "studio_saint_denis",
        "observed_at": dt.isoformat(),
        "status": status,
        "total_listings_count": count,
        "median_price": median_price,
        "average_price": median_price,
        "price_sample_size": 5 if median_price else None,
        "provider": "direct_http",
        "error_message": error_message,
    }


def test_merge_runs_pairs_start_and_finish():
    events = [
        {"run_id": "abc", "started_at": "2026-04-27T00:00:00+00:00", "status": "running", "provider": "direct_http"},
        {"run_id": "abc", "finished_at": "2026-04-27T00:00:10+00:00", "status": "success"},
    ]
    merged = merge_runs(events)
    assert len(merged) == 1
    run = merged[0]
    assert run["status"] == "success"
    assert run["provider"] == "direct_http"
    assert run["duration_seconds"] == 10
    assert run["category"] == "none"


def test_merge_runs_classifies_blocked_failure():
    events = [
        {"run_id": "x1", "started_at": "2026-04-27T00:00:00+00:00", "status": "running", "provider": "firecrawl"},
        {"run_id": "x1", "finished_at": "2026-04-27T00:00:05+00:00", "status": "failed",
         "error_message": "403 Forbidden - DataDome"},
    ]
    merged = merge_runs(events)
    assert merged[0]["category"] == "blocked"


def test_merge_runs_unfinished_run_stays_running():
    events = [
        {"run_id": "y1", "started_at": "2026-04-27T00:00:00+00:00", "status": "running", "provider": "firecrawl"},
    ]
    merged = merge_runs(events)
    assert merged[0]["status"] == "running"
    assert merged[0]["category"] == "running"
    assert merged[0]["duration_seconds"] is None


def test_build_search_timeseries_filters_and_sorts():
    observations = [
        _obs(days_ago=1, count=10),
        {**_obs(days_ago=5, count=5), "search_id": "other_search"},
        _obs(days_ago=3, count=8),
    ]
    series = build_search_timeseries(observations, "studio_saint_denis")
    assert [p["count"] for p in series] == [8, 10]


def test_compute_kpis_delta_7d_and_30d():
    series = build_search_timeseries([
        _obs(days_ago=40, count=100),
        _obs(days_ago=10, count=80),
        _obs(days_ago=1, count=70),
    ], "studio_saint_denis")
    kpis = compute_kpis(series, now=NOW)
    assert kpis["latest_count"] == 70
    assert kpis["delta_7d"]["delta"] == -10
    assert kpis["delta_30d"]["delta"] == -30


def test_compute_kpis_reports_last_failure():
    series = build_search_timeseries([
        _obs(days_ago=2, count=70),
        _obs(days_ago=1, count=None, status="failed", error_message="429 Too Many Requests"),
    ], "studio_saint_denis")
    kpis = compute_kpis(series, now=NOW)
    assert kpis["last_failure"]["category"] == "rate_limited"


def test_compute_health_stale_detection():
    merged = merge_runs([
        {"run_id": "a", "started_at": "2026-04-01T00:00:00+00:00", "status": "running", "provider": "p"},
        {"run_id": "a", "finished_at": "2026-04-01T00:00:05+00:00", "status": "success"},
    ])
    health = compute_health(merged, now=NOW)
    assert health["is_stale"] is True
    assert health["stale_days"] == 26


def test_compute_health_not_stale_when_recent():
    merged = merge_runs([
        {"run_id": "a", "started_at": "2026-04-26T00:00:00+00:00", "status": "running", "provider": "p"},
        {"run_id": "a", "finished_at": "2026-04-26T00:00:05+00:00", "status": "success"},
    ])
    health = compute_health(merged, now=NOW)
    assert health["is_stale"] is False
    assert health["success_rate_30d"] == 1.0
