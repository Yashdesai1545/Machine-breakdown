<<<<<<< HEAD
# 🏭 JSW Machine Breakdown Prediction System

A full-stack, professional-grade predictive maintenance system for JSW industrial machinery.
Built with Python (Flask + Scikit-learn) backend and HTML/CSS/JavaScript frontend with Chart.js visualizations.

---

## 🗂️ Project Structure

```
jsw_breakdown/
├── app.py                    # Flask web application (main entry point)
├── train_model.py            # ML dataset generation + model training
├── database.py               # SQLite schema + initialization
├── requirements.txt          # Python dependencies
│
├── dataset/
│   ├── machine_data.csv      # Generated training dataset (5000 records)
│   └── uploaded_logs/        # Uploaded CSV files for batch prediction
│
├── model/
│   ├── breakdown_model.pkl   # Trained RF + GB ensemble model
│   └── scaler.pkl            # StandardScaler
│
├── templates/
│   └── index.html            # Main dashboard (Jinja2 template)
│
├── static/
│   ├── css/style.css         # Industrial dark theme CSS
│   └── js/script.js          # Chart.js + API calls frontend
│
├── utils/
│   ├── preprocess.py         # Input validation & sensor normalization
│   ├── predictor.py          # ML inference engine (RF + GB ensemble)
│   ├── db_helper.py          # Database CRUD operations
│   └── chart_helper.py       # Plotly/Chart.js data formatters
│
└── reports/                  # Exported prediction CSVs
```

---

## ⚙️ Setup Instructions (VS Code)

### 1. Create & activate virtual environment
```bash
cd jsw_breakdown
python -m venv venv
# Windows:
venv\Scripts\activate
# Mac/Linux:
source venv/bin/activate
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Train the ML model (generates dataset + trains Random Forest + Gradient Boosting)
```bash
python train_model.py
```
Expected output:
- 5000-record synthetic dataset saved to `dataset/machine_data.csv`
- Ensemble model saved to `model/breakdown_model.pkl`
- Scaler saved to `model/scaler.pkl`
- Accuracy ~92%+, ROC-AUC ~0.97+

### 4. Start the Flask server
```bash
python app.py
```

### 5. Open the dashboard
Navigate to: **http://localhost:5000**

---

## 🤖 ML Model Details

| Component            | Details                            |
|----------------------|------------------------------------|
| Primary Model        | Random Forest (200 trees)          |
| Secondary Model      | Gradient Boosting (100 estimators) |
| Ensemble Strategy    | Weighted average (60% RF, 40% GB)  |
| Feature Scaling      | StandardScaler                     |
| Class Balancing      | `class_weight='balanced'`          |
| Train/Test Split     | 80% / 20% stratified               |

### Input Features (8 sensor parameters)

| Feature                  | Range         | Unit  |
|--------------------------|---------------|-------|
| Temperature              | 30 – 130      | °C    |
| Vibration                | 0.5 – 12      | mm/s  |
| Pressure                 | 60 – 200      | bar   |
| RPM                      | 500 – 3000    | RPM   |
| Current Load             | 10 – 100      | %     |
| Oil Level                | 5 – 100       | %     |
| Noise Level              | 50 – 115      | dB    |
| Hours Since Maintenance  | 0 – 1200      | hrs   |

### Risk Levels

| Score Range | Level    | Action                                  |
|-------------|----------|-----------------------------------------|
| 0–29%       | LOW      | Normal operation                        |
| 30–49%      | MEDIUM   | Monitor; schedule maintenance in 72 hrs |
| 50–74%      | HIGH     | Urgent maintenance within 24 hrs        |
| 75–100%     | CRITICAL | Immediate shutdown required             |

---

## 🌐 API Endpoints

| Method | Endpoint                          | Description                    |
|--------|-----------------------------------|--------------------------------|
| GET    | `/`                               | Dashboard UI                   |
| GET    | `/api/stats`                      | KPI statistics                 |
| GET    | `/api/machines`                   | All machines + latest risk     |
| POST   | `/api/predict`                    | Single sensor prediction       |
| POST   | `/api/predict/batch`              | CSV batch prediction           |
| GET    | `/api/predictions`                | Prediction history             |
| GET    | `/api/alerts`                     | System alerts                  |
| POST   | `/api/alerts/<id>/acknowledge`    | Acknowledge an alert           |
| GET    | `/api/charts/distribution`        | Risk distribution pie data     |
| GET    | `/api/charts/trend`               | Risk trend line data           |
| GET    | `/api/charts/importance`          | Feature importance bar data    |
| GET    | `/api/charts/timeline`            | Breakdown timeline bar data    |
| GET    | `/api/feature-ranges`             | Sensor ranges for frontend     |

---

## 📊 Dashboard Features

- **Dashboard** — KPI cards, breakdown timeline, risk distribution, machine health grid
- **Predict** — Real-time sensor input with sliders, prediction gauge, radar chart, confidence bars
- **Analytics** — Risk trend over time, feature importance, filterable prediction log table, CSV export
- **Machines** — Full machine registry with latest risk scores
- **Alerts** — Alert management with severity levels and acknowledgement

---

## 📂 CSV Batch Upload Format

```csv
temperature,vibration,pressure,rpm,current_load,oil_level,noise_level,hours_since_maintenance
72.5,3.2,118,1450,78,82,71,245
95.1,6.8,165,2100,94,28,96,720
```

---

## 🔧 Recommended VS Code Extensions

- Python (ms-python.python)
- Pylance
- Flask Snippets
- Thunder Client (API testing)

---

## 📝 License
Internal JSW use only. © 2025 JSW Group.
=======
# Machine-breakdown
>>>>>>> 38e28b59413b88a262e3561c953cb9b0e1007eed
