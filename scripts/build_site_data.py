#!/usr/bin/env python3
"""Build the static JSON consumed by the GitHub Pages dashboard (docs/data/).

Reads the git-tracked JSONL data (data/observations.jsonl, data/runs.jsonl)
and config/searches.yaml, aggregates them, and writes
docs/data/dashboard.json — everything the dashboard needs to render. The raw
JSONL files are not copied here: they live once, in data/, and the dashboard
links to them on GitHub.
"""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from tension974.aggregation import build_search_timeseries, compute_health, compute_kpis, merge_runs
from tension974.collector import load_searches
from tension974.settings import get_data_dir, get_searches_config_path


def _read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    rows = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def build(data_dir: Path, config_path: str, site_dir: Path) -> dict:
    observations = _read_jsonl(data_dir / "observations.jsonl")
    run_events = _read_jsonl(data_dir / "runs.jsonl")
    searches = [s for s in load_searches(config_path) if s.active]
    merged_runs = merge_runs(run_events)

    search_payloads = []
    for search in searches:
        series = build_search_timeseries(observations, search.id)
        search_payloads.append({
            "id": search.id,
            "name": search.name,
            "location": search.location,
            "property_type": search.property_type,
            "url": search.url,
            "kpis": compute_kpis(series),
            "timeseries": series,
        })

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "searches": search_payloads,
        "runs": merged_runs[:200],
        "health": compute_health(merged_runs),
    }

    site_data_dir = site_dir / "data"
    site_data_dir.mkdir(parents=True, exist_ok=True)
    (site_data_dir / "dashboard.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    return payload


if __name__ == "__main__":
    data_dir = Path(get_data_dir())
    config_path = get_searches_config_path()
    site_dir = Path("docs")

    payload = build(data_dir, config_path, site_dir)
    print(f"Wrote {site_dir / 'data' / 'dashboard.json'} "
          f"({len(payload['searches'])} recherche(s), {len(payload['runs'])} run(s))")
