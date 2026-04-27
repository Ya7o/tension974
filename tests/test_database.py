import tempfile
import os
import pytest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from tension974.database import init_db, insert_observation, get_observations, get_last_observation
from tension974.models import Observation


@pytest.fixture
def tmp_db():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        path = f.name
    init_db(path)
    yield path
    os.unlink(path)


def test_init_creates_tables(tmp_db):
    import sqlite3
    conn = sqlite3.connect(tmp_db)
    tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
    conn.close()
    assert "searches" in tables
    assert "observations" in tables
    assert "collection_runs" in tables


def test_insert_success_observation(tmp_db):
    obs = Observation(
        search_id="saint_denis_t3",
        observed_at="2024-01-15T21:15:00+00:00",
        status="success",
        provider="firecrawl",
        total_listings_count=242,
        raw_total_listings_text="242 annonces",
    )
    row_id = insert_observation(tmp_db, obs)
    assert row_id is not None and row_id > 0


def test_insert_failed_observation(tmp_db):
    obs = Observation(
        search_id="saint_denis_t3",
        observed_at="2024-01-15T21:15:00+00:00",
        status="failed",
        provider="firecrawl",
        error_message="Network error",
    )
    row_id = insert_observation(tmp_db, obs)
    assert row_id is not None and row_id > 0


def test_get_observations(tmp_db):
    for count in [100, 200, 242]:
        obs = Observation(
            search_id="saint_denis_t3",
            observed_at="2024-01-15T21:15:00+00:00",
            status="success",
            provider="firecrawl",
            total_listings_count=count,
        )
        insert_observation(tmp_db, obs)

    rows = get_observations(tmp_db, "saint_denis_t3")
    assert len(rows) == 3


def test_get_last_observation_success_only(tmp_db):
    insert_observation(tmp_db, Observation(
        search_id="saint_denis_t3",
        observed_at="2024-01-14T21:15:00+00:00",
        status="success",
        provider="firecrawl",
        total_listings_count=100,
    ))
    insert_observation(tmp_db, Observation(
        search_id="saint_denis_t3",
        observed_at="2024-01-15T21:15:00+00:00",
        status="failed",
        provider="firecrawl",
        error_message="err",
    ))
    last = get_last_observation(tmp_db, "saint_denis_t3")
    assert last is not None
    assert last["status"] == "success"
    assert last["total_listings_count"] == 100
