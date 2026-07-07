/* Minimal, dependency-free SVG chart helpers for the tension974 dashboard.
 * No CDN, no framework — small enough to read top to bottom.
 */
"use strict";

const SVG_NS = "http://www.w3.org/2000/svg";

function svgEl(tag, attrs) {
  const el = document.createElementNS(SVG_NS, tag);
  for (const [key, value] of Object.entries(attrs || {})) {
    el.setAttribute(key, value);
  }
  return el;
}

function textEl(tag, attrs, text) {
  const el = svgEl(tag, attrs);
  el.textContent = text;
  return el;
}

function niceMax(value) {
  if (value <= 0) return 10;
  const magnitude = Math.pow(10, Math.floor(Math.log10(value)));
  const normalized = value / magnitude;
  let step;
  if (normalized <= 1) step = 1;
  else if (normalized <= 2) step = 2;
  else if (normalized <= 5) step = 5;
  else step = 10;
  return step * magnitude;
}

function tickValues(maxY, count = 4) {
  const ticks = [];
  for (let i = 0; i <= count; i++) {
    ticks.push(Math.round((maxY * i) / count));
  }
  return ticks;
}

function formatCompact(value) {
  if (value === null || value === undefined) return "—";
  return new Intl.NumberFormat("fr-FR").format(value);
}

function formatDateShort(iso) {
  if (!iso) return "";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "";
  return d.toLocaleDateString("fr-FR", { day: "2-digit", month: "short" });
}

function formatDateFull(iso) {
  if (!iso) return "";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "";
  return d.toLocaleDateString("fr-FR", { day: "2-digit", month: "long", year: "numeric" });
}

function formatDateTimeFull(iso) {
  if (!iso) return "";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "";
  return d.toLocaleString("fr-FR", {
    day: "2-digit", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit",
  });
}

/**
 * Renders a multi-series line chart into `container`.
 * series: [{ id, label, color, points: [{x: isoString, y: number|null}] }]
 */
function renderLineChart(container, series, opts = {}) {
  container.innerHTML = "";
  const visibleSeries = series.filter((s) => s.points.some((p) => p.y !== null && p.y !== undefined));

  if (visibleSeries.length === 0) {
    container.appendChild(emptyState("Pas encore assez de données réussies pour ce graphique."));
    return;
  }

  const width = 720;
  const height = opts.height || 220;
  const margin = { top: 10, right: 58, bottom: 24, left: 40 };
  const plotW = width - margin.left - margin.right;
  const plotH = height - margin.top - margin.bottom;

  const allX = [];
  const allY = [];
  series.forEach((s) => s.points.forEach((p) => {
    allX.push(new Date(p.x).getTime());
    if (p.y !== null && p.y !== undefined) allY.push(p.y);
  }));
  const minX = Math.min(...allX);
  const maxX = Math.max(...allX);
  const maxY = niceMax(Math.max(...allY, 1) * 1.15);

  const xPos = (t) => margin.left + (maxX === minX ? plotW / 2 : ((t - minX) / (maxX - minX)) * plotW);
  const yPos = (v) => margin.top + plotH - (v / maxY) * plotH;

  const svg = svgEl("svg", {
    viewBox: `0 0 ${width} ${height}`,
    class: "chart-svg",
    role: "img",
    style: "width:100%;height:auto;display:block;",
  });

  // Gridlines + Y ticks
  const ticks = tickValues(maxY);
  ticks.forEach((tick) => {
    const y = yPos(tick);
    svg.appendChild(svgEl("line", {
      x1: margin.left, x2: width - margin.right, y1: y, y2: y,
      class: tick === 0 ? "baseline" : "gridline",
    }));
    svg.appendChild(textEl("text", { x: margin.left - 8, y: y + 3, "text-anchor": "end", class: "axis-label" }, formatCompact(tick)));
  });

  // X ticks: first, middle, last
  const xTickTimes = [minX, minX + (maxX - minX) / 2, maxX];
  const seenLabels = new Set();
  xTickTimes.forEach((t) => {
    const label = formatDateShort(new Date(t).toISOString());
    if (seenLabels.has(label)) return;
    seenLabels.add(label);
    svg.appendChild(textEl("text", { x: xPos(t), y: height - 4, "text-anchor": "middle", class: "axis-label" }, label));
  });

  // Lines
  const endLabelSlots = [];
  visibleSeries.forEach((s) => {
    const validPoints = s.points.filter((p) => p.y !== null && p.y !== undefined);
    if (validPoints.length === 0) return;

    let d = "";
    let broken = true;
    s.points.forEach((p) => {
      if (p.y === null || p.y === undefined) { broken = true; return; }
      const x = xPos(new Date(p.x).getTime());
      const y = yPos(p.y);
      d += (broken ? `M ${x},${y} ` : `L ${x},${y} `);
      broken = false;
    });

    svg.appendChild(svgEl("path", { d, fill: "none", stroke: s.color, "stroke-width": 2, "stroke-linejoin": "round", "stroke-linecap": "round" }));

    const last = validPoints[validPoints.length - 1];
    const lx = xPos(new Date(last.x).getTime());
    const ly = yPos(last.y);
    svg.appendChild(svgEl("circle", { cx: lx, cy: ly, r: 4, fill: s.color, stroke: "var(--surface-1)", "stroke-width": 2 }));
    endLabelSlots.push({ id: s.id, label: s.shortLabel || s.label, color: s.color, x: lx, y: ly, origY: ly });
  });

  // Direct end labels with simple vertical de-collision, confined to the
  // reserved right margin band so they never overflow the viewBox.
  endLabelSlots.sort((a, b) => a.y - b.y);
  const minGap = 13;
  for (let i = 1; i < endLabelSlots.length; i++) {
    if (endLabelSlots[i].y - endLabelSlots[i - 1].y < minGap) {
      endLabelSlots[i].y = endLabelSlots[i - 1].y + minGap;
    }
  }
  const labelX = width - margin.right + 6;
  endLabelSlots.forEach((slot) => {
    if (slot.y !== slot.y) return;
    if (Math.abs(slot.x - labelX) > 3 || Math.abs(slot.y - slot.origY) > 3) {
      svg.appendChild(svgEl("line", {
        x1: slot.x, y1: slot.origY, x2: labelX - 4, y2: slot.y,
        stroke: slot.color, "stroke-width": 1, opacity: 0.35,
      }));
    }
    const t = textEl("text", {
      x: labelX, y: slot.y + 3, class: "direct-label", fill: slot.color,
    }, "");
    t.textContent = slot.label;
    svg.appendChild(t);
  });

  // Hover layer: crosshair + unified tooltip.
  const hitRect = svgEl("rect", {
    x: margin.left, y: margin.top, width: plotW, height: plotH, fill: "transparent", style: "cursor:crosshair;",
  });
  const crosshair = svgEl("line", {
    x1: 0, x2: 0, y1: margin.top, y2: margin.top + plotH, class: "gridline", style: "opacity:0;",
  });
  svg.appendChild(crosshair);
  svg.appendChild(hitRect);

  const shell = document.createElement("div");
  shell.className = "chart-shell";
  shell.appendChild(svg);

  const tooltip = document.createElement("div");
  tooltip.className = "tooltip";
  shell.appendChild(tooltip);

  const uniqueX = [...new Set(allX)].sort((a, b) => a - b);

  function nearestValue(s, targetT) {
    let best = null;
    let bestDiff = Infinity;
    s.points.forEach((p) => {
      if (p.y === null || p.y === undefined) return;
      const diff = Math.abs(new Date(p.x).getTime() - targetT);
      if (diff < bestDiff) { bestDiff = diff; best = p; }
    });
    return best;
  }

  function showTooltip(evt) {
    const rect = svg.getBoundingClientRect();
    const scaleFactor = width / rect.width;
    const px = (evt.clientX - rect.left) * scaleFactor;
    const targetT = minX + ((px - margin.left) / plotW) * (maxX - minX);
    let closestT = uniqueX[0];
    let closestDiff = Infinity;
    uniqueX.forEach((t) => {
      const diff = Math.abs(t - targetT);
      if (diff < closestDiff) { closestDiff = diff; closestT = t; }
    });

    crosshair.setAttribute("x1", xPos(closestT));
    crosshair.setAttribute("x2", xPos(closestT));
    crosshair.style.opacity = "1";

    tooltip.innerHTML = "";
    const dateEl = document.createElement("div");
    dateEl.className = "tt-date";
    dateEl.textContent = formatDateFull(new Date(closestT).toISOString());
    tooltip.appendChild(dateEl);

    visibleSeries.forEach((s) => {
      const point = nearestValue(s, closestT);
      const row = document.createElement("div");
      row.className = "tt-row";
      const key = document.createElement("span");
      key.className = "tt-key";
      const swatch = document.createElement("span");
      swatch.className = "tt-swatch";
      swatch.style.background = s.color;
      key.appendChild(swatch);
      const labelNode = document.createElement("span");
      labelNode.textContent = s.label;
      key.appendChild(labelNode);
      const val = document.createElement("span");
      val.className = "tt-value";
      val.textContent = point ? (opts.formatValue ? opts.formatValue(point.y) : formatCompact(point.y)) : "—";
      row.appendChild(key);
      row.appendChild(val);
      tooltip.appendChild(row);
    });

    tooltip.classList.add("is-visible");
    const ttWidth = 170;
    let left = (xPos(closestT) / width) * rect.width + 12;
    if (left + ttWidth > rect.width) left = (xPos(closestT) / width) * rect.width - ttWidth - 12;
    tooltip.style.left = `${left}px`;
    tooltip.style.top = "6px";
  }

  function hideTooltip() {
    tooltip.classList.remove("is-visible");
    crosshair.style.opacity = "0";
  }

  hitRect.addEventListener("pointermove", showTooltip);
  hitRect.addEventListener("pointerleave", hideTooltip);

  container.appendChild(shell);

  // Legend (always present for 2+ series).
  if (series.length > 1) {
    const legend = document.createElement("div");
    legend.className = "legend";
    series.forEach((s) => {
      const item = document.createElement("span");
      item.className = "legend-item";
      const swatch = document.createElement("span");
      swatch.className = "legend-swatch";
      swatch.style.background = s.color;
      item.appendChild(swatch);
      const label = document.createElement("span");
      label.textContent = s.label;
      item.appendChild(label);
      legend.appendChild(item);
    });
    container.appendChild(legend);
  }
}

function emptyState(message) {
  const div = document.createElement("div");
  div.className = "empty-state";
  const p = document.createElement("p");
  p.textContent = message;
  div.appendChild(p);
  return div;
}

/** Generic accessible data table — the WCAG twin of any chart. */
function renderTable(container, columns, rows) {
  container.innerHTML = "";
  if (rows.length === 0) {
    container.appendChild(emptyState("Aucune donnée."));
    return;
  }
  const wrap = document.createElement("div");
  wrap.className = "data-table-wrap";
  const table = document.createElement("table");
  table.className = "data-table";

  const thead = document.createElement("thead");
  const headRow = document.createElement("tr");
  columns.forEach((col) => {
    const th = document.createElement("th");
    th.textContent = col.label;
    headRow.appendChild(th);
  });
  thead.appendChild(headRow);
  table.appendChild(thead);

  const tbody = document.createElement("tbody");
  rows.forEach((row) => {
    const tr = document.createElement("tr");
    columns.forEach((col) => {
      const td = document.createElement("td");
      td.textContent = col.format ? col.format(row) : (row[col.key] ?? "—");
      tr.appendChild(td);
    });
    tbody.appendChild(tr);
  });
  table.appendChild(tbody);
  wrap.appendChild(table);
  container.appendChild(wrap);
}

/** Wires a chart <-> table toggle pair sharing one container. */
function wireTableToggle(toggleBtn, chartContainer, tableContainer) {
  toggleBtn.addEventListener("click", () => {
    const showingTable = tableContainer.style.display !== "none";
    tableContainer.style.display = showingTable ? "none" : "block";
    chartContainer.style.display = showingTable ? "block" : "none";
    toggleBtn.classList.toggle("is-active", !showingTable);
    toggleBtn.textContent = showingTable ? "Vue tableau" : "Vue graphique";
  });
}

const CATEGORY_LABEL_FR = {
  none: "Succès",
  blocked: "Bloqué (firewall / anti-bot)",
  rate_limited: "Limite de débit",
  timeout: "Délai dépassé",
  network: "Erreur réseau",
  no_data: "Page changée",
  credentials: "Configuration",
  unknown: "Erreur inconnue",
  running: "En cours",
};

// Maps a failure category to one of the four fixed status roles so ticks
// and legend swatches carry real severity, not just success/failure red.
const CATEGORY_COLOR = {
  none: "var(--status-good)",
  running: "var(--status-muted)",
  rate_limited: "var(--status-warning)",
  no_data: "var(--status-warning)",
  timeout: "var(--status-serious)",
  network: "var(--status-serious)",
  blocked: "var(--status-critical)",
  credentials: "var(--status-critical)",
  unknown: "var(--status-critical)",
};

/**
 * Renders a horizontal strip of run ticks, most recent last, colored by
 * status, with a hover/focus tooltip. runs: merged run records (see
 * tension974/aggregation.py::merge_runs), most-recent-first.
 */
function renderRunStrip(container, runs) {
  container.innerHTML = "";
  if (runs.length === 0) {
    container.appendChild(emptyState("Aucune collecte enregistrée pour le moment."));
    return;
  }

  const shell = document.createElement("div");
  shell.className = "chart-shell";

  const strip = document.createElement("div");
  strip.className = "run-strip";

  const tooltip = document.createElement("div");
  tooltip.className = "tooltip";
  shell.appendChild(tooltip);

  const chronological = [...runs].reverse();
  chronological.forEach((run) => {
    const tick = document.createElement("div");
    tick.className = "run-tick";
    tick.style.background = CATEGORY_COLOR[run.category] || CATEGORY_COLOR.unknown;
    tick.tabIndex = 0;

    const show = () => {
      tooltip.innerHTML = "";
      const dateEl = document.createElement("div");
      dateEl.className = "tt-date";
      dateEl.textContent = formatDateTimeFull(run.started_at);
      tooltip.appendChild(dateEl);

      const rows = [
        ["Statut", CATEGORY_LABEL_FR[run.category] || run.category],
        ["Provider", run.provider || "—"],
        ["Durée", run.duration_seconds ? `${run.duration_seconds}s` : "—"],
      ];
      if (run.error_message) rows.push(["Erreur", run.error_message]);

      rows.forEach(([label, value]) => {
        const row = document.createElement("div");
        row.className = "tt-row";
        const key = document.createElement("span");
        key.className = "tt-key";
        key.textContent = label;
        const val = document.createElement("span");
        val.className = "tt-value";
        val.textContent = value;
        row.appendChild(key);
        row.appendChild(val);
        tooltip.appendChild(row);
      });

      tooltip.classList.add("is-visible");
      const shellRect = shell.getBoundingClientRect();
      const tickRect = tick.getBoundingClientRect();
      tooltip.style.left = `${tickRect.left - shellRect.left - 70}px`;
      tooltip.style.top = "-4px";
    };
    const hide = () => tooltip.classList.remove("is-visible");

    tick.addEventListener("pointerenter", show);
    tick.addEventListener("focus", show);
    tick.addEventListener("pointerleave", hide);
    tick.addEventListener("blur", hide);

    strip.appendChild(tick);
  });

  shell.appendChild(strip);
  container.appendChild(shell);
  container.scrollLeft = container.scrollWidth;
}
