import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from tension974 import collect
from tension974.models import Observation


def test_jsonl_storage_command_runs(monkeypatch, tmp_path):
    monkeypatch.setenv("DATA_DIR", str(tmp_path / "data"))

    def fake_run_collection(config_path, provider, storage):
        storage.initialize()
        return [
            Observation(
                search_id="saint_denis_t3",
                observed_at="2026-04-27T00:00:00+00:00",
                status="success",
                provider=provider.name,
                total_listings_count=12,
            )
        ]

    monkeypatch.setattr(collect, "run_collection_with_storage", fake_run_collection)

    assert collect.main(["--storage", "jsonl"]) == 0


def test_exit_code_is_nonzero_when_every_search_fails(monkeypatch, tmp_path):
    """Une collecte 100 % en échec doit faire échouer le job CI appelant."""
    monkeypatch.setenv("DATA_DIR", str(tmp_path / "data"))

    def fake_run_collection(config_path, provider, storage):
        storage.initialize()
        return [
            Observation(
                search_id="saint_denis_t3",
                observed_at="2026-04-27T00:00:00+00:00",
                status="failed",
                provider=provider.name,
                error_message="Blocked by anti-bot challenge.",
            )
        ]

    monkeypatch.setattr(collect, "run_collection_with_storage", fake_run_collection)

    assert collect.main(["--storage", "jsonl"]) == 1


def test_sqlite_storage_command_still_runs(monkeypatch, tmp_path):
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "tension974.db"))

    def fake_run_collection(config_path, provider, storage):
        storage.initialize()
        return [
            Observation(
                search_id="saint_denis_t3",
                observed_at="2026-04-27T00:00:00+00:00",
                status="success",
                provider=provider.name,
                total_listings_count=12,
            )
        ]

    monkeypatch.setattr(collect, "run_collection_with_storage", fake_run_collection)

    assert collect.main(["--storage", "sqlite"]) == 0
