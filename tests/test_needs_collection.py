"""Décision de rattrapage : ne relancer une collecte que si l'historique
n'a rien reçu, pour ne pas dépenser de crédits Firecrawl inutilement."""
from datetime import datetime, timedelta, timezone

from scripts.needs_collection import decide, latest_success, read_observations

NOW = datetime(2026, 8, 7, 5, 15, tzinfo=timezone.utc)


def _obs(days_ago: float, status: str = "success") -> dict:
    return {
        "search_id": "studio_saint_denis",
        "observed_at": (NOW - timedelta(days=days_ago)).isoformat(),
        "status": status,
    }


def test_no_catchup_when_weekly_collection_succeeded():
    needed, reason = decide([_obs(1)], max_age_days=6, now=NOW)
    assert needed is False
    assert "rien à rattraper" in reason


def test_catchup_when_last_success_is_too_old():
    """Cas du 6 août 2026 : le cron n'a jamais obtenu de runner."""
    needed, reason = decide([_obs(8)], max_age_days=6, now=NOW)
    assert needed is True
    assert "8 j" in reason


def test_catchup_when_history_is_empty():
    needed, reason = decide([], max_age_days=6, now=NOW)
    assert needed is True
    assert "aucun relevé" in reason


def test_failed_observations_do_not_count_as_a_collection():
    """Une collecte entièrement bloquée n'a rien ramené : on rattrape."""
    needed, _ = decide([_obs(8), _obs(0.5, status="failed")], max_age_days=6, now=NOW)
    assert needed is True


def test_latest_success_takes_the_most_recent_across_searches():
    observations = [_obs(5), {**_obs(2), "search_id": "t3_saint_denis"}, _obs(9)]
    assert latest_success(observations) == NOW - timedelta(days=2)


def test_latest_success_ignores_unparseable_timestamps():
    observations = [{"status": "success", "observed_at": "pas une date"}, _obs(3)]
    assert latest_success(observations) == NOW - timedelta(days=3)


def test_read_observations_skips_malformed_lines(tmp_path):
    path = tmp_path / "observations.jsonl"
    path.write_text(
        '{"status": "success", "observed_at": "2026-08-01T00:00:00+00:00"}\n'
        "{ceci n'est pas du json}\n"
        '{"status": "failed"}\n',
        encoding="utf-8",
    )
    assert len(read_observations(path)) == 2


def test_read_observations_on_missing_file(tmp_path):
    assert read_observations(tmp_path / "absent.jsonl") == []
