"""
Bendra duomenų įkėlimo/dalijimo logika, naudojama visų baseline modelių
(žr. baseline_linear.py, baseline_random_forest.py), kad nereikėtų jos dubliuoti.
"""

import pandas as pd

DATA_PATH = "data/kaggle_solar_merged.csv"
FEATURES = ["AMBIENT_TEMPERATURE", "MODULE_TEMPERATURE", "IRRADIATION", "IRRADIATION_X_TEMP"]
TARGET = "AC_POWER"
TRAIN_FRACTION = 0.8


def load_data(path: str = DATA_PATH) -> pd.DataFrame:
    """Įkelia apdorotus duomenis ir surūšiuoja chronologiškai (pagal laiką)."""
    data = pd.read_csv(path, parse_dates=["DATE_TIME"])
    return data.sort_values("DATE_TIME").reset_index(drop=True)


def chronological_split(data: pd.DataFrame, train_fraction: float = TRAIN_FRACTION):
    """Padalina duomenis į train/test CHRONOLOGIŠKAI (ne atsitiktinai per sklearn train_test_split).

    Pirmi `train_fraction` duomenų (laike) - treniravimui, likusi, VĖLESNĖ dalis -
    testavimui. Tai imituoja realią situaciją: modelis mato tik praeitį,
    testuojamas su ateitimi, kurios nematė.
    """
    split_index = int(len(data) * train_fraction)
    train = data.iloc[:split_index]
    test = data.iloc[split_index:]
    return train, test
