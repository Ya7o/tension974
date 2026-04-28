import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .models import Observation, SearchConfig


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def get_connection(db_path: str) -> sqlite3.Connection:
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db(db_path: str) -> None:
    conn = get_connection(db_path)
    with conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS searches (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                platform TEXT NOT NULL,
                url TEXT NOT NULL,
                location TEXT,
                property_type TEXT,
                active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS observations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                search_id TEXT NOT NULL,
                observed_at TEXT NOT NULL,
                total_listings_count INTEGER,
                raw_total_listings_text TEXT,
                average_price INTEGER,
                price_sample_size INTEGER,
                min_price INTEGER,
                max_price INTEGER,
                status TEXT NOT NULL,
                provider TEXT NOT NULL,
                error_message TEXT,
                credits_used INTEGER,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS collection_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                started_at TEXT NOT NULL,
                finished_at TEXT,
                status TEXT NOT NULL,
                provider TEXT,
                error_message TEXT
            );
        """)
    # Migration: add credits_used column if DB pre-dates this feature
    with conn:
        try:
            conn.execute("ALTER TABLE observations ADD COLUMN credits_used INTEGER")
        except Exception:
            pass
    for column, column_type in (
        ("average_price", "INTEGER"),
        ("price_sample_size", "INTEGER"),
        ("min_price", "INTEGER"),
        ("max_price", "INTEGER"),
    ):
        with conn:
            try:
                conn.execute(f"ALTER TABLE observations ADD COLUMN {column} {column_type}")
            except Exception:
                pass
    conn.close()


def upsert_search(db_path: str, search: SearchConfig) -> None:
    conn = get_connection(db_path)
    with conn:
        conn.execute(
            """
            INSERT INTO searches (id, name, platform, url, location, property_type, active, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                name=excluded.name,
                platform=excluded.platform,
                url=excluded.url,
                location=excluded.location,
                property_type=excluded.property_type,
                active=excluded.active
            """,
            (
                search.id,
                search.name,
                search.platform,
                search.url,
                search.location,
                search.property_type,
                1 if search.active else 0,
                _now_iso(),
            ),
        )
    conn.close()


def insert_observation(db_path: str, obs: Observation) -> int:
    conn = get_connection(db_path)
    now = _now_iso()
    with conn:
        cursor = conn.execute(
            """
            INSERT INTO observations
                (search_id, observed_at, total_listings_count, raw_total_listings_text,
                 average_price, price_sample_size, min_price, max_price,
                 status, provider, error_message, credits_used, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                obs.search_id,
                obs.observed_at,
                obs.total_listings_count,
                obs.raw_total_listings_text,
                obs.average_price,
                obs.price_sample_size,
                obs.min_price,
                obs.max_price,
                obs.status,
                obs.provider,
                obs.error_message,
                obs.credits_used,
                now,
            ),
        )
        row_id = cursor.lastrowid
    conn.close()
    return row_id


def get_observations(db_path: str, search_id: str, limit: int = 200) -> list[dict[str, Any]]:
    conn = get_connection(db_path)
    rows = conn.execute(
        """
        SELECT * FROM observations
        WHERE search_id = ?
        ORDER BY observed_at DESC
        LIMIT ?
        """,
        (search_id, limit),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_last_observation(db_path: str, search_id: str) -> dict[str, Any] | None:
    conn = get_connection(db_path)
    row = conn.execute(
        """
        SELECT * FROM observations
        WHERE search_id = ? AND status = 'success'
        ORDER BY observed_at DESC
        LIMIT 1
        """,
        (search_id,),
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def start_collection_run(db_path: str, provider: str) -> int:
    conn = get_connection(db_path)
    with conn:
        cursor = conn.execute(
            "INSERT INTO collection_runs (started_at, status, provider) VALUES (?, ?, ?)",
            (_now_iso(), "running", provider),
        )
        run_id = cursor.lastrowid
    conn.close()
    return run_id


def finish_collection_run(db_path: str, run_id: int, status: str, error_message: str | None = None) -> None:
    conn = get_connection(db_path)
    with conn:
        conn.execute(
            "UPDATE collection_runs SET finished_at=?, status=?, error_message=? WHERE id=?",
            (_now_iso(), status, error_message, run_id),
        )
    conn.close()


def get_total_credits_used(db_path: str, search_id: str) -> int:
    conn = get_connection(db_path)
    row = conn.execute(
        "SELECT COALESCE(SUM(credits_used), 0) FROM observations WHERE search_id = ?",
        (search_id,),
    ).fetchone()
    conn.close()
    return int(row[0]) if row else 0


def get_recent_errors(db_path: str, search_id: str, limit: int = 5) -> list[dict[str, Any]]:
    conn = get_connection(db_path)
    rows = conn.execute(
        """
        SELECT * FROM observations
        WHERE search_id = ? AND status = 'failed'
        ORDER BY observed_at DESC
        LIMIT ?
        """,
        (search_id, limit),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]
