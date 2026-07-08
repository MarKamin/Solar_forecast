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


if __name__ == "__main__":
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    period_data = get_period_predictions()
    print(f"Pasirinktas periodas: Elektrinė {PLANT_ID}, "
          f"{period_data['timestamp'].min()} – {period_data['timestamp'].max()} "
          f"({len(period_data)} eilučių)")

    timeseries_path = f"{OUTPUT_DIR}/timeseries_prognoze_vs_realybe.png"
    scatter_path = f"{OUTPUT_DIR}/sklaida_prognoze_vs_realybe.png"

    plot_timeseries(period_data, timeseries_path)
    plot_scatter(period_data, scatter_path)

    print(f"Grafikai išsaugoti:\n  {timeseries_path}\n  {scatter_path}")
