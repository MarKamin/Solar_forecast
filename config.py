"""
Konfigūracija: lokacijos ir saulės elektrinių parametrai.

Visos "švarios" reikšmės (koordinatės, elektrinių parametrai) laikomos čia, o ne
užkoduotos tiesiai API klientų kode. Jei ateityje reikės API raktų, jie taip pat
bus skaitomi čia (iš .env failo, ne užrašyti tekste).
"""

from dataclasses import dataclass


@dataclass
class Location:
    """Geografinė vieta, kuriai skaičiuojame saulės radiaciją/gamybą."""

    name: str
    latitude: float
    longitude: float


@dataclass
class PVSystem:
    """Saulės elektrinės parametrai, reikalingi Forecast.Solar prognozei.

    kwp: įrengta galia kilovatais (peak power)
    tilt: panelių pakreipimo kampas laipsniais nuo horizonto (0 = plokščiai, 90 = vertikaliai)
    azimuth: panelių orientacija laipsniais Forecast.Solar konvencija
        (0 = pietūs, -90 = rytai, 90 = vakarai)
    """

    kwp: float
    tilt: float
    azimuth: float
    system_type: str


LOCATIONS = {
    "eiguliai": Location(
        name="Kaunas, Eiguliai",
        latitude=54.93,
        longitude=23.93,
    ),
    "girininkai": Location(
        name="Girininkai I, Kauno raj.",
        latitude=54.84,
        longitude=23.70,
    ),
}

PV_SYSTEMS = {
    "eiguliai": PVSystem(kwp=5.0, tilt=35, azimuth=0, system_type="stogo elektrinė"),
    "girininkai": PVSystem(kwp=30.0, tilt=30, azimuth=0, system_type="žemės elektrinė"),
}
