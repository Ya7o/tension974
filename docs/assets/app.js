/* tension974 dashboard — wires data/dashboard.json to the chart components
 * defined in charts.js. Plain JS, no build step, no framework.
 *
 * Reading order on screen mirrors the questions actually asked when the page
 * is opened on a phone: is the data fresh, did the market move, where does
 * each typology stand. Everything below that is on demand.
 */
"use strict";

const SERIES_COLORS = ["var(--series-1)", "var(--series-2)", "var(--series-3)"];
const THEME_KEY = "t974-theme";
const FLAT_PCT = 3; // below this, a move is noise, not a trend
const MIN_HISTORY_FOR_LEVEL = 8;

let currentRangeDays = 365; // "12 mois" by default; null = tout l'historique
let currentPriceMetric = "median_price";
let DASHBOARD = null;
let RUNS = [];
let HEALTH = null;

/* ── Statistics ─────────────────────────────────────────────────────────
 * All of it derived client-side from data already present in
 * dashboard.json — no new collected field, no backend change.
 */

function quantile(sortedValues, q) {
  if (sortedValues.length === 0) return null;
  const pos = (sortedValues.length - 1) * q;
  const lower = Math.floor(pos);
  const upper = Math.ceil(pos);
  if (lower === upper) return sortedValues[lower];
  return sortedValues[lower] + (sortedValues[upper] - sortedValues[lower]) * (pos - lower);
}

/** Share of the history at or below `value`, ties counted half. */
function percentileRank(values, value) {
  if (values.length === 0) return null;
  let below = 0;
  let equal = 0;
  values.forEach((v) => {
    if (v < value) below += 1;
    else if (v === value) equal += 1;
  });
  return (below + equal / 2) / values.length;
}

const LEVELS = {
  tight: { key: "tight", label: "Tendu", hint: "offre rare" },
  normal: { key: "normal", label: "Normal", hint: "offre habituelle" },
  loose: { key: "loose", label: "Détendu", hint: "offre abondante" },
};

/**
 * Reads the latest listing count against the typology's own 12-month
 * distribution. Few listings = tight market, many listings = loose market
 * (see tension974-docs/01_PRODUCT_SPEC.md). Returns null when the history is
 * too short to say anything honest.
 */
function tensionLevel(series, now = Date.now()) {
  const cutoff = now - 365 * 86400000;
  const window = series.filter((p) =>
    p.success && p.count !== null && p.count !== undefined
    && new Date(p.observed_at).getTime() >= cutoff);
  if (window.length < MIN_HISTORY_FOR_LEVEL) return null;

  const values = window.map((p) => p.count).sort((a, b) => a - b);
  const latest = window[window.length - 1].count;
  const rank = percentileRank(values, latest);

  let level = LEVELS.normal;
  if (rank <= 0.33) level = LEVELS.tight;
  else if (rank >= 0.66) level = LEVELS.loose;

  return {
    ...level,
    rank,
    latest,
    median: Math.round(quantile(values, 0.5)),
    band: { lo: quantile(values, 0.25), hi: quantile(values, 0.75) },
    sampleSize: window.length,
  };
}

/** Turns a {delta, from, to} block from dashboard.json into a % move. */
function trendFromDelta(delta) {
  if (!delta) return null;
  const absolute = delta.to - delta.from;
  const pct = delta.from ? (absolute / delta.from) * 100 : null;
  let direction = "flat";
  if (pct === null) direction = absolute > 0 ? "up" : (absolute < 0 ? "down" : "flat");
  else if (pct >= FLAT_PCT) direction = "up";
  else if (pct <= -FLAT_PCT) direction = "down";
  return { pct, absolute, direction };
}

const ARROWS = { up: "↑", down: "↓", flat: "→" };

function trendChip(trend, { noun, neutral = false } = {}) {
  const span = document.createElement("span");
  span.className = `trend ${neutral ? "is-neutral" : `is-${trend ? trend.direction : "flat"}`}`;
  if (!trend) {
    span.classList.add("is-unknown");
    span.textContent = "pas de comparaison";
    return span;
  }
  const value = trend.pct === null ? formatCompact(trend.absolute) : formatPercent(trend.pct);
  span.textContent = `${ARROWS[trend.direction]} ${value}${noun ? ` ${noun}` : ""}`;
  return span;
}

/* ── Collection health ──────────────────────────────────────────────────
 * Rates and categories come from tension974/aggregation.py (compute_health),
 * published in dashboard.json — a single implementation instead of a
 * Python/JS pair that had already drifted apart. Staleness is the exception:
 * it MUST be recomputed at view time. dashboard.json is only regenerated when
 * the pipeline runs, so a frozen stale_days would keep saying "up to date"
 * forever on a dead pipeline — the one failure it exists to reveal.
 */

function healthFromPayload(h, now = Date.now()) {
  if (!h) {
    return {
      successRate7d: null,
      successRate30d: null,
      categoryCounts30d: {},
      lastSuccessAt: null,
      lastFinishedStatus: null,
      staleDays: null,
      isStale: true,
      totalRuns: 0,
    };
  }
  const staleDays = h.last_productive_at
    ? Math.floor((now - new Date(h.last_productive_at).getTime()) / 86400000)
    : null;
  const staleAfter = typeof h.stale_after_days === "number" ? h.stale_after_days : 10;
  return {
    successRate7d: h.success_rate_7d,
    successRate30d: h.success_rate_30d,
    categoryCounts30d: h.category_counts_30d || {},
    lastSuccessAt: h.last_success_at,
    lastFinishedStatus: h.last_finished_status,
    staleDays,
    isStale: staleDays === null || staleDays >= staleAfter,
    totalRuns: h.total_runs,
  };
}

/* ── Status bar ─────────────────────────────────────────────────────────── */

function latestReadingDate() {
  const dates = DASHBOARD.searches
    .map((s) => s.kpis.latest_date)
    .filter(Boolean)
    .sort();
  return dates.length ? dates[dates.length - 1] : null;
}

function renderStatusPill() {
  const pill = document.getElementById("status-pill");
  const label = document.getElementById("status-pill-text");
  pill.classList.remove("is-good", "is-warning", "is-critical", "is-unknown");

  const reading = latestReadingDate();
  const readingText = reading ? `relevé du ${formatDateShort(reading)}` : "aucun relevé";

  let tone = "is-good";
  let text = `Collecte à jour · ${readingText}`;

  if (HEALTH.totalRuns === 0) {
    tone = "is-unknown";
    text = `État de collecte inconnu · ${readingText}`;
  } else if (HEALTH.staleDays === null) {
    tone = "is-critical";
    text = `Aucune collecte exploitable · ${readingText}`;
  } else if (HEALTH.isStale) {
    tone = "is-critical";
    text = `Collecte en retard de ${HEALTH.staleDays} j · ${readingText}`;
  } else if (HEALTH.lastFinishedStatus === "failed") {
    tone = "is-critical";
    text = `Dernière collecte en échec · ${readingText}`;
  } else if (HEALTH.lastFinishedStatus === "partial") {
    tone = "is-warning";
    text = `Dernière collecte partielle · ${readingText}`;
  }

  pill.classList.add(tone);
  label.textContent = text;
}

/* ── Verdict ────────────────────────────────────────────────────────────── */

function joinFr(items) {
  if (items.length === 0) return "";
  if (items.length === 1) return items[0];
  return `${items.slice(0, -1).join(", ")} et ${items[items.length - 1]}`;
}

function buildVerdict(readings) {
  const known = readings.filter((r) => r.level);
  const sentences = [];

  if (known.length === 0) {
    sentences.push({ lead: "Historique encore trop court", rest: " pour situer le marché — les relevés s'accumulent à chaque collecte." });
  } else {
    const tight = known.filter((r) => r.level.key === "tight").length;
    const loose = known.filter((r) => r.level.key === "loose").length;
    let lead = "Marché dans sa normale";
    if (loose > tight && loose >= known.length / 2) lead = "Marché plutôt détendu";
    else if (tight > loose && tight >= known.length / 2) lead = "Marché plutôt tendu";
    else if (tight && loose) lead = "Signaux partagés";
    sentences.push({ lead, rest: " par rapport aux 12 derniers mois." });
  }

  const up = readings.filter((r) => r.countTrend && r.countTrend.direction === "up").map((r) => r.shortName);
  const down = readings.filter((r) => r.countTrend && r.countTrend.direction === "down").map((r) => r.shortName);
  const flat = readings.filter((r) => r.countTrend && r.countTrend.direction === "flat").map((r) => r.shortName);

  const clauses = [];
  if (up.length) clauses.push(`progresse sur ${joinFr(up)}`);
  if (down.length) clauses.push(`recule sur ${joinFr(down)}`);
  if (flat.length) clauses.push(`reste stable sur ${joinFr(flat)}`);
  if (clauses.length) {
    sentences.push({ lead: "", rest: `Sur 4 semaines, l'offre ${joinFr(clauses)}.` });
  }

  const movers = readings
    .filter((r) => r.priceTrend && r.priceTrend.direction !== "flat" && r.priceTrend.pct !== null)
    .map((r) => `${r.shortName} ${formatPercent(r.priceTrend.pct)}`);
  if (movers.length) {
    sentences.push({ lead: "", rest: `Côté prix médians : ${joinFr(movers)}.` });
  }

  return sentences;
}

function renderVerdict(readings) {
  const host = document.getElementById("verdict");
  host.innerHTML = "";
  buildVerdict(readings).forEach((sentence, i) => {
    const p = document.createElement("p");
    p.className = i === 0 ? "verdict-lead" : "verdict-detail";
    if (sentence.lead) {
      const strong = document.createElement("strong");
      strong.textContent = sentence.lead;
      p.appendChild(strong);
    }
    p.appendChild(document.createTextNode(sentence.rest));
    host.appendChild(p);
  });
}

/* ── Typology cards ─────────────────────────────────────────────────────── */

function buildReading(search, index) {
  const kpis = search.kpis;
  return {
    search,
    index,
    color: SERIES_COLORS[index % SERIES_COLORS.length],
    shortName: search.property_type || search.name,
    level: tensionLevel(search.timeseries),
    countTrend: trendFromDelta(kpis.delta_30d),
    countTrend7d: trendFromDelta(kpis.delta_7d),
    priceTrend: trendFromDelta(kpis.price_delta_30d),
  };
}

function metricValue(value, unit) {
  const p = document.createElement("p");
  p.className = "metric-value";
  const strong = document.createElement("strong");
  strong.textContent = value;
  p.appendChild(strong);
  p.appendChild(document.createTextNode(` ${unit}`));
  return p;
}

function buildCard(reading, freshestDate) {
  const { search, level, color } = reading;
  const kpis = search.kpis;

  const card = document.createElement("article");
  card.className = "card typology-card";
  card.style.setProperty("--accent", color);

  // Header: typology + tension level, never colour alone.
  const head = document.createElement("header");
  head.className = "typology-head";
  const name = document.createElement("h3");
  name.textContent = search.name;
  head.appendChild(name);

  const chip = document.createElement("span");
  chip.className = `level-chip ${level ? `is-${level.key}` : "is-unknown"}`;
  chip.textContent = level ? level.label : "Historique court";
  if (level) chip.title = `${level.hint} — ${Math.round(level.rank * 100)}ᵉ centile de ses 12 derniers mois`;
  head.appendChild(chip);
  card.appendChild(head);

  // The two headline numbers side by side: offer volume (the tension signal)
  // and price level (the positioning signal).
  const metrics = document.createElement("div");
  metrics.className = "metric-row";

  const countBlock = document.createElement("div");
  countBlock.className = "metric";
  countBlock.appendChild(metricValue(
    kpis.latest_count !== null && kpis.latest_count !== undefined ? formatCompact(kpis.latest_count) : "—",
    "annonces",
  ));
  const countTrends = document.createElement("p");
  countTrends.className = "metric-trends";
  countTrends.appendChild(trendChip(reading.countTrend, { noun: "/ 4 sem." }));
  if (reading.countTrend7d) {
    const weekly = document.createElement("span");
    weekly.className = "trend-secondary";
    const value = reading.countTrend7d.pct === null
      ? formatCompact(reading.countTrend7d.absolute)
      : formatPercent(reading.countTrend7d.pct);
    weekly.textContent = `${value} / 7 j`;
    countTrends.appendChild(weekly);
  }
  countBlock.appendChild(countTrends);
  metrics.appendChild(countBlock);

  const priceBlock = document.createElement("div");
  priceBlock.className = "metric";
  if (kpis.latest_median_price !== null && kpis.latest_median_price !== undefined) {
    priceBlock.appendChild(metricValue(`${formatCompact(kpis.latest_median_price)} €`, "médian"));
    const priceTrends = document.createElement("p");
    priceTrends.className = "metric-trends";
    priceTrends.appendChild(trendChip(reading.priceTrend, { noun: "/ 4 sem.", neutral: true }));
    // The headline price is a median of at most 30 prices read off page 1 of
    // the results — say so next to it, not only inside the data table.
    const note = document.createElement("span");
    note.className = "trend-secondary";
    const parts = [];
    if (kpis.latest_average_price) parts.push(`moy. ${formatCompact(kpis.latest_average_price)} €`);
    parts.push(kpis.price_sample_size ? `éch. ${formatCompact(kpis.price_sample_size)}` : "éch. ?");
    note.textContent = parts.join(" · ");
    priceTrends.appendChild(note);
    priceBlock.appendChild(priceTrends);
  } else {
    priceBlock.appendChild(metricValue("—", "médian"));
    const none = document.createElement("p");
    none.className = "metric-note";
    none.textContent = "prix pas encore relevés";
    priceBlock.appendChild(none);
  }
  metrics.appendChild(priceBlock);
  card.appendChild(metrics);

  // Sparkline: the shape of the last 12 months, with the usual range behind it.
  const spark = document.createElement("div");
  spark.className = "spark";
  card.appendChild(spark);
  const sparkPoints = search.timeseries
    .filter((p) => new Date(p.observed_at).getTime() >= Date.now() - 365 * 86400000)
    .map((p) => ({ x: p.observed_at, y: p.success ? p.count : null }));
  renderSparkline(spark, {
    points: sparkPoints,
    color,
    band: level ? level.band : null,
    height: 38,
    ariaLabel: level
      ? `${search.name} : ${formatCompact(level.latest)} annonces sur 12 mois, plage habituelle de ${formatCompact(Math.round(level.band.lo))} à ${formatCompact(Math.round(level.band.hi))}, médiane ${formatCompact(level.median)}.`
      : `${search.name} : tendance du nombre d'annonces sur 12 mois.`,
  });

  if (level) {
    const context = document.createElement("p");
    context.className = "spark-caption";
    context.textContent = `12 mois · habituel ${formatCompact(Math.round(level.band.lo))}–${formatCompact(Math.round(level.band.hi))} · médiane ${formatCompact(level.median)}`;
    card.appendChild(context);
  }

  // Freshness: a typology lagging behind the others must not hide in grey 11px.
  const isLagging = kpis.latest_date && freshestDate && kpis.latest_date < freshestDate;
  const freshFailure = kpis.last_failure && kpis.last_failure.date === freshestDate
    ? kpis.last_failure : null;
  if (isLagging || freshFailure) {
    const warn = document.createElement("p");
    warn.className = "card-warning";
    const cause = freshFailure
      ? `${CATEGORY_LABEL_FR[freshFailure.category] || freshFailure.category}`.toLowerCase()
      : null;
    // formatDateShort already ends in a period ("30 juil."), so don't add one.
    if (freshFailure && isLagging) {
      warn.textContent = `Collecte du ${formatDateShort(freshFailure.date)} en échec (${cause}) : les chiffres datent du ${formatDateShort(kpis.latest_date)}`;
    } else if (freshFailure) {
      warn.textContent = `Collecte du ${formatDateShort(freshFailure.date)} en échec : ${cause}.`;
    } else {
      warn.textContent = `Chiffres du ${formatDateShort(kpis.latest_date)}, en retard sur les autres typologies.`;
    }
    card.appendChild(warn);
  }

  return card;
}

/* ── Detail: one chart per typology, each at its own scale ─────────────── */

function filterByRange(points, dateKey) {
  if (currentRangeDays === null) return points;
  const cutoff = Date.now() - currentRangeDays * 86400000;
  return points.filter((p) => new Date(p[dateKey]).getTime() >= cutoff);
}

function renderSmallMultiples(host, readings, { field, formatValue, unit, zeroBased = true, trimLeadingEmpty = false }) {
  host.innerHTML = "";
  readings.forEach((reading) => {
    const { search, color } = reading;
    let points = filterByRange(search.timeseries, "observed_at")
      .map((p) => ({
        x: p.observed_at,
        y: (p.success && p[field] !== null && p[field] !== undefined) ? p[field] : null,
      }));
    // Prices only started being collected in April 2026: without this, a
    // 12-month view is nine months of empty axis and three months of curve.
    if (trimLeadingEmpty) {
      const first = points.findIndex((p) => p.y !== null);
      points = first > 0 ? points.slice(first) : points;
    }

    const block = document.createElement("div");
    block.className = "multiple";

    const caption = document.createElement("p");
    caption.className = "multiple-title";
    const dot = document.createElement("span");
    dot.className = "multiple-dot";
    dot.style.background = color;
    caption.appendChild(dot);
    caption.appendChild(document.createTextNode(search.name));
    block.appendChild(caption);

    const chart = document.createElement("div");
    chart.className = "multiple-chart";
    block.appendChild(chart);
    host.appendChild(block);

    renderLineChart(chart, [{
      id: search.id,
      label: search.name,
      shortLabel: reading.shortName,
      color,
      points,
    }], {
      formatValue,
      directLabels: false,
      showLegend: false,
      zeroBased,
      height: 150,
      ariaLabel: `${search.name} — ${unit} sur la période sélectionnée.`,
      emptyMessage: `Aucun relevé de ${unit} sur cette période.`,
    });
  });
}

function renderCountDetail(readings) {
  renderSmallMultiples(document.getElementById("count-charts"), readings, {
    field: "count",
    formatValue: (v) => `${formatCompact(v)} annonces`,
    unit: "nombre d'annonces",
  });

  const rows = [];
  readings.forEach(({ search }) => {
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

function renderPriceDetail(readings) {
  const metric = currentPriceMetric;
  renderSmallMultiples(document.getElementById("price-charts"), readings, {
    field: metric,
    formatValue: (v) => `${formatCompact(v)} €`,
    unit: "prix",
    zeroBased: false,
    trimLeadingEmpty: true,
  });

  const rows = [];
  readings.forEach(({ search }) => {
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

function renderPriceCoverageNote() {
  const note = document.getElementById("price-coverage");
  const firstPriced = DASHBOARD.searches
    .flatMap((s) => s.timeseries)
    .filter((p) => p.median_price !== null && p.median_price !== undefined)
    .map((p) => p.date)
    .sort()[0];
  note.textContent = firstPriced
    ? `Les prix ne sont relevés que depuis le ${formatDateFull(firstPriced)} : les courbes commencent à cette date. L'axe vertical ne part pas de zéro, pour laisser voir les variations.`
    : "Aucun prix relevé pour le moment.";
}

/* ── Detail: collection health, folded away behind the status pill ─────── */

function renderCollectionDetail() {
  renderRunStrip(document.getElementById("run-strip"), RUNS);

  renderTable(document.getElementById("run-table"), [
    { label: "Début", key: "started_at", format: (r) => formatDateTimeFull(r.started_at) },
    { label: "Statut", format: (r) => CATEGORY_LABEL_FR[r.category] || r.category },
    { label: "Provider", key: "provider", format: (r) => r.provider || "—" },
    { label: "Durée", format: (r) => (r.duration_seconds ? `${r.duration_seconds}s` : "—") },
    { label: "Erreur", format: (r) => r.error_message || "—" },
  ], RUNS);

  const legend = document.getElementById("category-legend");
  legend.innerHTML = "";
  Object.entries(HEALTH.categoryCounts30d).forEach(([category, count]) => {
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

  const statsEl = document.getElementById("health-stats");
  statsEl.innerHTML = "";
  const asPercent = (rate) => (rate === null ? "—" : `${Math.round(rate * 100)}%`);
  [
    ["Succès sur 7 j", asPercent(HEALTH.successRate7d)],
    ["Succès sur 30 j", asPercent(HEALTH.successRate30d)],
    ["Collectes exploitables", formatCompact(HEALTH.totalRuns)],
    ["Dernier succès", HEALTH.lastSuccessAt ? formatDateFull(HEALTH.lastSuccessAt) : "—"],
  ].forEach(([label, num]) => {
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

/* ── Wiring ─────────────────────────────────────────────────────────────── */

function renderDetail(readings) {
  renderCountDetail(readings);
  renderPriceDetail(readings);
}

function wireControls(readings) {
  document.querySelectorAll(".filter-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".filter-btn").forEach((b) => {
        b.classList.remove("is-active");
        b.setAttribute("aria-pressed", "false");
      });
      btn.classList.add("is-active");
      btn.setAttribute("aria-pressed", "true");
      currentRangeDays = btn.dataset.range === "all" ? null : Number(btn.dataset.range);
      renderDetail(readings);
    });
  });

  document.querySelectorAll(".price-toggle button").forEach((btn) => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".price-toggle button").forEach((b) => {
        b.classList.remove("is-active");
        b.setAttribute("aria-pressed", "false");
      });
      btn.classList.add("is-active");
      btn.setAttribute("aria-pressed", "true");
      currentPriceMetric = btn.dataset.priceMetric;
      renderPriceDetail(readings);
    });
  });

  document.querySelectorAll("[data-toggle]").forEach((btn) => {
    const key = btn.dataset.toggle;
    const charts = { count: "count-charts", price: "price-charts", runs: "run-strip" };
    const tables = { count: "count-table", price: "price-table", runs: "run-table" };
    wireTableToggle(btn, document.getElementById(charts[key]), document.getElementById(tables[key]));
  });

  // The status pill is the entry point to the collection details.
  const pill = document.getElementById("status-pill");
  const details = document.getElementById("collection-details");
  pill.addEventListener("click", () => {
    const open = details.open;
    details.open = !open;
    if (!open) details.scrollIntoView({ behavior: "smooth", block: "nearest" });
  });
}

function applyTheme(theme) {
  if (theme === "light" || theme === "dark") {
    document.documentElement.setAttribute("data-theme", theme);
  } else {
    document.documentElement.removeAttribute("data-theme");
  }
  const btn = document.getElementById("theme-toggle");
  if (!btn) return;
  const isDark = theme === "dark"
    || (!theme && window.matchMedia("(prefers-color-scheme: dark)").matches);
  btn.textContent = isDark ? "☀" : "☾";
  btn.setAttribute("aria-label", isDark ? "Passer en thème clair" : "Passer en thème sombre");
}

function wireTheme() {
  let stored = null;
  try { stored = localStorage.getItem(THEME_KEY); } catch (err) { stored = null; }
  applyTheme(stored);
  const btn = document.getElementById("theme-toggle");
  btn.addEventListener("click", () => {
    const isDark = document.documentElement.getAttribute("data-theme") === "dark"
      || (!document.documentElement.hasAttribute("data-theme")
        && window.matchMedia("(prefers-color-scheme: dark)").matches);
    const next = isDark ? "light" : "dark";
    try { localStorage.setItem(THEME_KEY, next); } catch (err) { /* private mode */ }
    applyTheme(next);
  });
}

async function init() {
  wireTheme();
  const appEl = document.getElementById("app");

  try {
    const res = await fetch("data/dashboard.json", { cache: "no-store" });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    DASHBOARD = await res.json();
  } catch (err) {
    appEl.innerHTML = "";
    appEl.appendChild(emptyState("Impossible de charger data/dashboard.json."));
    return;
  }

  RUNS = DASHBOARD.runs || [];
  HEALTH = healthFromPayload(DASHBOARD.health);

  // The collection state is worth knowing even when there is nothing to plot —
  // "no data" and "the scraper is blocked" are different problems.
  renderStatusPill();
  document.getElementById("generated-at").textContent =
    `Données générées le ${formatDateTimeFull(DASHBOARD.generated_at)}`;

  const hasAnyData = DASHBOARD.searches.some((s) => s.timeseries.length > 0);
  if (!hasAnyData) {
    appEl.innerHTML = "";
    const empty = document.createElement("div");
    empty.className = "empty-state";
    const p1 = document.createElement("p");
    p1.textContent = "Aucun relevé disponible pour le moment.";
    const p2 = document.createElement("p");
    p2.textContent = "Lance une collecte manuelle : onglet Actions → \"Collect tension974\" → Run workflow.";
    empty.appendChild(p1);
    empty.appendChild(p2);
    appEl.appendChild(empty);
    return;
  }

  appEl.innerHTML = "";
  appEl.appendChild(document.getElementById("tpl-main").content.cloneNode(true));

  const readings = DASHBOARD.searches.map(buildReading);
  renderVerdict(readings);

  const freshest = latestReadingDate();
  const grid = document.getElementById("card-grid");
  readings.forEach((reading) => grid.appendChild(buildCard(reading, freshest)));

  renderPriceCoverageNote();
  renderDetail(readings);
  renderCollectionDetail();
  wireControls(readings);
}

init();
