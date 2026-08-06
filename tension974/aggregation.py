"""Pure aggregation logic turning raw observations/runs into dashboard data.

Kept separate from file I/O (see scripts/build_site_data.py) so the
aggregation rules themselves are easy to unit test.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from statistics import mean
from typing import Any

from .diagnostics.classify import CATEGORY_NONE, CATEGORY_UNKNOWN, categorize_error

_STALE_AFTER_DAYS = 10


def parse_iso(value: str | None) -> datetime | None:
    if not value or not isinstance(value, str):
        return None
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    # Un horodatage sans fuseau (possible via l'ancienne migration Sheets ou
    # une édition manuelle) est réputé UTC : mélanger naïf et aware ferait
    # planter les tris et soustractions de tout le pipeline de publication.
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def merge_runs(run_events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Pair start/finish JSONL events sharing a run_id into one record each."""
    merged: dict[str, dict[str, Any]] = {}
    order: list[str] = []
    for event in run_events:
        run_id = event.get("run_id")
        if not run_id:
            continue
        if run_id not in merged:
            merged[run_id] = {"run_id": run_id}
            order.append(run_id)
        for key, value in event.items():
            if value is not None:
                merged[run_id][key] = value

    results = []
    for run_id in order:
        run = merged[run_id]
        started = parse_iso(run.get("started_at"))
        if started is None:
            # Sans horodatage de départ exploitable, le run est implaçable sur
            # la frise et fausserait les taux de santé — on l'écarte plutôt
            # que de le publier (colonnes décalées de l'ancienne migration
            # Google Sheets, par exemple).
            continue

        status = run.get("status", "unknown")
        if status == "running":
            category = "running"
        elif status == "success":
            category = CATEGORY_NONE
        elif status in ("partial", "failed"):
            category = categorize_error(run.get("error_message"))
            if category == CATEGORY_NONE:
                # Un run partial/failed sans message d'erreur ne doit jamais
                # s'afficher « Succès » en vert : categorize_error(None) vaut
                # none, on retombe sur unknown.
                category = CATEGORY_UNKNOWN
        else:
            category = CATEGORY_UNKNOWN
        run["category"] = category

        finished = parse_iso(run.get("finished_at"))
        run["duration_seconds"] = (
            round((finished - started).total_seconds()) if started and finished else None
        )
        results.append(run)

    # Tri chronologique réel : le tri lexicographique faisait remonter les
    # started_at non ISO en tête du JSON publié.
    results.sort(key=lambda r: parse_iso(r["started_at"]), reverse=True)
    return results


def build_search_timeseries(observations: list[dict[str, Any]], search_id: str) -> list[dict[str, Any]]:
    rows = [o for o in observations if o.get("search_id") == search_id]
    rows.sort(key=lambda o: o.get("observed_at") or "")

    series = []
    for row in rows:
        observed_at = row.get("observed_at")
        dt = parse_iso(observed_at)
        success = row.get("status") == "success"
        series.append({
            "observed_at": observed_at,
            "date": dt.date().isoformat() if dt else None,
            "success": success,
            "count": row.get("total_listings_count"),
            "median_price": row.get("median_price"),
            "average_price": row.get("average_price"),
            "price_sample_size": row.get("price_sample_size"),
            "provider": row.get("provider"),
            "error_category": CATEGORY_NONE if success else categorize_error(row.get("error_message")),
            "error_message": row.get("error_message"),
        })
    return series


def _value_delta(series: list[dict[str, Any]], field: str, days: int, now: datetime) -> dict[str, Any] | None:
    successful = [p for p in series if p["success"] and p.get(field) is not None]
    if len(successful) < 2:
        return None
    latest = successful[-1]
    latest_dt = parse_iso(latest["observed_at"])
    if latest_dt is None:
        return None
    # Fenêtre ancrée sur le DERNIER RELEVÉ, jamais sur l'heure de build : un
    # KPI qui change selon la minute de régénération n'est pas un KPI. Le point
    # de référence ne peut pas être le dernier relevé lui-même (l'ancien code
    # le comparait à lui-même → faux « 0 % »), doit être au moins `days` plus
    # vieux que lui, et pas plus de 2× la fenêtre — au-delà d'un trou de
    # collecte, on n'affiche rien plutôt qu'un delta trompeur.
    cutoff = latest_dt - timedelta(days=days)
    max_age = latest_dt - timedelta(days=days * 2)
    older = []
    for p in successful[:-1]:
        dt = parse_iso(p["observed_at"])
        if dt and max_age <= dt <= cutoff:
            older.append(p)
    if not older:
        return None
    old_value = older[-1][field]
    return {"delta": latest[field] - old_value, "from": old_value, "to": latest[field]}


def compute_kpis(series: list[dict[str, Any]], now: datetime | None = None) -> dict[str, Any]:
    now = now or datetime.now(timezone.utc)
    successful = [p for p in series if p["success"] and p.get("count") is not None]
    price_points = [p for p in series if p["success"] and p.get("median_price") is not None]
    recent_30d = [
        p for p in series
        if parse_iso(p["observed_at"]) and parse_iso(p["observed_at"]) >= now - timedelta(days=30)
    ]

    latest = successful[-1] if successful else None
    latest_price = price_points[-1] if price_points else None
    last_failure = next((p for p in reversed(series) if not p["success"]), None)

    success_rate_30d = (
        round(sum(1 for p in recent_30d if p["success"]) / len(recent_30d), 3) if recent_30d else None
    )

    return {
        "latest_count": latest["count"] if latest else None,
        "latest_date": latest["date"] if latest else None,
        "delta_7d": _value_delta(series, "count", 7, now),
        "delta_30d": _value_delta(series, "count", 30, now),
        "latest_median_price": latest_price["median_price"] if latest_price else None,
        "latest_average_price": latest_price["average_price"] if latest_price else None,
        "price_sample_size": latest_price["price_sample_size"] if latest_price else None,
        "price_delta_30d": _value_delta(series, "median_price", 30, now),
        "success_rate_30d": success_rate_30d,
        "last_failure": (
            {
                "date": last_failure["date"],
                "category": last_failure["error_category"],
                "message": last_failure["error_message"],
            }
            if last_failure else None
        ),
    }


def compute_health(merged_runs: list[dict[str, Any]], now: datetime | None = None) -> dict[str, Any]:
    now = now or datetime.now(timezone.utc)

    def _within(days: int) -> list[dict[str, Any]]:
        cutoff = now - timedelta(days=days)
        return [r for r in merged_runs if parse_iso(r.get("started_at")) and parse_iso(r.get("started_at")) >= cutoff]

    def _rate(runs: list[dict[str, Any]]) -> float | None:
        finished = [r for r in runs if r.get("status") in ("success", "partial", "failed")]
        if not finished:
            return None
        return round(sum(1 for r in finished if r["status"] == "success") / len(finished), 3)

    runs_30d = _within(30)
    category_counts: dict[str, int] = {}
    for run in runs_30d:
        category_counts[run["category"]] = category_counts.get(run["category"], 0) + 1

    finished_statuses = ("success", "partial", "failed")
    last_success = next((r for r in merged_runs if r.get("status") == "success"), None)
    last_finished = next((r for r in merged_runs if r.get("status") in finished_statuses), None)
    # La fraîcheur se mesure au dernier run qui a réellement produit des
    # relevés : un run partiel a quand même rafraîchi la plupart des typologies.
    last_productive = next((r for r in merged_runs if r.get("status") in ("success", "partial")), None)
    last_productive_at = parse_iso(last_productive["started_at"]) if last_productive else None
    stale_days = (now - last_productive_at).days if last_productive_at else None

    return {
        "success_rate_7d": _rate(_within(7)),
        "success_rate_30d": _rate(runs_30d),
        "category_counts_30d": category_counts,
        "last_success_at": last_success["started_at"] if last_success else None,
        "last_finished_status": last_finished["status"] if last_finished else None,
        "last_productive_at": last_productive["started_at"] if last_productive else None,
        # stale_days/is_stale sont figés à la date de génération : ils servent
        # aux consommateurs du JSON. Le dashboard, lui, recalcule la fraîcheur
        # à l'affichage depuis last_productive_at — sinon un pipeline mort
        # afficherait « à jour » pour toujours.
        "stale_days": stale_days,
        "is_stale": stale_days is None or stale_days >= _STALE_AFTER_DAYS,
        "stale_after_days": _STALE_AFTER_DAYS,
        "total_runs": len(merged_runs),
    }
