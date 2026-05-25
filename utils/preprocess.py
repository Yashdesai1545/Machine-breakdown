"""
utils/preprocess.py - Data preprocessing for REAL JSW dataset features
Features: air_temperature, process_temperature, rotational_speed,
          torque, tool_wear, vibration
"""

import pandas as pd
import numpy as np

# Min, Max, Default, Unit  — derived from actual dataset ranges with real-world margin
FEATURE_RANGES = {
    "air_temperature":       (292.0, 320.0, 302.0, "K"),
    "process_temperature":   (306.0, 335.0, 312.0, "K"),
    "rotational_speed":      (1050,  1800,  1423,  "RPM"),
    "torque":                (30.0,  95.0,  54.0,  "Nm"),
    "tool_wear":             (0,     360,   128,   "min"),
    "vibration":             (0.2,   9.0,   2.0,   "mm/s"),
}

# Column mapping from raw CSV → internal name
RAW_COL_MAP = {
    "Air temperature [K]":     "air_temperature",
    "Process temperature [K]": "process_temperature",
    "Rotational speed [rpm]":  "rotational_speed",
    "Torque [Nm]":             "torque",
    "Tool wear [min]":         "tool_wear",
    "Vibration [mm/s]":        "vibration",
}

# Failure-correlated thresholds (from domain + data analysis)
WARNING_THRESHOLDS = {
    "air_temperature":     {"warning": 305.0, "critical": 307.0},
    "process_temperature": {"warning": 314.0, "critical": 316.0},
    "rotational_speed":    {"warning": 1600,  "critical": 1700},
    "torque":              {"warning": 65.0,  "critical": 78.0},
    "tool_wear":           {"warning": 180,   "critical": 230},
    "vibration":           {"warning": 3.0,   "critical": 4.5},
}

# Failure type labels from dataset
FAILURE_TYPES = {
    "TWF": "Tool Wear Failure",
    "HDF": "Heat Dissipation Failure",
    "PWF": "Power Failure",
    "OSF": "Overstrain Failure",
}


def validate_input(data: dict) -> tuple:
    for feat, (lo, hi, _, unit) in FEATURE_RANGES.items():
        val = data.get(feat)
        if val is None:
            return False, f"Missing field: {feat}"
        try:
            val = float(val)
        except (TypeError, ValueError):
            return False, f"Invalid value for {feat}: must be numeric"
        if not (lo <= val <= hi):
            return False, f"{feat} value {val:.1f} out of range [{lo}, {hi}] {unit}"
    return True, "OK"


def get_sensor_status(feature: str, value: float) -> str:
    t = WARNING_THRESHOLDS.get(feature, {})
    warn = t.get("warning")
    crit = t.get("critical")
    if crit and value >= crit: return "critical"
    if warn and value >= warn: return "warning"
    return "normal"


def preprocess_csv(filepath: str) -> pd.DataFrame:
    """Load uploaded CSV — handles both raw column names and internal names."""
    df = pd.read_csv(filepath)

    # Try renaming raw columns if present
    df = df.rename(columns=RAW_COL_MAP)

    features = list(FEATURE_RANGES.keys())
    missing = [f for f in features if f not in df.columns]
    if missing:
        # Try to give helpful error with raw names
        raw_names = list(RAW_COL_MAP.keys())
        return None, f"CSV missing columns: {missing}. Expected: {raw_names}"

    for feat, (lo, hi, _, _u) in FEATURE_RANGES.items():
        df[feat] = df[feat].clip(lo, hi)

    df = df.dropna(subset=features)
    return df[features], None
