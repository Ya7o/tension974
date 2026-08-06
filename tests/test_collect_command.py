import sys


from tension974 import collect
from tension974.models import Observation


def test_jsonl_storage_command_runs(monkeypatch, tmp_path):
    monkeypatch.setenv("DATA_DIR", str(tmp_path / "data"))

    def fake_run_collection(config_path, provider, storage):
        storage.initialize()
        return [
            Observation(
                search_id="saint_denis_t3",
                observed_at="2026-04-27T00:00:00+00:00",
                status="success",
                provider=provider.name,
                total_listings_count=12,
            )
        ]

    monkeypatch.setattr(collect, "run_collection_with_storage", fake_run_collection)

    assert collect.main(["--storage", "jsonl"]) == 0


def test_exit_code_is_nonzero_when_every_search_fails(monkeypatch, tmp_path):
    """Une collecte 100 % en échec doit faire échouer le job CI appelant."""
    monkeypatch.setenv("DATA_DIR", str(tmp_path / "data"))

    def fake_run_collection(config_path, provider, storage):
        storage.initialize()
        return [
            Observation(
                search_id="saint_denis_t3",
                observed_at="2026-04-27T00:00:00+00:00",
                status="failed",
                provider=provider.name,
                error_message="Blocked by anti-bot challenge.",
            )
        ]

    monkeypatch.setattr(collect, "run_collection_with_storage", fake_run_collection)

    assert collect.main(["--storage", "jsonl"]) == 1


def test_exit_code_is_zero_when_only_some_searches_fail(monkeypatch, tmp_path):
    """Échec partiel = données quand même produites = job vert (le statut
    « partial » du run porte l'information)."""
    monkeypatch.setenv("DATA_DIR", str(tmp_path / "data"))

    def fake_run_collection(config_path, provider, storage):
        storage.initialize()
        return [
            Observation(search_id="a", observed_at="2026-04-27T00:00:00+00:00",
                        status="success", provider=provider.name, total_listings_count=12),
            Observation(search_id="b", observed_at="2026-04-27T00:00:00+00:00",
                        status="failed", provider=provider.name, error_message="blocked"),
        ]

    monkeypatch.setattr(collect, "run_collection_with_storage", fake_run_collection)

    assert collect.main(["--storage", "jsonl"]) == 0


class _FakeCreditsProvider:
    def __init__(self, payload):
        self._payload = payload

    def get_account_credits(self):
        return self._payload


def test_report_credits_emits_github_warning_when_low(monkeypatch, tmp_path, capsys):
    summary = tmp_path / "summary.md"
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(summary))
    import logging

    collect._report_credits(_FakeCreditsProvider({"remaining_credits": 40}), logging.getLogger("t"))

    out = capsys.readouterr().out
    assert "[CREDITS] 40" in out
    assert "::warning" in out
    assert "40" in summary.read_text(encoding="utf-8")


def test_report_credits_stays_quiet_above_threshold(monkeypatch, tmp_path, capsys):
    summary = tmp_path / "summary.md"
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(summary))
    import logging

    collect._report_credits(_FakeCreditsProvider({"remaining_credits": 5000}), logging.getLogger("t"))

    out = capsys.readouterr().out
    assert "[CREDITS] 5000" in out
    assert "::warning" not in out
    assert not summary.exists()


def test_report_credits_survives_error_and_bad_payloads(capsys):
    """Réponse en erreur, solde manquant ou non numérique : jamais de crash."""
    import logging
    logger = logging.getLogger("t")

    collect._report_credits(_FakeCreditsProvider({"error": "boom"}), logger)
    collect._report_credits(_FakeCreditsProvider({}), logger)
    collect._report_credits(_FakeCreditsProvider({"remaining_credits": "beaucoup"}), logger)

    assert "::warning" not in capsys.readouterr().out


def test_sqlite_storage_command_still_runs(monkeypatch, tmp_path):
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "tension974.db"))

    def fake_run_collection(config_path, provider, storage):
        storage.initialize()
        return [
            Observation(
                search_id="saint_denis_t3",
                observed_at="2026-04-27T00:00:00+00:00",
                status="success",
                provider=provider.name,
                total_listings_count=12,
            )
        ]

    monkeypatch.setattr(collect, "run_collection_with_storage", fake_run_collection)

    assert collect.main(["--storage", "sqlite"]) == 0
