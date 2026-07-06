"""
Etapas 1 pagrindinis skriptas.

Kiekvienai lokacijai iš config.py: gauna PVGIS istorinį (daugiametį) mėnesio dienos
vidurkį ir Forecast.Solar 1-2 dienų prognozę, abu įrašo į SQLite lentelę ir
atspausdina palyginimo lentelę konsolėje.
"""

import sqlite3
from datetime import date, datetime

from api_clients.forecast_solar import get_forecast_solar_estimate
from api_clients.pvgis import get_pvgis_monthly_estimate
from config import LOCATIONS, PV_SYSTEMS

DB_PATH = "data/solar_data.db"

SOURCE_PVGIS = "pvgis_historinis_vidurkis"
SOURCE_FORECAST_SOLAR = "forecast_solar"


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
    """Gauna PVGIS ir Forecast.Solar įverčius vienai lokacijai ir juos išsaugo."""
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

    for estimate_date in forecast:
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


def print_comparison_table(connection: sqlite3.Connection) -> None:
    """Atspausdina naujausią PVGIS vs Forecast.Solar palyginimą konsolėje."""
    rows = connection.execute(
        """
        SELECT location_name, estimate_date,
               MAX(CASE WHEN source = ? THEN estimated_kwh END) AS pvgis_kwh,
               MAX(CASE WHEN source = ? THEN estimated_kwh END) AS forecast_kwh
        FROM solar_estimates
        WHERE fetched_at = (SELECT MAX(fetched_at) FROM solar_estimates)
        GROUP BY location_name, estimate_date
        ORDER BY location_name, estimate_date
        """,
        (SOURCE_PVGIS, SOURCE_FORECAST_SOLAR),
    ).fetchall()

    print("\n" + "=" * 84)
    print(
        f"{'Lokacija':<26} {'Data':<12} {'PVGIS vid. (kWh)':<18} "
        f"{'Forecast.Solar (kWh)':<20} {'Skirtumas'}"
    )
    print("-" * 84)
    for location_name, estimate_date, pvgis_kwh, forecast_kwh in rows:
        diff = forecast_kwh - pvgis_kwh
        print(
            f"{location_name:<26} {estimate_date:<12} {pvgis_kwh:<18.2f} "
            f"{forecast_kwh:<20.2f} {diff:+.2f}"
        )
    print("=" * 84)
    print(
        "Pastaba: PVGIS stulpelis - daugiametis (2005-2020) to mėnesio dienos\n"
        "vidurkis, NE konkrečios dienos prognozė. Forecast.Solar - orais paremta\n"
        "1-2 dienų prognozė. Skirtumas rodo, kaip konkreti diena nukrypsta nuo\n"
        "istorinio vidurkio."
    )


def main() -> None:
    connection = sqlite3.connect(DB_PATH)
    init_db(connection)

    run_timestamp = datetime.now().isoformat(timespec="seconds")

    for location_key in LOCATIONS:
        try:
            collect_location(connection, location_key, run_timestamp)
        except RuntimeError as error:
            print(f"Klaida renkant duomenis ({location_key}): {error}")

    print_comparison_table(connection)
    connection.close()


if __name__ == "__main__":
    main()
