"""tension974 - Dashboard Streamlit."""
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

sys.path.insert(0, str(Path(__file__).parent))

from tension974.collector import load_searches
from tension974.database import get_observations, init_db
from tension974.settings import get_database_path, get_searches_config_path

st.set_page_config(page_title="tension974", page_icon="🏠", layout="wide")

st.markdown("""
<style>
  [data-testid="stHeader"] { display: none !important; }
  [data-testid="stToolbar"] { display: none !important; }
  #MainMenu { display: none !important; }
  footer { display: none !important; }
  .block-container { padding-top: 0.6rem !important; padding-bottom: 0.4rem; }
  [data-testid="stMetricValue"] { font-size: 2.4rem !important; font-weight: 800; }
  [data-testid="stMetricLabel"] { font-size: 0.75rem !important; color: #888; }
  [data-testid="stMetricDelta"] { font-size: 0.9rem !important; }
  hr { margin: 0.4rem 0 !important; }
  .section-title {
    font-size: 0.8rem; font-weight: 700; color: #777;
    text-transform: uppercase; letter-spacing: .05em; margin-bottom: 2px;
  }
  .t974-header { display: flex; align-items: center; gap: 12px; padding: 0.2rem 0 0.1rem 0; }
  .t974-header h1 {
    margin: 0 !important; padding: 0; font-size: 1.7rem !important;
    font-weight: 800; line-height: 1.1; color: #1a1a2e;
  }
  .t974-header p { margin: 2px 0 0 0; font-size: 0.8rem; color: #888; }
</style>
""", unsafe_allow_html=True)

LOGO_SVG = """
<svg width="46" height="46" viewBox="0 0 46 46" fill="none" xmlns="http://www.w3.org/2000/svg">
  <path d="M23 4 L42 20 L42 42 L4 42 L4 20 Z" fill="#1f77b4" opacity="0.12"/>
  <path d="M23 4 L42 20 L42 42 L4 42 L4 20 Z" stroke="#1f77b4" stroke-width="2.2" stroke-linejoin="round"/>
  <polyline points="9,36 16,30 22,32 30,24 37,17"
            stroke="#e05252" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" fill="none"/>
  <circle cx="37" cy="17" r="2.5" fill="#e05252"/>
</svg>
"""


def _get_secret(name: str) -> str | dict[str, Any] | None:
    value = os.environ.get(name)
    if value:
        return value
    try:
        value = st.secrets.get(name)
    except Exception:
        return None
    return value or None


def _storage_mode() -> str:
    configured = _get_secret("TENSION974_STORAGE")
    if configured:
        return str(configured).strip().lower()
    if _has_google_credentials() and _get_secret("GOOGLE_SHEET_ID"):
        return "google_sheets"
    if Path.cwd().as_posix().startswith("/mount/src/"):
        return "google_sheets"
    return "sqlite"


@st.cache_resource(show_spinner=False)
def _google_sheet(service_account_json: str, sheet_id: str):
    import gspread

    credentials = json.loads(service_account_json)
    client = gspread.service_account_from_dict(credentials)
    return client.open_by_key(sheet_id)


def _has_google_credentials() -> bool:
    if _get_secret("GOOGLE_SERVICE_ACCOUNT_JSON"):
        return True
    try:
        return bool(st.secrets.get("google_service_account"))
    except Exception:
        return False


def _google_credentials_json() -> str:
    raw_json = _get_secret("GOOGLE_SERVICE_ACCOUNT_JSON")
    if raw_json:
        if not isinstance(raw_json, str):
            return json.dumps(dict(raw_json), sort_keys=True)
        try:
            return json.dumps(json.loads(raw_json), sort_keys=True)
        except json.JSONDecodeError as exc:
            raise RuntimeError(
                "GOOGLE_SERVICE_ACCOUNT_JSON n'est pas un JSON valide. "
                "Utilise plutot le format [google_service_account] dans les secrets Streamlit."
            ) from exc

    try:
        credentials = st.secrets.get("google_service_account")
    except Exception:
        credentials = None
    if not credentials:
        raise RuntimeError("GOOGLE_SERVICE_ACCOUNT_JSON ou [google_service_account] est absent.")
    return json.dumps(dict(credentials), sort_keys=True)


def _read_google_worksheet(name: str) -> pd.DataFrame:
    sheet_id = _get_secret("GOOGLE_SHEET_ID")

    if not sheet_id:
        raise RuntimeError("GOOGLE_SHEET_ID est absent.")

    sheet = _google_sheet(_google_credentials_json(), str(sheet_id))
    try:
        worksheet = _find_worksheet(sheet, name)
        return _worksheet_to_dataframe(worksheet)
    except Exception as exc:
        available = ", ".join(w.title for w in sheet.worksheets()) or "aucun"
        raise RuntimeError(
            f"Onglet Google Sheets illisible: {name}. "
            f"Onglets disponibles: {available}. Detail: {exc}"
        ) from exc


def _worksheet_to_dataframe(worksheet) -> pd.DataFrame:
    values = worksheet.get_all_values()
    if not values:
        return pd.DataFrame()

    headers = _dedupe_headers(values[0])
    rows = values[1:]
    return pd.DataFrame(rows, columns=headers)


def _dedupe_headers(headers: list[str]) -> list[str]:
    seen: dict[str, int] = {}
    result = []
    for index, header in enumerate(headers):
        name = header.strip() or f"column_{index + 1}"
        count = seen.get(name, 0)
        seen[name] = count + 1
        result.append(name if count == 0 else f"{name}_{count + 1}")
    return result


def _find_worksheet(sheet, name: str):
    try:
        return sheet.worksheet(name)
    except Exception:
        pass

    wanted = name.strip().lower()
    for worksheet in sheet.worksheets():
        if worksheet.title.strip().lower() == wanted:
            return worksheet

    if name == "observations":
        for worksheet in sheet.worksheets():
            headers = [h.strip().lower() for h in worksheet.row_values(1)]
            if {"search_id", "observed_at"}.issubset(set(headers)):
                return worksheet

    raise RuntimeError(name)


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    text = str(value).strip().lower()
    return text in {"1", "true", "yes", "y", "success", "ok"}


def _normalize_observations(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    if "collected_at" not in df.columns:
        if "observed_at" in df.columns:
            df["collected_at"] = df["observed_at"]
        elif "created_at" in df.columns:
            df["collected_at"] = df["created_at"]
    if "count" not in df.columns and "total_listings_count" in df.columns:
        df["count"] = df["total_listings_count"]
    if "success" not in df.columns and "status" in df.columns:
        df["success"] = df["status"]
    if "raw_text" not in df.columns and "raw_total_listings_text" in df.columns:
        df["raw_text"] = df["raw_total_listings_text"]
    if "error" not in df.columns and "error_message" in df.columns:
        df["error"] = df["error_message"]

    if "collected_at" not in df.columns:
        df["collected_at"] = pd.NaT
    if "date" not in df.columns:
        df["date"] = df["collected_at"]
    if "count" not in df.columns:
        df["count"] = pd.NA
    for column in ("average_price", "price_sample_size", "min_price", "max_price"):
        if column not in df.columns:
            df[column] = pd.NA
    if "success" not in df.columns:
        df["success"] = True
    if "provider" not in df.columns:
        df["provider"] = ""
    if "search_id" not in df.columns:
        df["search_id"] = ""
    if "error" not in df.columns:
        df["error"] = ""

    df["collected_at"] = pd.to_datetime(df["collected_at"], errors="coerce", utc=True)
    df["date"] = pd.to_datetime(df["date"], errors="coerce").dt.date
    df["count"] = pd.to_numeric(df["count"], errors="coerce").astype("Int64")
    for column in ("average_price", "price_sample_size", "min_price", "max_price"):
        df[column] = pd.to_numeric(df[column], errors="coerce").astype("Int64")
    df["success"] = df["success"].map(_as_bool)
    return df.sort_values("collected_at", ascending=False)


def read_observations(storage: str) -> pd.DataFrame:
    if storage == "google_sheets":
        return _normalize_observations(_read_google_worksheet("observations"))
    if storage == "sqlite":
        db_path = get_database_path()
        init_db(db_path)
        searches = [s for s in load_searches(get_searches_config_path()) if s.active]
        rows = []
        for search in searches:
            rows.extend(get_observations(db_path, search.id, limit=500))
        return _normalize_observations(pd.DataFrame(rows))
    raise RuntimeError(f"Stockage non supporte: {storage}")


def read_runs(storage: str) -> pd.DataFrame:
    if storage == "google_sheets":
        df = _read_google_worksheet("runs")
    elif storage == "sqlite":
        return pd.DataFrame()
    else:
        raise RuntimeError(f"Stockage non supporte: {storage}")

    if df.empty:
        return df
    for column in ("started_at", "finished_at"):
        if column in df.columns:
            df[column] = pd.to_datetime(df[column], errors="coerce", utc=True)
    return df.sort_values("started_at", ascending=False) if "started_at" in df.columns else df


def _variation(observations: pd.DataFrame, days: int) -> tuple[int | None, str]:
    success = observations[observations["success"] & observations["count"].notna()].sort_values("collected_at")
    if len(success) < 2:
        return None, "-"
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    old = success[success["collected_at"] <= cutoff]
    if old.empty:
        return None, "-"
    delta = int(success.iloc[-1]["count"]) - int(old.iloc[-1]["count"])
    return delta, f"+{delta}" if delta >= 0 else str(delta)


def _price_variation(observations: pd.DataFrame, days: int) -> str:
    success = observations[
        observations["success"] & observations["average_price"].notna()
    ].sort_values("collected_at")
    if len(success) < 2:
        return "-"
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    old = success[success["collected_at"] <= cutoff]
    if old.empty:
        return "-"
    delta = int(success.iloc[-1]["average_price"]) - int(old.iloc[-1]["average_price"])
    return f"+{delta} EUR" if delta >= 0 else f"{delta} EUR"


def _sparkline(observations: pd.DataFrame, column: str = "count", color: str = "#1f77b4") -> go.Figure:
    pts = observations[observations["success"] & observations[column].notna()].sort_values("collected_at")
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=pts["date"],
        y=pts[column],
        mode="lines+markers",
        line=dict(color=color, width=2),
        marker=dict(size=3),
        hovertemplate="%{x}<br><b>%{y}</b><extra></extra>",
    ))
    fig.update_layout(
        height=155,
        margin=dict(l=2, r=2, t=6, b=2),
        xaxis=dict(showgrid=False, tickfont=dict(size=8), nticks=5),
        yaxis=dict(showgrid=True, gridcolor="#f0f0f0", tickfont=dict(size=8)),
        plot_bgcolor="white",
        paper_bgcolor="white",
    )
    return fig


def _history_table(observations: pd.DataFrame) -> pd.DataFrame:
    rows = observations[observations["success"]].sort_values("collected_at", ascending=False)
    df = rows[["date", "count", "average_price", "price_sample_size", "provider"]].copy()
    return df.rename(columns={
        "date": "Date",
        "count": "Annonces",
        "average_price": "Prix moyen",
        "price_sample_size": "Prix lus",
        "provider": "Source",
    })


try:
    searches = [s for s in load_searches(get_searches_config_path()) if s.active]
except Exception as exc:
    st.error(f"Erreur de configuration des recherches : {exc}")
    st.stop()

storage = _storage_mode()
try:
    observations = read_observations(storage)
    runs = read_runs(storage)
except Exception as exc:
    st.error(f"Impossible de lire les donnees {storage}: {exc}")
    st.info("Verifie TENSION974_STORAGE, GOOGLE_SERVICE_ACCOUNT_JSON et GOOGLE_SHEET_ID.")
    st.stop()

latest = observations["collected_at"].max() if not observations.empty else pd.NaT
source_label = "Google Sheets" if storage == "google_sheets" else "SQLite"

with st.sidebar:
    st.subheader("Donnees")
    st.caption(f"Source : **{source_label}**")
    st.caption(f"Releves : **{len(observations)}**")
    if pd.notna(latest):
        st.caption(f"Dernier releve : **{latest.strftime('%d/%m/%Y %H:%M UTC')}**")
    else:
        st.caption("Dernier releve : **aucun**")

    if not runs.empty:
        st.divider()
        st.subheader("Runs")
        last_run = runs.iloc[0]
        st.caption(f"Statut : **{last_run.get('status', '-')}**")
        finished = last_run.get("finished_at")
        if pd.notna(finished):
            st.caption(f"Fin : **{finished.strftime('%d/%m/%Y %H:%M UTC')}**")
        if last_run.get("error_message"):
            st.caption(f"Erreur : {last_run.get('error_message')}")

st.markdown(f"""
<div class="t974-header">
  {LOGO_SVG}
  <div>
    <h1>tension974</h1>
    <p>Saint-Denis, La Reunion - suivi de la tension locative</p>
  </div>
</div>
""", unsafe_allow_html=True)

st.caption(f"Source de donnees : {source_label} - {len(observations)} releve(s)")

if not searches:
    st.warning("Aucune recherche active.")
    st.stop()

if observations.empty:
    st.info(
        "Aucun releve disponible pour le moment. "
        f"Source actuellement utilisee : {source_label}."
    )
    st.stop()

success_observations = observations[observations["success"]]
if success_observations.empty:
    st.info("Aucun releve reussi disponible pour alimenter les graphiques.")
    st.stop()

st.divider()

kpi_cols = st.columns(3)
for col, search in zip(kpi_cols, searches):
    obs = observations[observations["search_id"] == search.id]
    success = obs[obs["success"] & obs["count"].notna()].sort_values("collected_at", ascending=False)
    price_success = obs[
        obs["success"] & obs["average_price"].notna()
    ].sort_values("collected_at", ascending=False)

    with col:
        st.markdown(f'<div class="section-title">{search.name}</div>', unsafe_allow_html=True)
        last = success.iloc[0] if not success.empty else None
        last_count = int(last["count"]) if last is not None else None
        last_date = last["date"].strftime("%Y-%m-%d") if last is not None and pd.notna(last["date"]) else "-"
        last_price = int(price_success.iloc[0]["average_price"]) if not price_success.empty else None
        price_sample = int(price_success.iloc[0]["price_sample_size"]) if (
            not price_success.empty and pd.notna(price_success.iloc[0]["price_sample_size"])
        ) else None
        _, var7 = _variation(obs, 7)
        _, var30 = _variation(obs, 30)
        price_var30 = _price_variation(obs, 30)

        st.metric(
            label=f"Releve du {last_date}",
            value=last_count if last_count is not None else "-",
            delta=var7 if var7 != "-" else None,
        )

        c1, c2 = st.columns(2)
        c1.caption(f"7 jours : **{var7}**")
        c2.caption(f"30 jours : **{var30}**")
        if last_price is not None:
            sample_label = f" ({price_sample} prix)" if price_sample else ""
            st.caption(f"Prix moyen : **{last_price} EUR**{sample_label} | 30 jours : **{price_var30}**")

        if not success.empty:
            st.plotly_chart(
                _sparkline(obs),
                use_container_width=True,
                config={"displayModeBar": False},
                key=f"spark_{search.id}",
            )
            if not price_success.empty:
                st.plotly_chart(
                    _sparkline(obs, column="average_price", color="#e05252"),
                    use_container_width=True,
                    config={"displayModeBar": False},
                    key=f"price_{search.id}",
                )
        else:
            st.info("Aucune donnee reussie")

        errors = obs[~obs["success"]].head(2)
        for _, err in errors.iterrows():
            date = err["collected_at"].strftime("%Y-%m-%d") if pd.notna(err["collected_at"]) else "-"
            st.caption(f"! {date} - {str(err.get('error', 'Erreur'))[:55]}")

st.divider()
st.markdown('<div class="section-title">Historique complet des releves</div>', unsafe_allow_html=True)

hist_cols = st.columns(3)
for col, search in zip(hist_cols, searches):
    with col:
        st.caption(f"**{search.name}**")
        obs = observations[observations["search_id"] == search.id]
        if not obs[obs["success"]].empty:
            st.dataframe(_history_table(obs), use_container_width=True, hide_index=True, height=320)
        else:
            st.info("Aucune donnee")

if not runs.empty:
    st.divider()
    st.markdown('<div class="section-title">Dernieres collectes</div>', unsafe_allow_html=True)
    visible = [c for c in ["started_at", "finished_at", "status", "provider", "error_message"] if c in runs.columns]
    st.dataframe(runs[visible].head(10), use_container_width=True, hide_index=True)

st.caption(f"Mis a jour : {datetime.now(timezone.utc).strftime('%d/%m/%Y %H:%M')} UTC")
