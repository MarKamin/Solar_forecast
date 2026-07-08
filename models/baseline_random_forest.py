"""
Baseline modelis: Random Forest (atsitiktinis miškas).

Tas pats X/y kaip linijinėje regresijoje (žr. baseline_linear.py), bet Random
Forest yra medžių ansamblis - daug sprendimų medžių treniruojami su skirtingais
atsitiktiniais duomenų/požymių pogrupiais, o galutinė prognozė yra jų vidurkis.
Tai leidžia modeliui pačiam atrasti NETIESINES sąveikas tarp požymių (pvz.
radiacijos ir temperatūros), kurių linijinei regresijai reikėjo aiškaus
IRRADIATION_X_TEMP nario.

Kadangi medžiai niekada neekstrapoliuoja už matytų y reikšmių ribų (kiekvienas
medžio "lapas" yra treniravimo reikšmių vidurkis), Random Forest niekada
neprognozuos neigiamos galios - `np.clip` pataisymas, kurio prireikė linijinei
regresijai, čia nereikalingas.
"""

import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

from models.data_utils import FEATURES, TARGET, chronological_split, load_data

N_ESTIMATORS = 200
RANDOM_STATE = 42


def train_and_evaluate(train: pd.DataFrame, test: pd.DataFrame) -> dict:
    """Treniruoja Random Forest, atspausdina metrikas ir grąžina rezultatus
    (naudojama HTML ataskaitos generavimui - žr. reports/generate_model_report.py)."""
    model = RandomForestRegressor(n_estimators=N_ESTIMATORS, random_state=RANDOM_STATE, n_jobs=-1)
    model.fit(train[FEATURES], train[TARGET])

    predictions = model.predict(test[FEATURES])

    mae = mean_absolute_error(test[TARGET], predictions)
    rmse = mean_squared_error(test[TARGET], predictions) ** 0.5
    r2 = r2_score(test[TARGET], predictions)

    print("--- Random Forest rezultatai (testavimo aibėje) ---")
    print(f"MAE  (vidutinė absoliuti paklaida):              {mae:.2f} W")
    print(f"RMSE (didesnę reikšmę teikia didelėms paklaidoms): {rmse:.2f} W")
    print(f"R²   (paaiškintos dispersijos dalis, 0-1):        {r2:.4f}")
    print()
    print("Požymių svarba (kiek modelis kiekvieną požymį naudojo prognozei, 0-1):")
    for feature, importance in zip(FEATURES, model.feature_importances_):
        print(f"  {feature}: {importance:.4f}")

    feature_importances = [
        {"name": feature, "value": float(importance)}
        for feature, importance in zip(FEATURES, model.feature_importances_)
    ]

    return {
        "name": "Random Forest",
        "dates": test["DATE_TIME"].dt.strftime("%Y-%m-%d %H:%M").tolist(),
        "actual": test[TARGET].tolist(),
        "predicted": predictions.tolist(),
        "irradiation": test["IRRADIATION"].tolist(),
        "plant_id": test["PLANT_ID"].tolist(),
        "metrics": {"mae": mae, "rmse": rmse, "r2": r2},
        "feature_importances": feature_importances,
    }


if __name__ == "__main__":
    from reports.generate_model_report import generate_report

    dataset = load_data()
    train_set, test_set = chronological_split(dataset)
    result = train_and_evaluate(train_set, test_set)

    REPORT_PATH = "reports/kaggle_baseline_modeliai.html"
    generate_report([result], REPORT_PATH)
    print(f"\nHTML ataskaita: {REPORT_PATH}")
