/* tension974 dashboard — wires data/dashboard.json to the chart components
 * defined in charts.js. Plain JS, no build step, no framework.
 */
"use strict";

const SERIES_COLORS = ["var(--series-1)", "var(--series-2)", "var(--series-3)"];
let currentRangeDays = null; // null = all time
let currentPriceMetric = "median_price";
let DASHBOARD = null;

function deltaBadge(delta, goodDirection) {
  // goodDirection: "up" means an increase is good (fewer people competing
  // for listings), "down" means an increase is bad (rising rents).
  if (!delta) return { text: "Données insuffisantes", cls: "flat" };
  const value = delta.delta;
  const sign = value > 0 ? "+" : "";
  const isGood = goodDirection === "up" ? value >= 0 : value <= 0;
  const cls = value === 0 ? "flat" : (isGood ? "good" : "bad");
  return { text: `${sign}${formatCompact(value)}`, cls };
}

function buildKpiCard(search, index) {
  const card = document.createElement("div");
  card.className = "card";
  const kpis = search.kpis;
  const color = SERIES_COLORS[index % SERIES_COLORS.length];

  const label = document.createElement("div");
  label.className = "kpi-label";
  label.style.color = color;
  label.textContent = search.name;
  card.appendChild(label);

  const sub = document.createElement("div");
  sub.className = "kpi-sub";
  sub.textContent = kpis.latest_date ? `Relevé du ${formatDateFull(kpis.latest_date)}` : "Aucun relevé";
  card.appendChild(sub);

  const value = document.createElement("div");
  value.className = "kpi-value";
  value.textContent = kpis.latest_count !== null && kpis.latest_count !== undefined ? formatCompact(kpis.latest_count) : "—";
  card.appendChild(value);

  const d7 = deltaBadge(kpis.delta_7d, "up");
  const d30 = deltaBadge(kpis.delta_30d, "up");
  const deltaRow = document.createElement("div");
  deltaRow.style.display = "flex";
  deltaRow.style.gap = "14px";

  const d7el = document.createElement("span");
  d7el.className = `kpi-delta ${d7.cls}`;
  d7el.textContent = `7j : ${d7.text}`;
  const d30el = document.createElement("span");
  d30el.className = `kpi-delta ${d30.cls}`;
  d30el.textContent = `30j : ${d30.text}`;
  deltaRow.appendChild(d7el);
  deltaRow.appendChild(d30el);
  card.appendChild(deltaRow);

  if (kpis.latest_median_price !== null && kpis.latest_median_price !== undefined) {
    const priceBlock = document.createElement("div");
    priceBlock.className = "kpi-price";
    const priceDelta = deltaBadge(kpis.price_delta_30d, "down");
    const strongMedian = document.createElement("strong");
    strongMedian.textContent = `${formatCompact(kpis.latest_median_price)} €`;
    priceBlock.append("Prix médian : ", strongMedian);
    if (kpis.latest_average_price) {
      priceBlock.append(` (moyen ${formatCompact(kpis.latest_average_price)} €)`);
    }
    const priceDeltaEl = document.createElement("span");
    priceDeltaEl.className = `kpi-delta ${priceDelta.cls}`;
    priceDeltaEl.style.marginLeft = "8px";
    priceDeltaEl.textContent = `30j : ${priceDelta.text}`;
    priceBlock.appendChild(priceDeltaEl);
    card.appendChild(priceBlock);
  }

  if (kpis.last_failure) {
    const errBlock = document.createElement("div");
    errBlock.className = "kpi-error";
    errBlock.textContent = `⚠ Dernier échec (${kpis.last_failure.date}) : ${CATEGORY_LABEL_FR[kpis.last_failure.category] || kpis.last_failure.category}`;
    card.appendChild(errBlock);
  }

  return card;
}

function filterByRange(points, dateKey) {
  if (currentRangeDays === null) return points;
  const cutoff = Date.now() - currentRangeDays * 86400000;
  return points.filter((p) => new Date(p[dateKey]).getTime() >= cutoff);
}

function renderCountChart() {
  const series = DASHBOARD.searches.map((search, i) => ({
    id: search.id,
    label: search.name,
    shortLabel: search.property_type || search.name,
    color: SERIES_COLORS[i % SERIES_COLORS.length],
    points: filterByRange(search.timeseries, "observed_at")
      .map((p) => ({ x: p.observed_at, y: p.success ? p.count : null })),
  }));
  renderLineChart(document.getElementById("count-chart"), series, { formatValue: (v) => `${formatCompact(v)} annonces` });

  const rows = [];
  DASHBOARD.searches.forEach((search) => {
    filterByRange(search.timeseries, "observed_at").forEach((p) => {
      if (p.success) rows.push({ date: p.date, name: search.name, count: p.count, provider: p.provider });
    });
  });
  rows.sort((a, b) => (a.date < b.date ? 1 : -1));
  renderTable(document.getElementById("count-table"), [
    { label: "Date", key: "date" },
    { label: "Recherche", key: "name" },
    { label: "Annonces", key: "count" },
    { label: "Source", key: "provider" },
  ], rows);
}

function renderPriceChart() {
  const metric = currentPriceMetric;
  const series = DASHBOARD.searches.map((search, i) => ({
    id: search.id,
    label: search.name,
    shortLabel: search.property_type || search.name,
    color: SERIES_COLORS[i % SERIES_COLORS.length],
    points: filterByRange(search.timeseries, "observed_at")
      .map((p) => ({ x: p.observed_at, y: (p.success && p[metric] !== null && p[metric] !== undefined) ? p[metric] : null })),
  }));
  renderLineChart(document.getElementById("price-chart"), series, { formatValue: (v) => `${formatCompact(v)} €` });

  const rows = [];
  DASHBOARD.searches.forEach((search) => {
    filterByRange(search.timeseries, "observed_at").forEach((p) => {
      if (p.success && p[metric] !== null && p[metric] !== undefined) {
        rows.push({ date: p.date, name: search.name, price: p[metric], sample: p.price_sample_size });
      }
    });
  });
  rows.sort((a, b) => (a.date < b.date ? 1 : -1));
  renderTable(document.getElementById("price-table"), [
    { label: "Date", key: "date" },
    { label: "Recherche", key: "name" },
    { label: metric === "median_price" ? "Prix médian (€)" : "Prix moyen (€)", key: "price" },
    { label: "Échantillon", key: "sample" },
  ], rows);
}

function renderRuns() {
  const runs = filterByRange(DASHBOARD.runs, "started_at");
  renderRunStrip(document.getElementById("run-strip"), runs);

  renderTable(document.getElementById("run-table"), [
    { label: "Début", key: "started_at", format: (r) => formatDateTimeFull(r.started_at) },
    { label: "Statut", format: (r) => CATEGORY_LABEL_FR[r.category] || r.category },
    { label: "Provider", key: "provider", format: (r) => r.provider || "—" },
    { label: "Durée", format: (r) => (r.duration_seconds ? `${r.duration_seconds}s` : "—") },
    { label: "Erreur", format: (r) => r.error_message || "—" },
  ], runs);

  const legend = document.getElementById("category-legend");
  legend.innerHTML = "";
  const counts = DASHBOARD.health.category_counts_30d || {};
  Object.entries(counts).forEach(([category, count]) => {
    const item = document.createElement("span");
    item.className = "item";
    const swatch = document.createElement("span");
    swatch.className = "swatch";
    swatch.style.background = CATEGORY_COLOR[category] || CATEGORY_COLOR.unknown;
    item.appendChild(swatch);
    const text = document.createElement("span");
    text.textContent = `${CATEGORY_LABEL_FR[category] || category} : ${count}`;
    item.appendChild(text);
    legend.appendChild(item);
  });

  const health = DASHBOARD.health;
  const statsEl = document.getElementById("health-stats");
  statsEl.innerHTML = "";
  const stats = [
    ["Taux de succès 7j", health.success_rate_7d !== null ? `${Math.round(health.success_rate_7d * 100)}%` : "—"],
    ["Taux de succès 30j", health.success_rate_30d !== null ? `${Math.round(health.success_rate_30d * 100)}%` : "—"],
    ["Collectes enregistrées", health.total_runs],
    ["Dernier succès", health.last_success_at ? formatDateFull(health.last_success_at) : "—"],
  ];
  stats.forEach(([label, num]) => {
    const div = document.createElement("div");
    div.className = "health-stat";
    const numEl = document.createElement("div");
    numEl.className = "num";
    numEl.textContent = num;
    const labelEl = document.createElement("div");
    labelEl.className = "label";
    labelEl.textContent = label;
    div.appendChild(numEl);
    div.appendChild(labelEl);
    statsEl.appendChild(div);
  });
}

function renderAll() {
  renderCountChart();
  renderPriceChart();
  renderRuns();
}

function wireFilters() {
  document.querySelectorAll(".filter-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".filter-btn").forEach((b) => b.classList.remove("is-active"));
      btn.classList.add("is-active");
      const range = btn.dataset.range;
      currentRangeDays = range === "all" ? null : Number(range);
      renderAll();
    });
  });

  document.querySelectorAll(".price-toggle button").forEach((btn) => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".price-toggle button").forEach((b) => b.classList.remove("is-active"));
      btn.classList.add("is-active");
      currentPriceMetric = btn.dataset.priceMetric;
      renderPriceChart();
    });
  });

  document.querySelectorAll("[data-toggle]").forEach((btn) => {
    const key = btn.dataset.toggle;
    const chartMap = { count: "count-chart", price: "price-chart", runs: "run-strip" };
    const tableMap = { count: "count-table", price: "price-table", runs: "run-table" };
    wireTableToggle(btn, document.getElementById(chartMap[key]), document.getElementById(tableMap[key]));
  });
}

function showStaleBanner(health) {
  const banner = document.getElementById("stale-banner");
  if (health.is_stale) {
    banner.classList.add("is-visible");
    document.getElementById("stale-banner-text").textContent =
      `Aucune collecte réussie depuis ${health.stale_days} jour(s) — vérifie le workflow GitHub Actions "Collect tension974".`;
  }
}

async function init() {
  const appEl = document.getElementById("app");
  try {
    const res = await fetch("data/dashboard.json", { cache: "no-store" });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    DASHBOARD = await res.json();
  } catch (err) {
    appEl.innerHTML = "";
    const empty = emptyState("Impossible de charger data/dashboard.json.");
    appEl.appendChild(empty);
    return;
  }

  document.getElementById("last-updated").textContent =
    `Mis à jour le ${formatDateTimeFull(DASHBOARD.generated_at)}`;

  const hasAnyData = DASHBOARD.searches.some((s) => s.timeseries.length > 0);
  if (!hasAnyData) {
    appEl.innerHTML = "";
    const empty = document.createElement("div");
    empty.className = "empty-state";
    empty.innerHTML = "";
    const p1 = document.createElement("p");
    p1.textContent = "Aucun relevé disponible pour le moment.";
    const p2 = document.createElement("p");
    p2.textContent = "Lance une collecte manuelle : onglet Actions → \"Collect tension974\" → Run workflow.";
    empty.appendChild(p1);
    empty.appendChild(p2);
    appEl.appendChild(empty);
    return;
  }

  showStaleBanner(DASHBOARD.health);

  const template = document.getElementById("tpl-main");
  appEl.innerHTML = "";
  appEl.appendChild(template.content.cloneNode(true));

  const kpiGrid = document.getElementById("kpi-grid");
  DASHBOARD.searches.forEach((search, i) => kpiGrid.appendChild(buildKpiCard(search, i)));

  wireFilters();
  renderAll();
}

init();
