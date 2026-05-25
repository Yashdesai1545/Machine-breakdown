"""
train_model.py - Trains ML model on REAL JSW machine dataset
Dataset: machine_data_new_500.csv (500 records, 16 columns)
Run: python train_model.py
"""

import pandas as pd
import numpy as np
import os
import joblib
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import (classification_report, roc_auc_score,
                             accuracy_score, f1_score)
from sklearn.utils import resample
import warnings
warnings.filterwarnings('ignore')

RAW_COLS = {
    "Air temperature [K]":     "air_temperature",
    "Process temperature [K]": "process_temperature",
    "Rotational speed [rpm]":  "rotational_speed",
    "Torque [Nm]":             "torque",
    "Tool wear [min]":         "tool_wear",
    "Vibration [mm/s]":        "vibration",
}

FEATURES = list(RAW_COLS.values())
TARGET   = "Machine failure"
DATASET_PATH = "dataset/machine_data_new_502.csv"


def load_and_clean(path):
    print(f"Loading dataset: {path}")
    df = pd.read_csv(path)
    df = df.rename(columns=RAW_COLS)
    keep = FEATURES + [TARGET, "Machine Name", "Machine ID", "Type", "TWF", "HDF", "PWF", "OSF"]
    df = df[[c for c in keep if c in df.columns]]
    df = df.dropna(subset=FEATURES + [TARGET])
    print(f"Shape: {df.shape}, Failure rate: {df[TARGET].mean()*100:.1f}%")
    return df


def augment_minority(X, y):
    majority = X[y == 0]
    minority = X[y == 1]
    target_count = int(len(majority) * 0.40)
    minority_up = resample(minority, replace=True, n_samples=target_count, random_state=42)
    X_bal = pd.concat([majority, minority_up]).reset_index(drop=True)
    y_bal = pd.Series([0] * len(majority) + [1] * len(minority_up), name=TARGET)
    print(f"After oversampling training data: {len(X_bal)} records, {y_bal.mean()*100:.1f}% failure rate")
    return X_bal, y_bal


def train(df_raw):
    print("Training ML ensemble model...")
    X, y = df_raw[FEATURES], df_raw[TARGET]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.20, random_state=42, stratify=y)

    X_train_bal, y_train_bal = augment_minority(X_train, y_train)

    scaler = StandardScaler()
    X_train_sc = scaler.fit_transform(X_train_bal)
    X_test_sc = scaler.transform(X_test)

    rf = RandomForestClassifier(n_estimators=300, max_depth=10,
                                class_weight="balanced", random_state=42, n_jobs=-1)
    rf.fit(X_train_sc, y_train_bal)

    gb = GradientBoostingClassifier(n_estimators=150, learning_rate=0.08,
                                    max_depth=4, subsample=0.8, random_state=42)
    gb.fit(X_train_sc, y_train_bal)

    rf_prob = rf.predict_proba(X_test_sc)[:, 1]
    gb_prob = gb.predict_proba(X_test_sc)[:, 1]
    ens_prob = rf_prob * 0.60 + gb_prob * 0.40
    ens_pred = (ens_prob >= 0.50).astype(int)

    print(f"\nEnsemble Accuracy : {accuracy_score(y_test, ens_pred)*100:.2f}%")
    print(f"F1-Score          : {f1_score(y_test, ens_pred)*100:.2f}%")
    print(f"ROC-AUC           : {roc_auc_score(y_test, ens_prob):.4f}")
    print(classification_report(y_test, ens_pred, target_names=["Normal","Failure"]))

    cv = cross_val_score(
        Pipeline([('scaler', StandardScaler()), ('rf', RandomForestClassifier(
            n_estimators=300, max_depth=10, class_weight='balanced', random_state=42, n_jobs=-1))]),
        X, y, cv=5, scoring='roc_auc')
    print(f"5-Fold CV ROC-AUC: {cv.mean():.4f} +/- {cv.std():.4f}")

    fi = pd.Series(rf.feature_importances_, index=FEATURES).sort_values(ascending=False)
    print("\nFeature Importances:")
    for feat, imp in fi.items():
        print(f"  {feat:<28} {'█'*int(imp*60)} {imp:.4f}")

    os.makedirs("model", exist_ok=True)
    bundle = {"rf": rf, "gb": gb, "features": FEATURES, "dataset": "machine_data_new_500.csv"}
    joblib.dump(bundle, "model/breakdown_model.pkl")
    joblib.dump(scaler,  "model/scaler.pkl")

    import json
    with open("model/column_map.json", "w") as f:
        json.dump(RAW_COLS, f, indent=2)

    print("\nSaved: model/breakdown_model.pkl | model/scaler.pkl | model/column_map.json")
    return rf, gb, scaler


if __name__ == "__main__":
    df_raw = load_and_clean(DATASET_PATH)
    df_raw.to_csv("dataset/machine_data_clean.csv", index=False)
    train(df_raw)
    print("Done! Run: python app.py")
