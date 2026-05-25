"""
utils/db_helper.py - MySQL database helpers (6-feature real dataset)
"""

import random
import pandas as pd
from database import get_connection
from datetime import datetime, timedelta

DATASET_PATH = "dataset/machine_data_new_502.csv"


def save_prediction(machine_id: str, sensor_data: dict, prediction: dict):
    conn = get_connection()
    try:
        with conn.cursor() as c:
            c.execute("""
                INSERT INTO predictions
                (machine_id, air_temperature, process_temperature, rotational_speed,
                 torque, tool_wear, vibration, risk_score, risk_level,
                 predicted_breakdown, recommendation)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """, (
                machine_id,
                sensor_data.get("air_temperature"),
                sensor_data.get("process_temperature"),
                sensor_data.get("rotational_speed"),
                sensor_data.get("torque"),
                sensor_data.get("tool_wear"),
                sensor_data.get("vibration"),
                prediction["risk_score"],
                prediction["risk_level"],
                prediction["predicted_breakdown"],
                prediction["recommendation"]
            ))
            if prediction["risk_level"] in ("HIGH", "CRITICAL"):
                severity = "critical" if prediction["risk_level"] == "CRITICAL" else "high"
                c.execute("""
                    INSERT INTO alerts (machine_id, alert_type, severity, message)
                    VALUES (%s, 'Breakdown Risk', %s, %s)
                """, (machine_id, severity,
                      f"{prediction['risk_level']} risk — {prediction['recommendation']}"))
        conn.commit()
    finally:
        conn.close()


def get_recent_predictions(machine_id=None, limit=50):
    conn = get_connection()
    try:
        with conn.cursor() as c:
            if machine_id:
                c.execute(
                    "SELECT * FROM predictions WHERE machine_id=%s ORDER BY timestamp DESC LIMIT %s",
                    (machine_id, limit))
            else:
                c.execute(
                    "SELECT * FROM predictions ORDER BY timestamp DESC LIMIT %s", (limit,))
            rows = c.fetchall()
    finally:
        conn.close()
    # Convert datetime to string for JSON
    for r in rows:
        if isinstance(r.get("timestamp"), datetime):
            r["timestamp"] = r["timestamp"].strftime("%Y-%m-%d %H:%M:%S")
    return rows


def get_all_machines():
    conn = get_connection()
    try:
        with conn.cursor() as c:
            c.execute("SELECT * FROM machines ORDER BY machine_id")
            rows = c.fetchall()
    finally:
        conn.close()
    return rows


def get_machine_stats():
    conn = get_connection()
    try:
        with conn.cursor() as c:
            c.execute("SELECT COUNT(*) as cnt FROM machines")
            total = c.fetchone()["cnt"]
            c.execute("SELECT COUNT(*) as cnt FROM predictions WHERE DATE(timestamp)=CURDATE()")
            pred_td = c.fetchone()["cnt"]
            c.execute("""SELECT COUNT(*) as cnt FROM predictions
                         WHERE risk_level IN ('HIGH','CRITICAL') AND DATE(timestamp)=CURDATE()""")
            crit_td = c.fetchone()["cnt"]
            c.execute("SELECT COUNT(*) as cnt FROM alerts WHERE acknowledged=0")
            unack = c.fetchone()["cnt"]
    finally:
        conn.close()
    return {"total_machines": total, "predictions_today": pred_td,
            "critical_today": crit_td, "unacknowledged_alerts": unack}


def get_risk_trend(machine_id, days=7):
    conn = get_connection()
    try:
        with conn.cursor() as c:
            c.execute("""
                SELECT DATE(timestamp) as day,
                       AVG(risk_score) as avg_risk,
                       MAX(risk_score) as max_risk,
                       COUNT(*) as count
                FROM predictions
                WHERE machine_id=%s
                  AND timestamp >= DATE_SUB(NOW(), INTERVAL %s DAY)
                GROUP BY DATE(timestamp)
                ORDER BY day
            """, (machine_id, days))
            rows = c.fetchall()
    finally:
        conn.close()
    for r in rows:
        if hasattr(r.get("day"), "strftime"):
            r["day"] = r["day"].strftime("%Y-%m-%d")
        r["avg_risk"] = float(r["avg_risk"] or 0)
        r["max_risk"] = float(r["max_risk"] or 0)
    return rows


def get_alerts(limit=20):
    conn = get_connection()
    try:
        with conn.cursor() as c:
            c.execute("SELECT * FROM alerts ORDER BY timestamp DESC LIMIT %s", (limit,))
            rows = c.fetchall()
    finally:
        conn.close()
    for r in rows:
        if isinstance(r.get("timestamp"), datetime):
            r["timestamp"] = r["timestamp"].strftime("%Y-%m-%d %H:%M:%S")
    return rows


def acknowledge_alert(alert_id):
    conn = get_connection()
    try:
        with conn.cursor() as c:
            c.execute("UPDATE alerts SET acknowledged=1 WHERE id=%s", (alert_id,))
        conn.commit()
    finally:
        conn.close()


def get_csv_machines():
    """Return all 60 unique machines from the real CSV for dropdowns."""
    try:
        df = pd.read_csv(DATASET_PATH)
        machines = (
            df[["Machine Name", "Machine ID", "Type"]]
            .drop_duplicates("Machine Name")
            .sort_values("Machine Name")
            .to_dict("records")
        )
        return machines
    except Exception:
        return []


def seed_demo_data():
    """Seed 14 days of historical predictions using REAL CSV rows."""
    conn = get_connection()
    try:
        with conn.cursor() as c:
            c.execute("SELECT COUNT(*) as cnt FROM predictions")
            existing = c.fetchone()["cnt"]
    finally:
        conn.close()

    if existing > 5:
        return

    import sys, numpy as np
    sys.path.insert(0, ".")
    from utils.predictor import predict_single
    from utils.preprocess import FEATURE_RANGES

    # Use machine_ids that are in the machines table
    machine_ids = [
        "JSW-BLF-01", "JSW-BLF-02", "JSW-CNC-01", "JSW-CNC-02",
        "JSW-CNV-01", "JSW-HRM-01", "JSW-HRM-02", "JSW-BOF-01",
        "JSW-EAF-01", "JSW-GRD-01", "JSW-HYD-01", "JSW-CRM-01",
    ]

    for mid in machine_ids:
        for day_offset in range(14, 0, -1):
            for _ in range(random.randint(3, 6)):
                data = {
                    "air_temperature":     float(np.random.normal(302, 2.5)),
                    "process_temperature": float(np.random.normal(311, 2.2)),
                    "rotational_speed":    float(np.random.normal(1423, 145)),
                    "torque":              float(np.random.normal(52, 12)),
                    "tool_wear":           float(np.random.uniform(0, 255)),
                    "vibration":           float(np.random.exponential(1.5)),
                }
                for feat, (lo, hi, _, _u) in FEATURE_RANGES.items():
                    data[feat] = max(lo, min(hi, data[feat]))
                try:
                    pred = predict_single(data)
                    ts = (datetime.now() - timedelta(
                        days=day_offset, seconds=random.randint(0, 86400))
                    ).strftime("%Y-%m-%d %H:%M:%S")
                    conn2 = get_connection()
                    try:
                        with conn2.cursor() as c2:
                            c2.execute("""
                                INSERT INTO predictions
                                (machine_id, timestamp, air_temperature, process_temperature,
                                 rotational_speed, torque, tool_wear, vibration,
                                 risk_score, risk_level, predicted_breakdown, recommendation)
                                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                            """, (mid, ts,
                                  data["air_temperature"], data["process_temperature"],
                                  data["rotational_speed"], data["torque"],
                                  data["tool_wear"], data["vibration"],
                                  pred["risk_score"], pred["risk_level"],
                                  pred["predicted_breakdown"], pred["recommendation"]))
                        conn2.commit()
                    finally:
                        conn2.close()
                except Exception as e:
                    print(f"Seed error: {e}")
    print("Demo data seeded into MySQL.")
