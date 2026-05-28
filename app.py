"""
app.py - JSW Machine Breakdown Prediction System (MySQL Edition)
Run: python app.py
"""

import warnings
warnings.filterwarnings("ignore")

import os
from dotenv import load_dotenv

load_dotenv()

import pandas as pd
import numpy as np
from functools import wraps
from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from flask_cors import CORS
from werkzeug.utils import secure_filename

from database import init_db
from utils.predictor import predict_single, predict_batch, load_model
from utils.preprocess import validate_input, preprocess_csv, FEATURE_RANGES
from utils.db_helper import (
    save_prediction, get_recent_predictions, get_all_machines,
    get_machine_stats, get_alerts, acknowledge_alert, seed_demo_data,
    get_csv_machines
)
from utils.auth_helper import normalize_username, create_user, verify_password, get_user_by_username
from utils.chart_helper import (
    risk_distribution_chart, risk_trend_chart, sensor_radar_chart,
    feature_importance_chart, machines_risk_heatmap, breakdown_timeline
)

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "a-very-secret-key-123")
CORS(app)
app.config["UPLOAD_FOLDER"]      = "dataset/uploaded_logs"
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024

def initialize_database():
    init_db()

initialize_database()

DATASET_PATH = "dataset/machine_data_new_504.csv"

os.makedirs("dataset/uploaded_logs", exist_ok=True)
os.makedirs("reports", exist_ok=True)


def login_required(view_func):
    @wraps(view_func)
    def wrapped_view(*args, **kwargs):
        if not session.get("logged_in"):
            return redirect(url_for("login"))
        return view_func(*args, **kwargs)
    return wrapped_view


@app.route("/login", methods=["GET", "POST"])
def login():
    if session.get("logged_in"):
        return redirect(url_for("index"))

    error = None
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        if verify_password(username, password):
            session["logged_in"] = True
            session["username"] = normalize_username(username)
            return redirect(url_for("index"))
        error = "Invalid username or password"

    return render_template("login.html", error=error)


@app.route("/signup", methods=["GET", "POST"])
def signup():
    if session.get("logged_in"):
        return redirect(url_for("index"))

    error = None
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        confirm  = request.form.get("confirm_password", "")
        if not username or not password:
            error = "Username and password are required."
        elif password != confirm:
            error = "Passwords do not match."
        elif get_user_by_username(username) is not None:
            error = "That username is already taken."
        else:
            try:
                normalized = create_user(username, password)
                session["logged_in"] = True
                session["username"] = normalized
                return redirect(url_for("index"))
            except Exception as exc:
                error = str(exc)

    return render_template("signup.html", error=error)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


# ── Pages ────────────────────────────────────────────────────────
@app.route("/")
@login_required
def index():
    return render_template("index.html")


# ── Stats ─────────────────────────────────────────────────────────
@app.route("/api/stats")
def api_stats():
    try:
        return jsonify({"success": True, "data": get_machine_stats()})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# ── Machines (MySQL table) ─────────────────────────────────────────
@app.route("/api/machines")
def api_machines():
    try:
        machines = get_all_machines()
        heatmap  = machines_risk_heatmap()
        risk_map = {r["machine_id"]: r for r in heatmap}
        for m in machines:
            r = risk_map.get(m["machine_id"], {})
            m["latest_risk_score"] = r.get("risk_score", 0)
            m["latest_risk_level"] = r.get("risk_level", "UNKNOWN")
        return jsonify({"success": True, "data": machines})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# ── CSV Machines — all 60 real machines from dataset ──────────────
@app.route("/api/csv-machines")
def api_csv_machines():
    """Returns CSV machines for dropdowns & grid.

    By default returns unique machines (one per `Machine Name`).
    Pass `?unique=0` to return all rows from the CSV (e.g. 500 records).
    """
    try:
        df = pd.read_csv(DATASET_PATH)
        unique = request.args.get("unique", "1")
        if unique == "0":
            # Return all rows (full dataset)
            machines = (
                df[["Machine Name", "Machine ID", "Type"]]
                .rename(columns={"Machine Name": "machine_name",
                                  "Machine ID":   "product_id",
                                  "Type":         "machine_type"})
                .to_dict("records")
            )
        else:
            # Default: return one entry per unique machine name
            machines = (
                df[["Machine Name", "Machine ID", "Type"]]
                .drop_duplicates("Machine Name")
                .sort_values("Machine Name")
                .rename(columns={"Machine Name": "machine_name",
                                  "Machine ID":   "product_id",
                                  "Type":         "machine_type"})
                .to_dict("records")
            )
        return jsonify({"success": True, "data": machines})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# ── Dataset samples for batch visualization ────────────────────────
@app.route("/api/machine-samples")
def api_machine_samples():
    try:
        df = pd.read_csv(DATASET_PATH)
        samples = [
            {
                "machine_id":   str(row["Machine ID"]),
                "machine_name": str(row["Machine Name"]),
                "air_temperature":     float(row["Air temperature [K]"]),
                "process_temperature": float(row["Process temperature [K]"]),
                "rotational_speed":    float(row["Rotational speed [rpm]"]),
                "torque":              float(row["Torque [Nm]"]),
                "tool_wear":           float(row["Tool wear [min]"]),
                "vibration":           float(row["Vibration [mm/s]"]),
                "actual_failure":      int(row["Machine failure"]),
            }
            for _, row in df.iterrows()
        ]
        return jsonify({"success": True, "data": samples})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# ── NEW: Dataset analytics endpoints (data from CSV, not DB) ──────

@app.route("/api/dataset/failure-by-type")
def api_failure_by_type():
    """Failure counts by machine type (H/M/L) from dataset."""
    try:
        df = pd.read_csv(DATASET_PATH)
        result = (
            df.groupby("Type")["Machine failure"]
            .agg(total="count", failures="sum")
            .reset_index()
        )
        result["failure_rate"] = (result["failures"] / result["total"] * 100).round(2)
        type_labels = {"H": "Heavy", "M": "Medium", "L": "Light"}
        return jsonify({
            "success": True,
            "labels":        [type_labels.get(t, t) for t in result["Type"].tolist()],
            "total":         result["total"].tolist(),
            "failures":      result["failures"].tolist(),
            "failure_rates": result["failure_rate"].tolist(),
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/dataset/failure-by-machine")
def api_failure_by_machine():
    """Failure count per machine (top 20) from dataset."""
    try:
        df = pd.read_csv(DATASET_PATH)
        result = (
            df.groupby("Machine Name")["Machine failure"]
            .agg(total="count", failures="sum")
            .reset_index()
            .sort_values("failures", ascending=False)
            .head(20)
        )
        result["failure_rate"] = (result["failures"] / result["total"] * 100).round(1)
        return jsonify({
            "success":       True,
            "labels":        result["Machine Name"].tolist(),
            "failures":      result["failures"].tolist(),
            "failure_rates": result["failure_rate"].tolist(),
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/dataset/failure-causes")
def api_failure_causes():
    """Breakdown of root-cause failure types from dataset."""
    try:
        df = pd.read_csv(DATASET_PATH)
        causes = {
            "Tool Wear Failure":       int(df["TWF"].sum()),
            "Heat Dissipation Failure": int(df["HDF"].sum()),
            "Power Failure":            int(df["PWF"].sum()),
            "Overstrain Failure":       int(df["OSF"].sum()),
            "Random Failure":           int(df["RNF"].sum()),
        }
        return jsonify({
            "success": True,
            "labels": list(causes.keys()),
            "values": list(causes.values()),
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/dataset/sensor-stats")
def api_sensor_stats():
    """Sensor statistics split by failure/no-failure from dataset."""
    try:
        df   = pd.read_csv(DATASET_PATH)
        cols = {
            "Air temperature [K]":     "Air Temp (K)",
            "Process temperature [K]": "Process Temp (K)",
            "Rotational speed [rpm]":  "Rotational Speed (RPM)",
            "Torque [Nm]":             "Torque (Nm)",
            "Tool wear [min]":         "Tool Wear (min)",
            "Vibration [mm/s]":        "Vibration (mm/s)",
        }
        ok  = df[df["Machine failure"] == 0]
        bad = df[df["Machine failure"] == 1]
        result = []
        for col, label in cols.items():
            result.append({
                "feature":        label,
                "mean_normal":    round(float(ok[col].mean()), 2),
                "mean_failure":   round(float(bad[col].mean()), 2),
                "std_normal":     round(float(ok[col].std()),  2),
                "std_failure":    round(float(bad[col].std()),  2),
            })
        return jsonify({"success": True, "data": result})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/dataset/tool-wear-bins")
def api_tool_wear_bins():
    """Tool wear distribution binned into ranges from dataset."""
    try:
        df   = pd.read_csv(DATASET_PATH)
        bins = [0, 50, 100, 150, 200, 260]
        lbls = ["0-50", "51-100", "101-150", "151-200", "201-260"]
        df["bin"] = pd.cut(df["Tool wear [min]"], bins=bins, labels=lbls, right=True)
        grouped   = df.groupby("bin", observed=True)
        totals    = grouped["Machine failure"].count().tolist()
        failures  = grouped["Machine failure"].sum().tolist()
        return jsonify({
            "success":  True,
            "labels":   lbls,
            "total":    [int(x) for x in totals],
            "failures": [int(x) for x in failures],
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/dataset/machine-sensor-profile")
def api_machine_sensor_profile():
    """Average sensor values per machine from dataset (for radar/comparison)."""
    machine_id = request.args.get("machine_id", "").strip()
    machine = request.args.get("machine", "").strip()
    try:
        df = pd.read_csv(DATASET_PATH)
        if machine_id:
            df = df[df["Machine ID"] == machine_id]
        elif machine:
            df = df[df["Machine Name"] == machine]
        if df.empty:
            return jsonify({"success": False, "error": "Machine not found"}), 404
        profile = {
            "machine_name":        machine or machine_id or "All Machines",
            "air_temperature":     round(float(df["Air temperature [K]"].mean()), 2),
            "process_temperature": round(float(df["Process temperature [K]"].mean()), 2),
            "rotational_speed":    round(float(df["Rotational speed [rpm]"].mean()), 1),
            "torque":              round(float(df["Torque [Nm]"].mean()), 2),
            "tool_wear":           round(float(df["Tool wear [min]"].mean()), 1),
            "vibration":           round(float(df["Vibration [mm/s]"].mean()), 3),
            "failure_rate":        round(float(df["Machine failure"].mean()) * 100, 1),
        }
        return jsonify({"success": True, "data": profile})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# ── Single Prediction ──────────────────────────────────────────────
@app.route("/api/predict", methods=["POST"])
def api_predict():
    try:
        body        = request.get_json()
        machine_id  = body.get("machine_id", "UNKNOWN")
        sensor_data = {k: float(v) for k, v in body.items() if k in FEATURE_RANGES}

        valid, msg = validate_input(sensor_data)
        if not valid:
            return jsonify({"success": False, "error": msg}), 400

        prediction = predict_single(sensor_data)
        save_prediction(machine_id, sensor_data, prediction)
        radar = sensor_radar_chart(sensor_data)

        return jsonify({"success": True, "prediction": prediction, "radar": radar})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# ── Batch Prediction ───────────────────────────────────────────────
@app.route("/api/predict/batch", methods=["POST"])
def api_predict_batch():
    try:
        if "file" not in request.files:
            return jsonify({"success": False, "error": "No file provided"}), 400
        f = request.files["file"]
        if not f.filename.endswith(".csv"):
            return jsonify({"success": False, "error": "Only CSV files allowed"}), 400

        filepath = os.path.join(app.config["UPLOAD_FOLDER"], secure_filename(f.filename))
        f.save(filepath)

        df, err = preprocess_csv(filepath)
        if err:
            return jsonify({"success": False, "error": err}), 400

        results         = predict_batch(df)
        breakdown_count = sum(1 for r in results if r["breakdown"] == 1)

        return jsonify({
            "success":         True,
            "total_records":   len(results),
            "breakdown_count": breakdown_count,
            "results":         results[:100]
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# ── History ────────────────────────────────────────────────────────
@app.route("/api/predictions")
def api_predictions():
    machine_id = request.args.get("machine_id")
    limit      = int(request.args.get("limit", 50))
    try:
        return jsonify({"success": True, "data": get_recent_predictions(machine_id, limit)})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# ── Alerts ─────────────────────────────────────────────────────────
@app.route("/api/alerts")
def api_alerts():
    try:
        return jsonify({"success": True, "data": get_alerts(30)})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/alerts/<int:alert_id>/acknowledge", methods=["POST"])
def api_ack_alert(alert_id):
    try:
        acknowledge_alert(alert_id)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# ── Charts ─────────────────────────────────────────────────────────
@app.route("/api/charts/distribution")
def api_chart_dist():
    return jsonify(risk_distribution_chart(request.args.get("machine_id")))

@app.route("/api/charts/trend")
def api_chart_trend():
    return jsonify(risk_trend_chart(
        request.args.get("machine_id", "JSW-BLF-01"),
        int(request.args.get("days", 14))
    ))

@app.route("/api/charts/importance")
def api_chart_importance():
    return jsonify(feature_importance_chart())

@app.route("/api/charts/heatmap")
def api_chart_heatmap():
    return jsonify({"data": machines_risk_heatmap()})

@app.route("/api/charts/timeline")
def api_chart_timeline():
    return jsonify(breakdown_timeline(int(request.args.get("days", 30))))

@app.route("/api/feature-ranges")
def api_feature_ranges():
    data = {k: {"min": v[0], "max": v[1], "default": v[2], "unit": v[3]}
            for k, v in FEATURE_RANGES.items()}
    return jsonify(data)


# ── Startup ────────────────────────────────────────────────────────
import os

if __name__ == "__main__":
    print("=" * 50)
    print(" JSW Machine Breakdown Prediction System")
    print(" Database: MySQL")
    print("=" * 50)

    init_db()

    try:
        load_model()

    except FileNotFoundError:
        print("Model not found. Run: python train_model.py")

    port = int(os.environ.get("PORT", 5000))

    app.run(host="0.0.0.0", port=port)