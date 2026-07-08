"""
Sugeneruoja INTERAKTYVIĄ (varnelėmis įjungiama/išjungiama) laiko eilutės ir sklaidos
grafiko versiją tam pačiam "besikeičiančių debesų" periodui, kurį naudoja
reports/generate_static_charts.py. Skirta TIK peržiūrai/tyrinėjimui naršyklėje -
statiniai PNG (reports/figures/) lieka faktinis darbo priedas, nes tam reikalauta
NE interaktyvių paveikslėlių.
"""

import json

from reports.generate_static_charts import PERIOD_END, PERIOD_START, PLANT_ID, get_period_predictions

OUTPUT_PATH = "reports/interaktyvus_grafikas.html"


def generate() -> None:
    period = get_period_predictions()
    data = {
        "plantId": PLANT_ID,
        "periodStart": PERIOD_START,
        "periodEnd": PERIOD_END[:10],
        "timestamps": period["timestamp"].dt.strftime("%Y-%m-%d %H:%M").tolist(),
        "actual": period["actual_power"].tolist(),
        "lr": period["lr_predicted"].tolist(),
        "rf": period["rf_predicted"].tolist(),
    }
    html = _HTML_TEMPLATE.replace("__DATA__", json.dumps(data, ensure_ascii=False))
    with open(OUTPUT_PATH, "w", encoding="utf-8") as file:
        file.write(html)
    print(f"Interaktyvus grafikas išsaugotas: {OUTPUT_PATH}")


_HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="lt">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Interaktyvus grafikas - LR vs RF</title>
<style>
  :root {
    --surface-1: #fcfcfb; --page-plane: #f9f9f7; --text-primary: #0b0b0b;
    --text-secondary: #52514e; --text-muted: #898781; --gridline: #e1e0d9;
    --baseline: #c3c2b7; --border: rgba(11,11,11,0.10);
    --series-actual: #0b0b0b; --series-lr: #2a78d6; --series-rf: #e34948;
  }
  @media (prefers-color-scheme: dark) {
    :root {
      --surface-1: #1a1a19; --page-plane: #0d0d0d; --text-primary: #ffffff;
      --text-secondary: #c3c2b7; --text-muted: #898781; --gridline: #2c2c2a;
      --baseline: #383835; --border: rgba(255,255,255,0.10);
      --series-actual: #ffffff; --series-lr: #3987e5; --series-rf: #e66767;
    }
  }
  :root[data-theme="dark"] {
    --surface-1: #1a1a19; --page-plane: #0d0d0d; --text-primary: #ffffff;
    --text-secondary: #c3c2b7; --text-muted: #898781; --gridline: #2c2c2a;
    --baseline: #383835; --border: rgba(255,255,255,0.10);
    --series-actual: #ffffff; --series-lr: #3987e5; --series-rf: #e66767;
  }
  :root[data-theme="light"] {
    --surface-1: #fcfcfb; --page-plane: #f9f9f7; --text-primary: #0b0b0b;
    --text-secondary: #52514e; --text-muted: #898781; --gridline: #e1e0d9;
    --baseline: #c3c2b7; --border: rgba(11,11,11,0.10);
    --series-actual: #0b0b0b; --series-lr: #2a78d6; --series-rf: #e34948;
  }
  * { box-sizing: border-box; }
  body { margin: 0; background: var(--page-plane); color: var(--text-primary);
    font-family: system-ui, -apple-system, "Segoe UI", sans-serif; }
  .root { max-width: 1180px; margin: 0 auto; padding: 32px 20px 48px; }
  h1 { font-size: 20px; font-weight: 600; margin: 0 0 6px; }
  .subtitle { color: var(--text-secondary); font-size: 14px; margin: 0 0 20px;
    max-width: 80ch; line-height: 1.5; }
  .panel { background: var(--surface-1); border: 1px solid var(--border);
    border-radius: 10px; padding: 18px 20px; margin-bottom: 24px; }
  .panel h2 { font-size: 14px; font-weight: 600; margin: 0 0 12px; }
  .controls { display: flex; flex-wrap: wrap; gap: 18px; margin-bottom: 14px;
    font-size: 13.5px; color: var(--text-secondary); }
  .controls label { display: flex; align-items: center; gap: 7px; cursor: pointer;
    user-select: none; }
  .controls input[type="checkbox"] { width: 15px; height: 15px; cursor: pointer;
    accent-color: var(--text-secondary); }
  .swatch { width: 12px; height: 12px; border-radius: 3px; flex: none; }
  svg text { font-family: system-ui, -apple-system, "Segoe UI", sans-serif; }
  .axis-label { fill: var(--text-muted); font-size: 11px; }
  .gridline { stroke: var(--gridline); stroke-width: 1; }
  .baseline-line { stroke: var(--baseline); stroke-width: 1; }
  .series-hidden { display: none; }
  .tip { font-size: 12px; color: var(--text-muted); margin-top: 8px; }
</style>
</head>
<body>
<div class="root">
  <h1>Interaktyvus grafikas (tik peržiūrai) - LR vs RF</h1>
  <p class="subtitle">
    Ta pati Elektrinė ir periodas kaip statiniuose PNG (<code>reports/figures/</code>),
    bet čia galite pele užvesti ant taškų/linijų ir varnelėmis įjungti/išjungti
    kiekvieną seriją, kad grafikas nebūtų per tankus. <b>Šis puslapis - tik tyrinėjimui;
    faktiniam darbui naudokite statinius PNG failus.</b>
  </p>

  <div class="panel">
    <h2>1. Laiko eilutė</h2>
    <div class="controls" id="timeseries-controls"></div>
    <div id="timeseries-chart"></div>
  </div>

  <div class="panel">
    <h2>2. Sklaidos grafikas</h2>
    <div class="controls" id="scatter-controls"></div>
    <div id="scatter-chart"></div>
  </div>
</div>

<script>
  const data = __DATA__;

  const SERIES = [
    { key: "actual", label: "Reali gamyba", color: "var(--series-actual)" },
    { key: "lr", label: "Linijinė regresija", color: "var(--series-lr)" },
    { key: "rf", label: "Random Forest", color: "var(--series-rf)" },
  ];

  function niceMax(value) {
    const magnitude = Math.pow(10, Math.floor(Math.log10(value)));
    const normalized = value / magnitude;
    let step;
    if (normalized <= 1) step = 1;
    else if (normalized <= 2) step = 2;
    else if (normalized <= 5) step = 5;
    else step = 10;
    return step * magnitude;
  }

  function formatW(value) {
    return value.toLocaleString("lt-LT", { maximumFractionDigits: 0 });
  }

  function buildControls(containerId, seriesList, onToggle) {
    const container = document.getElementById(containerId);
    seriesList.forEach((series) => {
      const label = document.createElement("label");
      label.innerHTML = `
        <input type="checkbox" checked data-series="${series.key}">
        <span class="swatch" style="background:${series.color};"></span>
        ${series.label}
      `;
      label.querySelector("input").addEventListener("change", (event) => {
        onToggle(series.key, event.target.checked);
      });
      container.appendChild(label);
    });
  }

  // ---------- Laiko eilutė ----------
  function renderTimeSeries() {
    const width = 1100, height = 420;
    const margin = { left: 60, right: 20, top: 20, bottom: 50 };
    const plotW = width - margin.left - margin.right;
    const plotH = height - margin.top - margin.bottom;
    const n = data.timestamps.length;

    const maxVal = niceMax(Math.max(...data.actual, ...data.lr, ...data.rf) * 1.1);
    const scaleX = (i) => margin.left + (i / (n - 1)) * plotW;
    const scaleY = (v) => margin.top + plotH - (v / maxVal) * plotH;

    let svg = `<svg viewBox="0 0 ${width} ${height}" width="100%" height="${height}" role="img" aria-label="Laiko eilutė">`;

    [0, 0.25, 0.5, 0.75, 1].forEach((f) => {
      const y = margin.top + plotH - plotH * f;
      svg += `<line class="gridline" x1="${margin.left}" x2="${width - margin.right}" y1="${y}" y2="${y}" />`;
      svg += `<text class="axis-label" x="${margin.left - 8}" y="${y + 4}" text-anchor="end">${formatW(maxVal * f)}</text>`;
    });

    const labelStep = Math.max(1, Math.floor(n / 10));
    data.timestamps.forEach((ts, i) => {
      if (i % labelStep !== 0 && i !== n - 1) return;
      svg += `<text class="axis-label" x="${scaleX(i)}" y="${height - margin.bottom + 18}" text-anchor="middle">${ts.slice(5, 16)}</text>`;
    });

    SERIES.forEach((series) => {
      const values = data[series.key];
      const points = values.map((v, i) => [scaleX(i), scaleY(v)]);
      const path = points.map((p, i) => (i === 0 ? "M" : "L") + p[0].toFixed(1) + "," + p[1].toFixed(1)).join(" ");
      const strokeWidth = series.key === "actual" ? 2.4 : 1.6;
      svg += `<g class="series-group" data-series="${series.key}">
        <path d="${path}" fill="none" stroke="${series.color}" stroke-width="${strokeWidth}" stroke-linejoin="round" />
      </g>`;
    });

    svg += `</svg>`;
    document.getElementById("timeseries-chart").innerHTML = svg;
  }

  // ---------- Sklaidos grafikas ----------
  function renderScatter() {
    const width = 640, height = 640;
    const margin = { left: 60, right: 20, top: 20, bottom: 50 };
    const plotW = width - margin.left - margin.right;
    const plotH = height - margin.top - margin.bottom;

    const maxVal = niceMax(Math.max(...data.actual, ...data.lr, ...data.rf) * 1.05);
    const scaleX = (v) => margin.left + (v / maxVal) * plotW;
    const scaleY = (v) => margin.top + plotH - (v / maxVal) * plotH;

    let svg = `<svg viewBox="0 0 ${width} ${height}" width="100%" height="${height}" style="max-width:640px;" role="img" aria-label="Sklaidos grafikas">`;

    [0, 0.25, 0.5, 0.75, 1].forEach((f) => {
      const y = margin.top + plotH - plotH * f;
      svg += `<line class="gridline" x1="${margin.left}" x2="${width - margin.right}" y1="${y}" y2="${y}" />`;
      svg += `<text class="axis-label" x="${margin.left - 8}" y="${y + 4}" text-anchor="end">${formatW(maxVal * f)}</text>`;
    });

    svg += `<line class="baseline-line" x1="${scaleX(0)}" y1="${scaleY(0)}" x2="${scaleX(maxVal)}" y2="${scaleY(maxVal)}" />`;

    ["lr", "rf"].forEach((key) => {
      const series = SERIES.find((s) => s.key === key);
      let group = `<g class="series-group" data-series="${key}">`;
      data.actual.forEach((actualValue, i) => {
        const predicted = data[key][i];
        group += `<circle cx="${scaleX(actualValue).toFixed(1)}" cy="${scaleY(predicted).toFixed(1)}" r="4" fill="${series.color}" opacity="0.6" />`;
      });
      group += `</g>`;
      svg += group;
    });

    svg += `<text class="axis-label" x="${margin.left + plotW / 2}" y="${height - 8}" text-anchor="middle">Reali galia (W)</text>`;
    svg += `</svg>`;
    document.getElementById("scatter-chart").innerHTML = svg;
  }

  function toggleSeries(chartContainerId, key, visible) {
    const group = document.querySelector(`#${chartContainerId} [data-series="${key}"]`);
    if (group) group.classList.toggle("series-hidden", !visible);
  }

  renderTimeSeries();
  buildControls("timeseries-controls", SERIES, (key, visible) => toggleSeries("timeseries-chart", key, visible));

  renderScatter();
  buildControls("scatter-controls", SERIES.filter((s) => s.key !== "actual"),
    (key, visible) => toggleSeries("scatter-chart", key, visible));
</script>
</body>
</html>
"""


if __name__ == "__main__":
    generate()
