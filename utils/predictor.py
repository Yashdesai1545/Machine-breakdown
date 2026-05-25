"""
utils/predictor.py - ML prediction engine for real JSW sensor data
"""

import joblib
import warnings
warnings.filterwarnings("ignore", category=UserWarning)
import numpy as np
import os

MODEL_PATH  = "model/breakdown_model.pkl"
SCALER_PATH = "model/scaler.pkl"

_model_bundle = None
_scaler       = None


def load_model():
    global _model_bundle, _scaler
    if not os.path.exists(MODEL_PATH):
        raise FileNotFoundError("Model not found. Run: python train_model.py")
    _model_bundle = joblib.load(MODEL_PATH)
    _scaler       = joblib.load(SCALER_PATH)
    print(f"Model loaded. Features: {_model_bundle['features']}")


def _ensure_loaded():
    global _model_bundle, _scaler
    if _model_bundle is None:
        load_model()


def predict_single(sensor_data: dict) -> dict:
    _ensure_loaded()
    features = _model_bundle["features"]
    rf = _model_bundle["rf"]
    gb = _model_bundle["gb"]

    X    = np.array([[sensor_data[f] for f in features]])
    X_sc = _scaler.transform(X)

    rf_prob  = float(rf.predict_proba(X_sc)[0][1])
    gb_prob  = float(gb.predict_proba(X_sc)[0][1])
    risk_score = rf_prob * 0.60 + gb_prob * 0.40

    predicted_breakdown = int(risk_score >= 0.50)

    if risk_score >= 0.75:
        risk_level = "CRITICAL"
        recommendation = "⚠️ Immediate machine shutdown required. Critical breakdown risk detected."
    elif risk_score >= 0.50:
        risk_level = "HIGH"
        recommendation = "🔴 Schedule urgent maintenance within 24 hours. High failure probability."
    elif risk_score >= 0.30:
        risk_level = "MEDIUM"
        recommendation = "🟡 Monitor closely. Plan preventive maintenance within 72 hours."
    else:
        risk_level = "LOW"
        recommendation = "✅ Machine operating within normal parameters. Continue scheduled monitoring."

    return {
        "risk_score":          round(risk_score * 100, 2),
        "risk_level":          risk_level,
        "predicted_breakdown": predicted_breakdown,
        "recommendation":      recommendation,
        "rf_confidence":       round(rf_prob * 100, 2),
        "gb_confidence":       round(gb_prob * 100, 2),
    }


def predict_batch(df) -> list:
    _ensure_loaded()
    features = _model_bundle["features"]
    rf = _model_bundle["rf"]
    gb = _model_bundle["gb"]

    X_sc     = _scaler.transform(df[features].values)
    rf_probs = rf.predict_proba(X_sc)[:, 1]
    gb_probs = gb.predict_proba(X_sc)[:, 1]
    risk_scores = rf_probs * 0.60 + gb_probs * 0.40

    results = []
    for i, score in enumerate(risk_scores):
        score = float(score)
        if score >= 0.75:   level = "CRITICAL"
        elif score >= 0.50: level = "HIGH"
        elif score >= 0.30: level = "MEDIUM"
        else:               level = "LOW"
        results.append({
            "row":        i + 1,
            "risk_score": round(score * 100, 2),
            "risk_level": level,
            "breakdown":  int(score >= 0.50)
        })
    return results
