"""Classify collection failures for the dashboard health timeline.

Turns a raw error_message into a stable category so the dashboard can show
*why* a collection failed (anti-bot firewall vs. network vs. page format
change) instead of just a red dot.
"""
from __future__ import annotations

import re

CATEGORY_BLOCKED = "blocked"
CATEGORY_RATE_LIMITED = "rate_limited"
CATEGORY_TIMEOUT = "timeout"
CATEGORY_NETWORK = "network"
CATEGORY_NO_DATA = "no_data"
CATEGORY_CREDENTIALS = "credentials"
CATEGORY_UNKNOWN = "unknown"
CATEGORY_NONE = "none"

_LABELS = {
    CATEGORY_BLOCKED: "Bloqué (firewall / anti-bot)",
    CATEGORY_RATE_LIMITED: "Limite de débit",
    CATEGORY_TIMEOUT: "Délai dépassé",
    CATEGORY_NETWORK: "Erreur réseau",
    CATEGORY_NO_DATA: "Page changée / compteur introuvable",
    CATEGORY_CREDENTIALS: "Erreur de configuration",
    CATEGORY_UNKNOWN: "Erreur inconnue",
    CATEGORY_NONE: "Succès",
}

_PATTERNS: list[tuple[str, re.Pattern]] = [
    (CATEGORY_BLOCKED, re.compile(
        r"datadome|captcha|forbidden|access denied|cloudflare|"
        r"\b403\b|blocked|bot detection|akamai|perimeterx",
        re.IGNORECASE,
    )),
    (CATEGORY_RATE_LIMITED, re.compile(r"\b429\b|rate limit|too many requests", re.IGNORECASE)),
    (CATEGORY_TIMEOUT, re.compile(r"timed?\s*out|timeout", re.IGNORECASE)),
    (CATEGORY_CREDENTIALS, re.compile(r"api[_ ]?key|credentials|unauthorized|\b401\b", re.IGNORECASE)),
    (CATEGORY_NETWORK, re.compile(
        r"connection|dns|resolve|refused|reset by peer|network|"
        r"ssl|certificate|\b5\d\d\b",
        re.IGNORECASE,
    )),
    (CATEGORY_NO_DATA, re.compile(r"no listings count|compteur introuvable|introuvable", re.IGNORECASE)),
]


def categorize_error(error_message: str | None) -> str:
    """Return a stable category slug for an observation's error_message."""
    if not error_message:
        return CATEGORY_NONE
    for category, pattern in _PATTERNS:
        if pattern.search(error_message):
            return category
    return CATEGORY_UNKNOWN


def category_label(category: str) -> str:
    return _LABELS.get(category, category)
