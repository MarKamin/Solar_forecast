"""
Generuoja reports/etapas1_palyginimas.html iš SQLite duomenų.

Paleidžiama automatiškai iš main.py po kiekvieno duomenų rinkimo, kad HTML
ataskaita visada atspindėtų naujausią duomenų bazės būklę. Galima paleisti ir
atskirai: `python -m reports.generate_report`.

Naudoja paprastą token'ų pakeitimą (str.replace), ne str.format(), nes HTML/CSS/
JS šablone yra daug riestinių skliaustelių ({}), kuriuos .format() interpretuotų
kaip vietos rezervavimo ženklus.
"""

import json
import sqlite3

from config import PV_SYSTEMS

SOURCE_PVGIS = "pvgis_historinis_vidurkis"
SOURCE_FORECAST_SOLAR = "forecast_solar"
SOURCE_OPEN_METEO = "open_meteo_apskaiciuota"


def _rows_to_dataset(rows: list) -> list:
    """Paverčia SQL eilutes į JS grafikams tinkamą struktūrą, sugrupuotą pagal lokaciją."""
    by_location = {}
    for location_key, location_name, estimate_date, pvgis, open_meteo, forecast in rows:
        if pvgis is None or open_meteo is None or forecast is None:
            continue  # praleidžiam nepilnas eilutes (pvz. jei viena API grąžino klaidą)
        system = PV_SYSTEMS[location_key]
        entry = by_location.setdefault(
            location_key,
            {
                "key": location_key,
                "name": location_name,
                "kwp": f"{system.kwp:g} kWp, {system.system_type}",
                "rows": [],
            },
        )
        entry["rows"].append(
            {
                "date": estimate_date,
                "pvgis": pvgis,
                "openMeteo": open_meteo,
                "forecast": forecast,
            }
        )
    return list(by_location.values())


def fetch_latest_snapshot(connection: sqlite3.Connection) -> list:
    """Naujausio paleidimo (paskutinės dienos) prognozuojamos datos, lokacija po lokacijos."""
    rows = connection.execute(
        """
        SELECT location_key, location_name, estimate_date,
               MAX(CASE WHEN source = ? THEN estimated_kwh END) AS pvgis,
               MAX(CASE WHEN source = ? THEN estimated_kwh END) AS open_meteo,
               MAX(CASE WHEN source = ? THEN estimated_kwh END) AS forecast
        FROM solar_estimates
        WHERE substr(fetched_at, 1, 10) = (SELECT substr(MAX(fetched_at), 1, 10) FROM solar_estimates)
        GROUP BY location_key, location_name, estimate_date
        ORDER BY location_key, estimate_date
        """,
        (SOURCE_PVGIS, SOURCE_OPEN_METEO, SOURCE_FORECAST_SOLAR),
    ).fetchall()
    return _rows_to_dataset(rows)


def fetch_full_history(connection: sqlite3.Connection) -> list:
    """Visa istorija - kiekvienai datai naujausia žinoma reikšmė (jei buvo keli paleidimai/retry)."""
    rows = connection.execute(
        """
        WITH latest AS (
            SELECT location_key, location_name, source, estimate_date, estimated_kwh,
                   ROW_NUMBER() OVER (
                       PARTITION BY location_key, source, estimate_date
                       ORDER BY fetched_at DESC
                   ) AS rn
            FROM solar_estimates
        )
        SELECT location_key, location_name, estimate_date,
               MAX(CASE WHEN source = ? THEN estimated_kwh END) AS pvgis,
               MAX(CASE WHEN source = ? THEN estimated_kwh END) AS open_meteo,
               MAX(CASE WHEN source = ? THEN estimated_kwh END) AS forecast
        FROM latest
        WHERE rn = 1
        GROUP BY location_key, location_name, estimate_date
        ORDER BY location_key, estimate_date
        """,
        (SOURCE_PVGIS, SOURCE_OPEN_METEO, SOURCE_FORECAST_SOLAR),
    ).fetchall()
    return _rows_to_dataset(rows)


def generate_report(connection: sqlite3.Connection, output_path: str) -> None:
    """Sugeneruoja HTML ataskaitą: naujausios dienos stulpeliai + visos istorijos linijos."""
    snapshot_dataset = fetch_latest_snapshot(connection)
    history_dataset = fetch_full_history(connection)

    html = _HTML_TEMPLATE.replace(
        "__SNAPSHOT_DATA__", json.dumps(snapshot_dataset, ensure_ascii=False)
    ).replace("__HISTORY_DATA__", json.dumps(history_dataset, ensure_ascii=False))

    with open(output_path, "w", encoding="utf-8") as file:
        file.write(html)


_HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="lt">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>PVGIS vs Open-Meteo vs Forecast.Solar palyginimas</title>
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
    --series-1:       #2a78d6;
    --series-2:       #1baf7a;
    --series-3:       #eda100;
  }
  @media (prefers-color-scheme: dark) {
    .viz-root {
      --surface-1:      #1a1a19;
      --page-plane:     #0d0d0d;
      --text-primary:   #ffffff;
      --text-secondary: #c3c2b7;
      --text-muted:     #898781;
      --gridline:       #2c2c2a;
      --baseline:       #383835;
      --border:         rgba(255,255,255,0.10);
      --series-1:       #3987e5;
      --series-2:       #199e70;
      --series-3:       #c98500;
    }
  }
  :root[data-theme="dark"] .viz-root {
    --surface-1: #1a1a19; --page-plane: #0d0d0d; --text-primary: #ffffff;
    --text-secondary: #c3c2b7; --text-muted: #898781; --gridline: #2c2c2a;
    --baseline: #383835; --border: rgba(255,255,255,0.10);
    --series-1: #3987e5; --series-2: #199e70; --series-3: #c98500;
  }
  :root[data-theme="light"] .viz-root {
    --surface-1: #fcfcfb; --page-plane: #f9f9f7; --text-primary: #0b0b0b;
    --text-secondary: #52514e; --text-muted: #898781; --gridline: #e1e0d9;
    --baseline: #c3c2b7; --border: rgba(11,11,11,0.10);
    --series-1: #2a78d6; --series-2: #1baf7a; --series-3: #eda100;
  }

  * { box-sizing: border-box; }

  body { margin: 0; background: var(--page-plane); color: var(--text-primary);
    font-family: system-ui, -apple-system, "Segoe UI", sans-serif; }

  .viz-root { max-width: 960px; margin: 0 auto; padding: 32px 20px 48px; }

  h1 { font-size: 20px; font-weight: 600; margin: 0 0 6px; }
  h2.section-title { font-size: 15px; font-weight: 600; margin: 28px 0 4px; }

  .subtitle { color: var(--text-secondary); font-size: 14px; margin: 0 0 24px;
    max-width: 68ch; line-height: 1.5; }

  .legend { display: flex; flex-wrap: wrap; gap: 20px; align-items: center;
    margin-bottom: 20px; font-size: 13px; color: var(--text-secondary); }
  .legend-item { display: flex; align-items: center; gap: 6px; }
  .legend-swatch { width: 10px; height: 10px; border-radius: 2px; flex: none; }

  .panels { display: flex; flex-wrap: wrap; gap: 20px; }
  .panel { background: var(--surface-1); border: 1px solid var(--border);
    border-radius: 10px; padding: 16px 16px 8px; flex: 1 1 340px; min-width: 300px;
    overflow-x: auto; }
  .panel h3 { font-size: 14px; font-weight: 600; margin: 0 0 2px; }
  .panel .panel-sub { font-size: 12px; color: var(--text-muted); margin: 0 0 8px; }

  svg text { font-family: system-ui, -apple-system, "Segoe UI", sans-serif; }
  .axis-label { fill: var(--text-muted); font-size: 11px; }
  .value-label { fill: var(--text-secondary); font-size: 10.5px; font-weight: 600; }
  .gridline { stroke: var(--gridline); stroke-width: 1; }
  .baseline { stroke: var(--baseline); stroke-width: 1; }

  table { border-collapse: collapse; width: 100%; margin-top: 12px; font-size: 13px; }
  caption { text-align: left; font-size: 14px; font-weight: 600; margin-bottom: 8px;
    color: var(--text-primary); }
  th, td { text-align: left; padding: 8px 12px; border-bottom: 1px solid var(--gridline); }
  th { color: var(--text-muted); font-weight: 500; font-size: 12px; }
  td.num, th.num { text-align: right; font-variant-numeric: tabular-nums; }

  .note { margin-top: 20px; font-size: 12.5px; color: var(--text-muted);
    line-height: 1.6; max-width: 74ch; }
  .note b { color: var(--text-secondary); }

  .layout { display: flex; gap: 28px; align-items: flex-start; flex-wrap: wrap; }
  .main-content { flex: 3 1 480px; min-width: 0; }
  .sidebar { flex: 1 1 260px; max-width: 300px; display: flex; flex-direction: column;
    gap: 14px; }
  .info-card { background: var(--surface-1); border: 1px solid var(--border);
    border-radius: 10px; padding: 14px 16px; }
  .info-card h3 { font-size: 13px; font-weight: 600; margin: 0 0 6px; display: flex;
    align-items: center; gap: 7px; }
  .info-card p { font-size: 12.5px; color: var(--text-secondary); line-height: 1.55;
    margin: 0 0 6px; }
  .info-card p:last-child { margin-bottom: 0; }
  .info-card .formula { display: block; font-family: ui-monospace, "SF Mono", Consolas, monospace;
    font-size: 11px; color: var(--text-muted); background: var(--page-plane);
    border: 1px solid var(--border); border-radius: 6px; padding: 6px 8px; line-height: 1.5;
    overflow-x: auto; white-space: pre; }
</style>
</head>
<body>

<div class="viz-root">
  <div class="layout">
    <div class="main-content">
      <h1>Saulės gamybos įvertis: PVGIS vs Open-Meteo vs Forecast.Solar</h1>
      <p class="subtitle">
        Duomenys renkami automatiškai (<code>cron</code> + <code>main.py</code>) ir saugomi
        SQLite lentelėje (<code>data/solar_data.db</code>). Šis puslapis
        sugeneruojamas iš naujo po kiekvieno sėkmingo duomenų rinkimo.
      </p>

      <div class="legend">
        <div class="legend-item">
          <span class="legend-swatch" style="background: var(--series-1);"></span>
          PVGIS istorinis vidurkis (2005-2020, tik baseline)
        </div>
        <div class="legend-item">
          <span class="legend-swatch" style="background: var(--series-3);"></span>
          Open-Meteo apskaičiuota (tos dienos etalonas)
        </div>
        <div class="legend-item">
          <span class="legend-swatch" style="background: var(--series-2);"></span>
          Forecast.Solar prognozė
        </div>
      </div>

      <h2 class="section-title">Naujausia prognozė</h2>
      <div class="panels" id="snapshot-panels"></div>

      <h2 class="section-title">Laiko eilutė (visa istorija)</h2>
      <div class="panels" id="history-panels"></div>

      <table id="data-table">
        <caption>Visi duomenys (naujausia žinoma reikšmė kiekvienai datai)</caption>
        <thead>
          <tr>
            <th>Lokacija</th>
            <th>Data</th>
            <th class="num">PVGIS vid. (kWh)</th>
            <th class="num">Open-Meteo (kWh)</th>
            <th class="num">Forecast.Solar (kWh)</th>
            <th class="num">Progn. paklaida (kWh)</th>
          </tr>
        </thead>
        <tbody></tbody>
      </table>

      <p class="note">
        <b>Pastaba dėl metodologijos:</b> PVGIS stulpelis rodo daugiametį (2005-2020) to
        mėnesio dienos gamybos vidurkį — tai planavimo/baseline atskaitos taškas, NE
        konkrečios dienos etalonas. Open-Meteo stulpelis paverčia tos konkrečios dienos
        radiaciją į apytikslę gamybą (radiacija × kWp × performance ratio 0,80 -
        supaprastintas GHI, ne POA, modelis) ir yra tinkamas etalonas Forecast.Solar
        tikslumui vertinti. <b>„Progn. paklaida"</b> = Forecast.Solar − Open-Meteo (ne
        PVGIS) — tai metodologiškai teisingas palyginimas tai pačiai dienai.
      </p>
    </div>

    <div class="sidebar">
      <div class="info-card">
        <h3><span class="legend-swatch" style="background: var(--series-1);"></span>PVGIS</h3>
        <p>
          Europos Komisijos JRC įrankis. Duoda daugiametį (2005–2020) mėnesio dienos
          gamybos vidurkį pagal palydovinius radiacijos duomenis — tai klimato
          statistika, ne konkrečios dienos prognozė.
        </p>
        <code class="formula">GET re.jrc.ec.europa.eu/api/v5_2/PVcalc
  ?lat, lon, peakpower (kWp),
   angle (tilt), aspect (azimuth),
   loss (14%)
→ E_d: vid. dienos gamyba (kWh)</code>
      </div>

      <div class="info-card">
        <h3><span class="legend-swatch" style="background: var(--series-3);"></span>Open-Meteo</h3>
        <p>
          Nemokamas orų duomenų API. Duoda konkrečios dienos saulės radiaciją, kuri
          čia paverčiama apytiksle gamyba — laikinas "kiek tą dieną realiai turėjo
          pagaminti" etalonas, kol nėra tikrų inverterio duomenų.
        </p>
        <code class="formula">GET api.open-meteo.com/v1/forecast
  ?lat, lon,
   daily=shortwave_radiation_sum

gamyba (kWh) =
  (radiacija MJ/m² ÷ 3,6)
  × kWp × performance_ratio (0,80)</code>
      </div>

      <div class="info-card">
        <h3><span class="legend-swatch" style="background: var(--series-2);"></span>Forecast.Solar</h3>
        <p>
          Nemokamas (be rakto) FV gamybos prognozės API, paremtas orų prognoze.
          Duoda 1–2 dienų gamybos įvertį konkrečiai sistemai. Limitas: 12
          užklausų/val. vienam IP.
        </p>
        <code class="formula">GET api.forecast.solar/estimate/
  {lat}/{lon}/{tilt}/{azimuth}/{kwp}

→ watt_hours_day: prognozuojama
  gamyba kiekvienai dienai (Wh)</code>
      </div>
    </div>
  </div>
</div>

<script>
  const snapshotDataset = __SNAPSHOT_DATA__;
  const historyDataset = __HISTORY_DATA__;

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

  function formatKwh(value) {
    return value.toLocaleString("lt-LT", { minimumFractionDigits: 1, maximumFractionDigits: 1 });
  }

  function renderBarPanel(location) {
    const width = 320, height = 240;
    const marginLeft = 40, marginRight = 12, marginTop = 20, marginBottom = 30;
    const plotWidth = width - marginLeft - marginRight;
    const plotHeight = height - marginTop - marginBottom;

    const maxValue = Math.max(...location.rows.flatMap((r) => [r.pvgis, r.openMeteo, r.forecast]));
    const top = niceMax(maxValue * 1.15);

    const barWidth = 18, barGap = 2;
    const groupWidth = barWidth * 3 + barGap * 2;
    const groupGap = (plotWidth - groupWidth * location.rows.length) / (location.rows.length + 1);
    const scaleY = (value) => (value / top) * plotHeight;

    let svg = `<svg viewBox="0 0 ${width} ${height}" width="100%" height="${height}" role="img" aria-label="${location.name} naujausia prognozė">`;

    [0, 0.5, 1].forEach((fraction) => {
      const y = marginTop + plotHeight - plotHeight * fraction;
      const isBaseline = fraction === 0;
      svg += `<line class="${isBaseline ? "baseline" : "gridline"}" x1="${marginLeft}" x2="${width - marginRight}" y1="${y}" y2="${y}" />`;
      svg += `<text class="axis-label" x="${marginLeft - 8}" y="${y + 4}" text-anchor="end">${formatKwh(top * fraction)}</text>`;
    });

    const seriesOrder = [
      { field: "pvgis", color: "var(--series-1)" },
      { field: "openMeteo", color: "var(--series-3)" },
      { field: "forecast", color: "var(--series-2)" },
    ];

    location.rows.forEach((row, i) => {
      const groupX = marginLeft + groupGap * (i + 1) + groupWidth * i;
      const baseY = marginTop + plotHeight;
      seriesOrder.forEach((series, seriesIndex) => {
        const value = row[series.field];
        const barHeight = scaleY(value);
        const barX = groupX + seriesIndex * (barWidth + barGap);
        svg += `<rect x="${barX}" y="${baseY - barHeight}" width="${barWidth}" height="${Math.max(barHeight, 1)}" rx="4" fill="${series.color}" />`;
        svg += `<text class="value-label" x="${barX + barWidth / 2}" y="${baseY - barHeight - 5}" text-anchor="middle">${formatKwh(value)}</text>`;
      });
      const shortDate = row.date.slice(5);
      svg += `<text class="axis-label" x="${groupX + groupWidth / 2}" y="${baseY + 18}" text-anchor="middle">${shortDate}</text>`;
    });

    svg += `</svg>`;
    return svg;
  }

  function renderLinePanel(location) {
    const width = 460, height = 230;
    const marginLeft = 42, marginRight = 46, marginTop = 20, marginBottom = 30;
    const plotWidth = width - marginLeft - marginRight;
    const plotHeight = height - marginTop - marginBottom;

    const rows = location.rows;
    const maxValue = Math.max(...rows.flatMap((r) => [r.pvgis, r.openMeteo, r.forecast]));
    const top = niceMax(maxValue * 1.15);

    const xStep = rows.length > 1 ? plotWidth / (rows.length - 1) : 0;
    const scaleX = (i) => marginLeft + (rows.length > 1 ? i * xStep : plotWidth / 2);
    const scaleY = (value) => marginTop + plotHeight - (value / top) * plotHeight;

    let svg = `<svg viewBox="0 0 ${width} ${height}" width="100%" height="${height}" role="img" aria-label="${location.name} laiko eilutė">`;

    [0, 0.5, 1].forEach((fraction) => {
      const y = marginTop + plotHeight - plotHeight * fraction;
      const isBaseline = fraction === 0;
      svg += `<line class="${isBaseline ? "baseline" : "gridline"}" x1="${marginLeft}" x2="${width - marginRight}" y1="${y}" y2="${y}" />`;
      svg += `<text class="axis-label" x="${marginLeft - 8}" y="${y + 4}" text-anchor="end">${formatKwh(top * fraction)}</text>`;
    });

    const seriesDefs = [
      { field: "pvgis", color: "var(--series-1)", label: "PVGIS" },
      { field: "openMeteo", color: "var(--series-3)", label: "Open-Meteo" },
      { field: "forecast", color: "var(--series-2)", label: "Forecast.Solar" },
    ];

    seriesDefs.forEach((series) => {
      const points = rows.map((row, i) => [scaleX(i), scaleY(row[series.field])]);
      const path = points.map((p, i) => (i === 0 ? "M" : "L") + p[0].toFixed(1) + "," + p[1].toFixed(1)).join(" ");
      svg += `<path d="${path}" fill="none" stroke="${series.color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" />`;

      points.forEach(([x, y], i) => {
        svg += `<circle cx="${x}" cy="${y}" r="4" fill="${series.color}" stroke="var(--surface-1)" stroke-width="2"><title>${rows[i].date}: ${formatKwh(rows[i][series.field])} kWh (${series.label})</title></circle>`;
      });

      const [lastX, lastY] = points[points.length - 1];
      const lastValue = rows[rows.length - 1][series.field];
      svg += `<text class="value-label" x="${lastX + 8}" y="${lastY + 4}" text-anchor="start">${formatKwh(lastValue)}</text>`;
    });

    const maxLabels = 8;
    const labelStep = Math.max(1, Math.ceil(rows.length / maxLabels));
    rows.forEach((row, i) => {
      if (i % labelStep !== 0 && i !== rows.length - 1) return;
      svg += `<text class="axis-label" x="${scaleX(i)}" y="${marginTop + plotHeight + 18}" text-anchor="middle">${row.date.slice(5)}</text>`;
    });

    svg += `</svg>`;
    return svg;
  }

  function renderPanels(containerId, dataset, renderFn) {
    const container = document.getElementById(containerId);
    dataset.forEach((location) => {
      const panel = document.createElement("div");
      panel.className = "panel";
      panel.innerHTML = `<h3>${location.name}</h3><p class="panel-sub">${location.kwp}</p>${renderFn(location)}`;
      container.appendChild(panel);
    });
  }

  renderPanels("snapshot-panels", snapshotDataset, renderBarPanel);
  renderPanels("history-panels", historyDataset, renderLinePanel);

  const tbody = document.querySelector("#data-table tbody");
  historyDataset.forEach((location) => {
    const rowsDesc = [...location.rows].reverse();
    rowsDesc.forEach((row) => {
      const forecastError = row.forecast - row.openMeteo;
      const tr = document.createElement("tr");
      tr.innerHTML = `
        <td>${location.name}</td>
        <td>${row.date}</td>
        <td class="num">${formatKwh(row.pvgis)}</td>
        <td class="num">${formatKwh(row.openMeteo)}</td>
        <td class="num">${formatKwh(row.forecast)}</td>
        <td class="num">${forecastError >= 0 ? "+" : ""}${formatKwh(forecastError)}</td>
      `;
      tbody.appendChild(tr);
    });
  });
</script>

</body>
</html>
"""


if __name__ == "__main__":
    from main import DB_PATH

    connection = sqlite3.connect(DB_PATH)
    generate_report(connection, "reports/etapas1_palyginimas.html")
    connection.close()
    print("Ataskaita sugeneruota: reports/etapas1_palyginimas.html")
