"""
Generuoja HTML ataskaitą su baseline ML modelio(-ių) rezultatų vizualizacija.

Priima kiekvieno modelio testavimo aibės prognozes ir sugeneruoja
reports/kaggle_baseline_modeliai.html su: metrikų kortelėmis, prognozė-vs-realybė
sklaidos diagrama, laiko eilutės grafiku (reali vs prognozuota galia) ir
koeficientų stulpeline diagrama (jei modelis linijinis - t.y. turi 'coefficients').

`results` parametras - sąrašas, kad ateityje būtų lengva pridėti daugiau modelių
(pvz. Random Forest) tam pačiam palyginimui, nekeičiant šablono.
"""

import json


def generate_report(results: list, output_path: str) -> None:
    html = _HTML_TEMPLATE.replace(
        "__RESULTS_DATA__", json.dumps(results, ensure_ascii=False)
    )
    with open(output_path, "w", encoding="utf-8") as file:
        file.write(html)


_HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="lt">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Baseline ML modelio rezultatai</title>
<style>
  .viz-root {
    --surface-1:      #fcfcfb;
    --page-plane:     #f9f9f7;
    --text-primary:   #0b0b0b;
    --text-secondary: #52514e;
    --text-muted:     #898781;
    --gridline:       #e1e0d9;
    --baseline:       #c3c2b7;
    --border:         rgba(11,11,11,0.10);
    --series-1:       #2a78d6; /* reali reikšmė / teigiamas koeficientas */
    --series-2:       #1baf7a; /* prognozė */
    --series-neg:      #e34948; /* neigiamas koeficientas (diverging red pole) */
  }
  @media (prefers-color-scheme: dark) {
    .viz-root {
      --surface-1: #1a1a19; --page-plane: #0d0d0d; --text-primary: #ffffff;
      --text-secondary: #c3c2b7; --text-muted: #898781; --gridline: #2c2c2a;
      --baseline: #383835; --border: rgba(255,255,255,0.10);
      --series-1: #3987e5; --series-2: #199e70; --series-neg: #e66767;
    }
  }
  :root[data-theme="dark"] .viz-root {
    --surface-1: #1a1a19; --page-plane: #0d0d0d; --text-primary: #ffffff;
    --text-secondary: #c3c2b7; --text-muted: #898781; --gridline: #2c2c2a;
    --baseline: #383835; --border: rgba(255,255,255,0.10);
    --series-1: #3987e5; --series-2: #199e70; --series-neg: #e66767;
  }
  :root[data-theme="light"] .viz-root {
    --surface-1: #fcfcfb; --page-plane: #f9f9f7; --text-primary: #0b0b0b;
    --text-secondary: #52514e; --text-muted: #898781; --gridline: #e1e0d9;
    --baseline: #c3c2b7; --border: rgba(11,11,11,0.10);
    --series-1: #2a78d6; --series-2: #1baf7a; --series-neg: #e34948;
  }

  * { box-sizing: border-box; }
  body { margin: 0; background: var(--page-plane); color: var(--text-primary);
    font-family: system-ui, -apple-system, "Segoe UI", sans-serif; }
  .viz-root { max-width: 1000px; margin: 0 auto; padding: 32px 20px 48px; }

  h1 { font-size: 20px; font-weight: 600; margin: 0 0 6px; }
  h2.section-title { font-size: 15px; font-weight: 600; margin: 28px 0 4px; }
  .subtitle { color: var(--text-secondary); font-size: 14px; margin: 0 0 20px;
    max-width: 70ch; line-height: 1.5; }

  table.compare { border-collapse: collapse; width: 100%; margin: 0 0 8px; font-size: 13.5px; }
  table.compare caption { text-align: left; font-size: 14px; font-weight: 600;
    margin-bottom: 8px; color: var(--text-primary); }
  table.compare th, table.compare td { text-align: right; padding: 9px 14px;
    border-bottom: 1px solid var(--gridline); font-variant-numeric: tabular-nums; }
  table.compare th:first-child, table.compare td:first-child { text-align: left;
    font-variant-numeric: normal; }
  table.compare th { color: var(--text-muted); font-weight: 500; font-size: 12px; }
  table.compare td.best { color: var(--series-2); font-weight: 700; }

  .stat-row { display: flex; gap: 16px; flex-wrap: wrap; margin-bottom: 8px; }
  .stat-tile { background: var(--surface-1); border: 1px solid var(--border);
    border-radius: 10px; padding: 14px 18px; flex: 1 1 140px; }
  .stat-tile .label { font-size: 12px; color: var(--text-muted); margin-bottom: 4px; }
  .stat-tile .value { font-size: 22px; font-weight: 600; color: var(--text-primary); }

  .layout { display: flex; gap: 28px; align-items: flex-start; flex-wrap: wrap; }
  .main-content { flex: 3 1 480px; min-width: 0; }
  .sidebar { flex: 1 1 260px; max-width: 300px; display: flex; flex-direction: column; gap: 14px; }
  .info-card { background: var(--surface-1); border: 1px solid var(--border);
    border-radius: 10px; padding: 14px 16px; }
  .info-card h3 { font-size: 13px; font-weight: 600; margin: 0 0 6px; }
  .info-card p { font-size: 12.5px; color: var(--text-secondary); line-height: 1.55; margin: 0; }

  .panels { display: flex; flex-wrap: wrap; gap: 20px; }
  .panel { background: var(--surface-1); border: 1px solid var(--border);
    border-radius: 10px; padding: 16px 16px 8px; flex: 1 1 400px; min-width: 300px;
    overflow-x: auto; }
  .panel h3 { font-size: 14px; font-weight: 600; margin: 0 0 8px; }

  svg text { font-family: system-ui, -apple-system, "Segoe UI", sans-serif; }
  .axis-label { fill: var(--text-muted); font-size: 11px; }
  .gridline { stroke: var(--gridline); stroke-width: 1; }
  .baseline-line { stroke: var(--baseline); stroke-width: 1; }

  .legend { display: flex; flex-wrap: wrap; gap: 16px; font-size: 12.5px;
    color: var(--text-secondary); margin: 8px 0 16px; }
  .legend-item { display: flex; align-items: center; gap: 6px; }
  .legend-swatch { width: 10px; height: 10px; border-radius: 2px; flex: none; }

  .note { margin-top: 20px; font-size: 12.5px; color: var(--text-muted);
    line-height: 1.6; max-width: 76ch; }
  .note b { color: var(--text-secondary); }
</style>
</head>
<body>

<div class="viz-root">
  <div class="layout">
    <div class="main-content">
      <h1>Baseline ML modelio rezultatai (Kaggle duomenys)</h1>
      <p class="subtitle">
        Modelis prognozuoja <code>AC_POWER</code> (reali, išmatuota gamyba) iš oro sąlygų
        požymių. Testavimo aibė - chronologiškai VĖLIAUSI 20% duomenų, kurių modelis
        nematė treniruodamasis.
      </p>
      <div id="comparison"></div>
      <div id="content"></div>
    </div>

    <div class="sidebar">
      <div class="info-card">
        <h3>Kas yra MAE / RMSE / R²?</h3>
        <p><b>MAE</b> - vidutinis prognozės nuokrypis nuo realybės (vatais), be ženklo.
        Lengviausia suprasti: "vidutiniškai suklystame per tiek W".</p>
        <p style="margin-top:8px;"><b>RMSE</b> - panašus į MAE, bet klaidas prieš
        vidurkinant pakelia kvadratu - todėl kelios DIDELĖS klaidos jį padidina
        labiau nei daug mažų. Jei RMSE gerokai didesnis už MAE, yra pavienių
        stambių klaidų.</p>
        <p style="margin-top:8px;"><b>R²</b> - kokia dalis (0-1) realios galios
        svyravimų paaiškinama modeliu. 1,0 = tobulas modelis, 0 = ne geresnis už
        paprastą vidurkį.</p>
      </div>
      <div class="info-card">
        <h3>Prognozė vs realybė</h3>
        <p>Kiekvienas taškas - viena testavimo eilutė. Kuo arčiau įstrižainės (reali =
        prognozė), tuo tikslesnė prognozė. Taškai virš linijos - modelis pervertino,
        po linija - nuvertino.</p>
      </div>
      <div class="info-card">
        <h3>Laiko eilutė</h3>
        <p>Reali ir prognozuota galia per testavimo periodą. Padeda pamatyti, ar
        klaidos susijusios su konkrečiu laiku (pvz. debesuotomis dienomis), ar
        pasiskirsčiusios tolygiai.</p>
      </div>
      <div class="info-card">
        <h3>Koeficientai / požymių svarba</h3>
        <p>Linijinei regresijai - kiek keičiasi galia (W), pakitus požymiui 1 vienetu
        (mėlyna - teigiamas ryšys, raudona - neigiamas). Random Forest neturi
        koeficientų (medžiai, ne formulė) - vietoj to rodoma, kiek % modelis
        kiekvieną požymį naudojo priimdamas sprendimus.</p>
      </div>
      <div class="info-card">
        <h3>Svarbu</h3>
        <p>Duomenys iš dviejų Indijos elektrinių (Kaggle) - naudojami kaip laikinas
        REALUS target'as, kol laukiama Lietuvos duomenų. Šio modelio tikslumas
        specifinis Indijos klimatui, tiesiogiai Lietuvai netaikytinas - tikslas yra
        patikrinti vamzdyną, ne gauti galutinį modelį.</p>
      </div>
    </div>
  </div>
</div>

<script>
  const results = __RESULTS_DATA__;

  function formatW(value) {
    return value.toLocaleString("lt-LT", { maximumFractionDigits: 0 });
  }

  function niceMax(value) {
    if (value <= 0) return 1;
    const magnitude = Math.pow(10, Math.floor(Math.log10(value)));
    const normalized = value / magnitude;
    let step;
    if (normalized <= 1) step = 1;
    else if (normalized <= 2) step = 2;
    else if (normalized <= 5) step = 5;
    else step = 10;
    return step * magnitude;
  }

  function renderComparisonTable(results) {
    if (results.length < 2) return "";

    const bestMae = Math.min(...results.map((r) => r.metrics.mae));
    const bestRmse = Math.min(...results.map((r) => r.metrics.rmse));
    const bestR2 = Math.max(...results.map((r) => r.metrics.r2));

    const rows = results.map((r) => `
      <tr>
        <td>${r.name}</td>
        <td class="${r.metrics.mae === bestMae ? "best" : ""}">${formatW(r.metrics.mae)} W</td>
        <td class="${r.metrics.rmse === bestRmse ? "best" : ""}">${formatW(r.metrics.rmse)} W</td>
        <td class="${r.metrics.r2 === bestR2 ? "best" : ""}">${r.metrics.r2.toFixed(4)}</td>
      </tr>`).join("");

    return `
      <table class="compare">
        <caption>Modelių palyginimas (testavimo aibėje) - žalia = geresnis rezultatas</caption>
        <thead><tr><th>Modelis</th><th>MAE</th><th>RMSE</th><th>R²</th></tr></thead>
        <tbody>${rows}</tbody>
      </table>`;
  }

  function renderStatTiles(result) {
    const m = result.metrics;
    return `
      <div class="stat-row">
        <div class="stat-tile"><div class="label">MAE</div><div class="value">${formatW(m.mae)} W</div></div>
        <div class="stat-tile"><div class="label">RMSE</div><div class="value">${formatW(m.rmse)} W</div></div>
        <div class="stat-tile"><div class="label">R²</div><div class="value">${m.r2.toFixed(3)}</div></div>
      </div>`;
  }

  function renderScatter(result) {
    const width = 460, height = 380;
    const margin = { left: 55, right: 20, top: 20, bottom: 40 };
    const plotW = width - margin.left - margin.right;
    const plotH = height - margin.top - margin.bottom;

    const allValues = result.actual.concat(result.predicted);
    const maxVal = niceMax(Math.max(...allValues) * 1.05);

    const scaleX = (v) => margin.left + (v / maxVal) * plotW;
    const scaleY = (v) => margin.top + plotH - (v / maxVal) * plotH;

    let svg = `<svg viewBox="0 0 ${width} ${height}" width="100%" height="${height}" role="img" aria-label="Prognozė vs realybė">`;

    [0, 0.5, 1].forEach((f) => {
      const y = margin.top + plotH - plotH * f;
      const x = margin.left + plotW * f;
      svg += `<line class="gridline" x1="${margin.left}" x2="${width - margin.right}" y1="${y}" y2="${y}" />`;
      svg += `<text class="axis-label" x="${margin.left - 8}" y="${y + 4}" text-anchor="end">${formatW(maxVal * f)}</text>`;
      svg += `<text class="axis-label" x="${x}" y="${height - margin.bottom + 18}" text-anchor="middle">${formatW(maxVal * f)}</text>`;
    });

    // y = x atskaitos linija
    svg += `<line class="baseline-line" x1="${scaleX(0)}" y1="${scaleY(0)}" x2="${scaleX(maxVal)}" y2="${scaleY(maxVal)}" />`;

    result.actual.forEach((actual, i) => {
      const predicted = result.predicted[i];
      svg += `<circle cx="${scaleX(actual).toFixed(1)}" cy="${scaleY(predicted).toFixed(1)}" r="2.5" fill="var(--series-1)" opacity="0.45" />`;
    });

    svg += `<text class="axis-label" x="${margin.left + plotW / 2}" y="${height - 6}" text-anchor="middle">Reali galia (W)</text>`;
    svg += `</svg>`;
    return svg;
  }

  function renderTimeSeries(result) {
    const width = 460, height = 380;
    const margin = { left: 55, right: 16, top: 20, bottom: 40 };
    const plotW = width - margin.left - margin.right;
    const plotH = height - margin.top - margin.bottom;

    const n = result.actual.length;
    const maxVal = niceMax(Math.max(...result.actual, ...result.predicted) * 1.1);

    const scaleX = (i) => margin.left + (i / (n - 1)) * plotW;
    const scaleY = (v) => margin.top + plotH - (v / maxVal) * plotH;

    let svg = `<svg viewBox="0 0 ${width} ${height}" width="100%" height="${height}" role="img" aria-label="Reali vs prognozuota galia laike">`;

    [0, 0.5, 1].forEach((f) => {
      const y = margin.top + plotH - plotH * f;
      svg += `<line class="gridline" x1="${margin.left}" x2="${width - margin.right}" y1="${y}" y2="${y}" />`;
      svg += `<text class="axis-label" x="${margin.left - 8}" y="${y + 4}" text-anchor="end">${formatW(maxVal * f)}</text>`;
    });

    function pathFor(values) {
      return values.map((v, i) => (i === 0 ? "M" : "L") + scaleX(i).toFixed(1) + "," + scaleY(v).toFixed(1)).join(" ");
    }

    svg += `<path d="${pathFor(result.actual)}" fill="none" stroke="var(--series-1)" stroke-width="1.5" stroke-linejoin="round" />`;
    svg += `<path d="${pathFor(result.predicted)}" fill="none" stroke="var(--series-2)" stroke-width="1.5" stroke-linejoin="round" opacity="0.85" />`;

    const labelStep = Math.max(1, Math.floor(n / 5));
    result.dates.forEach((date, i) => {
      if (i % labelStep !== 0 && i !== n - 1) return;
      svg += `<text class="axis-label" x="${scaleX(i)}" y="${height - margin.bottom + 18}" text-anchor="middle">${date.slice(5, 10)}</text>`;
    });

    svg += `</svg>`;
    return svg;
  }

  function renderCoefficients(result) {
    if (!result.coefficients) return "";
    const width = 460;
    const rowHeight = 34;
    const margin = { left: 150, right: 60, top: 10, bottom: 10 };
    const plotW = width - margin.left - margin.right;
    const height = margin.top + margin.bottom + rowHeight * result.coefficients.length;

    const maxAbs = niceMax(Math.max(...result.coefficients.map((c) => Math.abs(c.value))) * 1.15);
    const centerX = margin.left + plotW / 2;
    const scale = (v) => (v / maxAbs) * (plotW / 2);

    let svg = `<svg viewBox="0 0 ${width} ${height}" width="100%" height="${height}" role="img" aria-label="Modelio koeficientai">`;
    svg += `<line class="baseline-line" x1="${centerX}" x2="${centerX}" y1="${margin.top}" y2="${height - margin.bottom}" />`;

    result.coefficients.forEach((c, i) => {
      const y = margin.top + i * rowHeight + rowHeight / 2;
      const barLen = scale(c.value);
      const barX = c.value >= 0 ? centerX : centerX + barLen;
      const color = c.value >= 0 ? "var(--series-1)" : "var(--series-neg)";
      svg += `<text class="axis-label" x="${margin.left - 10}" y="${y + 4}" text-anchor="end">${c.name}</text>`;
      svg += `<rect x="${barX.toFixed(1)}" y="${y - 9}" width="${Math.abs(barLen).toFixed(1)}" height="18" rx="3" fill="${color}" />`;
      svg += `<text class="axis-label" x="${(centerX + barLen + (c.value >= 0 ? 6 : -6)).toFixed(1)}" y="${y + 4}" text-anchor="${c.value >= 0 ? "start" : "end"}">${formatW(c.value)}</text>`;
    });

    svg += `</svg>`;
    return svg;
  }

  function renderFeatureImportances(result) {
    if (!result.feature_importances) return "";
    const sorted = [...result.feature_importances].sort((a, b) => b.value - a.value);

    const width = 460;
    const rowHeight = 34;
    const margin = { left: 150, right: 50, top: 10, bottom: 10 };
    const plotW = width - margin.left - margin.right;
    const height = margin.top + margin.bottom + rowHeight * sorted.length;

    const maxVal = niceMax(Math.max(...sorted.map((f) => f.value)) * 1.15);
    const scale = (v) => (v / maxVal) * plotW;

    let svg = `<svg viewBox="0 0 ${width} ${height}" width="100%" height="${height}" role="img" aria-label="Požymių svarba">`;

    sorted.forEach((f, i) => {
      const y = margin.top + i * rowHeight + rowHeight / 2;
      const barLen = scale(f.value);
      svg += `<text class="axis-label" x="${margin.left - 10}" y="${y + 4}" text-anchor="end">${f.name}</text>`;
      svg += `<rect x="${margin.left}" y="${y - 9}" width="${barLen.toFixed(1)}" height="18" rx="3" fill="var(--series-1)" />`;
      svg += `<text class="axis-label" x="${(margin.left + barLen + 6).toFixed(1)}" y="${y + 4}" text-anchor="start">${(f.value * 100).toFixed(1)}%</text>`;
    });

    svg += `</svg>`;
    return svg;
  }

  document.getElementById("comparison").innerHTML = renderComparisonTable(results);

  const content = document.getElementById("content");
  results.forEach((result) => {
    const section = document.createElement("div");
    section.innerHTML = `
      <h2 class="section-title">${result.name}</h2>
      ${renderStatTiles(result)}
      <div class="legend">
        <div class="legend-item"><span class="legend-swatch" style="background: var(--series-1);"></span>Reali galia</div>
        <div class="legend-item"><span class="legend-swatch" style="background: var(--series-2);"></span>Prognozė</div>
      </div>
      <div class="panels">
        <div class="panel"><h3>Prognozė vs realybė</h3>${renderScatter(result)}</div>
        <div class="panel"><h3>Laiko eilutė (testavimo periodas)</h3>${renderTimeSeries(result)}</div>
      </div>
      ${result.coefficients ? `<div class="panels"><div class="panel" style="flex-basis: 100%;"><h3>Koeficientai</h3>${renderCoefficients(result)}</div></div>` : ""}
      ${result.feature_importances ? `<div class="panels"><div class="panel" style="flex-basis: 100%;"><h3>Požymių svarba</h3>${renderFeatureImportances(result)}</div></div>` : ""}
    `;
    content.appendChild(section);
  });
</script>

</body>
</html>
"""
