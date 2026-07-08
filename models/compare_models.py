"""
Paleidžia visus baseline modelius su TA PAČIA duomenų dalybimi (train/test split)
ir sugeneruoja vieną bendrą HTML ataskaitą jų palyginimui.
"""

from models import baseline_linear, baseline_random_forest
from models.data_utils import chronological_split, load_data
from reports.generate_model_report import generate_report

REPORT_PATH = "reports/kaggle_baseline_modeliai.html"


if __name__ == "__main__":
    dataset = load_data()
    train_set, test_set = chronological_split(dataset)

    print("=" * 60)
    linear_result = baseline_linear.train_and_evaluate(train_set, test_set)
    print("\n" + "=" * 60)
    forest_result = baseline_random_forest.train_and_evaluate(train_set, test_set)
    print("=" * 60)

    generate_report([linear_result, forest_result], REPORT_PATH)
    print(f"\nHTML ataskaita (abu modeliai): {REPORT_PATH}")
