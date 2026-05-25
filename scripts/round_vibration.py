"""Round the vibration readings in the dataset CSV to 2 decimal places.
Creates a backup file `machine_data_new_500.csv.bak` before overwriting.

Usage:
  python scripts/round_vibration.py
"""
import os
import shutil
import pandas as pd

CSV_PATH = os.path.join("dataset", "machine_data_new_500.csv")
BACKUP_PATH = CSV_PATH + ".bak"


def find_vibration_column(df: pd.DataFrame) -> str | None:
    candidates = ["Vibration [mm/s]", "vibration", "Vibration"]
    for c in candidates:
        if c in df.columns:
            return c
    # fallback: try case-insensitive
    for col in df.columns:
        if col.lower().startswith("vibration"):
            return col
    return None


def main():
    if not os.path.exists(CSV_PATH):
        print(f"CSV not found: {CSV_PATH}")
        return

    # Backup
    if not os.path.exists(BACKUP_PATH):
        shutil.copy2(CSV_PATH, BACKUP_PATH)
        print(f"Backup created: {BACKUP_PATH}")
    else:
        print(f"Backup already exists: {BACKUP_PATH}")

    df = pd.read_csv(CSV_PATH)
    vib_col = find_vibration_column(df)
    if vib_col is None:
        print("Could not find a vibration column in the CSV.")
        return

    # Ensure numeric and round
    df[vib_col] = pd.to_numeric(df[vib_col], errors="coerce").round(2)

    df.to_csv(CSV_PATH, index=False)
    print(f"Rounded column '{vib_col}' to 2 decimals and wrote: {CSV_PATH}")

    # Show a small sample
    print(df[[vib_col]].head(10).to_string(index=False))


if __name__ == "__main__":
    main()
