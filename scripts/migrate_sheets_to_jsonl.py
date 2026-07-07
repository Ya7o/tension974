#!/usr/bin/env python3
"""One-off migration: Google Sheets ("observations"/"runs") -> data/*.jsonl.

This is a bridge for the GitHub Pages migration: the project used to write
its canonical history to a Google Sheet. This script pulls that history once
so it keeps living in the repo (data/observations.jsonl, data/runs.jsonl)
instead of an external spreadsheet.

Requires gspread + google-auth (not part of the main requirements.txt — the
migrate-sheets-to-jsonl.yml workflow installs them just for this one run) and
the GOOGLE_SERVICE_ACCOUNT_JSON / GOOGLE_SHEET_ID secrets that were used by
the old Streamlit dashboard.

Usage:
    GOOGLE_SERVICE_ACCOUNT_JSON=... GOOGLE_SHEET_ID=... python scripts/migrate_sheets_to_jsonl.py
"""
import json
import os
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from tension974.settings import get_data_dir

OBSERVATION_INT_FIELDS = (
    "total_listings_count",
    "median_price",
    "average_price",
    "price_sample_size",
    "min_price",
    "max_price",
    "credits_used",
)


def _cell(value):
    return value.strip() if isinstance(value, str) else value


def _int_or_none(value):
    value = _cell(value)
    if value in (None, ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _rows_from_worksheet(worksheet) -> list[dict]:
    values = worksheet.get_all_values()
    if not values:
        return []
    headers = [h.strip() for h in values[0]]
    rows = []
    for raw in values[1:]:
        raw = (raw + [""] * len(headers))[:len(headers)]
        row = dict(zip(headers, raw))
        if any(v not in (None, "") for v in row.values()):
            rows.append(row)
    return rows


def convert_observations(rows: list[dict]) -> list[dict]:
    converted = []
    for row in rows:
        obs = {
            "search_id": _cell(row.get("search_id")) or "",
            "observed_at": _cell(row.get("observed_at")) or "",
            "status": _cell(row.get("status")) or "failed",
            "provider": _cell(row.get("provider")) or "",
            "raw_total_listings_text": _cell(row.get("raw_total_listings_text")) or None,
            "error_message": _cell(row.get("error_message")) or None,
            "created_at": _cell(row.get("created_at")) or _cell(row.get("observed_at")) or "",
        }
        for field in OBSERVATION_INT_FIELDS:
            obs[field] = _int_or_none(row.get(field))
        if obs["search_id"] and obs["observed_at"]:
            converted.append(obs)
    return converted


def convert_runs(rows: list[dict]) -> list[dict]:
    """Each sheet row already merges start+finish; re-split into two JSONL
    events (matching JsonlStorage's format) so aggregation.merge_runs can
    pair them the same way as freshly collected runs."""
    events = []
    for row in rows:
        run_id = uuid.uuid4().hex[:12]
        started_at = _cell(row.get("started_at")) or None
        finished_at = _cell(row.get("finished_at")) or None
        status = _cell(row.get("status")) or "unknown"
        provider = _cell(row.get("provider")) or None
        error_message = _cell(row.get("error_message")) or None
        if not started_at:
            continue
        events.append({
            "run_id": run_id, "started_at": started_at, "finished_at": None,
            "status": "running", "provider": provider, "error_message": None,
        })
        events.append({
            "run_id": run_id, "started_at": None, "finished_at": finished_at,
            "status": status, "provider": None, "error_message": error_message,
        })
    return events


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False, sort_keys=True))
            f.write("\n")


def main() -> int:
    import gspread

    service_account_json = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON")
    sheet_id = os.environ.get("GOOGLE_SHEET_ID")
    if not service_account_json:
        print("ERROR: GOOGLE_SERVICE_ACCOUNT_JSON is missing", file=sys.stderr)
        return 1
    if not sheet_id:
        print("ERROR: GOOGLE_SHEET_ID is missing", file=sys.stderr)
        return 1

    client = gspread.service_account_from_dict(json.loads(service_account_json))
    spreadsheet = client.open_by_key(sheet_id)

    observations = convert_observations(_rows_from_worksheet(spreadsheet.worksheet("observations")))
    observations.sort(key=lambda o: o["observed_at"])
    run_events = []
    try:
        run_rows = _rows_from_worksheet(spreadsheet.worksheet("runs"))
        run_events = convert_runs(run_rows)
    except Exception as exc:
        print(f"WARNING: could not read 'runs' worksheet: {exc}", file=sys.stderr)

    data_dir = Path(get_data_dir())
    _write_jsonl(data_dir / "observations.jsonl", observations)
    _write_jsonl(data_dir / "runs.jsonl", run_events)

    print(f"Migrated {len(observations)} observation(s) and {len(run_events) // 2} run(s) "
          f"into {data_dir}/observations.jsonl and {data_dir}/runs.jsonl")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
