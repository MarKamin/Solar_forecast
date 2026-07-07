"""
Etapas 1 pagrindinis skriptas.

Kiekvienai lokacijai iš config.py: gauna PVGIS istorinį (daugiametį) mėnesio dienos
vidurkį, Forecast.Solar 1-2 dienų prognozę ir Open-Meteo radiacija paremtą "ką tą
dieną realiai turėjo pagaminti" įvertį; visus tris įrašo į SQLite lentelę ir
atspausdina palyginimo lentelę konsolėje.

Metodologinė taisyklė: PVGIS ilgametis vidurkis NIEKADA nenaudojamas kaip
tikslumo etalonas pavienei dienai - jis lieka atskirai, tik planavimo/baseline
kontekstui. Teisingas tikslumo palyginimas yra Forecast.Solar prognozė vs
Open-Meteo apskaičiuota gamyba TAI PAČIAI dienai (žr. print_comparison_table).
"""

import sqlite3
from datetime import date, datetime

from api_clients.forecast_solar import get_forecast_solar_estimate
from api_clients.open_meteo import get_daily_radiation
from api_clients.pvgis import get_pvgis_monthly_estimate
from config import LOCATIONS, PV_SYSTEMS
from reports.generate_report import generate_report
from utils.production_estimate import estimate_production_kwh

DB_PATH = "data/solar_data.db"
REPORT_PATH = "reports/etapas1_palyginimas.html"

SOURCE_PVGIS = "pvgis_historinis_vidurkis"
SOURCE_FORECAST_SOLAR = "forecast_solar"
SOURCE_OPEN_METEO = "open_meteo_apskaiciuota"


def init_db(connection: sqlite3.Connection) -> None:
    """Sukuria `solar_estimates` lentelę, jei ji dar neegzistuoja."""
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS solar_estimates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            location_key TEXT NOT NULL,
            location_name TEXT NOT NULL,
            source TEXT NOT NULL,
            estimate_date TEXT NOT NULL,
            estimated_kwh REAL NOT NULL,
            kwp REAL NOT NULL,
            fetched_at TEXT NOT NULL
        )
        """
    )
    connection.commit()


def save_estimate(
    connection: sqlite3.Connection,
    location_key: str,
    location_name: str,
    source: str,
    estimate_date: str,
    estimated_kwh: float,
    kwp: float,
    run_timestamp: str,
) -> None:
    """Įrašo vieną įvertį į lentelę.

    Pastaba: kiekvienas paleidimas prideda naujas eilutes (neperrašo senų), nes
    norime kaupti laiko eilutę, kaip prognozės keitėsi laikui bėgant - tai
    pravers vėliau, lyginant prognozes su realia gamyba. `run_timestamp` yra
    bendras visam vienam main() paleidimui (žr. main()), kad palyginimo
    lentelė galėtų patikimai atskirti "šio paleidimo" eilutes nuo senesnių.
    """
    connection.execute(
        """
        INSERT INTO solar_estimates
            (location_key, location_name, source, estimate_date, estimated_kwh, kwp, fetched_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            location_key,
            location_name,
            source,
            estimate_date,
            estimated_kwh,
            kwp,
            run_timestamp,
        ),
    )
    connection.commit()


def collect_location(
    connection: sqlite3.Connection, location_key: str, run_timestamp: str
) -> None:
    """Gauna PVGIS, Forecast.Solar ir Open-Meteo įverčius vienai lokacijai ir juos išsaugo."""
    location = LOCATIONS[location_key]
    system = PV_SYSTEMS[location_key]

    print(f"Renkami duomenys: {location.name}...")

    pvgis_result = get_pvgis_monthly_estimate(location, system)
    current_month = date.today().month
    monthly_row = next(
        month for month in pvgis_result["monthly"] if month["month"] == current_month
    )
    pvgis_daily_avg_kwh = monthly_row["E_d"]

    forecast = get_forecast_solar_estimate(location, system)
    forecast_dates = sorted(forecast)

    radiation = get_daily_radiation(location, forecast_dates[0], forecast_dates[-1])

    for estimate_date in forecast_dates:
        save_estimate(
            connection,
            location_key,
            location.name,
            SOURCE_PVGIS,
            estimate_date,
            pvgis_daily_avg_kwh,
            system.kwp,
            run_timestamp,
        )

    for estimate_date, watt_hours in forecast.items():
        save_estimate(
            connection,
            location_key,
            location.name,
            SOURCE_FORECAST_SOLAR,
            estimate_date,
            watt_hours / 1000,
            system.kwp,
            run_timestamp,
        )

    for estimate_date, radiation_mj_per_m2 in radiation.items():
        save_estimate(
            connection,
            location_key,
            location.name,
            SOURCE_OPEN_METEO,
            estimate_date,
            estimate_production_kwh(radiation_mj_per_m2, system.kwp),
            system.kwp,
            run_timestamp,
        )


def print_comparison_table(connection: sqlite3.Connection) -> None:
    """Atspausdina naujausią PVGIS / Open-Meteo / Forecast.Solar palyginimą konsolėje."""
    rows = connection.execute(
        """
        SELECT location_name, estimate_date,
               MAX(CASE WHEN source = ? THEN estimated_kwh END) AS pvgis_kwh,
               MAX(CASE WHEN source = ? THEN estimated_kwh END) AS open_meteo_kwh,
               MAX(CASE WHEN source = ? THEN estimated_kwh END) AS forecast_kwh
        FROM solar_estimates
        WHERE substr(fetched_at, 1, 10) = (SELECT substr(MAX(fetched_at), 1, 10) FROM solar_estimates)
        GROUP BY location_name, estimate_date
        ORDER BY location_name, estimate_date
        """,
        (SOURCE_PVGIS, SOURCE_OPEN_METEO, SOURCE_FORECAST_SOLAR),
    ).fetchall()

    print("\n" + "=" * 104)
    print(
        f"{'Lokacija':<26} {'Data':<12} {'PVGIS vid. (kWh)':<18} "
        f"{'Open-Meteo (kWh)':<18} {'Forecast.Solar (kWh)':<20} {'Progn. paklaida'}"
    )
    print("-" * 104)
    for location_name, estimate_date, pvgis_kwh, open_meteo_kwh, forecast_kwh in rows:
        forecast_error = forecast_kwh - open_meteo_kwh
        print(
            f"{location_name:<26} {estimate_date:<12} {pvgis_kwh:<18.2f} "
            f"{open_meteo_kwh:<18.2f} {forecast_kwh:<20.2f} {forecast_error:+.2f}"
        )
    print("=" * 104)
    print(
        "Pastaba: PVGIS - daugiametis (2005-2020) to mėnesio dienos vidurkis, TIK\n"
        "planavimo/baseline kontekstui, NE tikslumo etalonas pavienei dienai.\n"
        "Open-Meteo - radiacija paversta apytiksle gamyba (žr. utils/production_estimate.py),\n"
        "TAI PAČIAI dienai - tinkamas etalonas prognozės tikslumui vertinti. 'Progn.\n"
        "paklaida' = Forecast.Solar - Open-Meteo (teisingas palyginimas, ne su PVGIS)."
    )


def already_collected_today(connection: sqlite3.Connection, location_key: str) -> bool:
    """Patikrina, ar šiai lokacijai duomenys jau sėkmingai surinkti šiandien.

    Leidžia main.py saugiai paleisti kelis kartus per dieną (pvz. cron 7:00,
    11:00, 12:00, 13:00 kaip atsarginius bandymus, jei kompiuteris 7:00 buvo
    išjungtas) - jei ankstesnis paleidimas tą pačią dieną jau pavyko, vėlesni
    tiesiog praleidžiami, o ne kuria dublikatus ar be reikalo švaisto API
    užklausų limitą (ypač svarbu Forecast.Solar 12 užklausų/val. limitui).
    """
    today = date.today().isoformat()
    count = connection.execute(
        "SELECT COUNT(*) FROM solar_estimates WHERE location_key = ? AND fetched_at LIKE ?",
        (location_key, f"{today}%"),
    ).fetchone()[0]
    return count > 0


def main() -> None:
    connection = sqlite3.connect(DB_PATH)
    init_db(connection)

    run_timestamp = datetime.now().isoformat(timespec="seconds")

    for location_key in LOCATIONS:
        if already_collected_today(connection, location_key):
            print(f"{LOCATIONS[location_key].name}: šiandien jau surinkta anksčiau - praleidžiama.")
            continue
        try:
            collect_location(connection, location_key, run_timestamp)
        except RuntimeError as error:
            print(f"Klaida renkant duomenis ({location_key}): {error}")

    print_comparison_table(connection)
    generate_report(connection, REPORT_PATH)
    print(f"\nHTML ataskaita atnaujinta: {REPORT_PATH}")
    connection.close()


if __name__ == "__main__":
    main()
