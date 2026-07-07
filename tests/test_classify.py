import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from tension974.diagnostics.classify import categorize_error, category_label, CATEGORY_NONE


def test_none_message_is_none_category():
    assert categorize_error(None) == CATEGORY_NONE
    assert categorize_error("") == CATEGORY_NONE


def test_blocked_detection():
    assert categorize_error("403 Forbidden - DataDome challenge") == "blocked"
    assert categorize_error("Request blocked by Cloudflare") == "blocked"


def test_rate_limited_detection():
    assert categorize_error("429 Too Many Requests") == "rate_limited"


def test_timeout_detection():
    assert categorize_error("Read timed out after 20s") == "timeout"


def test_network_detection():
    assert categorize_error("Connection refused by remote host") == "network"


def test_no_data_detection():
    assert categorize_error("No listings count found in content.") == "no_data"


def test_credentials_detection():
    assert categorize_error("FIRECRAWL_API_KEY invalid: 401 Unauthorized") == "credentials"


def test_unknown_falls_back():
    assert categorize_error("Something weird happened") == "unknown"


def test_category_label_has_french_text():
    assert "Bloqué" in category_label("blocked")
    assert category_label("made_up") == "made_up"
