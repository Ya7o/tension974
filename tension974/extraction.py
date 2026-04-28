import re
from dataclasses import dataclass
from statistics import median


_PATTERN = re.compile(
    r"(\d[\d\s ]*)\s*annonce",
    re.IGNORECASE,
)
_MAX_PRICE_SAMPLE_SIZE = 30

_PRICE_PATTERN = re.compile(
    r"(?<![\w/])((?:\d{1,3}[\s ]\d{3})|\d{2,5})\s*(?:€|EUR|euros?)(?=$|[^\w])",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class PriceStats:
    median_price: int
    average_price: int
    sample_size: int
    min_price: int
    max_price: int


def extract_total_listings_count(text: str) -> int | None:
    """Extract total listings count from Leboncoin page text.

    Handles: "242 annonces", "1 annonce", "1 234 annonces", non-breaking spaces.
    Returns None if no count found. Returns 0 for "Aucune annonce".
    """
    if not text:
        return None

    if re.search(r"aucune\s+annonce", text, re.IGNORECASE):
        return 0

    match = _PATTERN.search(text)
    if not match:
        return None

    raw = match.group(1)
    # Remove all whitespace and non-breaking spaces used as thousands separators
    digits = re.sub(r"[\s ]", "", raw)
    try:
        return int(digits)
    except ValueError:
        return None


def extract_price_stats(text: str) -> PriceStats | None:
    """Extract rough price stats from visible listing prices.

    The search pages also contain filter prices and sometimes deposits/fees. This
    keeps a conservative rental range to avoid counting listing ids, dates, or
    obviously unrelated values.
    """
    prices = extract_listing_prices(text)
    if not prices:
        return None
    prices = prices[:_MAX_PRICE_SAMPLE_SIZE]
    return PriceStats(
        median_price=round(median(prices)),
        average_price=round(sum(prices) / len(prices)),
        sample_size=len(prices),
        min_price=min(prices),
        max_price=max(prices),
    )


def extract_listing_prices(text: str) -> list[int]:
    if not text:
        return []

    prices: list[int] = []
    for match in _PRICE_PATTERN.finditer(text):
        value = _parse_price(match.group(1))
        if value is None:
            continue
        if not 250 <= value <= 5000:
            continue
        if _looks_like_filter_price(text, match.start()):
            continue
        prices.append(value)

    return prices


def _parse_price(raw: str) -> int | None:
    digits = re.sub(r"[\s ]", "", raw)
    try:
        return int(digits)
    except ValueError:
        return None


def _looks_like_filter_price(text: str, start: int) -> bool:
    line_start = text.rfind("\n", 0, start) + 1
    context = text[line_start:start].lower()
    return any(
        marker in context
        for marker in (
            "prix",
            "budget",
            "loyer max",
            "loyer min",
            "minimum",
            "maximum",
            "filtre",
            "filter",
        )
    )
