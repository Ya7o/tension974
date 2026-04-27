import pytest
from tension974.extraction import extract_total_listings_count


@pytest.mark.parametrize("text,expected", [
    ("242 annonces", 242),
    ("1 annonce", 1),
    ("1 234 annonces", 1234),
    ("1 234 annonces", 1234),
    ("  57   annonces disponibles", 57),
    ("Aucune annonce trouvée", 0),
    ("aucune annonce", 0),
    ("Pas de résultat ici", None),
    ("", None),
    ("Bonjour le monde", None),
    ("12 345 annonces", 12345),
])
def test_extract(text, expected):
    assert extract_total_listings_count(text) == expected
