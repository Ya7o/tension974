/* Minimal, dependency-free SVG chart helpers for the tension974 dashboard.
 * No CDN, no framework — small enough to read top to bottom.
 *
 * Charts are drawn at the container's real pixel width (1 SVG user unit =
 * 1 CSS pixel) and re-drawn on resize, so axis labels keep their intended
 * size on a 375px phone instead of being scaled down with the viewBox.
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

/**
 * Picks a round tick interval first, then the axis maximum, so ticks read
 * 0/20/40/60 rather than 0/67/133/200 — and so a series peaking at 52 is not
 * squeezed into the bottom half of a 0-100 axis.
 */
function niceScale(minValue, maxValue, tickCount = 4) {
  const span = (maxValue - minValue) || Math.abs(maxValue) || 1;
  const raw = span / tickCount;
  const magnitude = Math.pow(10, Math.floor(Math.log10(raw)));
  const normalized = raw / magnitude;
  let step;
  if (normalized <= 1) step = 1;
  else if (normalized <= 2) step = 2;
  else if (normalized <= 2.5) step = 2.5;
  else if (normalized <= 5) step = 5;
  else step = 10;
  const interval = step * magnitude;
  const min = Math.floor(minValue / interval) * interval;
  const max = Math.ceil(maxValue / interval) * interval;
  const ticks = [];
  for (let value = min; value <= max + interval / 2; value += interval) {
    ticks.push(Math.round(value * 1000) / 1000);
  }
  return { min, max, ticks };
}

function formatCompact(value) {
  if (value === null || value === undefined) return "—";
  return new Intl.NumberFormat("fr-FR").format(value);
}

function formatPercent(value, { withSign = true } = {}) {
  if (value === null || value === undefined || Number.isNaN(value)) return "—";
  const rounded = Math.abs(value) >= 10 ? Math.round(value) : Math.round(value * 10) / 10;
  const sign = withSign && rounded > 0 ? "+" : "";
  return `${sign}${new Intl.NumberFormat("fr-FR", { maximumFractionDigits: 1 }).format(rounded)} %`;
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

/* ── Time axis ─────────────────────────────────────────────────────────
 * The collection cadence is irregular (3-15 day backfill, then weekly), so
 * evenly-spaced ticks would lie about when readings happened. We tick on
 * month boundaries instead and thin them to fit the available width.
 */

function monthTicks(minMs, maxMs, maxTicks) {
  const start = new Date(minMs);
  let cursor = new Date(Date.UTC(start.getUTCFullYear(), start.getUTCMonth(), 1));
  if (cursor.getTime() < minMs) {
    cursor = new Date(Date.UTC(cursor.getUTCFullYear(), cursor.getUTCMonth() + 1, 1));
  }
  const all = [];
  while (cursor.getTime() <= maxMs && all.length < 200) {
    all.push(cursor.getTime());
    cursor = new Date(Date.UTC(cursor.getUTCFullYear(), cursor.getUTCMonth() + 1, 1));
  }
  if (all.length === 0) return [minMs, maxMs];
  const step = Math.max(1, Math.ceil(all.length / Math.max(1, maxTicks)));
  return all.filter((_, i) => i % step === 0);
}

function formatMonthTick(ms, withYear) {
  const d = new Date(ms);
  const month = d.toLocaleDateString("fr-FR", { month: "short", timeZone: "UTC" }).replace(".", "");
  return withYear ? `${month} ${String(d.getUTCFullYear()).slice(2)}` : month;
}

/* ── Responsive rendering ──────────────────────────────────────────────
 * Re-invokes `draw(width)` whenever the container's width changes by more
 * than a few pixels. Guarded so that replacing the container's own content
 * (which fires the observer again) does not loop.
 */
function renderResponsive(container, draw) {
  if (container._t974Observer) {
    container._t974Observer.disconnect();
    container._t974Observer = null;
  }
  let lastWidth = 0;
  const run = () => {
    const width = Math.round(container.clientWidth);
    if (width < 40) return; // hidden / collapsed: wait until it is shown
    if (Math.abs(width - lastWidth) < 6) return;
    lastWidth = width;
    draw(width);
  };
  run();
  if (typeof ResizeObserver === "function") {
    const observer = new ResizeObserver(run);
    observer.observe(container);
    container._t974Observer = observer;
  }
}

/* ── Sparkline ─────────────────────────────────────────────────────────
 * The at-a-glance trend inside a typology card: the shape of the series,
 * plus a grey band showing where the value usually sits (p25-p75 of its own
 * history) so "is this high or low?" is answered without reading numbers.
 */
function renderSparkline(container, opts) {
  const points = (opts.points || []).filter((p) => p.y !== null && p.y !== undefined);
  container.innerHTML = "";
  if (points.length < 2) {
    const note = document.createElement("p");
    note.className = "spark-empty";
    note.textContent = "Pas assez de relevés pour tracer une tendance.";
    container.appendChild(note);
    return;
  }

  renderResponsive(container, (width) => {
    container.innerHTML = "";
    const height = opts.height || 48;
    const padY = 5;
    const padRight = 5;

    const xs = points.map((p) => new Date(p.x).getTime());
    const ys = points.map((p) => p.y);
    const minX = Math.min(...xs);
    const maxX = Math.max(...xs);
    let minY = Math.min(...ys, opts.band ? opts.band.lo : Infinity);
    let maxY = Math.max(...ys, opts.band ? opts.band.hi : -Infinity);
    if (maxY === minY) { maxY += 1; minY -= 1; }

    const plotW = width - padRight;
    const xPos = (t) => (maxX === minX ? plotW / 2 : ((t - minX) / (maxX - minX)) * plotW);
    const yPos = (v) => padY + (1 - (v - minY) / (maxY - minY)) * (height - padY * 2);

    const svg = svgEl("svg", {
      viewBox: `0 0 ${width} ${height}`,
      width, height,
      class: "spark-svg",
      role: "img",
      focusable: "false",
      style: "display:block;",
    });
    svg.appendChild(textEl("title", {}, opts.ariaLabel || "Tendance"));
    if (opts.ariaLabel) svg.setAttribute("aria-label", opts.ariaLabel);

    if (opts.band && opts.band.lo !== undefined && opts.band.hi !== undefined) {
      const top = yPos(opts.band.hi);
      const bottom = yPos(opts.band.lo);
      svg.appendChild(svgEl("rect", {
        x: 0, y: Math.min(top, bottom), width: plotW, height: Math.max(2, Math.abs(bottom - top)),
        class: "spark-band",
      }));
    }

    let d = "";
    points.forEach((p, i) => {
      const x = xPos(new Date(p.x).getTime());
      const y = yPos(p.y);
      d += `${i === 0 ? "M" : "L"} ${x.toFixed(1)},${y.toFixed(1)} `;
    });
    svg.appendChild(svgEl("path", {
      d, fill: "none", stroke: opts.color || "currentColor",
      "stroke-width": 1.8, "stroke-linejoin": "round", "stroke-linecap": "round",
    }));

    const last = points[points.length - 1];
    svg.appendChild(svgEl("circle", {
      cx: xPos(new Date(last.x).getTime()), cy: yPos(last.y), r: 3.2,
      fill: opts.color || "currentColor", stroke: "var(--surface-1)", "stroke-width": 1.6,
    }));

    container.appendChild(svg);
  });
}

/* ── Line chart ────────────────────────────────────────────────────────
 * series: [{ id, label, shortLabel, color, points: [{x: isoString, y: number|null}] }]
 * Nulls are failed collections, not absent history — they are bridged with a
 * dashed segment so a gap reads as "relevé manquant", not "flat".
 */
function renderLineChart(container, series, opts = {}) {
  const hasData = series.some((s) => s.points.some((p) => p.y !== null && p.y !== undefined));
  if (!hasData) {
    container.innerHTML = "";
    container.appendChild(emptyState(opts.emptyMessage || "Pas encore assez de relevés réussis pour ce graphique."));
    return;
  }

  renderResponsive(container, (width) => {
    container.innerHTML = "";
    const compact = width < 420;
    const height = opts.height || (compact ? 150 : 190);
    const margin = {
      top: 10,
      right: opts.directLabels === false ? 12 : (compact ? 12 : 56),
      bottom: 22,
      left: opts.axisWidth || (compact ? 34 : 42),
    };
    const plotW = Math.max(40, width - margin.left - margin.right);
    const plotH = height - margin.top - margin.bottom;

    const allX = [];
    const allY = [];
    series.forEach((s) => s.points.forEach((p) => {
      const t = new Date(p.x).getTime();
      if (!Number.isNaN(t)) allX.push(t);
      if (p.y !== null && p.y !== undefined) allY.push(p.y);
    }));
    const minX = Math.min(...allX);
    const maxX = Math.max(...allX);

    // Counts are volumes, so their axis starts at zero. Prices are levels
    // around 600-1300 €: forcing zero flattens every variation into a
    // straight line at the top of the plot, which is what we are fixing.
    const dataMin = Math.min(...allY);
    const dataMax = Math.max(...allY, 1);
    const pad = (dataMax - dataMin) * 0.12 || Math.abs(dataMax) * 0.05 || 1;
    const scale = opts.zeroBased === false
      ? niceScale(dataMin - pad, dataMax + pad, compact ? 3 : 4)
      : niceScale(0, dataMax * 1.05, compact ? 3 : 4);
    const minY = scale.min;
    const maxY = scale.max;

    const xPos = (t) => margin.left + (maxX === minX ? plotW / 2 : ((t - minX) / (maxX - minX)) * plotW);
    const yPos = (v) => margin.top + plotH - ((v - minY) / (maxY - minY)) * plotH;

    const svg = svgEl("svg", {
      viewBox: `0 0 ${width} ${height}`,
      width, height,
      class: "chart-svg",
      role: "img",
      style: "display:block;",
    });
    const ariaLabel = opts.ariaLabel
      || `Évolution de ${series.map((s) => s.label).join(", ")} du ${formatDateFull(new Date(minX).toISOString())} au ${formatDateFull(new Date(maxX).toISOString())}.`;
    svg.setAttribute("aria-label", ariaLabel);
    svg.appendChild(textEl("title", {}, ariaLabel));

    // Gridlines + Y ticks
    scale.ticks.forEach((tick) => {
      const y = yPos(tick);
      svg.appendChild(svgEl("line", {
        x1: margin.left, x2: width - margin.right, y1: y, y2: y,
        class: tick === 0 ? "baseline" : "gridline",
      }));
      svg.appendChild(textEl("text", {
        x: margin.left - 6, y: y + 3.5, "text-anchor": "end", class: "axis-label",
      }, formatCompact(tick)));
    });

    // X ticks on month boundaries, thinned to the available width.
    const maxTicks = Math.max(2, Math.floor(plotW / (compact ? 46 : 62)));
    const ticks = monthTicks(minX, maxX, maxTicks);
    ticks.forEach((t, i) => {
      const d = new Date(t);
      const withYear = i === 0 || d.getUTCMonth() === 0;
      svg.appendChild(svgEl("line", {
        x1: xPos(t), x2: xPos(t), y1: margin.top, y2: margin.top + plotH, class: "gridline-x",
      }));
      svg.appendChild(textEl("text", {
        x: xPos(t), y: height - 6, "text-anchor": "middle", class: "axis-label",
      }, formatMonthTick(t, withYear)));
    });

    // Series
    const endLabelSlots = [];
    series.forEach((s) => {
      const valid = s.points.filter((p) => p.y !== null && p.y !== undefined);
      if (valid.length === 0) return;

      // Solid path across consecutive readings; dashed bridge across gaps.
      let solid = "";
      const bridges = [];
      let previous = null;
      let broken = true;
      s.points.forEach((p) => {
        if (p.y === null || p.y === undefined) { broken = true; return; }
        const x = xPos(new Date(p.x).getTime());
        const y = yPos(p.y);
        if (broken && previous) bridges.push({ x1: previous.x, y1: previous.y, x2: x, y2: y });
        solid += (broken ? `M ${x.toFixed(1)},${y.toFixed(1)} ` : `L ${x.toFixed(1)},${y.toFixed(1)} `);
        previous = { x, y };
        broken = false;
      });

      bridges.forEach((b) => svg.appendChild(svgEl("line", {
        x1: b.x1, y1: b.y1, x2: b.x2, y2: b.y2,
        stroke: s.color, "stroke-width": 1.6, "stroke-dasharray": "3 3", opacity: 0.55,
      })));

      svg.appendChild(svgEl("path", {
        d: solid, fill: "none", stroke: s.color, "stroke-width": 2,
        "stroke-linejoin": "round", "stroke-linecap": "round",
      }));

      // Real-reading markers: the cadence is irregular, so show where the
      // measurements actually are instead of implying a continuous line.
      if (valid.length <= 90) {
        valid.forEach((p) => svg.appendChild(svgEl("circle", {
          cx: xPos(new Date(p.x).getTime()), cy: yPos(p.y), r: 1.9, fill: s.color, opacity: 0.75,
        })));
      }

      const last = valid[valid.length - 1];
      const lx = xPos(new Date(last.x).getTime());
      const ly = yPos(last.y);
      svg.appendChild(svgEl("circle", {
        cx: lx, cy: ly, r: 4, fill: s.color, stroke: "var(--surface-1)", "stroke-width": 2,
      }));
      endLabelSlots.push({ id: s.id, label: s.shortLabel || s.label, color: s.color, x: lx, y: ly, origY: ly });
    });

    // Direct end labels, confined to the reserved right margin band.
    if (opts.directLabels !== false && !compact) {
      endLabelSlots.sort((a, b) => a.y - b.y);
      const minGap = 13;
      for (let i = 1; i < endLabelSlots.length; i++) {
        if (endLabelSlots[i].y - endLabelSlots[i - 1].y < minGap) {
          endLabelSlots[i].y = endLabelSlots[i - 1].y + minGap;
        }
      }
      const labelX = width - margin.right + 6;
      endLabelSlots.forEach((slot) => {
        if (Math.abs(slot.x - labelX) > 3 || Math.abs(slot.y - slot.origY) > 3) {
          svg.appendChild(svgEl("line", {
            x1: slot.x, y1: slot.origY, x2: labelX - 4, y2: slot.y,
            stroke: slot.color, "stroke-width": 1, opacity: 0.35,
          }));
        }
        svg.appendChild(textEl("text", {
          x: labelX, y: slot.y + 3, class: "direct-label", fill: slot.color,
        }, slot.label));
      });
    }

    // Hover / touch layer: crosshair + unified tooltip.
    const crosshair = svgEl("line", {
      x1: 0, x2: 0, y1: margin.top, y2: margin.top + plotH, class: "crosshair", style: "opacity:0;",
    });
    svg.appendChild(crosshair);
    const hitRect = svgEl("rect", {
      x: margin.left, y: margin.top, width: plotW, height: plotH,
      fill: "transparent", style: "cursor:crosshair;touch-action:pan-y;",
    });
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

      series.forEach((s) => {
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
      const ttWidth = tooltip.offsetWidth || 170;
      let left = (xPos(closestT) / width) * rect.width + 12;
      if (left + ttWidth > rect.width) left = (xPos(closestT) / width) * rect.width - ttWidth - 12;
      tooltip.style.left = `${Math.max(0, left)}px`;
      tooltip.style.top = "4px";
    }

    function hideTooltip() {
      tooltip.classList.remove("is-visible");
      crosshair.style.opacity = "0";
    }

    hitRect.addEventListener("pointerdown", showTooltip);
    hitRect.addEventListener("pointermove", showTooltip);
    hitRect.addEventListener("pointerleave", hideTooltip);
    hitRect.addEventListener("pointercancel", hideTooltip);

    container.appendChild(shell);

    if (opts.showLegend !== false && series.length > 1) {
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
  });
}

/* Touch has no "pointerleave": one global listener dismisses any open
 * tooltip when the next tap lands outside its chart. Registered once, so
 * re-rendering charts on resize never stacks listeners. */
document.addEventListener("pointerdown", (evt) => {
  document.querySelectorAll(".tooltip.is-visible").forEach((tooltip) => {
    const shell = tooltip.closest(".chart-shell");
    if (shell && shell.contains(evt.target)) return;
    tooltip.classList.remove("is-visible");
    const crosshair = shell && shell.querySelector(".crosshair");
    if (crosshair) crosshair.style.opacity = "0";
  });
});

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
    th.scope = "col";
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
    toggleBtn.setAttribute("aria-pressed", String(!showingTable));
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
    container.appendChild(emptyState("Aucune collecte exploitable enregistrée."));
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
    const tick = document.createElement("button");
    tick.type = "button";
    tick.className = "run-tick";
    tick.style.setProperty("--tick-color", CATEGORY_COLOR[run.category] || CATEGORY_COLOR.unknown);
    tick.setAttribute("aria-label",
      `${formatDateTimeFull(run.started_at)} — ${CATEGORY_LABEL_FR[run.category] || run.category}`);

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
      const ttWidth = tooltip.offsetWidth || 170;
      let left = tickRect.left - shellRect.left - ttWidth / 2;
      left = Math.max(0, Math.min(left, shellRect.width - ttWidth));
      tooltip.style.left = `${left}px`;
      tooltip.style.top = "-4px";
    };
    const hide = () => tooltip.classList.remove("is-visible");

    tick.addEventListener("pointerenter", show);
    tick.addEventListener("focus", show);
    tick.addEventListener("click", show);
    tick.addEventListener("pointerleave", hide);
    tick.addEventListener("blur", hide);

    strip.appendChild(tick);
  });

  shell.appendChild(strip);
  container.appendChild(shell);
  strip.scrollLeft = strip.scrollWidth;
}
