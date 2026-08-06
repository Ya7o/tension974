"""Premiers tests des providers — sans réseau.

FirecrawlProvider est le provider de production : sa branche métadonnées
(dict vs objet SDK) est la source unique du comptage de crédits.
"""
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).parent.parent))

from tension974.providers import firecrawl_provider
from tension974.providers.firecrawl_provider import FirecrawlProvider


class _FakeClient:
    def __init__(self, result=None, exc=None):
        self._result = result
        self._exc = exc

    def scrape(self, url, formats=None):
        if self._exc:
            raise self._exc
        return self._result


def _provider_with(result=None, exc=None) -> FirecrawlProvider:
    provider = FirecrawlProvider(api_key="fc-test")
    provider._client = _FakeClient(result=result, exc=exc)
    return provider


def test_fetch_reads_dict_result_and_camelcase_credits():
    provider = _provider_with(result={
        "markdown": "Leboncoin\n\n242 annonces",
        "html": "<html></html>",
        "metadata": {"creditsUsed": 5},
    })

    fetch = provider.fetch("https://example.test")

    assert fetch.success is True
    assert fetch.content == "Leboncoin\n\n242 annonces"
    assert fetch.content_type == "markdown"
    assert fetch.credits_used == 5


def test_fetch_reads_sdk_object_result_and_metadata_attribute():
    metadata = SimpleNamespace(credits_used=3)
    provider = _provider_with(result=SimpleNamespace(
        markdown="110 annonces", html="", metadata=metadata,
    ))

    fetch = provider.fetch("https://example.test")

    assert fetch.success is True
    assert fetch.content == "110 annonces"
    assert fetch.credits_used == 3


def test_fetch_falls_back_to_html_when_no_markdown():
    provider = _provider_with(result={"markdown": "", "html": "<p>39 annonces</p>", "metadata": {}})

    fetch = provider.fetch("https://example.test")

    assert fetch.success is True
    assert fetch.content == "<p>39 annonces</p>"
    assert fetch.content_type == "html"
    assert fetch.credits_used is None


def test_fetch_turns_sdk_exception_into_failed_result():
    provider = _provider_with(exc=RuntimeError("Payment Required"))

    fetch = provider.fetch("https://example.test")

    assert fetch.success is False
    assert "Payment Required" in (fetch.error_message or "")
    assert fetch.provider == "firecrawl"


class _FakeResponse:
    def __init__(self, payload, status=200):
        self._payload = payload
        self.status_code = status

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")

    def json(self):
        return self._payload


def test_get_account_credits_success(monkeypatch):
    monkeypatch.setattr(
        firecrawl_provider.requests, "get",
        lambda url, headers=None, timeout=None: _FakeResponse(
            {"success": True, "data": {"remaining_credits": 480, "plan_credits": 500}},
        ),
    )
    credits = FirecrawlProvider(api_key="fc-test").get_account_credits()
    assert credits["remaining_credits"] == 480


def test_get_account_credits_network_error_returns_error_dict(monkeypatch):
    def boom(url, headers=None, timeout=None):
        raise ConnectionError("dns failure")

    monkeypatch.setattr(firecrawl_provider.requests, "get", boom)
    credits = FirecrawlProvider(api_key="fc-test").get_account_credits()
    assert "error" in credits
