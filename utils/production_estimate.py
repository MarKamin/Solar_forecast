"""
Fizikinis FV gamybos įvertis pagal saulės radiaciją.

Supaprastintas (A) variantas: naudoja horizontalią radiaciją (GHI - Global
Horizontal Irradiance), NE panelio plokštumos radiaciją (POA - Plane of
Array). Tai reiškia, kad neatsižvelgiama į tikslų panelių nuolydį (tilt) ir
orientaciją (azimuth) santykyje su saulės padėtimi dangaus skliaute.

TODO: jei ateityje reikės didesnio tikslumo, perrašyti naudojant `pvlib`
biblioteką ir jos POA transpozicijos modelį (pvz. Perez modelis), kuris
tinkamai įvertina tilt/azimuth poveikį.
"""

DEFAULT_PERFORMANCE_RATIO = 0.80


def estimate_production_kwh(
    radiation_mj_per_m2: float,
    kwp: float,
    performance_ratio: float = DEFAULT_PERFORMANCE_RATIO,
) -> float:
    """
    Apskaičiuoja apytikslę FV gamybą (kWh) iš dienos radiacijos sumos.

    Formulė: gamyba = radiacija (kWh/m^2) * instaliuota galia (kWp) * performance ratio

    Parametrai:
        radiation_mj_per_m2: dienos suminė radiacija, MJ/m^2 (iš Open-Meteo)
        kwp: instaliuota galia, kilovatais
        performance_ratio: sistemos našumo koeficientas (0-1), numatyta 0.80 -
            tipinė Europos vertė, apimanti nuostolius nuo temperatūros, laidų,
            inverterio ir kt. Tai ĮVERTIS, ne konkrečiai sistemai išmatuota vertė.

    Grąžina:
        Apytikslė dienos gamyba, kWh.
    """
    radiation_kwh_per_m2 = radiation_mj_per_m2 / 3.6
    return radiation_kwh_per_m2 * kwp * performance_ratio
