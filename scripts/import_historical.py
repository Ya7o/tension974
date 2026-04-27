#!/usr/bin/env python3
"""Import des données historiques manuelles dans la base SQLite."""
import sys
import math
from pathlib import Path
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).parent.parent))

from tension974.settings import get_database_path, get_searches_config_path
from tension974.database import init_db, upsert_search, insert_observation
from tension974.collector import load_searches
from tension974.models import Observation

# ── Données historiques ──────────────────────────────────────────────────────
# Format : (année, mois, [valeurs relevées dans le mois])
HISTORICAL = {
    "studio_saint_denis": [
        (2025,  6, [180, 160, 146, 130, 124, 100]),
        (2025,  8, [96, 94, 74, 74, 78]),
        (2025,  9, [64, 63, 59, 61, 54]),
        (2025, 10, [48, 52]),
        (2025, 11, [57, 61, 62]),
        (2025, 12, [56, 69]),
        (2026,  1, [72, 73, 71, 57]),
        (2026,  2, [57, 58, 68]),
        (2026,  3, [80, 86, 88]),
    ],
    "t2_t3_saint_denis": [
        (2025, 12, [59]),
        (2026,  1, [55, 50, 58, 59]),
        (2026,  2, [53, 54, 58]),
        (2026,  3, [70, 71, 66]),
    ],
    "t3_saint_denis": [
        (2025,  6, [40]),
        (2025,  7, [43, 41, 39, 41]),
        (2025,  8, [36, 39, 41, 39]),
        (2025,  9, [35, 40, 36, 43]),
        (2025, 10, [40, 32]),
        (2025, 11, [36, 34, 31]),
        (2025, 12, [34, 30, 32]),
        (2026,  1, [30, 30, 29, 31]),
        (2026,  2, [31, 28]),
        (2026,  3, [31, 32, 39]),
    ],
}


def _spread_days(n: int) -> list[int]:
    """Répartit n relevés sur ~28 jours (du 2 au 28)."""
    if n == 1:
        return [14]
    return [round(2 + i * 26 / (n - 1)) for i in range(n)]


def _make_iso(year: int, month: int, day: int) -> str:
    # Heure cron 21h15 La Réunion = 17h15 UTC
    return datetime(year, month, day, 17, 15, 0, tzinfo=timezone.utc).isoformat()


def main():
    db_path = get_database_path()
    config_path = get_searches_config_path()

    init_db(db_path)
    searches = {s.id: s for s in load_searches(config_path)}

    total = 0
    for search_id, months in HISTORICAL.items():
        if search_id not in searches:
            print(f"SKIP: {search_id} absent de la config")
            continue
        upsert_search(db_path, searches[search_id])
        for year, month, values in months:
            days = _spread_days(len(values))
            for day, count in zip(days, values):
                obs = Observation(
                    search_id=search_id,
                    observed_at=_make_iso(year, month, day),
                    status="success",
                    provider="historical_import",
                    total_listings_count=count,
                    raw_total_listings_text=f"{count} annonces",
                    credits_used=0,
                )
                insert_observation(db_path, obs)
                total += 1
        print(f"[OK] {search_id} : {sum(len(v) for _, _, v in months)} relevés importés")

    print(f"\nTotal : {total} observations insérées.")


if __name__ == "__main__":
    main()
