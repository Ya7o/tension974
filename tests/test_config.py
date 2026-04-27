import pytest
from pathlib import Path

CONFIG_PATH = Path(__file__).parent.parent / "config" / "searches.yaml"

EXPECTED_IDS = {"studio_saint_denis", "t2_t3_saint_denis", "t3_saint_denis"}


def test_config_file_exists():
    assert CONFIG_PATH.exists()


def test_config_loads():
    import yaml
    with open(CONFIG_PATH, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    assert "searches" in data
    assert len(data["searches"]) == 3


def test_all_searches_present():
    import yaml
    with open(CONFIG_PATH, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    ids = {s["id"] for s in data["searches"]}
    assert ids == EXPECTED_IDS


def test_all_urls_are_leboncoin():
    import yaml
    with open(CONFIG_PATH, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    for s in data["searches"]:
        assert "leboncoin.fr" in s["url"], f"{s['id']} URL invalide"


def test_all_searches_active():
    import yaml
    with open(CONFIG_PATH, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    for s in data["searches"]:
        assert s.get("active") is True, f"{s['id']} n'est pas actif"


def test_load_searches():
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from tension974.collector import load_searches
    searches = load_searches(str(CONFIG_PATH))
    assert len(searches) == 3
    ids = {s.id for s in searches}
    assert ids == EXPECTED_IDS
