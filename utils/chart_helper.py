"""
utils/chart_helper.py - Chart data generators (MySQL version)
"""

from database import get_connection
from utils.db_helper import get_risk_trend
from datetime import datetime


def risk_distribution_chart(machine_id=None):
    conn = get_connection()
    try:
        with conn.cursor() as c:
            query = "SELECT risk_level, COUNT(*) as cnt FROM predictions"
            params = []
            if machine_id:
                query += " WHERE machine_id=%s"
                params.append(machine_id)
            query += " GROUP BY risk_level"
            c.execute(query, tuple(params))
            rows = c.fetchall()
    finally:
        conn.close()
    labels = [r["risk_level"] for r in rows]
    values = [r["cnt"] for r in rows]
    colors = {"LOW": "#22c55e", "MEDIUM": "#f59e0b", "HIGH": "#f97316", "CRITICAL": "#ef4444"}
    return {"type": "pie", "labels": labels, "values": values,
            "colors": [colors.get(l, "#6b7280") for l in labels]}


def risk_trend_chart(machine_id, days=14):
    trend = get_risk_trend(machine_id, days)
    return {
        "type":  "line",
        "x":     [r["day"] for r in trend],
        "y_avg": [round(r["avg_risk"], 2) for r in trend],
        "y_max": [round(r["max_risk"], 2) for r in trend],
        "counts": [r["count"] for r in trend]
    }


def sensor_radar_chart(sensor_data: dict):
    from utils.preprocess import FEATURE_RANGES
    labels, values, normals = [], [], []
    for feat, (lo, hi, normal, _) in FEATURE_RANGES.items():
        labels.append(feat.replace("_", " ").title())
        val_norm = (sensor_data.get(feat, normal) - lo) / (hi - lo) * 100
        nrm_norm = (normal - lo) / (hi - lo) * 100
        values.append(round(max(0, min(100, val_norm)), 1))
        normals.append(round(max(0, min(100, nrm_norm)), 1))
    return {"type": "radar", "labels": labels, "current": values, "normal": normals}


def feature_importance_chart():
    import os, joblib
    if not os.path.exists("model/breakdown_model.pkl"):
        return {}
    bundle = joblib.load("model/breakdown_model.pkl")
    rf, features = bundle["rf"], bundle["features"]
    pairs = sorted(zip(features, rf.feature_importances_), key=lambda x: x[1], reverse=True)
    return {
        "type":   "bar",
        "labels": [p[0].replace("_", " ").title() for p in pairs],
        "values": [round(p[1] * 100, 2) for p in pairs]
    }


def machines_risk_heatmap():
    conn = get_connection()
    try:
        with conn.cursor() as c:
            c.execute("""
                SELECT p.machine_id, m.machine_name, p.risk_score, p.risk_level
                FROM predictions p
                JOIN machines m ON m.machine_id = p.machine_id
                WHERE p.id IN (
                    SELECT MAX(id) FROM predictions GROUP BY machine_id
                )
                ORDER BY p.risk_score DESC
            """)
            rows = c.fetchall()
    finally:
        conn.close()
    return rows


def breakdown_timeline(days=30):
    conn = get_connection()
    try:
        with conn.cursor() as c:
            c.execute("""
                SELECT DATE(timestamp) as day,
                       SUM(predicted_breakdown) as breakdowns,
                       COUNT(*) as total_predictions
                FROM predictions
                WHERE timestamp >= DATE_SUB(NOW(), INTERVAL %s DAY)
                GROUP BY DATE(timestamp)
                ORDER BY day
            """, (days,))
            rows = c.fetchall()
    finally:
        conn.close()
    result_x, result_b, result_t = [], [], []
    for r in rows:
        day = r["day"]
        if hasattr(day, "strftime"):
            day = day.strftime("%Y-%m-%d")
        result_x.append(day)
        result_b.append(int(r["breakdowns"] or 0))
        result_t.append(int(r["total_predictions"] or 0))
    return {"type": "bar_line", "x": result_x, "breakdowns": result_b, "total": result_t}
