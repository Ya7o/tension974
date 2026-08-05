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
  - id: inactive_search
    name: "Inactive"
    platform: leboncoin
    url: "https://www.leboncoin.fr/recherche?text=inactive"
    active: false
"""

NOW = datetime.now(timezone.utc)


def _iso(days_ago: float) -> str:
    return (NOW - timedelta(days=days_ago)).isoformat()


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")


def test_build_writes_dashboard_json(tmp_path):
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    config_path = tmp_path / "searches.yaml"
    config_path.write_text(CONFIG_YAML, encoding="utf-8")

    _write_jsonl(data_dir / "observations.jsonl", [
        {
            "search_id": "studio_saint_denis",
            "observed_at": _iso(6),
            "status": "success",
            "provider": "direct_http",
            "total_listings_count": 57,
            "median_price": 650,
        },
        {
            "search_id": "studio_saint_denis",
            "observed_at": _iso(1),
            "status": "failed",
            "provider": "direct_http",
            "error_message": "403 Forbidden - DataDome",
        },
    ])
    _write_jsonl(data_dir / "runs.jsonl", [
        {"run_id": "r1", "started_at": _iso(6), "status": "running", "provider": "direct_http"},
        {"run_id": "r1", "finished_at": _iso(6), "status": "success"},
        {"run_id": "r2", "started_at": _iso(1), "status": "running", "provider": "direct_http"},
        {"run_id": "r2", "finished_at": _iso(1), "status": "failed",
         "error_message": "403 Forbidden - DataDome"},
    ])

    site_dir = tmp_path / "docs"
    payload = build(data_dir, str(config_path), site_dir)

    assert len(payload["searches"]) == 1
    assert payload["searches"][0]["id"] == "studio_saint_denis"
    assert payload["searches"][0]["kpis"]["latest_count"] == 57
    assert len(payload["runs"]) == 2
    assert payload["health"]["category_counts_30d"].get("blocked") == 1

    dashboard_json = site_dir / "data" / "dashboard.json"
    assert dashboard_json.exists()
    on_disk = json.loads(dashboard_json.read_text(encoding="utf-8"))
    assert on_disk["searches"][0]["id"] == "studio_saint_denis"
    # Les JSONL bruts ne sont plus dupliqués dans docs/data/ : ils vivent une
    # seule fois dans data/, le dashboard pointe vers GitHub pour le téléchargement.
    assert not (site_dir / "data" / "observations.jsonl").exists()
    assert not (site_dir / "data" / "runs.jsonl").exists()
