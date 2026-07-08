"""
Baseline modelis: linijinė regresija.

Prognozuoja AC_POWER (reali, išmatuota gamyba) iš oro sąlygų požymių. Naudoja
Kaggle "Solar Power Generation Data" (žr. kaggle_csv_apdorojimas.py) kaip
laikiną, metodologiškai teisingą target'ą, kol laukiama realių Lietuvos
elektrinių duomenų (žr. lstm_target_taisykle.md - X vs y taisyklė).

Train/test split daromas CHRONOLOGIŠKAI (žr. models/data_utils.py), ne
atsitiktinai, nes tai laiko eilutės duomenys - modelis turi būti testuojamas
su ATEITIES duomenimis, kurių nematė treniruodamasis.
"""

import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

from models.data_utils import FEATURES, TARGET, chronological_split, load_data


def train_and_evaluate(train: pd.DataFrame, test: pd.DataFrame) -> dict:
    """Treniruoja linijinę regresiją, atspausdina metrikas ir grąžina rezultatus
    (naudojama HTML ataskaitos generavimui - žr. reports/generate_model_report.py)."""
    model = LinearRegression()
    model.fit(train[FEATURES], train[TARGET])

    predictions = model.predict(test[FEATURES])

    # Galia fiziškai negali būti neigiama - linijinė regresija to "nežino" (naktį,
    # kai IRRADIATION=0, likę nariai - AMBIENT/MODULE_TEMPERATURE - vis tiek gali
    # nustumti prognozę žemiau nulio). Apkarpome iki 0, kad prognozė atitiktų
    # fizikinį apribojimą. Šis pataisymas pagerina MAE nedaug (~2%), nes didžioji
    # klaidos dalis susidaro dieną, bet pašalina fiziškai neįmanomas reikšmes.
    predictions = np.clip(predictions, 0, None)

    mae = mean_absolute_error(test[TARGET], predictions)
    rmse = mean_squared_error(test[TARGET], predictions) ** 0.5
    r2 = r2_score(test[TARGET], predictions)

    print(f"Treniravimo eilučių: {len(train)}, testavimo eilučių: {len(test)}")
    print(f"Treniravimo laikotarpis: {train['DATE_TIME'].min()} - {train['DATE_TIME'].max()}")
    print(f"Testavimo laikotarpis:   {test['DATE_TIME'].min()} - {test['DATE_TIME'].max()}")
    print()
    print("--- Linijinės regresijos rezultatai (testavimo aibėje) ---")
    print(f"MAE  (vidutinė absoliuti paklaida):              {mae:.2f} W")
    print(f"RMSE (didesnę reikšmę teikia didelėms paklaidoms): {rmse:.2f} W")
    print(f"R²   (paaiškintos dispersijos dalis, 0-1):        {r2:.4f}")
    print()
    print("Koeficientai (kiek keičiasi galia (W), pakitus požymiui 1 vienetu):")
    for feature, coefficient in zip(FEATURES, model.coef_):
        print(f"  {feature}: {coefficient:.4f}")
    print(f"  (laisvasis narys / intercept): {model.intercept_:.4f}")

    coefficients = [
        {"name": feature, "value": float(coefficient)}
        for feature, coefficient in zip(FEATURES, model.coef_)
    ]
    coefficients.append({"name": "intercept", "value": float(model.intercept_)})

    return {
        "name": "Linijinė regresija",
        "dates": test["DATE_TIME"].dt.strftime("%Y-%m-%d %H:%M").tolist(),
        "actual": test[TARGET].tolist(),
        "predicted": predictions.tolist(),
        "irradiation": test["IRRADIATION"].tolist(),
        "plant_id": test["PLANT_ID"].tolist(),
        "metrics": {"mae": mae, "rmse": rmse, "r2": r2},
        "coefficients": coefficients,
    }


if __name__ == "__main__":
    from reports.generate_model_report import generate_report

    dataset = load_data()
    train_set, test_set = chronological_split(dataset)
    result = train_and_evaluate(train_set, test_set)

    REPORT_PATH = "reports/kaggle_baseline_modeliai.html"
    generate_report([result], REPORT_PATH)
    print(f"\nHTML ataskaita: {REPORT_PATH}")
