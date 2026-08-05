import pytest
from tension974.extraction import extract_listing_prices, extract_price_stats, extract_total_listings_count


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


@pytest.mark.parametrize("text,expected", [
    # Régressions : l'ancien motif avalait tout chiffre voisin à travers les
    # retours à la ligne et fabriquait des compteurs fantaisistes (67012).
    ("Loyer 670\n12 annonces", 12),
    ("Prix\n1200\n\n12 annonces", 12),
    ("Studio 650 € charges comprises\n110 annonces", 110),
    # Un widget "annonce sauvegardée" ne doit pas masquer le vrai compteur.
    ("1 annonce sauvegardée\n\nLeboncoin\n242 annonces", 242),
    ("3 annonces vues récemment\n88 annonces", 88),
    # Plafond de vraisemblance : un nombre absurde est un artefact, pas un compteur.
    ("999999999 annonces", None),
])
def test_extract_regressions(text, expected):
    assert extract_total_listings_count(text) == expected


def test_extract_listing_prices():
    text = """
    242 annonces
    Filtres prix max 1 000 €
    Studio meuble - Saint-Denis
    690 €
    Appartement T2 proche centre
    850 EUR
    Grand T3
    1 250 euros
    """

    assert extract_listing_prices(text) == [690, 850, 1250]


def test_extract_price_stats():
    stats = extract_price_stats("690 €\n850 €\n1 250 €")

    assert stats is not None
    assert stats.median_price == 850
    assert stats.average_price == 930
    assert stats.sample_size == 3
    assert stats.min_price == 690
    assert stats.max_price == 1250


def test_extract_price_stats_returns_none_without_prices():
    assert extract_price_stats("242 annonces sans prix visible") is None


def test_extract_price_stats_caps_sample_to_first_30_prices():
    prices = "\n".join(f"{500 + i} €" for i in range(35))

    stats = extract_price_stats(prices)

    assert stats is not None
    assert stats.sample_size == 30
    assert stats.min_price == 500
    assert stats.max_price == 529
    assert stats.median_price == 514
