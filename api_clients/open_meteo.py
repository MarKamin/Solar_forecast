"""
Open-Meteo API klientas.

Open-Meteo - nemokamas (be API rakto) orų duomenų šaltinis. Čia naudojamas kaip
laikinas apytikslis "ką realiai turėjo pagaminti" atskaitos taškas konkrečiai
dienai, kol dar neturime tikrų gamybos duomenų iš elektrinių. Skirtingai nei
PVGIS (ilgametis klimato vidurkis) ar Forecast.Solar (FV gamybos prognozė),
Open-Meteo duoda IŠMATUOTĄ/PROGNOZUOJAMĄ saulės radiaciją konkrečiai dienai -
todėl tinka sąžiningai lyginti su Forecast.Solar prognoze tai pačiai dienai
(žr. utils/production_estimate.py, kur radiacija paverčiama kWh).

Pastaba: naudojamas /v1/forecast endpoint'as, kuris apima artimą praeitį ir
ateitį. Senesnėms (praėjusių mėnesių) datoms reikėtų archyvo endpoint'o
(archive-api.open-meteo.com) - tai čia NEĮGYVENDINTA, nes kol kas reikia tik
artimiausių dienų (tų pačių, kurioms turime Forecast.Solar prognozę).
"""

import requests

from config import Location

OPEN_METEO_API_URL = "https://api.open-meteo.com/v1/forecast"


def get_daily_radiation(location: Location, start_date: str, end_date: str) -> dict:
    """
    Gauna dienos suminę trumpabangę radiaciją (shortwave_radiation_sum), MJ/m^2.

    Parametrai:
        location: vietos koordinatės (Location objektas iš config.py)
        start_date, end_date: datos "YYYY-MM-DD" formatu, imtinai

    Grąžina:
        dict {data (YYYY-MM-DD): radiacija MJ/m^2}

    Išmeta:
        RuntimeError, jei API nepasiekiamas arba atsakymo formatas netikėtas.
    """
    params = {
        "latitude": location.latitude,
        "longitude": location.longitude,
        "daily": "shortwave_radiation_sum",
        "timezone": "Europe/Vilnius",
        "start_date": start_date,
        "end_date": end_date,
    }

    try:
        response = requests.get(OPEN_METEO_API_URL, params=params, timeout=30)
        response.raise_for_status()
    except requests.exceptions.RequestException as error:
        raise RuntimeError(
            f"Nepavyko pasiekti Open-Meteo API vietai '{location.name}': {error}"
        ) from error

    data = response.json()

    try:
        dates = data["daily"]["time"]
        radiation_values = data["daily"]["shortwave_radiation_sum"]
    except KeyError as error:
        raise RuntimeError(
            f"Netikėtas Open-Meteo atsakymo formatas vietai '{location.name}': "
            f"trūksta rakto {error}"
        ) from error

    return dict(zip(dates, radiation_values))


if __name__ == "__main__":
    from datetime import date, timedelta

    from config import LOCATIONS

    demo_location = LOCATIONS["eiguliai"]
    today = date.today().isoformat()
    tomorrow = (date.today() + timedelta(days=1)).isoformat()

    radiation = get_daily_radiation(demo_location, today, tomorrow)
    print(f"Open-Meteo radiacija: {demo_location.name}")
    for day, value in radiation.items():
        print(f"  {day}: {value} MJ/m^2")
