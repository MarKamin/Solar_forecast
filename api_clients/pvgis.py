"""
PVGIS API klientas.

PVGIS (Photovoltaic Geographical Information System) - Europos Komisijos JRC įrankis,
teikiantis istorinius saulės radiacijos duomenis ir apskaičiuojantis tikėtiną FV
elektrinės gamybą pagal daugiamečius (2005-2020) klimato duomenis. Tai NĖRA prognozė
konkrečiai dienai, o statistinis vidurkis - naudinga kaip atskaitos taškas, kiek
paprastai pagamina tokia elektrinė šioje vietoje.
"""

import requests

from config import Location, PVSystem

PVGIS_API_URL = "https://re.jrc.ec.europa.eu/api/v5_2/PVcalc"


def get_pvgis_monthly_estimate(
    location: Location, system: PVSystem, system_loss_percent: float = 14.0
) -> dict:
    """
    Gauna PVGIS mėnesinius vidutinius FV gamybos ir radiacijos įverčius.

    Parametrai:
        location: vietos koordinatės (Location objektas iš config.py)
        system: elektrinės parametrai - galia, kampas, orientacija (PVSystem objektas)
        system_loss_percent: bendri sistemos nuostoliai procentais (laidai, inverteris,
            temperatūra ir kt.) - PVGIS numatytoji rekomendacija ~14%

    Grąžina:
        dict su raktais "monthly" (12 įrašų sąrašas: mėnuo, vidutinė dienos gamyba
        E_d kWh, mėnesio suma E_m kWh, radiacija H(i)_d kWh/m^2) ir "yearly"
        (metinė suma E_y ir vidutinė dienos gamyba E_d kWh).

    Išmeta:
        RuntimeError, jei API nepasiekiamas arba atsakymo formatas netikėtas.
    """
    params = {
        "lat": location.latitude,
        "lon": location.longitude,
        "peakpower": system.kwp,
        "loss": system_loss_percent,
        "angle": system.tilt,
        "aspect": system.azimuth,
        "outputformat": "json",
    }

    try:
        response = requests.get(PVGIS_API_URL, params=params, timeout=30)
        response.raise_for_status()
    except requests.exceptions.RequestException as error:
        raise RuntimeError(
            f"Nepavyko pasiekti PVGIS API vietai '{location.name}': {error}"
        ) from error

    data = response.json()

    try:
        monthly = data["outputs"]["monthly"]["fixed"]
        yearly = data["outputs"]["totals"]["fixed"]
    except KeyError as error:
        raise RuntimeError(
            f"Netikėtas PVGIS atsakymo formatas vietai '{location.name}': "
            f"trūksta rakto {error}"
        ) from error

    return {"monthly": monthly, "yearly": yearly}


if __name__ == "__main__":
    from config import LOCATIONS, PV_SYSTEMS

    demo_location = LOCATIONS["eiguliai"]
    demo_system = PV_SYSTEMS["eiguliai"]

    result = get_pvgis_monthly_estimate(demo_location, demo_system)
    print(f"PVGIS įvertis: {demo_location.name} ({demo_system.kwp} kWp, {demo_system.tilt}° kampas)")
    print(f"Vidutinė metinė gamyba: {result['yearly']['E_y']} kWh")
    print(f"Vidutinė dienos gamyba: {result['yearly']['E_d']} kWh")
