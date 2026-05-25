"""scripts/predict_dataset.py

Run predictions on the bundled dataset `dataset/machine_data_new_500.csv`.
By default this performs inference and prints a summary. Use `--commit` to
save predictions into the MySQL `predictions` table via `save_prediction()`.

Usage:
  python scripts/predict_dataset.py         # dry-run, prints summary
  python scripts/predict_dataset.py --commit  # save into DB
"""
import argparse
import pandas as pd
import os
from utils.predictor import load_model, predict_single
from utils.preprocess import preprocess_csv, FEATURE_RANGES
from utils.db_helper import save_prediction

DATASET_PATH = os.path.join("dataset", "machine_data_new_500.csv")


def _machine_id_from_name(name: str, idx: int) -> str:
    parts = name.split("-")
    suffix = parts[-1].strip().zfill(2) if len(parts) > 1 else str(idx + 1).zfill(2)
    words = parts[0].strip().split()
    prefix = "".join(w[0].upper() for w in words)[:3].ljust(3, "X")
    return f"JSW-{prefix}-{suffix}"


def main(commit: bool, limit: int | None):
    if not os.path.exists(DATASET_PATH):
        raise FileNotFoundError(f"Dataset not found: {DATASET_PATH}")

    print("Loading model...")
    try:
        load_model()
    except FileNotFoundError as e:
        print(e)
        return

    print(f"Reading dataset: {DATASET_PATH}")
    raw = pd.read_csv(DATASET_PATH)
    df_features, err = preprocess_csv(DATASET_PATH)
    if err:
        print("Preprocess error:", err)
        return

    n = len(df_features)
    if limit:
        n = min(n, limit)

    print(f"Running predictions for {n} rows (commit={commit})...")

    totals = {"rows": 0, "breakdowns": 0}

    features = list(FEATURE_RANGES.keys())
    for i in range(n):
        row = df_features.iloc[i]
        sensor_data = {f: float(row[f]) for f in features}

        pred = predict_single(sensor_data)

        # Determine machine id (match DB seeding logic)
        machine_name = str(raw.iloc[i]["Machine Name"]) if "Machine Name" in raw.columns else f"ROW-{i+1}"
        machine_id = _machine_id_from_name(machine_name, i)

        totals["rows"] += 1
        if pred.get("predicted_breakdown") == 1:
            totals["breakdowns"] += 1

        if commit:
            try:
                save_prediction(machine_id, sensor_data, pred)
            except Exception as e:
                print(f"Failed saving row {i+1}: {e}")

        if (i + 1) % 50 == 0:
            print(f"  Processed {i+1}/{n} rows...")

    print("Done.")
    print(f"Rows processed: {totals['rows']}")
    print(f"Predicted breakdowns: {totals['breakdowns']}")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--commit", action="store_true", help="Save predictions into MySQL")
    p.add_argument("--limit", type=int, default=None, help="Limit number of rows to process")
    args = p.parse_args()
    main(args.commit, args.limit)
