"""
Forecast.Solar API klientas.

Forecast.Solar - viešas (nemokamas, be API rakto) trumpalaikės (1-2 dienų) saulės FV
gamybos prognozės servisas. Prognozė paremta orų duomenimis, o ne istoriniais
vidurkiais - todėl tinka lyginti su PVGIS istoriniu vidurkiu (žr. pvgis.py).

Svarbu: nemokama versija ribojama iki 12 užklausų per valandą vienam IP adresui.
"""

import requests

from config import Location, PVSystem

FORECAST_SOLAR_API_URL = "https://api.forecast.solar/estimate"


def get_forecast_solar_estimate(location: Location, system: PVSystem) -> dict:
    """
    Gauna Forecast.Solar trumpalaikę (šiandien + rytoj) FV gamybos prognozę.

    Parametrai:
        location: vietos koordinatės (Location objektas iš config.py)
        system: elektrinės parametrai - galia, kampas, orientacija (PVSystem objektas)

    Grąžina:
        dict {data (YYYY-MM-DD): prognozuojama dienos gamyba Wh}, pvz.
        {"2026-07-06": 11418, "2026-07-07": 9255}

    Išmeta:
        RuntimeError, jei API nepasiekiamas, viršytas užklausų limitas (12/val.),
        arba atsakymo formatas netikėtas.
    """
    url = (
        f"{FORECAST_SOLAR_API_URL}/{location.latitude}/{location.longitude}/"
        f"{system.tilt}/{system.azimuth}/{system.kwp}"
    )

    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
    except requests.exceptions.RequestException as error:
        raise RuntimeError(
            f"Nepavyko pasiekti Forecast.Solar API vietai '{location.name}': {error}"
        ) from error

    data = response.json()

    message = data.get("message", {})
    if message.get("code") != 0:
        raise RuntimeError(
            f"Forecast.Solar API grąžino klaidą vietai '{location.name}': "
            f"{message.get('text', 'nežinoma klaida')}"
        )

    try:
        daily_watt_hours = data["result"]["watt_hours_day"]
    except KeyError as error:
        raise RuntimeError(
            f"Netikėtas Forecast.Solar atsakymo formatas vietai '{location.name}': "
            f"trūksta rakto {error}"
        ) from error

    return daily_watt_hours


if __name__ == "__main__":
    from config import LOCATIONS, PV_SYSTEMS

    demo_location = LOCATIONS["eiguliai"]
    demo_system = PV_SYSTEMS["eiguliai"]

    forecast = get_forecast_solar_estimate(demo_location, demo_system)
    print(f"Forecast.Solar prognozė: {demo_location.name} ({demo_system.kwp} kWp)")
    for date, watt_hours in forecast.items():
        print(f"  {date}: {watt_hours / 1000:.2f} kWh")
