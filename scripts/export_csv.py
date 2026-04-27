#!/usr/bin/env python3
"""Export observations to CSV."""
import csv
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from tension974.settings import get_database_path, get_searches_config_path, get_log_level, get_log_file
from tension974.logging_config import setup_logging
from tension974.collector import load_searches
from tension974.database import get_observations

if __name__ == "__main__":
    logger = setup_logging(get_log_level(), get_log_file())
    db_path = get_database_path()
    config_path = get_searches_config_path()
    searches = load_searches(config_path)

    Path("exports").mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    for search in searches:
        rows = get_observations(db_path, search.id)
        if not rows:
            logger.info("No observations for %s", search.id)
            continue
        filename = f"exports/{search.id}_{timestamp}.csv"
        with open(filename, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=rows[0].keys())
            writer.writeheader()
            writer.writerows(rows)
        logger.info("Exported %d rows to %s", len(rows), filename)
        print(f"Exported: {filename} ({len(rows)} rows)")
