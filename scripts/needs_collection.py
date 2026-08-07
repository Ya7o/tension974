#!/usr/bin/env python3
"""Décide si une collecte de rattrapage est nécessaire.

Le cron hebdomadaire peut être perdu sans qu'aucun garde-fou du workflow ne
puisse s'appliquer : si GitHub n'alloue pas de runner (incident du 6 août
2026 — job annulé après 15 min d'attente, zéro étape exécutée), il n'y a ni
collecte, ni commit, ni notification. Les crons de rattrapage des jours
suivants appellent donc ce script, qui ne relance une collecte que si aucun
relevé n'a réussi depuis `--max-age-days` jours — pour ne pas consommer de
crédits Firecrawl quand la collecte hebdomadaire a fait son travail.

Écrit `needed=true|false` dans $GITHUB_OUTPUT quand la variable existe.
"""
import argparse
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from tension974.aggregation import parse_iso
from tension974.settings import get_data_dir


def latest_success(observations: list[dict]) -> datetime | None:
    """Horodatage du relevé réussi le plus récent, tous search_id confondus."""
    dates = [
        parsed
        for o in observations
        if o.get("status") == "success"
        and (parsed := parse_iso(o.get("observed_at"))) is not None
    ]
    return max(dates) if dates else None


def decide(observations: list[dict], max_age_days: int, now: datetime) -> tuple[bool, str]:
    last = latest_success(observations)
    if last is None:
        return True, "aucun relevé réussi dans l'historique"
    age = now - last
    if age > timedelta(days=max_age_days):
        return True, (
            f"dernier relevé réussi il y a {age.days} j "
            f"({last.date().isoformat()}) — au-delà du seuil de {max_age_days} j"
        )
    return False, (
        f"dernier relevé réussi il y a {age.days} j "
        f"({last.date().isoformat()}) — rien à rattraper"
    )


def read_observations(path: Path) -> list[dict]:
    """Lecture tolérante : une ligne illisible ne doit pas bloquer la décision."""
    if not path.exists():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            print(f"WARN: ligne JSONL ignorée dans {path}", file=sys.stderr)
    return rows


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Rattrapage de collecte nécessaire ?")
    parser.add_argument(
        "--max-age-days",
        type=int,
        default=6,
        help="Âge maximal toléré du dernier relevé réussi (défaut : 6 jours).",
    )
    args = parser.parse_args(argv)

    observations = read_observations(Path(get_data_dir()) / "observations.jsonl")
    needed, reason = decide(observations, args.max_age_days, datetime.now(timezone.utc))

    print(f"{'Rattrapage nécessaire' if needed else 'Pas de rattrapage'} : {reason}")
    output = os.environ.get("GITHUB_OUTPUT")
    if output:
        with open(output, "a", encoding="utf-8") as f:
            f.write(f"needed={'true' if needed else 'false'}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
