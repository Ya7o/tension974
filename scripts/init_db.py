#!/usr/bin/env python3
"""Initialize the SQLite database."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from tension974.settings import get_database_path, get_log_level, get_log_file
from tension974.logging_config import setup_logging
from tension974.database import init_db

if __name__ == "__main__":
    logger = setup_logging(get_log_level(), get_log_file())
    db_path = get_database_path()
    init_db(db_path)
    logger.info("Database initialized at %s", db_path)
    print(f"Database initialized: {db_path}")
