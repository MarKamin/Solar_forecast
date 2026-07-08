"""
Generuoja statinius, aukštos kokybės (300 DPI) PNG grafikus baigiamajam darbui:
laiko eilutę ir sklaidos grafiką, lyginančius LR/RF prognozes su realia gamyba
kintančios radiacijos (besikeičiančių debesų) periode.

Skirtingai nuo reports/kaggle_baseline_modeliai.html (interaktyvi HTML apžvalga
visam testavimo periodui), šis skriptas sufokusuoja į TRUMPĄ, vizualiai aiškų
periodą, tinkamą tiesiogiai įklijuoti į Word/PDF dokumentą.

Periodo parinkimas: Elektrinė 4136001, 2020-06-13 - 2020-06-15 (3 dienos).
Šios dienos pasirinktos patikrinus "trūkumo" koeficientą (kreivės bendra kitimo
suma / (2 x dienos pikas)) - kuo didesnis, tuo daugiau greitų radiacijos šuolių
(besikeičiantys debesys), o ne sklandus giedros/apniukusios dienos kilimas-kritimas.
Ši elektrinė turėjo nuosekliai aukščiausią koeficientą (2.9-3.5) ir anksčiau
pasirodė santykinai sunkiau nuspėjama (didesnė normalizuota MAE) - būtent tokiomis
sąlygomis geriausiai matosi skirtumas tarp LR ir RF tikslumo.
"""

import base64
import os

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LinearRegression

from models.data_utils import FEATURES, TARGET, chronological_split, load_data

PLANT_ID = 4136001
PERIOD_START = "2020-06-13"
PERIOD_END = "2020-06-15 23:59:59"
OUTPUT_DIR = "reports/figures"


def get_period_predictions() -> pd.DataFrame:
    """Treniruoja LR ir RF (identiškai kaip models/baseline_*.py) ir grąžina plataus
    formato lentelę pasirinktam periodui/elektrinei: timestamp, actual_power,
    lr_predicted, rf_predicted."""
    data = load_data()
    train, test = chronological_split(data)

    lr = LinearRegression().fit(train[FEATURES], train[TARGET])
    rf = RandomForestRegressor(n_estimators=200, random_state=42, n_jobs=-1)
    rf.fit(train[FEATURES], train[TARGET])

    test = test.copy()
    test["lr_predicted"] = np.clip(lr.predict(test[FEATURES]), 0, None)
    test["rf_predicted"] = rf.predict(test[FEATURES])

    period = test[
        (test["PLANT_ID"] == PLANT_ID)
        & (test["DATE_TIME"] >= PERIOD_START)
        & (test["DATE_TIME"] <= PERIOD_END)
    ].sort_values("DATE_TIME")

    return period[["DATE_TIME", TARGET, "lr_predicted", "rf_predicted"]].rename(
        columns={"DATE_TIME": "timestamp", TARGET: "actual_power"}
    )


def plot_timeseries(period: pd.DataFrame, output_path: str) -> None:
    """Linijinis grafikas: reali gamyba (ištisinė, juoda, stora) vs LR/RF prognozės
    (punktyrinės, skirtingi stiliai/spalvos)."""
    fig, ax = plt.subplots(figsize=(10, 5))

    ax.plot(period["timestamp"], period["actual_power"], color="black",
            linewidth=2.2, label="Reali gamyba")
    ax.plot(period["timestamp"], period["lr_predicted"], color="#2a78d6",
            linestyle="--", linewidth=1.4, label="Linijinės regresijos prognozė")
    ax.plot(period["timestamp"], period["rf_predicted"], color="#e34948",
            linestyle=":", linewidth=1.8, label="Random Forest prognozė")

    ax.set_xlabel("Laikas")
    ax.set_ylabel("Galia (W)")
    ax.set_title(f"Prognozė vs reali gamyba — Elektrinė {PLANT_ID}, "
                 f"{PERIOD_START} – {PERIOD_END[:10]}")
    ax.legend(loc="upper right", frameon=False, fontsize=9)
    ax.grid(True, alpha=0.25)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    ax.xaxis.set_major_locator(mdates.HourLocator(interval=6))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%m-%d %H:%M"))
    fig.autofmt_xdate(rotation=30)

    fig.tight_layout()
    fig.savefig(output_path, dpi=300)
    plt.close(fig)


def plot_scatter(period: pd.DataFrame, output_path: str) -> None:
    """Sklaidos grafikas: reali vs prognozuota galia, su y=x atskaitos linija."""
    fig, ax = plt.subplots(figsize=(6, 6))

    max_val = max(
        period["actual_power"].max(), period["lr_predicted"].max(), period["rf_predicted"].max()
    ) * 1.05

    ax.plot([0, max_val], [0, max_val], color="gray", linestyle="--",
            linewidth=1, label="Idealus atitikimas (y = x)")
    ax.scatter(period["actual_power"], period["lr_predicted"], color="#2a78d6",
               alpha=0.7, s=28, label="Linijinė regresija")
    ax.scatter(period["actual_power"], period["rf_predicted"], color="#e34948",
               alpha=0.7, s=28, label="Random Forest")

    ax.set_xlabel("Reali galia (W)")
    ax.set_ylabel("Prognozuota galia (W)")
    ax.set_title(f"Prognozė vs realybė — Elektrinė {PLANT_ID}\n"
                 f"{PERIOD_START} – {PERIOD_END[:10]}", fontsize=12)
    ax.set_xlim(0, max_val)
    ax.set_ylim(0, max_val)
    ax.set_aspect("equal")
    ax.legend(loc="upper left", frameon=False, fontsize=9)
    ax.grid(True, alpha=0.25)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    fig.tight_layout()
    fig.savefig(output_path, dpi=300)
    plt.close(fig)


def build_html_viewer(timeseries_path: str, scatter_path: str, output_path: str) -> None:
    """Sudeda abu PNG į vieną savarankišką HTML failą (base64 įterpta), kad juos būtų
    galima peržiūrėti naršyklėje, ne tik atidarant atskirus paveikslėlio failus."""
    def _to_base64(path: str) -> str:
        with open(path, "rb") as file:
            return base64.b64encode(file.read()).decode("ascii")

    html = f"""<!DOCTYPE html>
<html lang="lt">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Statiniai grafikai baigiamajam darbui - LR vs RF</title>
<style>
  :root {{
    --surface-1: #fcfcfb; --page-plane: #f9f9f7; --text-primary: #0b0b0b;
    --text-secondary: #52514e; --text-muted: #898781; --border: rgba(11,11,11,0.10);
  }}
  @media (prefers-color-scheme: dark) {{
    :root {{
      --surface-1: #1a1a19; --page-plane: #0d0d0d; --text-primary: #ffffff;
      --text-secondary: #c3c2b7; --text-muted: #898781; --border: rgba(255,255,255,0.10);
    }}
  }}
  :root[data-theme="dark"] {{
    --surface-1: #1a1a19; --page-plane: #0d0d0d; --text-primary: #ffffff;
    --text-secondary: #c3c2b7; --text-muted: #898781; --border: rgba(255,255,255,0.10);
  }}
  :root[data-theme="light"] {{
    --surface-1: #fcfcfb; --page-plane: #f9f9f7; --text-primary: #0b0b0b;
    --text-secondary: #52514e; --text-muted: #898781; --border: rgba(11,11,11,0.10);
  }}
  * {{ box-sizing: border-box; }}
  body {{ margin: 0; background: var(--page-plane); color: var(--text-primary);
    font-family: system-ui, -apple-system, "Segoe UI", sans-serif; }}
  .root {{ max-width: 880px; margin: 0 auto; padding: 32px 20px 48px; }}
  h1 {{ font-size: 20px; font-weight: 600; margin: 0 0 6px; }}
  .subtitle {{ color: var(--text-secondary); font-size: 14px; margin: 0 0 24px;
    max-width: 72ch; line-height: 1.5; }}
  .panel {{ background: var(--surface-1); border: 1px solid var(--border);
    border-radius: 10px; padding: 16px; margin-bottom: 24px; }}
  .panel h2 {{ font-size: 14px; font-weight: 600; margin: 0 0 12px; }}
  .panel img {{ width: 100%; height: auto; border-radius: 4px; display: block; }}
  .note {{ font-size: 12.5px; color: var(--text-muted); line-height: 1.6; max-width: 72ch; }}
</style>
</head>
<body>
<div class="root">
  <h1>Statiniai grafikai (300 DPI) - baigiamajam darbui</h1>
  <p class="subtitle">
    Elektrinė {PLANT_ID}, {PERIOD_START} – {PERIOD_END[:10]} - periodas su besikeičiančiais
    debesimis (aukščiausias radiacijos "trūkumo" koeficientas testavimo aibėje), kur
    geriausiai matosi skirtumas tarp linijinės regresijos ir Random Forest tikslumo.
    Originalūs PNG failai: <code>reports/figures/</code>.
  </p>

  <div class="panel">
    <h2>1. Laiko eilutė - prognozė vs reali gamyba</h2>
    <img src="data:image/png;base64,{_to_base64(timeseries_path)}" alt="Laiko eilutė">
  </div>

  <div class="panel">
    <h2>2. Sklaidos grafikas - prognozė vs realybė</h2>
    <img src="data:image/png;base64,{_to_base64(scatter_path)}" alt="Sklaidos grafikas">
  </div>

  <p class="note">
    Šie du grafiko tipai (laiko eilutė + sklaida) yra numatyti kaip standartinė,
    pakartojama vizualizacijos pora kiekvienam būsimam prognozavimo metodo palyginimui
    su realia gamyba (LSTM, o vėliau - realūs Lietuvos elektrinių duomenys).
  </p>
</div>
</body>
</html>
"""
    with open(output_path, "w", encoding="utf-8") as file:
        file.write(html)


if __name__ == "__main__":
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    period_data = get_period_predictions()
    print(f"Pasirinktas periodas: Elektrinė {PLANT_ID}, "
          f"{period_data['timestamp'].min()} – {period_data['timestamp'].max()} "
          f"({len(period_data)} eilučių)")

    timeseries_path = f"{OUTPUT_DIR}/timeseries_prognoze_vs_realybe.png"
    scatter_path = f"{OUTPUT_DIR}/sklaida_prognoze_vs_realybe.png"
    html_path = "reports/statiniai_grafikai.html"

    plot_timeseries(period_data, timeseries_path)
    plot_scatter(period_data, scatter_path)
    build_html_viewer(timeseries_path, scatter_path, html_path)

    print(f"Grafikai išsaugoti:\n  {timeseries_path}\n  {scatter_path}\n  {html_path}")
