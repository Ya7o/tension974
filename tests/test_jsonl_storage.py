import json


from tension974.models import Observation
from tension974.storage import JsonlStorage


def test_initialize_creates_files(tmp_path):
    storage = JsonlStorage(str(tmp_path / "data"))
    storage.initialize()
    assert (tmp_path / "data" / "observations.jsonl").exists()
    assert (tmp_path / "data" / "runs.jsonl").exists()


def test_insert_observation_appends_jsonl_line(tmp_path):
    storage = JsonlStorage(str(tmp_path / "data"))
    storage.initialize()
    storage.insert_observation(Observation(
        search_id="studio_saint_denis",
        observed_at="2026-04-27T17:15:00+00:00",
        status="success",
        provider="direct_http",
        total_listings_count=57,
    ))
    lines = (tmp_path / "data" / "observations.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    row = json.loads(lines[0])
    assert row["search_id"] == "studio_saint_denis"
    assert row["total_listings_count"] == 57
    assert row["created_at"]


def test_insert_observation_is_append_only(tmp_path):
    storage = JsonlStorage(str(tmp_path / "data"))
    storage.initialize()
    for count in (1, 2):
        storage.insert_observation(Observation(
            search_id="studio_saint_denis",
            observed_at="2026-04-27T17:15:00+00:00",
            status="success",
            provider="direct_http",
            total_listings_count=count,
        ))
    lines = (tmp_path / "data" / "observations.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2


def test_start_and_finish_run_pairs_by_run_id(tmp_path):
    storage = JsonlStorage(str(tmp_path / "data"))
    storage.initialize()
    run_id = storage.start_run("direct_http")
    storage.finish_run(run_id, "success")

    lines = [json.loads(line) for line in (tmp_path / "data" / "runs.jsonl").read_text(encoding="utf-8").splitlines()]
    assert len(lines) == 2
    assert lines[0]["run_id"] == run_id
    assert lines[0]["status"] == "running"
    assert lines[1]["run_id"] == run_id
    assert lines[1]["status"] == "success"
    assert lines[1]["finished_at"]
