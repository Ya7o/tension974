"""tension974 — Dashboard Streamlit."""
import sys
from pathlib import Path
from datetime import datetime, timezone, timedelta

import streamlit as st
import pandas as pd
import plotly.graph_objects as go

sys.path.insert(0, str(Path(__file__).parent))

from tension974.settings import get_database_path, get_searches_config_path, get_firecrawl_api_key
from tension974.database import init_db, get_observations, get_last_observation, get_recent_errors
from tension974.collector import load_searches, run_collection
from tension974.providers.firecrawl_provider import FirecrawlProvider
from tension974.providers.simple_http_provider import SimpleHttpProvider

st.set_page_config(page_title="tension974", page_icon="🏠", layout="wide")

st.markdown("""
<style>
  /* ── Masquer la barre Streamlit ── */
  [data-testid="stHeader"]          { display: none !important; }
  [data-testid="stToolbar"]         { display: none !important; }
  #MainMenu                         { display: none !important; }
  footer                            { display: none !important; }

  /* ── Compacité générale ── */
  .block-container { padding-top: 0.6rem !important; padding-bottom: 0.4rem; }
  [data-testid="stMetricValue"]  { font-size: 2.4rem !important; font-weight: 800; }
  [data-testid="stMetricLabel"]  { font-size: 0.75rem !important; color: #888; }
  [data-testid="stMetricDelta"]  { font-size: 0.9rem !important; }
  .stRadio > div { gap: 0.6rem; }
  [data-testid="stRadio"] label { font-size: 0.85rem; }
  hr { margin: 0.4rem 0 !important; }
  .section-title { font-size: 0.8rem; font-weight: 700; color: #777;
                   text-transform: uppercase; letter-spacing: .05em;
                   margin-bottom: 2px; }

  /* ── Logo + titre ── */
  .t974-header {
    display: flex; align-items: center; gap: 12px;
    padding: 0.2rem 0 0.1rem 0;
  }
  .t974-header h1 {
    margin: 0 !important; padding: 0;
    font-size: 1.7rem !important; font-weight: 800;
    line-height: 1.1; color: #1a1a2e;
  }
  .t974-header p {
    margin: 2px 0 0 0; font-size: 0.8rem; color: #888;
  }
</style>
""", unsafe_allow_html=True)

# ── Logo SVG inline ───────────────────────────────────────────────────────────
LOGO_SVG = """
<svg width="46" height="46" viewBox="0 0 46 46" fill="none" xmlns="http://www.w3.org/2000/svg">
  <!-- Maison -->
  <path d="M23 4 L42 20 L42 42 L4 42 L4 20 Z" fill="#1f77b4" opacity="0.12"/>
  <path d="M23 4 L42 20 L42 42 L4 42 L4 20 Z" stroke="#1f77b4" stroke-width="2.2" stroke-linejoin="round"/>
  <!-- Toit : ligne centrale -->
  <line x1="23" y1="4" x2="23" y2="4" stroke="#1f77b4" stroke-width="2"/>
  <!-- Courbe tendance (baisse puis remontée) -->
  <polyline points="9,36 16,30 22,32 30,24 37,17"
            stroke="#e05252" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" fill="none"/>
  <circle cx="37" cy="17" r="2.5" fill="#e05252"/>
</svg>
"""


# ── Helpers ───────────────────────────────────────────────────────────────────
def _run_and_display(config_path, db_path, provider):
    try:
        results = run_collection(config_path, db_path, provider)
        for obs in results:
            if obs.status == "success":
                cr = f" — {obs.credits_used} cr." if obs.credits_used else " — 0 cr."
                st.success(f"**{obs.search_id}** : {obs.total_listings_count} annonces{cr}")
            else:
                st.error(f"**{obs.search_id}** : {obs.error_message}")
        st.rerun()
    except Exception as exc:
        st.error(f"Erreur : {exc}")


def _variation(observations: list[dict], days: int) -> tuple[int | None, str]:
    success = [o for o in observations
               if o["status"] == "success" and o["total_listings_count"] is not None]
    if len(success) < 2:
        return None, "—"
    success.sort(key=lambda o: o["observed_at"])
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    old = [o for o in success if o["observed_at"] <= cutoff]
    if not old:
        return None, "—"
    delta = success[-1]["total_listings_count"] - old[-1]["total_listings_count"]
    return delta, (f"+{delta}" if delta >= 0 else str(delta))


def _sparkline(observations: list[dict]) -> go.Figure:
    pts = sorted(
        [o for o in observations if o["status"] == "success" and o["total_listings_count"] is not None],
        key=lambda o: o["observed_at"],
    )
    xs = [o["observed_at"][:10] for o in pts]
    ys = [o["total_listings_count"] for o in pts]
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=xs, y=ys, mode="lines+markers",
        line=dict(color="#1f77b4", width=2),
        marker=dict(size=3),
        hovertemplate="%{x}<br><b>%{y} annonces</b><extra></extra>",
    ))
    fig.update_layout(
        height=155, margin=dict(l=2, r=2, t=6, b=2),
        xaxis=dict(showgrid=False, tickfont=dict(size=8), nticks=5),
        yaxis=dict(showgrid=True, gridcolor="#f0f0f0", tickfont=dict(size=8)),
        plot_bgcolor="white", paper_bgcolor="white",
    )
    return fig


def _history_table(observations: list[dict]) -> pd.DataFrame:
    rows = [o for o in observations if o["status"] == "success"]
    rows.sort(key=lambda o: o["observed_at"], reverse=True)
    df = pd.DataFrame(rows)[["observed_at", "total_listings_count", "provider"]].copy()
    df["observed_at"] = df["observed_at"].str[:10]
    df = df.rename(columns={
        "observed_at": "Date",
        "total_listings_count": "Annonces",
        "provider": "Source",
    })
    return df


# ── Init ──────────────────────────────────────────────────────────────────────
db_path = get_database_path()
config_path = get_searches_config_path()
api_key = get_firecrawl_api_key()

try:
    init_db(db_path)
    searches = load_searches(config_path)
    active = [s for s in searches if s.active]
except Exception as e:
    st.error(f"Erreur de configuration : {e}")
    st.stop()

# ── Charger données ───────────────────────────────────────────────────────────
all_obs   = {s.id: get_observations(db_path, s.id, limit=200) for s in active}
all_last  = {s.id: get_last_observation(db_path, s.id)        for s in active}
all_errs  = {s.id: get_recent_errors(db_path, s.id, limit=2)  for s in active}

# ── HEADER — ligne 1 : logo + titre ──────────────────────────────────────────
st.markdown(f"""
<div class="t974-header">
  {LOGO_SVG}
  <div>
    <h1>tension974</h1>
    <p>Saint-Denis, La Réunion — suivi de la tension locative</p>
  </div>
</div>
""", unsafe_allow_html=True)

# ── HEADER — ligne 2 : radio | boutons | crédits ─────────────────────────────
c_mode, c_b1, c_b2, c_credits = st.columns([3, 1.3, 1.3, 3])

with c_mode:
    mode = st.radio(
        "Mode de collecte",
        options=["Direct (0 crédit)", "Firecrawl"],
        horizontal=True,
    )

use_firecrawl = mode == "Firecrawl"

with c_b1:
    collect_clicked = st.button("⟳  Collecter", type="primary", use_container_width=True)

with c_b2:
    test_clicked = st.button("🔑  Tester clé API", use_container_width=True,
                             disabled=not use_firecrawl)

with c_credits:
    if api_key:
        try:
            fc_data = FirecrawlProvider(api_key=api_key).get_account_credits()
            if "error" not in fc_data:
                rem  = fc_data.get("remaining_credits", "—")
                plan = fc_data.get("plan_credits", "—")
                st.caption(f"Crédits Firecrawl : **{rem}** / {plan}")
        except Exception:
            pass

# ── Actions ───────────────────────────────────────────────────────────────────
if collect_clicked:
    provider = FirecrawlProvider(api_key=api_key) if use_firecrawl else SimpleHttpProvider()
    if use_firecrawl and not api_key:
        st.error("FIRECRAWL_API_KEY manquante dans .env")
    else:
        label = "Firecrawl…" if use_firecrawl else "directe (0 crédit)…"
        with st.spinner(f"Collecte {label}"):
            _run_and_display(config_path, db_path, provider)

if test_clicked:
    if not api_key:
        st.error("FIRECRAWL_API_KEY manquante dans .env")
    else:
        with st.spinner("Test de la clé…"):
            ok, msg = FirecrawlProvider(api_key=api_key).test_api_key()
            (st.success if ok else st.error)(msg)

st.divider()

# ══════════════════════════════════════════════════════════════════════════════
# ÉCRAN 1 — 3 blocs KPI + sparkline (above the fold)
# ══════════════════════════════════════════════════════════════════════════════
if not active:
    st.warning("Aucune recherche active.")
    st.stop()

kpi_cols = st.columns(3)

for col, search in zip(kpi_cols, active):
    obs   = all_obs[search.id]
    last  = all_last[search.id]
    errs  = all_errs[search.id]

    with col:
        st.markdown(f'<div class="section-title">{search.name}</div>', unsafe_allow_html=True)

        last_count = last["total_listings_count"] if last else None
        last_date  = last["observed_at"][:10] if last else "—"

        _, var7  = _variation(obs, 7)
        delta30, var30 = _variation(obs, 30)

        st.metric(
            label=f"Relevé du {last_date}",
            value=last_count if last_count is not None else "—",
            delta=var7 if var7 != "—" else None,
        )

        c1, c2 = st.columns(2)
        c1.caption(f"7 jours : **{var7}**")
        c2.caption(f"30 jours : **{var30}**")

        if obs:
            st.plotly_chart(_sparkline(obs), use_container_width=True,
                            config={"displayModeBar": False}, key=f"spark_{search.id}")

        for err in errs:
            st.caption(f"⚠ {err['observed_at'][:10]} — {err['error_message'][:55]}")

# ══════════════════════════════════════════════════════════════════════════════
# ÉCRAN 2 — Tableaux historiques (scroll)
# ══════════════════════════════════════════════════════════════════════════════
st.divider()
st.markdown('<div class="section-title">Historique complet des relevés</div>', unsafe_allow_html=True)

hist_cols = st.columns(3)

for col, search in zip(hist_cols, active):
    with col:
        st.caption(f"**{search.name}**")
        obs = all_obs[search.id]
        if obs:
            df = _history_table(obs)
            st.dataframe(df, use_container_width=True, hide_index=True, height=320)
        else:
            st.info("Aucune donnée")

st.caption(f"Mis à jour : {datetime.now(timezone.utc).strftime('%d/%m/%Y %H:%M')} UTC")
