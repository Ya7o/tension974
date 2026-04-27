"""Direct HTTP provider — scrape Leboncoin sans Firecrawl.

Stratégies en cascade :
  1. GET classique + __NEXT_DATA__ JSON  (URLs simples, 0 crédit)
  2. Next.js _next/data/{buildId}/recherche.json  (contourne DataDome sur real_estate_type)
  3. Playwright  (fallback si installé)
"""
import json
import logging
import re
import time
from urllib.parse import urlparse, parse_qs, urlencode

import requests

from ..extraction import extract_total_listings_count
from ..models import FetchResult
from .base import FetchProvider

logger = logging.getLogger("tension974.direct")

_BASE = "https://www.leboncoin.fr"
_SIMPLE_URL = f"{_BASE}/recherche?category=10&locations=Saint-Denis__-20.905210884748794_55.475948319967685_7424_5000&furnished=1&sort=time&order=desc"

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "fr-FR,fr;q=0.9,en-US;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
}

_NEXT_DATA_RE = re.compile(
    r'<script\s+id="__NEXT_DATA__"\s+type="application/json">(.*?)</script>',
    re.DOTALL,
)
_BUILD_ID_RE = re.compile(r'"buildId"\s*:\s*"([^"]+)"')


def _get_search_data_from_html(html: str) -> int | None:
    m = _NEXT_DATA_RE.search(html)
    if not m:
        return None
    try:
        data = json.loads(m.group(1))
        sd = data.get("props", {}).get("pageProps", {}).get("searchData", {})
        total = sd.get("total")
        if total is not None:
            return int(total)
    except (json.JSONDecodeError, ValueError, TypeError):
        pass
    return None


def _get_build_id(html: str) -> str | None:
    m = _BUILD_ID_RE.search(html)
    return m.group(1) if m else None


def _url_to_next_params(url: str) -> dict:
    """Extract query params from a Leboncoin search URL for _next/data."""
    qs = parse_qs(urlparse(url).query, keep_blank_values=True)
    # flatten single-value lists
    params = {k: v[0] for k, v in qs.items()}
    # drop session-specific params that don't affect results
    for drop in ("from", "sa"):
        params.pop(drop, None)
    return params


def _try_next_data_api(session: requests.Session, build_id: str, url: str, timeout: int) -> int | None:
    """Call /_next/data/{buildId}/recherche.json with the search params."""
    params = _url_to_next_params(url)
    next_url = f"{_BASE}/_next/data/{build_id}/recherche.json"
    try:
        r = session.get(
            next_url,
            params=params,
            headers={**_HEADERS, "Accept": "application/json", "Sec-Fetch-Dest": "empty", "Sec-Fetch-Mode": "cors"},
            timeout=timeout,
        )
        if r.status_code != 200:
            logger.debug("_next/data returned %s", r.status_code)
            return None
        data = r.json()
        sd = data.get("pageProps", {}).get("searchData", {})
        total = sd.get("total")
        if total is not None:
            logger.debug("_next/data total=%s", total)
            return int(total)
    except Exception as exc:
        logger.debug("_next/data error: %s", exc)
    return None


def _try_playwright(url: str) -> FetchResult:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return FetchResult(
            success=False,
            provider="direct_playwright",
            error_message="Playwright non installé : pip install playwright && playwright install chromium",
        )
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(user_agent=_HEADERS["User-Agent"], locale="fr-FR")
            page.goto(url, wait_until="domcontentloaded", timeout=30000)
            page.wait_for_selector("body", timeout=10000)
            html = page.content()
            browser.close()

        total = _get_search_data_from_html(html)
        if total is not None:
            return FetchResult(
                success=True,
                content=f"{total} annonces",
                provider="direct_playwright",
                credits_used=0,
                raw_metadata={"strategy": "playwright+next_data"},
            )
        count = extract_total_listings_count(re.sub(r"<[^>]+>", " ", html))
        if count is not None:
            return FetchResult(
                success=True,
                content=f"{count} annonces",
                provider="direct_playwright",
                credits_used=0,
                raw_metadata={"strategy": "playwright+regex"},
            )
        return FetchResult(success=False, provider="direct_playwright",
                           error_message="Playwright: compteur introuvable.")
    except Exception as exc:
        return FetchResult(success=False, provider="direct_playwright",
                           error_message=f"Playwright: {exc}")


class SimpleHttpProvider(FetchProvider):
    """Provider direct sans Firecrawl — zéro crédit consommé."""

    def __init__(self, timeout: int = 20) -> None:
        self._timeout = timeout
        self._session = requests.Session()
        self._session.headers.update(_HEADERS)
        self._build_id: str | None = None

    @property
    def name(self) -> str:
        return "direct_http"

    def _ensure_build_id(self) -> str | None:
        """Fetch buildId from a URL that reliably returns 200."""
        if self._build_id:
            return self._build_id
        try:
            r = self._session.get(_SIMPLE_URL, timeout=self._timeout)
            if r.status_code == 200:
                self._build_id = _get_build_id(r.text)
                logger.debug("buildId: %s", self._build_id)
        except Exception as exc:
            logger.warning("Could not fetch buildId: %s", exc)
        return self._build_id

    def fetch(self, url: str) -> FetchResult:
        logger.info("Direct HTTP fetch: %s", url[:80])

        # ── Strategy 1 : direct GET + __NEXT_DATA__ ──────────────────────────
        try:
            r = self._session.get(url, timeout=self._timeout, allow_redirects=True)
            if r.status_code == 200:
                total = _get_search_data_from_html(r.text)
                if total is not None:
                    logger.info("Strategy 1 (direct+__NEXT_DATA__): %d annonces", total)
                    # cache buildId for later use
                    if not self._build_id:
                        self._build_id = _get_build_id(r.text)
                    return FetchResult(
                        success=True,
                        content=f"{total} annonces",
                        content_type="json",
                        provider=self.name,
                        status_code=200,
                        credits_used=0,
                        raw_metadata={"strategy": "direct+next_data"},
                    )
                # Fallback regex on HTML
                count = extract_total_listings_count(re.sub(r"<[^>]+>", " ", r.text))
                if count is not None:
                    logger.info("Strategy 1b (direct+regex): %d annonces", count)
                    return FetchResult(
                        success=True,
                        content=f"{count} annonces",
                        provider=self.name,
                        status_code=200,
                        credits_used=0,
                        raw_metadata={"strategy": "direct+html_regex"},
                    )

        except requests.RequestException as exc:
            logger.debug("Direct GET failed: %s", exc)

        # ── Strategy 2 : _next/data/{buildId}/recherche.json ─────────────────
        logger.info("Strategy 2: _next/data API")
        build_id = self._ensure_build_id()
        if build_id:
            total = _try_next_data_api(self._session, build_id, url, self._timeout)
            if total is not None:
                logger.info("Strategy 2 (_next/data): %d annonces", total)
                return FetchResult(
                    success=True,
                    content=f"{total} annonces",
                    content_type="json",
                    provider=self.name,
                    credits_used=0,
                    raw_metadata={"strategy": "_next/data", "build_id": build_id},
                )

        # ── Strategy 3 : Playwright ───────────────────────────────────────────
        logger.info("Strategy 3: Playwright fallback")
        result = _try_playwright(url)
        return result
