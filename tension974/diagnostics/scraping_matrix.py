"""
Scraping diagnostics matrix — tension974.

Tests 19 methods (15 spécifiés + 4 anti-bot avancés) sur l'URL Leboncoin configurée.
Résultats : debug/scraping_diagnostics_summary.json

Usage:
    python -m tension974.diagnostics.scraping_matrix
    DEBUG_SCRAPING=true python -m tension974.diagnostics.scraping_matrix
"""
from __future__ import annotations

import json
import logging
import os
import re
import socket
import sys
import time
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

import yaml

logger = logging.getLogger(__name__)

_DEBUG = os.environ.get("DEBUG_SCRAPING", "").lower() in ("1", "true", "yes")
_PROJECT_ROOT = Path(__file__).parent.parent.parent
_DEBUG_DIR = _PROJECT_ROOT / "debug"

# ── Browser identity ──────────────────────────────────────────────────────────

_BROWSER_UA = (
    "Mozilla/5.0 (X11; Linux x86_64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)

_BROWSER_HEADERS = {
    "User-Agent": _BROWSER_UA,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "fr-FR,fr;q=0.9,en-US;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
    "Cache-Control": "no-cache",
    "Pragma": "no-cache",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
}

# Chrome 124 Client Hints — prouve que le navigateur supporte le mécanisme
_CLIENT_HINTS = {
    "Sec-CH-UA": '"Chromium";v="124", "Google Chrome";v="124", "Not-A.Brand";v="99"',
    "Sec-CH-UA-Mobile": "?0",
    "Sec-CH-UA-Platform": '"Linux"',
}

# ── Regex patterns ────────────────────────────────────────────────────────────

_COUNT_PATTERNS = [
    re.compile(r"(\d[\d\s ]*)\s+annonces?", re.IGNORECASE),
    re.compile(r"(\d[\d\s ]*)\s+résultats?", re.IGNORECASE),
    re.compile(r"Plus\s+de\s+(\d[\d\s ]*)\s+annonces?", re.IGNORECASE),
]

_NEXT_DATA_RE = re.compile(
    r'<script\s+id="__NEXT_DATA__"\s+type="application/json">(.*?)</script>',
    re.DOTALL,
)

# ── Environment ───────────────────────────────────────────────────────────────


def _detect_environment() -> str:
    if os.environ.get("GITHUB_ACTIONS") == "true":
        return "github_actions"
    if os.environ.get("STREAMLIT_SHARING_MODE") or os.environ.get("STREAMLIT_SERVER_PORT"):
        return "streamlit_cloud"
    return "local"


def _check_packages() -> dict:
    pkgs: dict[str, str | None] = {}
    for name, import_name in [
        ("httpx", "httpx"),
        ("beautifulsoup4", "bs4"),
        ("playwright", "playwright"),
        ("curl_cffi", "curl_cffi"),
        ("requests", "requests"),
    ]:
        try:
            mod = __import__(import_name)
            pkgs[name] = getattr(mod, "__version__", "installed")
        except ImportError:
            pkgs[name] = None
    return pkgs


def _environment_info() -> dict:
    return {
        "environment": _detect_environment(),
        "python_version": sys.version,
        "platform": sys.platform,
        "github_actions": os.environ.get("GITHUB_ACTIONS", ""),
        "runner_os": os.environ.get("RUNNER_OS", ""),
        "ci": os.environ.get("CI", ""),
        "hostname": socket.gethostname(),
        "debug_scraping": _DEBUG,
        "packages": _check_packages(),
    }


# ── Config ────────────────────────────────────────────────────────────────────


def _load_configured_url() -> str:
    config_path = _PROJECT_ROOT / "config" / "searches.yaml"
    try:
        with config_path.open() as f:
            data = yaml.safe_load(f)
        for search in data.get("searches", []):
            if search.get("active") and search.get("url"):
                return search["url"]
    except Exception as exc:
        logger.warning("Could not load searches.yaml: %s", exc)
    # Fallback minimal
    return (
        "https://www.leboncoin.fr/recherche?category=10"
        "&locations=Saint-Denis__-20.905210884748794_55.475948319967685_7424_5000"
        "&furnished=1&sort=time&order=desc"
    )


# ── URL helpers ───────────────────────────────────────────────────────────────


def _strip_session_params(url: str) -> str:
    """Remove session-tracking params (from, sa) from a Leboncoin URL."""
    parsed = urlparse(url)
    qs = parse_qs(parsed.query, keep_blank_values=True)
    for drop in ("from", "sa"):
        qs.pop(drop, None)
    return urlunparse(parsed._replace(query=urlencode([(k, v[0]) for k, v in qs.items()])))


def _reencode_url(url: str) -> str:
    """Reconstruct URL with urllib.parse to normalise percent-encoding."""
    parsed = urlparse(url)
    qs = parse_qs(parsed.query, keep_blank_values=True)
    return urlunparse(parsed._replace(query=urlencode([(k, v[0]) for k, v in qs.items()])))


# ── HTML analysis ─────────────────────────────────────────────────────────────


def _extract_count(text: str) -> tuple[str | None, int | None]:
    if re.search(r"aucune\s+annonce", text, re.IGNORECASE):
        return "aucune annonce", 0
    for pat in _COUNT_PATTERNS:
        m = pat.search(text)
        if m:
            digits = re.sub(r"[\s ]", "", m.group(1))
            try:
                return m.group(0), int(digits)
            except ValueError:
                pass
    return None, None


def _analyze_html(html: str) -> dict[str, Any]:
    lower = html.lower()
    raw_match, count = _extract_count(html)
    return {
        "contains_annonces": "annonce" in lower,
        "contains_datadome": "datadome" in lower,
        "contains_captcha": "captcha" in lower or "recaptcha" in lower,
        "contains_blocked": "blocked" in lower or "bloqué" in lower,
        "contains_forbidden": "forbidden" in lower or "access denied" in lower,
        "raw_match": raw_match,
        "count": count,
    }


def _extract_next_data_count(html: str) -> tuple[str | None, int | None]:
    m = _NEXT_DATA_RE.search(html)
    if not m:
        return None, None
    try:
        data = json.loads(m.group(1))
        sd = data.get("props", {}).get("pageProps", {}).get("searchData", {})
        total = sd.get("total")
        if total is not None:
            return f"__NEXT_DATA__.searchData.total={total}", int(total)
    except (json.JSONDecodeError, ValueError, TypeError):
        pass
    return None, None


def _deep_find(obj: Any, key: str) -> Any:
    """Recursively find first value for key in nested dicts/lists."""
    if isinstance(obj, dict):
        if key in obj:
            return obj[key]
        for v in obj.values():
            result = _deep_find(v, key)
            if result is not None:
                return result
    elif isinstance(obj, list):
        for item in obj:
            result = _deep_find(item, key)
            if result is not None:
                return result
    return None


# ── Result helpers ────────────────────────────────────────────────────────────


def _base_result(test_id: str, method: str, url_variant: str) -> dict:
    return {
        "test_id": test_id,
        "environment": _detect_environment(),
        "method": method,
        "url_variant": url_variant,
        "status_code": None,
        "final_url": None,
        "content_type": None,
        "content_length": None,
        "duration_ms": None,
        "contains_annonces": False,
        "contains_datadome": False,
        "contains_captcha": False,
        "contains_blocked": False,
        "contains_forbidden": False,
        "raw_match": None,
        "count": None,
        "success": False,
        "error": None,
    }


def _save_debug(name: str, content: str | bytes) -> None:
    if not _DEBUG:
        return
    _DEBUG_DIR.mkdir(parents=True, exist_ok=True)
    path = _DEBUG_DIR / name
    if isinstance(content, bytes):
        path.write_bytes(content)
    else:
        path.write_text(content, encoding="utf-8")


def _scrub_headers(headers) -> dict:
    """Copie des en-têtes sans les cookies.

    Les dumps de debug partent en artefact CI public (et ont déjà fini
    committés) : un `set-cookie: datadome=…` y vivrait un an. On les remplace
    par un marqueur plutôt que de les supprimer, pour garder l'information
    qu'un cookie a été servi.
    """
    scrubbed = {}
    for key, value in dict(headers).items():
        if key.lower() in ("set-cookie", "cookie"):
            scrubbed[key] = "[cookie retiré du dump]"
        else:
            scrubbed[key] = value
    return scrubbed


# ── HTTPX helper ──────────────────────────────────────────────────────────────


def _httpx_get(test_id: str, url: str, headers: dict, http2: bool = False) -> dict:
    result = _base_result(
        test_id,
        method="httpx_http2" if http2 else "httpx",
        url_variant=url,
    )
    try:
        import httpx
    except ImportError:
        result["error"] = "httpx not installed — pip install 'httpx[http2]'"
        return result

    t0 = time.monotonic()
    try:
        with httpx.Client(http2=http2, follow_redirects=True, timeout=20) as client:
            resp = client.get(url, headers=headers)
        elapsed = round((time.monotonic() - t0) * 1000, 1)
        html = resp.text
        signals = _analyze_html(html)
        result.update(
            {
                "status_code": resp.status_code,
                "final_url": str(resp.url),
                "content_type": resp.headers.get("content-type", ""),
                "content_length": len(resp.content),
                "duration_ms": elapsed,
                **signals,
                "success": resp.status_code == 200 and signals["count"] is not None,
            }
        )
        if resp.status_code in (403, 429, 503):
            result["contains_blocked"] = True
        _save_debug(f"{test_id}_response.html", html)
        _save_debug(
            f"{test_id}_metadata.json",
            json.dumps(
                {"status_code": resp.status_code, "headers": _scrub_headers(resp.headers)},
                indent=2,
            ),
        )
    except Exception as exc:
        result["error"] = str(exc)
        result["duration_ms"] = round((time.monotonic() - t0) * 1000, 1)

    return result


# ── Tests 1–7 : HTTP header & URL variants ────────────────────────────────────


def test_http_minimal(url: str) -> dict:
    return _httpx_get("http_minimal", url, {"User-Agent": "tension974/1.0"})


def test_http_browser_headers(url: str) -> dict:
    return _httpx_get("http_browser_headers", url, _BROWSER_HEADERS)


def test_http_browser_headers_http2(url: str) -> dict:
    return _httpx_get("http_browser_headers_http2", url, _BROWSER_HEADERS, http2=True)


def test_url_exact(url: str) -> dict:
    return _httpx_get("url_exact", url, _BROWSER_HEADERS)


def test_url_without_from(url: str) -> dict:
    return _httpx_get("url_without_from", _strip_session_params(url), _BROWSER_HEADERS)


def test_url_encoded(url: str) -> dict:
    return _httpx_get("url_encoded", _reencode_url(url), _BROWSER_HEADERS)


def test_url_minimal_search() -> dict:
    return _httpx_get(
        "url_minimal_search",
        "https://www.leboncoin.fr/recherche?text=t3",
        _BROWSER_HEADERS,
    )


# ── Tests 8–11 : HTML parsing techniques ─────────────────────────────────────


def test_html_regex_text(url: str) -> dict:
    """Multiple regex patterns on raw HTML."""
    result = _base_result("html_regex_text", method="httpx+regex", url_variant=url)
    try:
        import httpx
    except ImportError:
        result["error"] = "httpx not installed"
        return result

    t0 = time.monotonic()
    try:
        with httpx.Client(follow_redirects=True, timeout=20) as client:
            resp = client.get(url, headers=_BROWSER_HEADERS)
        elapsed = round((time.monotonic() - t0) * 1000, 1)
        html = resp.text
        signals = _analyze_html(html)

        # Plain-text strip, then retry patterns on stripped text
        stripped = re.sub(r"<[^>]+>", " ", html)
        stripped = re.sub(r"\s+", " ", stripped)
        if signals["count"] is None:
            raw_match, count = _extract_count(stripped)
            signals["raw_match"] = raw_match
            signals["count"] = count

        result.update(
            {
                "status_code": resp.status_code,
                "final_url": str(resp.url),
                "content_type": resp.headers.get("content-type", ""),
                "content_length": len(resp.content),
                "duration_ms": elapsed,
                **signals,
                "success": resp.status_code == 200 and signals["count"] is not None,
            }
        )
        _save_debug("html_regex_text_response.html", html)
    except Exception as exc:
        result["error"] = str(exc)
        result["duration_ms"] = round((time.monotonic() - t0) * 1000, 1)

    return result


def test_html_meta_tags(url: str) -> dict:
    """Extract title, meta description, og:title, og:description and search for count."""
    result = _base_result("html_meta_tags", method="httpx+meta_tags", url_variant=url)
    try:
        import httpx
    except ImportError:
        result["error"] = "httpx not installed"
        return result

    t0 = time.monotonic()
    try:
        with httpx.Client(follow_redirects=True, timeout=20) as client:
            resp = client.get(url, headers=_BROWSER_HEADERS)
        elapsed = round((time.monotonic() - t0) * 1000, 1)
        html = resp.text
        signals = _analyze_html(html)

        meta: dict[str, str] = {}
        tm = re.search(r"<title[^>]*>(.*?)</title>", html, re.DOTALL | re.IGNORECASE)
        if tm:
            meta["title"] = re.sub(r"<[^>]+>", "", tm.group(1)).strip()

        for attr, name in [
            ("name", "description"),
            ("property", "og:title"),
            ("property", "og:description"),
        ]:
            m = re.search(
                rf'<meta\s+(?:[^>]*\s+)?{attr}="{re.escape(name)}"(?:[^>]*\s+)?content="([^"]*)"',
                html,
                re.IGNORECASE,
            ) or re.search(
                rf'<meta\s+(?:[^>]*\s+)?content="([^"]*)"(?:[^>]*\s+)?{attr}="{re.escape(name)}"',
                html,
                re.IGNORECASE,
            )
            if m:
                meta[name] = m.group(1)

        meta_text = " ".join(meta.values())
        meta_raw, meta_count = _extract_count(meta_text)
        if meta_count is not None and signals["count"] is None:
            signals["raw_match"] = meta_raw
            signals["count"] = meta_count

        result.update(
            {
                "status_code": resp.status_code,
                "final_url": str(resp.url),
                "content_type": resp.headers.get("content-type", ""),
                "content_length": len(resp.content),
                "duration_ms": elapsed,
                **signals,
                "success": resp.status_code == 200 and signals["count"] is not None,
            }
        )
        _save_debug("html_meta_tags_response.html", html)
        _save_debug("html_meta_tags_metadata.json", json.dumps({"meta": meta}, indent=2))
    except Exception as exc:
        result["error"] = str(exc)
        result["duration_ms"] = round((time.monotonic() - t0) * 1000, 1)

    return result


def test_html_embedded_json(url: str) -> dict:
    """Search __NEXT_DATA__, application/json, application/ld+json for count keys."""
    result = _base_result("html_embedded_json", method="httpx+embedded_json", url_variant=url)
    try:
        import httpx
    except ImportError:
        result["error"] = "httpx not installed"
        return result

    t0 = time.monotonic()
    try:
        with httpx.Client(follow_redirects=True, timeout=20) as client:
            resp = client.get(url, headers=_BROWSER_HEADERS)
        elapsed = round((time.monotonic() - t0) * 1000, 1)
        html = resp.text
        signals = _analyze_html(html)

        # Priority 1 — __NEXT_DATA__
        raw_match, count = _extract_next_data_count(html)

        # Priority 2 — inline JSON scripts
        if count is None:
            json_scripts = re.findall(
                r'<script[^>]+type=["\']application/(?:ld\+)?json["\'][^>]*>(.*?)</script>',
                html,
                re.DOTALL | re.IGNORECASE,
            )
            for script in json_scripts:
                try:
                    data = json.loads(script.strip())
                    for key in ("count", "total", "totalCount", "results", "search", "ads", "listings"):
                        val = _deep_find(data, key)
                        if isinstance(val, int) and val > 0:
                            count = val
                            raw_match = f"json_script.{key}={val}"
                            break
                    if count is not None:
                        break
                except (json.JSONDecodeError, TypeError):
                    pass

        if count is not None:
            signals["count"] = count
            signals["raw_match"] = raw_match

        result.update(
            {
                "status_code": resp.status_code,
                "final_url": str(resp.url),
                "content_type": resp.headers.get("content-type", ""),
                "content_length": len(resp.content),
                "duration_ms": elapsed,
                **signals,
                "success": resp.status_code == 200 and signals["count"] is not None,
            }
        )
        _save_debug("html_embedded_json_response.html", html)
    except Exception as exc:
        result["error"] = str(exc)
        result["duration_ms"] = round((time.monotonic() - t0) * 1000, 1)

    return result


def test_html_visible_text_beautifulsoup(url: str) -> dict:
    """BS4 — strip scripts/styles, extract visible text, search for count."""
    result = _base_result(
        "html_visible_text_beautifulsoup",
        method="httpx+beautifulsoup",
        url_variant=url,
    )
    try:
        import httpx
    except ImportError:
        result["error"] = "httpx not installed"
        return result

    t0 = time.monotonic()
    try:
        with httpx.Client(follow_redirects=True, timeout=20) as client:
            resp = client.get(url, headers=_BROWSER_HEADERS)
        elapsed = round((time.monotonic() - t0) * 1000, 1)
        html = resp.text
        signals = _analyze_html(html)

        bs4_error: str | None = None
        try:
            from bs4 import BeautifulSoup

            soup = BeautifulSoup(html, "html.parser")
            for tag in soup(["script", "style", "noscript"]):
                tag.decompose()
            visible = re.sub(r"\s+", " ", soup.get_text(separator=" ")).strip()

            raw_match, count = _extract_count(visible)
            if count is not None and signals["count"] is None:
                signals["raw_match"] = raw_match
                signals["count"] = count

            _save_debug("html_visible_text_beautifulsoup_text.txt", visible[:80_000])
        except ImportError:
            bs4_error = "beautifulsoup4 not installed — pip install beautifulsoup4"

        result.update(
            {
                "status_code": resp.status_code,
                "final_url": str(resp.url),
                "content_type": resp.headers.get("content-type", ""),
                "content_length": len(resp.content),
                "duration_ms": elapsed,
                **signals,
                "success": resp.status_code == 200 and signals["count"] is not None,
                "error": bs4_error,
            }
        )
        _save_debug("html_visible_text_beautifulsoup_response.html", html)
    except Exception as exc:
        result["error"] = str(exc)
        result["duration_ms"] = round((time.monotonic() - t0) * 1000, 1)

    return result


# ── Tests 12–15 : Playwright ──────────────────────────────────────────────────


def _playwright_available() -> bool:
    try:
        from playwright.sync_api import sync_playwright  # noqa: F401

        return True
    except ImportError:
        return False


def _playwright_missing_result(test_id: str, url: str) -> dict:
    r = _base_result(test_id, method="playwright_chromium", url_variant=url)
    r["error"] = "playwright not installed — pip install playwright && playwright install chromium"
    return r


def _pw_analyze(html: str, body_text: str) -> dict:
    signals = _analyze_html(html)
    if signals["count"] is None:
        raw_match, count = _extract_count(body_text)
        signals["raw_match"] = raw_match
        signals["count"] = count
    return signals


def test_playwright_headless_basic(url: str) -> dict:
    if not _playwright_available():
        return _playwright_missing_result("playwright_headless_basic", url)

    result = _base_result("playwright_headless_basic", method="playwright_chromium", url_variant=url)
    t0 = time.monotonic()
    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            resp = page.goto(url, wait_until="networkidle", timeout=30_000)
            body_text = page.inner_text("body")
            html = page.content()
            status = resp.status if resp else None
            final_url = page.url
            browser.close()

        elapsed = round((time.monotonic() - t0) * 1000, 1)
        signals = _pw_analyze(html, body_text)
        result.update(
            {
                "status_code": status,
                "final_url": final_url,
                "content_length": len(html),
                "duration_ms": elapsed,
                **signals,
                "success": signals["count"] is not None,
            }
        )
        _save_debug("playwright_headless_basic_response.html", html)
        _save_debug("playwright_body_text.txt", body_text)
    except Exception as exc:
        result["error"] = str(exc)
        result["duration_ms"] = round((time.monotonic() - t0) * 1000, 1)

    return result


def test_playwright_headless_locale_fr(url: str) -> dict:
    if not _playwright_available():
        return _playwright_missing_result("playwright_headless_locale_fr", url)

    result = _base_result(
        "playwright_headless_locale_fr", method="playwright_chromium_fr", url_variant=url
    )
    t0 = time.monotonic()
    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            ctx = browser.new_context(
                locale="fr-FR",
                timezone_id="Indian/Reunion",
                viewport={"width": 1366, "height": 768},
                user_agent=_BROWSER_UA,
            )
            page = ctx.new_page()
            resp = page.goto(url, wait_until="networkidle", timeout=30_000)
            body_text = page.inner_text("body")
            html = page.content()
            status = resp.status if resp else None
            final_url = page.url
            browser.close()

        elapsed = round((time.monotonic() - t0) * 1000, 1)
        signals = _pw_analyze(html, body_text)
        result.update(
            {
                "status_code": status,
                "final_url": final_url,
                "content_length": len(html),
                "duration_ms": elapsed,
                **signals,
                "success": signals["count"] is not None,
            }
        )
        _save_debug("playwright_headless_locale_fr_response.html", html)
    except Exception as exc:
        result["error"] = str(exc)
        result["duration_ms"] = round((time.monotonic() - t0) * 1000, 1)

    return result


def test_playwright_wait_progressive(url: str) -> dict:
    """Capture body text at t≈2s, t≈5s, t≈10s from navigation start."""
    if not _playwright_available():
        return _playwright_missing_result("playwright_wait_progressive", url)

    result = _base_result(
        "playwright_wait_progressive",
        method="playwright_chromium_progressive",
        url_variant=url,
    )
    t0 = time.monotonic()
    checkpoints: dict[str, dict] = {}
    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            ctx = browser.new_context(
                locale="fr-FR",
                timezone_id="Indian/Reunion",
                viewport={"width": 1366, "height": 768},
                user_agent=_BROWSER_UA,
            )
            page = ctx.new_page()
            page.goto(url, wait_until="domcontentloaded", timeout=30_000)

            # Δ waits: 2s → 3s → 5s  ≈ 2s, 5s, 10s from start
            for label, delta_ms in [("t2s", 2_000), ("t5s", 3_000), ("t10s", 5_000)]:
                page.wait_for_timeout(delta_ms)
                try:
                    body_text = page.inner_text("body")
                    raw_match, count = _extract_count(body_text)
                    checkpoints[label] = {"raw_match": raw_match, "count": count}
                except Exception as e:
                    checkpoints[label] = {"raw_match": None, "count": None, "error": str(e)}

            html = page.content()
            final_url = page.url
            browser.close()

        elapsed = round((time.monotonic() - t0) * 1000, 1)
        signals = _analyze_html(html)

        # Use best available count from checkpoints
        for cp in checkpoints.values():
            if cp.get("count") is not None and signals["count"] is None:
                signals["count"] = cp["count"]
                signals["raw_match"] = cp["raw_match"]
                break

        result.update(
            {
                "final_url": final_url,
                "content_length": len(html),
                "duration_ms": elapsed,
                **signals,
                "success": signals["count"] is not None,
            }
        )
        _save_debug(
            "playwright_wait_progressive_checkpoints.json",
            json.dumps(checkpoints, indent=2),
        )
        _save_debug("playwright_wait_progressive_response.html", html)
    except Exception as exc:
        result["error"] = str(exc)
        result["duration_ms"] = round((time.monotonic() - t0) * 1000, 1)

    return result


def test_playwright_screenshot(url: str) -> dict:
    """Playwright + screenshot (saved when DEBUG_SCRAPING=true)."""
    if not _playwright_available():
        return _playwright_missing_result("playwright_screenshot", url)

    result = _base_result(
        "playwright_screenshot", method="playwright_chromium_screenshot", url_variant=url
    )
    t0 = time.monotonic()
    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            ctx = browser.new_context(
                locale="fr-FR",
                timezone_id="Indian/Reunion",
                viewport={"width": 1366, "height": 768},
                user_agent=_BROWSER_UA,
            )
            page = ctx.new_page()
            resp = page.goto(url, wait_until="networkidle", timeout=30_000)
            page.wait_for_timeout(2_000)

            if _DEBUG:
                _DEBUG_DIR.mkdir(parents=True, exist_ok=True)
                page.screenshot(
                    path=str(_DEBUG_DIR / "playwright_screenshot.png"), full_page=True
                )

            body_text = page.inner_text("body")
            html = page.content()
            status = resp.status if resp else None
            final_url = page.url
            browser.close()

        elapsed = round((time.monotonic() - t0) * 1000, 1)
        signals = _pw_analyze(html, body_text)
        result.update(
            {
                "status_code": status,
                "final_url": final_url,
                "content_length": len(html),
                "duration_ms": elapsed,
                **signals,
                "success": signals["count"] is not None,
            }
        )
        _save_debug("playwright_screenshot_response.html", html)
    except Exception as exc:
        result["error"] = str(exc)
        result["duration_ms"] = round((time.monotonic() - t0) * 1000, 1)

    return result


# ── Tests 16–19 : Anti-bot bypass techniques ──────────────────────────────────


def test_http_referrer_google(url: str) -> dict:
    """
    Simulate organic search traffic — Referer: google.fr.
    DataDome attribue un score de confiance plus élevé aux sessions venant
    d'un moteur de recherche. Teste si l'origine HTTP change le comportement.
    """
    headers = {
        **_BROWSER_HEADERS,
        "Referer": "https://www.google.fr/",
        "Sec-Fetch-Site": "cross-site",
    }
    return _httpx_get("http_referrer_google", url, headers)


def test_http_client_hints(url: str) -> dict:
    """
    Ajoute les Sec-CH-UA Client Hints (Chrome 124).
    Leur absence est un signal bot — Chrome les envoie systématiquement
    depuis la v89. Les scrapers sans TLS spoofing les omettent souvent.
    """
    return _httpx_get("http_client_hints", url, {**_BROWSER_HEADERS, **_CLIENT_HINTS})


def test_http_session_warmup(url: str) -> dict:
    """
    Cookie warmup — visite la homepage avant la recherche.
    DataDome crée un cookie _dd_s lors de la première visite ; les requêtes
    suivantes dans la même session reçoivent un score de confiance plus élevé.
    """
    result = _base_result("http_session_warmup", method="httpx_cookie_warmup", url_variant=url)
    try:
        import httpx
    except ImportError:
        result["error"] = "httpx not installed"
        return result

    t0 = time.monotonic()
    try:
        with httpx.Client(follow_redirects=True, timeout=20) as client:
            # Step 1 — homepage (no referrer, fresh session)
            try:
                client.get(
                    "https://www.leboncoin.fr/",
                    headers={**_BROWSER_HEADERS, "Sec-Fetch-Site": "none"},
                )
                time.sleep(1.2)
            except Exception:
                pass  # warmup failure is non-fatal

            # Step 2 — search with same-origin referrer (cookies already set)
            headers = {
                **_BROWSER_HEADERS,
                "Referer": "https://www.leboncoin.fr/",
                "Sec-Fetch-Site": "same-origin",
            }
            resp = client.get(url, headers=headers)

        elapsed = round((time.monotonic() - t0) * 1000, 1)
        html = resp.text
        signals = _analyze_html(html)
        result.update(
            {
                "status_code": resp.status_code,
                "final_url": str(resp.url),
                "content_type": resp.headers.get("content-type", ""),
                "content_length": len(resp.content),
                "duration_ms": elapsed,
                **signals,
                "success": resp.status_code == 200 and signals["count"] is not None,
            }
        )
        if resp.status_code in (403, 429, 503):
            result["contains_blocked"] = True
        _save_debug("http_session_warmup_response.html", html)
        _save_debug(
            "http_session_warmup_metadata.json",
            json.dumps({"status_code": resp.status_code, "headers": _scrub_headers(resp.headers)}, indent=2),
        )
    except Exception as exc:
        result["error"] = str(exc)
        result["duration_ms"] = round((time.monotonic() - t0) * 1000, 1)

    return result


def test_http_curl_cffi(url: str) -> dict:
    """
    TLS fingerprint spoofing via curl_cffi (impersonate=chrome124).
    Contourne la détection JA3/JA4 — la signature TLS du handshake correspond
    exactement à celle de Chrome 124. httpx et requests exposent une signature
    OpenSSL reconnaissable comme non-browser.
    """
    result = _base_result("http_curl_cffi", method="curl_cffi_chrome124", url_variant=url)
    try:
        from curl_cffi import requests as cffi_requests
    except ImportError:
        result["error"] = "curl_cffi not installed — pip install curl-cffi"
        return result

    t0 = time.monotonic()
    try:
        # curl_cffi gère User-Agent et Accept-Encoding nativement pour chrome124
        headers = {
            k: v
            for k, v in {**_BROWSER_HEADERS, **_CLIENT_HINTS}.items()
            if k not in ("User-Agent", "Accept-Encoding")
        }
        resp = cffi_requests.get(
            url,
            impersonate="chrome124",
            headers=headers,
            timeout=20,
            allow_redirects=True,
        )
        elapsed = round((time.monotonic() - t0) * 1000, 1)
        html = resp.text
        signals = _analyze_html(html)
        result.update(
            {
                "status_code": resp.status_code,
                "final_url": str(resp.url),
                "content_type": resp.headers.get("content-type", ""),
                "content_length": len(resp.content),
                "duration_ms": elapsed,
                **signals,
                "success": resp.status_code == 200 and signals["count"] is not None,
            }
        )
        if resp.status_code in (403, 429, 503):
            result["contains_blocked"] = True
        _save_debug("http_curl_cffi_response.html", html)
        _save_debug(
            "http_curl_cffi_metadata.json",
            json.dumps({"status_code": resp.status_code, "headers": _scrub_headers(resp.headers)}, indent=2),
        )
    except Exception as exc:
        result["error"] = str(exc)
        result["duration_ms"] = round((time.monotonic() - t0) * 1000, 1)

    return result


# ── Orchestration ─────────────────────────────────────────────────────────────


def run_all_tests(url: str) -> list[dict]:
    tests = [
        # — Spécifiés —
        ("http_minimal", lambda: test_http_minimal(url)),
        ("http_browser_headers", lambda: test_http_browser_headers(url)),
        ("http_browser_headers_http2", lambda: test_http_browser_headers_http2(url)),
        ("url_exact", lambda: test_url_exact(url)),
        ("url_without_from", lambda: test_url_without_from(url)),
        ("url_encoded", lambda: test_url_encoded(url)),
        ("url_minimal_search", lambda: test_url_minimal_search()),
        ("html_regex_text", lambda: test_html_regex_text(url)),
        ("html_meta_tags", lambda: test_html_meta_tags(url)),
        ("html_embedded_json", lambda: test_html_embedded_json(url)),
        ("html_visible_text_beautifulsoup", lambda: test_html_visible_text_beautifulsoup(url)),
        ("playwright_headless_basic", lambda: test_playwright_headless_basic(url)),
        ("playwright_headless_locale_fr", lambda: test_playwright_headless_locale_fr(url)),
        ("playwright_wait_progressive", lambda: test_playwright_wait_progressive(url)),
        ("playwright_screenshot", lambda: test_playwright_screenshot(url)),
        # — Anti-bot bypass (ajouts) —
        ("http_referrer_google", lambda: test_http_referrer_google(url)),
        ("http_client_hints", lambda: test_http_client_hints(url)),
        ("http_session_warmup", lambda: test_http_session_warmup(url)),
        ("http_curl_cffi", lambda: test_http_curl_cffi(url)),
    ]

    results: list[dict] = []
    for test_id, fn in tests:
        logger.info("▶ %s", test_id)
        try:
            r = fn()
        except Exception as exc:
            r = _base_result(test_id, method="unknown", url_variant=url)
            r["error"] = f"Unhandled exception: {exc}"
        results.append(r)
        status = "✓" if r["success"] else "✗"
        logger.info(
            "  %s count=%-6s status=%-4s %s",
            status,
            r.get("count"),
            r.get("status_code"),
            r.get("error") or "",
        )

    return results


# ── Entry point ───────────────────────────────────────────────────────────────


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        stream=sys.stdout,
    )

    url = _load_configured_url()
    env = _detect_environment()
    logger.info("environment : %s", env)
    logger.info("url         : %s", url[:120])
    logger.info("DEBUG_SCRAPING: %s", _DEBUG)

    if _DEBUG:
        _DEBUG_DIR.mkdir(parents=True, exist_ok=True)
        (_DEBUG_DIR / "environment_info.json").write_text(
            json.dumps(_environment_info(), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    results = run_all_tests(url)

    summary = {
        "environment": env,
        "url": url,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "debug": _DEBUG,
        "total": len(results),
        "successful": sum(1 for r in results if r["success"]),
        "results": results,
    }

    _DEBUG_DIR.mkdir(parents=True, exist_ok=True)
    summary_path = _DEBUG_DIR / "scraping_diagnostics_summary.json"
    summary_path.write_text(
        json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    # ── Console table ─────────────────────────────────────────────────────────
    w = 44
    print()
    print("=" * 90)
    print(f"{'TEST_ID':<{w}} {'STATUS':<9} {'COUNT':<8} {'HTTP':<6} ERROR")
    print("=" * 90)
    for r in results:
        flag = "SUCCESS" if r["success"] else "FAILED "
        print(
            f"{r['test_id']:<{w}} {flag:<9} {str(r.get('count') or ''):<8} "
            f"{str(r.get('status_code') or ''):<6} {r.get('error') or ''}"
        )
    print("=" * 90)
    print(f"  {summary['successful']}/{summary['total']} tests successful")
    print(f"  Summary → {summary_path}")
    print()


if __name__ == "__main__":
    main()
