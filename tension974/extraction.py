import re


_PATTERN = re.compile(
    r"(\d[\d\s ]*)\s*annonce",
    re.IGNORECASE,
)


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
