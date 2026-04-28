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
