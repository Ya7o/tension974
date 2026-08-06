"""Contrat du dashboard.json publié.

docs/assets/app.js et charts.js lisent une vingtaine de clés de ce fichier.
Renommer l'une d'elles côté Python casserait la page silencieusement (aucun
test JS n'existe) : ce test verrouille le contrat. Chaque clé listée ici est
réellement lue par le front — si tu en retires une, vérifie d'abord app.js.
"""
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.build_site_data import build

CONFIG_YAML = """
searches:
  - id: studio_saint_denis
    name: "Studio — Saint-Denis"
    platform: leboncoin
    url: "https://www.leboncoin.fr/recherche?text=studio"
    location: "Saint-Denis"
    property_type: "Studio"
    active: true
"""

NOW = datetime.now(timezone.utc)


def _iso(days_ago: float) -> str:
    return (NOW - timedelta(days=days_ago)).isoformat()


def _build_payload(tmp_path) -> dict:
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    config_path = tmp_path / "searches.yaml"
    config_path.write_text(CONFIG_YAML, encoding="utf-8")

    observations = [
        {"search_id": "studio_saint_denis", "observed_at": _iso(8), "status": "success",
         "provider": "firecrawl", "total_listings_count": 100, "median_price": 640,
         "average_price": 650, "price_sample_size": 30, "credits_used": 5},
        {"search_id": "studio_saint_denis", "observed_at": _iso(1), "status": "success",
         "provider": "firecrawl", "total_listings_count": 110, "median_price": 646,
         "average_price": 660, "price_sample_size": 30, "credits_used": 5},
        {"search_id": "studio_saint_denis", "observed_at": _iso(0.5), "status": "failed",
         "provider": "firecrawl",
         "error_message": "Blocked by anti-bot challenge (page asks to enable JS / disable ad blocker)."},
    ]
    runs = [
        {"run_id": "r1", "started_at": _iso(8), "status": "running", "provider": "firecrawl"},
        {"run_id": "r1", "finished_at": _iso(8), "status": "success"},
        {"run_id": "r2", "started_at": _iso(1), "status": "running", "provider": "firecrawl"},
        {"run_id": "r2", "finished_at": _iso(1), "status": "partial",
         "error_message": "Blocked by anti-bot challenge."},
    ]
    (data_dir / "observations.jsonl").write_text(
        "\n".join(json.dumps(r) for r in observations) + "\n", encoding="utf-8")
    (data_dir / "runs.jsonl").write_text(
        "\n".join(json.dumps(r) for r in runs) + "\n", encoding="utf-8")

    return build(data_dir, str(config_path), tmp_path / "docs")


# Clés lues par le front, fichier par fichier (grep app.js / charts.js).
TOP_LEVEL_KEYS = {"generated_at", "searches", "runs", "health"}
HEALTH_KEYS = {
    "success_rate_7d", "success_rate_30d", "category_counts_30d",
    "last_success_at", "last_finished_status", "last_productive_at",
    "stale_days", "is_stale", "stale_after_days", "total_runs",
}
SEARCH_KEYS = {"id", "name", "location", "property_type", "url", "kpis", "timeseries"}
KPI_KEYS = {
    "latest_count", "latest_date", "delta_7d", "delta_30d",
    "latest_median_price", "latest_average_price", "price_sample_size",
    "price_delta_30d", "success_rate_30d", "last_failure",
}
POINT_KEYS = {
    "observed_at", "date", "success", "count", "median_price",
    "average_price", "price_sample_size", "provider", "error_category", "error_message",
}
RUN_ALWAYS_KEYS = {"run_id", "started_at", "status", "category", "duration_seconds"}
DELTA_KEYS = {"delta", "from", "to"}
LAST_FAILURE_KEYS = {"date", "category", "message"}


def test_dashboard_payload_carries_every_key_the_frontend_reads(tmp_path):
    payload = _build_payload(tmp_path)

    assert TOP_LEVEL_KEYS <= set(payload)
    assert HEALTH_KEYS <= set(payload["health"])

    search = payload["searches"][0]
    assert SEARCH_KEYS <= set(search)
    assert KPI_KEYS <= set(search["kpis"])

    for point in search["timeseries"]:
        assert POINT_KEYS <= set(point)

    for run in payload["runs"]:
        assert RUN_ALWAYS_KEYS <= set(run)

    delta = search["kpis"]["delta_7d"]
    assert delta is not None and DELTA_KEYS <= set(delta)

    failure = search["kpis"]["last_failure"]
    assert failure is not None and LAST_FAILURE_KEYS <= set(failure)


def test_dashboard_payload_is_json_serializable_and_written(tmp_path):
    _build_payload(tmp_path)
    on_disk = json.loads((tmp_path / "docs" / "data" / "dashboard.json").read_text(encoding="utf-8"))
    assert on_disk["searches"][0]["id"] == "studio_saint_denis"


def test_antibot_failure_is_published_as_blocked(tmp_path):
    payload = _build_payload(tmp_path)
    last_failure = payload["searches"][0]["kpis"]["last_failure"]
    assert last_failure["category"] == "blocked"
