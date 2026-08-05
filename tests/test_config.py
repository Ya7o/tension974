"""Validation structurelle de config/searches.yaml.

Volontairement pas de verrou sur le contenu exact (ids, nombre de recherches,
active: true) : la config de production doit pouvoir évoluer sans casser les
tests. On vérifie la forme, pas les choix éditoriaux.
"""
import pytest
from pathlib import Path

CONFIG_PATH = Path(__file__).parent.parent / "config" / "searches.yaml"

REQUIRED_KEYS = ("id", "name", "platform", "url")


def _load():
    import yaml
    with open(CONFIG_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f)


def test_config_file_exists():
    assert CONFIG_PATH.exists()


def test_config_has_searches():
    data = _load()
    assert "searches" in data
    assert len(data["searches"]) >= 1


def test_each_search_has_required_keys():
    for s in _load()["searches"]:
        for key in REQUIRED_KEYS:
            assert s.get(key), f"clé '{key}' manquante ou vide dans {s}"


def test_search_ids_are_unique():
    ids = [s["id"] for s in _load()["searches"]]
    assert len(ids) == len(set(ids)), f"ids dupliqués : {ids}"


def test_leboncoin_searches_have_leboncoin_urls():
    for s in _load()["searches"]:
        if s["platform"] == "leboncoin":
            assert "leboncoin.fr" in s["url"], f"{s['id']} URL invalide"


def test_load_searches_parses_the_real_config():
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from tension974.collector import load_searches
    searches = load_searches(str(CONFIG_PATH))
    assert len(searches) >= 1
    for s in searches:
        assert s.id and s.name and s.url
