from scripts.migrate_sheets_to_jsonl import convert_observations, convert_runs


def test_convert_observations_parses_ints_and_skips_blank_rows():
    rows = [
        {
            "search_id": "studio_saint_denis",
            "observed_at": "2026-04-20T17:15:00+00:00",
            "total_listings_count": "57",
            "median_price": "650",
            "status": "success",
            "provider": "firecrawl",
            "created_at": "2026-04-20T17:15:01+00:00",
        },
        {"search_id": "", "observed_at": ""},
    ]
    converted = convert_observations(rows)
    assert len(converted) == 1
    assert converted[0]["total_listings_count"] == 57
    assert converted[0]["median_price"] == 650


def test_convert_observations_missing_price_is_none():
    rows = [{
        "search_id": "studio_saint_denis",
        "observed_at": "2026-04-20T17:15:00+00:00",
        "total_listings_count": "57",
        "median_price": "",
        "status": "success",
        "provider": "firecrawl",
    }]
    converted = convert_observations(rows)
    assert converted[0]["median_price"] is None


def test_convert_runs_splits_into_start_and_finish_events():
    rows = [{
        "started_at": "2026-04-20T17:15:00+00:00",
        "finished_at": "2026-04-20T17:15:05+00:00",
        "status": "success",
        "provider": "firecrawl",
        "error_message": "",
    }]
    events = convert_runs(rows)
    assert len(events) == 2
    assert events[0]["status"] == "running"
    assert events[1]["status"] == "success"
    assert events[0]["run_id"] == events[1]["run_id"]


def test_convert_runs_skips_rows_without_started_at():
    rows = [{"started_at": "", "finished_at": "2026-04-20T17:15:05+00:00", "status": "success"}]
    assert convert_runs(rows) == []
