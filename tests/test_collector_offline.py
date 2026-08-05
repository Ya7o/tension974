import tempfile
import os
import pytest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from tension974.database import init_db, get_observations
from tension974.models import FetchResult, SearchConfig
from tension974.providers.base import FetchProvider
from tension974.collector import collect_one


class FakeProvider(FetchProvider):
    def __init__(self, result: FetchResult):
        self._result = result

    @property
    def name(self) -> str:
        return "fake"

    def fetch(self, url: str) -> FetchResult:
        return self._result


class SequenceProvider(FetchProvider):
    def __init__(self, results: list[FetchResult]):
        self._results = results
        self.calls = 0

    @property
    def name(self) -> str:
        return "sequence"

    def fetch(self, url: str) -> FetchResult:
        result = self._results[min(self.calls, len(self._results) - 1)]
        self.calls += 1
        return result


SEARCH = SearchConfig(
    id="saint_denis_t3",
    name="Saint-Denis - T3",
    platform="leboncoin",
    url="https://www.leboncoin.fr/recherche?text=t3",
)


@pytest.fixture
def tmp_db():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        path = f.name
    init_db(path)
    yield path
    os.unlink(path)


def test_collect_with_count(tmp_db):
    provider = FakeProvider(FetchResult(
        success=True,
        content="Leboncoin\n\n242 annonces\n\nFiltres",
        provider="fake",
    ))
    obs = collect_one(SEARCH, provider, tmp_db)
    assert obs.status == "success"
    assert obs.total_listings_count == 242
    rows = get_observations(tmp_db, "saint_denis_t3")
    assert len(rows) == 1


def test_collect_without_count(tmp_db):
    provider = FakeProvider(FetchResult(
        success=True,
        content="Page vide sans compteur.",
        provider="fake",
    ))
    obs = collect_one(SEARCH, provider, tmp_db)
    assert obs.status == "failed"
    assert obs.total_listings_count is None


def test_collect_provider_error(tmp_db):
    provider = FakeProvider(FetchResult(
        success=False,
        provider="fake",
        error_message="Connection refused",
    ))
    obs = collect_one(SEARCH, provider, tmp_db)
    assert obs.status == "failed"
    assert "Connection refused" in (obs.error_message or "")
    rows = get_observations(tmp_db, "saint_denis_t3")
    assert len(rows) == 1
    assert rows[0]["status"] == "failed"


ANTIBOT_PAGE = "Please enable JS and disable any ad blocker"


def test_collect_retries_when_page_has_no_count(tmp_db, monkeypatch):
    """An anti-bot challenge arrives as a 200 with no count: retry it.

    Leboncoin's DataDome page used to slip through unretried because the fetch
    itself had succeeded — that is how the 30 July 2026 T2/T3 collection was
    lost after a single attempt.
    """
    monkeypatch.setattr("tension974.collector.time.sleep", lambda seconds: None)
    provider = SequenceProvider([
        FetchResult(success=True, content=ANTIBOT_PAGE, provider="fake", credits_used=5),
        FetchResult(success=True, content="Leboncoin\n\n242 annonces", provider="fake", credits_used=5),
    ])

    obs = collect_one(SEARCH, provider, tmp_db)

    assert provider.calls == 2
    assert obs.status == "success"
    assert obs.total_listings_count == 242
    assert obs.credits_used == 10


def test_collect_without_count_keeps_served_page(tmp_db, monkeypatch):
    """When every attempt is blocked, keep the page as the only diagnostic."""
    monkeypatch.setattr("tension974.collector.time.sleep", lambda seconds: None)
    provider = SequenceProvider([
        FetchResult(success=True, content=ANTIBOT_PAGE, provider="fake", credits_used=5),
    ])

    obs = collect_one(SEARCH, provider, tmp_db)

    assert provider.calls == 2
    assert obs.status == "failed"
    assert obs.total_listings_count is None
    # The DataDome interstitial must surface as an anti-bot block, not as a
    # generic "page changed" failure — the dashboard colors depend on it.
    assert "anti-bot" in (obs.error_message or "")
    assert obs.raw_total_listings_text == ANTIBOT_PAGE
    assert obs.credits_used == 10


def test_collect_page_without_count_and_without_antibot_signature(tmp_db, monkeypatch):
    """A really changed page (no anti-bot marker) keeps the no_data message."""
    monkeypatch.setattr("tension974.collector.time.sleep", lambda seconds: None)
    provider = SequenceProvider([
        FetchResult(success=True, content="Une page inattendue sans compteur.", provider="fake"),
    ])

    obs = collect_one(SEARCH, provider, tmp_db)

    assert obs.status == "failed"
    assert obs.error_message == "No listings count found in content."


def test_collect_does_not_retry_a_valid_page(tmp_db):
    """A page carrying a count costs exactly one call — no wasted credits."""
    provider = SequenceProvider([
        FetchResult(success=True, content="Leboncoin\n\n242 annonces", provider="fake", credits_used=5),
    ])

    obs = collect_one(SEARCH, provider, tmp_db)

    assert provider.calls == 1
    assert obs.status == "success"
    assert obs.credits_used == 5


def test_collect_retries_once_then_succeeds(tmp_db, monkeypatch):
    monkeypatch.setattr("tension974.collector.time.sleep", lambda seconds: None)
    provider = SequenceProvider([
        FetchResult(success=False, provider="fake", error_message="Temporary error", credits_used=1),
        FetchResult(success=True, content="Leboncoin\n\n242 annonces", provider="fake", credits_used=1),
    ])

    obs = collect_one(SEARCH, provider, tmp_db)

    assert provider.calls == 2
    assert obs.status == "success"
    assert obs.total_listings_count == 242
    assert obs.credits_used == 2
