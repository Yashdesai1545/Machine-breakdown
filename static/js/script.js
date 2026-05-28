/**
 * JSW Machine Breakdown Prediction System — script.js
 * MySQL edition | 500-record dataset | Dynamic dropdowns & charts
 */

"use strict";

const API = "";
let featureRanges  = {};
let dbMachines     = [];   // from MySQL (risk scores)
let csvMachines    = [];   // all 60 from CSV (dropdowns & grid)
let csvFullRows    = [];   // full CSV rows (e.g. 500 records)
let charts         = {};
let radarChart     = null;
let gaugeChart     = null;
let datasetRadarChart = null;
let predTableData  = [];

// ══════════════════ INIT ══════════════════
document.addEventListener("DOMContentLoaded", async () => {
  startClock();
  setupNavigation();
  await Promise.all([loadFeatureRanges(), loadDbMachines(), loadCsvMachines()]);
  buildSensorInputs();
  populateMachineSelects();
  await loadDashboard();
});

// ══════════════════ CLOCK ══════════════════
function startClock() {
  const el   = document.getElementById("clock");
  const tick = () => {
    el.textContent = new Date().toLocaleString("en-IN", {
      dateStyle: "medium",
      timeStyle: "medium",
      hour12: false
    });
  };
  tick();
  setInterval(tick, 1000);
}

// ══════════════════ NAVIGATION ══════════════════
function setupNavigation() {
  document.querySelectorAll(".nav-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      const section = btn.dataset.section;
      document.querySelectorAll(".nav-btn").forEach(b => b.classList.remove("active"));
      document.querySelectorAll(".section").forEach(s => s.classList.remove("active"));
      btn.classList.add("active");
      document.getElementById(`section-${section}`).classList.add("active");
      if (section === "analytics") loadAnalytics();
      if (section === "machines")  renderMachinesGrid();
      if (section === "alerts")    loadAlerts();
    });
  });
}

// ══════════════════ DATA LOADERS ══════════════════
async function loadFeatureRanges() {
  try {
    const res  = await fetch(`${API}/api/feature-ranges`);
    featureRanges = await res.json();
  } catch (e) { console.error("Feature ranges load failed", e); }
}

async function loadDbMachines() {
  try {
    const res  = await fetch(`${API}/api/machines`);
    const data = await res.json();
    if (data.success) dbMachines = data.data;
  } catch (e) { console.error("DB machines load failed", e); }
}

async function loadCsvMachines() {
  try {
    const [uniqueRes, fullRes] = await Promise.all([
      fetch(`${API}/api/csv-machines`),
      fetch(`${API}/api/csv-machines?unique=0`)
    ]);
    const uniqueData = await uniqueRes.json();
    const fullData   = await fullRes.json();
    if (uniqueData.success) csvMachines = uniqueData.data;
    if (fullData.success) csvFullRows = fullData.data;
  } catch (e) { console.error("CSV machines load failed", e); }
}

async function loadDashboard() {
  await Promise.all([
    loadStats(),
    loadTimeline(),
    loadDistributionChart(),
    loadDatasetCharts(),
  ]);
}

async function loadStats() {
  try {
    const res  = await fetch(`${API}/api/stats`);
    const data = await res.json();
    if (data.success) {
      const s = data.data;
      const machinesEl = document.getElementById("kpi-machines");
      if (machinesEl) machinesEl.textContent = s.total_machines;
      document.getElementById("kpi-predictions").textContent = s.predictions_today;
      document.getElementById("kpi-critical").textContent    = s.critical_today;
      document.getElementById("kpi-alerts").textContent      = s.unacknowledged_alerts;
      document.getElementById("alert-badge").textContent     = s.unacknowledged_alerts;
    }
  } catch (e) { console.error("Stats load failed", e); }
}

async function loadTimeline() {
  const days = document.getElementById("timeline-days")?.value || 30;
  try {
    const res  = await fetch(`${API}/api/charts/timeline?days=${days}`);
    renderTimelineChart(await res.json());
  } catch (e) { console.error("Timeline failed", e); }
}

async function loadDistributionChart() {
  try {
    const res  = await fetch(`${API}/api/charts/distribution`);
    renderDistributionChart(await res.json());
  } catch (e) { console.error("Distribution failed", e); }
}


// ══════════════════ DATASET CHARTS (Dashboard) ══════════════════
async function loadDatasetCharts() {
  try {
    const [typeRes, causesRes, toolRes, machineRes, sensorRes] = await Promise.all([
      fetch(`${API}/api/dataset/failure-by-type`),
      fetch(`${API}/api/dataset/failure-causes`),
      fetch(`${API}/api/dataset/tool-wear-bins`),
      fetch(`${API}/api/dataset/failure-by-machine`),
      fetch(`${API}/api/dataset/sensor-stats`),
    ]);
    renderTypeFailureChart(await typeRes.json());
    renderFailureCausesChart(await causesRes.json());
    renderToolWearBinsChart(await toolRes.json());
    renderMachineFailuresChart(await machineRes.json());
    renderSensorComparisonChart(await sensorRes.json());
  } catch (e) { console.error("Dataset charts failed", e); }
}

function renderTypeFailureChart(data) {
  if (!data.success) return;
  destroyChart("type-failure");
  const ctx = document.getElementById("chart-type-failure").getContext("2d");
  charts["type-failure"] = new Chart(ctx, {
    type: "bar",
    data: {
      labels: data.labels,
      datasets: [
        { label: "Total Machines", data: data.total,    backgroundColor: "rgba(59,130,246,0.5)", borderColor: "#3b82f6", borderWidth: 1 },
        { label: "Failures",       data: data.failures, backgroundColor: "rgba(26,86,219,0.7)",  borderColor: "#1a56db", borderWidth: 1 },
      ]
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: {
        ...chartDefaults.plugins,
        tooltip: {
          ...chartDefaults.plugins.tooltip,
          callbacks: {
            afterBody: (items) => {
              const i = items[0].dataIndex;
              return `Failure Rate: ${data.failure_rates[i]}%`;
            }
          }
        }
      },
      scales: chartDefaults.scales,
    }
  });
}

function renderFailureCausesChart(data) {
  if (!data.success) return;
  destroyChart("failure-causes");
  const ctx = document.getElementById("chart-failure-causes").getContext("2d");
  charts["failure-causes"] = new Chart(ctx, {
    type: "doughnut",
    data: {
      labels: data.labels,
      datasets: [{ data: data.values,
        backgroundColor: ["#1a56db","#60a5fa","#93c5fd","#3b82f6","#60a5fa"],
        borderColor: "#0e1117", borderWidth: 3 }]
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: {
        legend: { position: "bottom", labels: { color: "#8b98b4", padding: 10, font: { size: 11 } } },
        tooltip: chartDefaults.plugins.tooltip,
      },
      cutout: "60%"
    }
  });
}

function renderToolWearBinsChart(data) {
  if (!data.success) return;
  destroyChart("toolwear-bins");
  const ctx = document.getElementById("chart-toolwear-bins").getContext("2d");
  charts["toolwear-bins"] = new Chart(ctx, {
    type: "bar",
    data: {
      labels: data.labels,
      datasets: [
        { label: "Total",    data: data.total,    backgroundColor: "rgba(59,130,246,0.4)", borderColor: "#3b82f6", borderWidth: 1 },
        { label: "Failures", data: data.failures, backgroundColor: "rgba(26,86,219,0.7)",  borderColor: "#1a56db", borderWidth: 1 },
      ]
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: chartDefaults.plugins,
      scales: {
        x: { ...chartDefaults.scales.x, title: { display: true, text: "Tool Wear (min)", color: "#8b98b4" } },
        y: chartDefaults.scales.y,
      }
    }
  });
}

function renderMachineFailuresChart(data) {
  if (!data.success) return;
  destroyChart("machine-failures");
  const ctx = document.getElementById("chart-machine-failures").getContext("2d");
  const colors = data.failures.map(v => v > 3 ? "#ef4444" : v > 1 ? "#f97316" : "#3b82f6");
  charts["machine-failures"] = new Chart(ctx, {
    type: "bar",
    data: {
      labels: data.labels,
      datasets: [{ label: "Failure Count", data: data.failures, backgroundColor: colors, borderRadius: 4 }]
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      indexAxis: "y",
      plugins: chartDefaults.plugins,
      scales: {
        x: chartDefaults.scales.x,
        y: { ticks: { color: "#8b98b4", font: { size: 10 } }, grid: { color: "#1e2840" } }
      }
    }
  });
}

function renderSensorComparisonChart(data) {
  if (!data.success) return;
  destroyChart("sensor-comparison");
  const ctx = document.getElementById("chart-sensor-comparison").getContext("2d");
  const labels     = data.data.map(d => d.feature);
  const normals    = data.data.map(d => d.mean_normal);
  const failures   = data.data.map(d => d.mean_failure);
  charts["sensor-comparison"] = new Chart(ctx, {
    type: "radar",
    data: {
      labels,
      datasets: [
        { label: "Normal (No Failure)", data: normals.map((v,i) => normalizeForRadar(v, i, data.data)),
          borderColor: "#22c55e", backgroundColor: "rgba(34,197,94,0.15)", pointBackgroundColor: "#22c55e", pointRadius: 4 },
        { label: "Failure",             data: failures.map((v,i) => normalizeForRadar(v, i, data.data)),
          borderColor: "#ef4444", backgroundColor: "rgba(239,68,68,0.15)", pointBackgroundColor: "#ef4444", pointRadius: 4 },
      ]
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: chartDefaults.plugins,
      scales: {
        r: {
          angleLines:  { color: "#1e2840" },
          grid:        { color: "#1e2840" },
          pointLabels: { color: "#8b98b4", font: { size: 10 } },
          ticks:       { color: "#4a5568", backdropColor: "transparent", display: false },
          min: 0, max: 100
        }
      }
    }
  });
}

// Normalize sensor values 0-100 relative to the min-max across both groups
function normalizeForRadar(value, idx, dataArr) {
  const d   = dataArr[idx];
  const min = Math.min(d.mean_normal, d.mean_failure) * 0.95;
  const max = Math.max(d.mean_normal, d.mean_failure) * 1.05;
  if (max === min) return 50;
  return Math.round(((value - min) / (max - min)) * 100);
}

function getMachineSelectSource(selectId) {
  return selectId === "analytics-machine"
    ? csvMachines
    : (csvFullRows.length ? csvFullRows : csvMachines);
}

function filterMachineSelect(selectId, searchId) {
  const select = document.getElementById(selectId);
  const search = document.getElementById(searchId);
  if (!select) return;

  const query = (search?.value || "").trim().toLowerCase();
  const source = getMachineSelectSource(selectId);
  const options = source.filter(m => {
    const text = `${m.machine_name} ${m.product_id}`.toLowerCase();
    return query === "" || text.includes(query);
  });

  const defaultOption = selectId === "analytics-machine"
    ? '<option value="">All Machines</option>'
    : '<option value="">-- Select Machine --</option>';

  select.innerHTML = defaultOption + options.map(m => {
    if (selectId === "pred-machine") {
      return `<option value="${m.product_id}" data-machine-name="${m.machine_name}">${m.machine_name} (${m.product_id})</option>`;
    }
    return `<option value="${m.machine_name}">${m.machine_name} (${m.product_id})</option>`;
  }).join("");
}

// ══════════════════ MACHINE SELECTS — from CSV dataset ══════════════════
function searchMachineOnEnter(event, selectId, searchId) {
  if (event.key !== "Enter") return;
  event.preventDefault();
  selectMachineFromSearch(selectId, searchId);
}

function selectMachineFromSearch(selectId, searchId) {
  const select = document.getElementById(selectId);
  const search = document.getElementById(searchId);
  if (!select || !search) return;

  const query = (search.value || "").trim().toLowerCase();
  if (!query) return;

  filterMachineSelect(selectId, searchId);
  const options = Array.from(select.querySelectorAll("option[value]:not([value=''])"));
  if (!options.length) {
    showToast("No machine found for that ID or name", "warning");
    return;
  }

  const exact = options.find(opt => {
    const text = opt.textContent.toLowerCase();
    return text === query || text.includes(`(${query})`) || text.startsWith(query + " ") || text.includes(query);
  });

  const option = exact || options[0];
  select.value = option.value;

  if (selectId === "pred-machine") {
    loadSelectedMachineSensors();
  } else if (selectId === "analytics-machine") {
    loadAnalytics();
  }
}

function populateMachineSelects() {
  filterMachineSelect("pred-machine", "pred-machine-search");
  filterMachineSelect("analytics-machine", "analytics-machine-search");
}

// ══════════════════ MACHINES GRID — 60 real CSV machines (+ search/filter) ══════════════════
let _allMachineCards = [];

function renderMachinesGrid() {
  const grid = document.getElementById("machines-grid");
  const riskMap = {};
  dbMachines.forEach(m => { riskMap[m.machine_name] = m; });

  const source = csvFullRows.length ? csvFullRows : csvMachines;

  _allMachineCards = source.map(m => {
    const db       = riskMap[m.machine_name] || {};
    const score    = db.latest_risk_score || 0;
    const level    = db.latest_risk_level || "UNKNOWN";
    const typeLabel = m.machine_type === "H" ? "Heavy" : m.machine_type === "M" ? "Medium" : "Light";
    return {
      machine_type: m.machine_type,
      machine_name: m.machine_name,
      html: `
        <div class="machine-card" data-type="${m.machine_type}" data-name="${m.machine_name.toLowerCase()}">
          <div class="mc-header">
            <span class="mc-id">${m.product_id}</span>
            <span class="risk-pill ${level}">${level}</span>
          </div>
          <div class="mc-name">${m.machine_name}</div>
          <div class="mc-dept">⚙ Type: ${typeLabel}</div>
          <div class="mc-info">
            <span>Product ID <strong>${m.product_id}</strong></span>
            <span>Machine Type <strong>${m.machine_type}</strong></span>
          </div>
          <div class="mc-risk">
            <span class="mc-risk-label">Latest Risk Score</span>
            <strong style="color:${riskColor(level)};font-family:var(--font-display);font-size:18px">
              ${score ? score.toFixed(1) + "%" : "—"}
            </strong>
          </div>
        </div>`
    };
  });

  const badge = document.getElementById("machines-count-badge");
  const count = source.length;
  if (badge) badge.textContent = `${count} machines`;

  grid.innerHTML = _allMachineCards.map(c => c.html).join("");
}

function filterMachinesGrid() {
  const search = (document.getElementById("machines-search")?.value || "").toLowerCase();
  const type   = document.getElementById("machines-type-filter")?.value || "";
  const grid   = document.getElementById("machines-grid");

  const filtered = _allMachineCards.filter(c =>
    (type === "" || c.machine_type === type) &&
    (search === "" || c.machine_name.toLowerCase().includes(search))
  );

  const badge = document.getElementById("machines-count-badge");
  if (badge) badge.textContent = `${filtered.length} of ${_allMachineCards.length} machines`;

  grid.innerHTML = filtered.length
    ? filtered.map(c => c.html).join("")
    : `<div style="color:var(--text-dim);text-align:center;padding:40px;grid-column:1/-1">No machines match the filter</div>`;
}

// ══════════════════ ANALYTICS ══════════════════
async function loadAnalytics() {
  const mode = document.getElementById("analytics-mode")?.value || "db";
  if (mode === "dataset") {
    await loadDatasetAnalytics();
  } else {
    await loadDbAnalytics();
  }
}

function switchAnalyticsMode() {
  const mode    = document.getElementById("analytics-mode")?.value || "db";
  const dbView  = document.getElementById("analytics-db-view");
  const dsView  = document.getElementById("analytics-dataset-view");
  if (mode === "dataset") {
    dbView.style.display = "none";
    dsView.style.display = "block";
    loadDatasetAnalytics();
  } else {
    dbView.style.display = "block";
    dsView.style.display = "none";
    loadDbAnalytics();
  }
}

async function loadDbAnalytics() {
  // Use analytics-machine as a DB machine_id (look up from dbMachines by name)
  const machineName = document.getElementById("analytics-machine").value;
  const days        = document.getElementById("analytics-days").value;

  // Map machine_name → machine_id for the trend endpoint
  let machineId = "";
  if (machineName) {
    const dbMatch = dbMachines.find(m => m.machine_name === machineName);
    machineId = dbMatch ? dbMatch.machine_id : "JSW-BLF-01";
  }

  const trendUrl = `${API}/api/charts/trend?machine_id=${machineId || "JSW-BLF-01"}&days=${days}`;

  try {
    const [trendRes, importRes, predRes] = await Promise.all([
      fetch(trendUrl),
      fetch(`${API}/api/charts/importance`),
      fetch(`${API}/api/predictions?machine_id=${machineId}&limit=100`)
    ]);
    renderTrendChart(await trendRes.json());
    renderImportanceChart(await importRes.json());
    const pData = await predRes.json();
    if (pData.success) { predTableData = pData.data; renderPredTable(); }
  } catch (e) { console.error("Analytics (DB) failed", e); }
}

async function loadDatasetAnalytics() {
  const machineName = document.getElementById("analytics-machine")?.value || "";
  const titleEl     = document.getElementById("dataset-profile-title");
  if (titleEl) titleEl.textContent = machineName
    ? `Sensor Profile — ${machineName} (Dataset)`
    : "Sensor Profile — All Machines (Dataset Avg)";

  try {
    const [profileRes, typeRes] = await Promise.all([
      fetch(`${API}/api/dataset/machine-sensor-profile?machine=${encodeURIComponent(machineName)}`),
      fetch(`${API}/api/dataset/failure-by-type`),
    ]);
    const profile = await profileRes.json();
    const typeData = await typeRes.json();

    if (profile.success) renderDatasetRadarChart(profile.data);
    if (typeData.success) renderAnalyticsTypeChart(typeData);

    // Show stats cards
    if (profile.success) renderDatasetProfileStats(profile.data);
  } catch (e) { console.error("Analytics (Dataset) failed", e); }
}

function renderDatasetRadarChart(profile) {
  if (datasetRadarChart) { datasetRadarChart.destroy(); datasetRadarChart = null; }
  const ctx    = document.getElementById("chart-dataset-radar")?.getContext("2d");
  if (!ctx) return;
  const labels = ["Air Temp (K)", "Process Temp (K)", "Speed (RPM)", "Torque (Nm)", "Tool Wear (min)", "Vibration (mm/s)"];
  const raw    = [
    profile.air_temperature, profile.process_temperature,
    profile.rotational_speed, profile.torque, profile.tool_wear, profile.vibration
  ];
  const ranges = [
    [295, 310], [306, 318], [1100, 1800], [30, 90], [0, 260], [0.2, 6.0]
  ];
  const normalized = raw.map((v, i) => {
    const [lo, hi] = ranges[i];
    return Math.round(((v - lo) / (hi - lo)) * 100);
  });

  datasetRadarChart = new Chart(ctx, {
    type: "radar",
    data: {
      labels,
      datasets: [{
        label: profile.machine_name,
        data: normalized,
        borderColor: "#3b82f6",
        backgroundColor: "rgba(59,130,246,0.2)",
        pointBackgroundColor: "#3b82f6",
        pointRadius: 5
      }]
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: chartDefaults.plugins,
      scales: {
        r: {
          angleLines:  { color: "#1e2840" },
          grid:        { color: "#1e2840" },
          pointLabels: { color: "#8b98b4", font: { size: 11 } },
          ticks:       { color: "#4a5568", backdropColor: "transparent" },
          min: 0, max: 100
        }
      }
    }
  });
}

function renderAnalyticsTypeChart(data) {
  destroyChart("analytics-type");
  const ctx = document.getElementById("chart-analytics-type")?.getContext("2d");
  if (!ctx) return;
  charts["analytics-type"] = new Chart(ctx, {
    type: "bar",
    data: {
      labels: data.labels,
      datasets: [{
        label: "Failure Rate %",
        data: data.failure_rates,
        backgroundColor: ["rgba(239,68,68,0.7)","rgba(245,158,11,0.7)","rgba(34,197,94,0.7)"],
        borderColor:     ["#ef4444","#f59e0b","#22c55e"],
        borderWidth: 1, borderRadius: 6
      }]
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: chartDefaults.plugins,
      scales: {
        x: chartDefaults.scales.x,
        y: { ...chartDefaults.scales.y, ticks: { ...chartDefaults.scales.y.ticks, callback: v => v + "%" } }
      }
    }
  });
}

function renderDatasetProfileStats(profile) {
  const box = document.getElementById("dataset-profile-stats");
  if (!box) return;
  const stats = [
    { label: "Avg Air Temp",      value: profile.air_temperature + " K",      icon: "🌡" },
    { label: "Avg Process Temp",  value: profile.process_temperature + " K",   icon: "🔥" },
    { label: "Avg Rotational Speed", value: profile.rotational_speed + " RPM", icon: "⚙" },
    { label: "Avg Torque",        value: profile.torque + " Nm",               icon: "🔩" },
    { label: "Avg Tool Wear",     value: profile.tool_wear + " min",           icon: "🛠" },
    { label: "Avg Vibration",     value: profile.vibration + " mm/s",          icon: "📳" },
  ];
  box.innerHTML = `<div class="dataset-stats-grid">` +
    stats.map(s => `
      <div class="ds-stat-card">
        <span class="ds-stat-icon">${s.icon}</span>
        <div class="ds-stat-label">${s.label}</div>
        <div class="ds-stat-value" style="${s.highlight ? "color:" + s.highlight : ""}">${s.value}</div>
      </div>`).join("") +
    `</div>`;
}

async function loadAlerts() {
  try {
    const res  = await fetch(`${API}/api/alerts`);
    const data = await res.json();
    if (!data.success) return;
    const list = document.getElementById("alerts-list");
    if (!data.data.length) {
      list.innerHTML = `<div style="color:var(--text-dim);text-align:center;padding:40px">No alerts found</div>`;
      return;
    }
    list.innerHTML = data.data.map(a => {
      const icon = a.severity === "critical" ? "🚨" : a.severity === "high" ? "⚠️" : "ℹ️";
      const ackd = a.acknowledged ? " acknowledged" : "";
      return `
        <div class="alert-item ${a.severity}${ackd}" id="alert-${a.id}">
          <div class="alert-icon">${icon}</div>
          <div class="alert-body">
            <div class="alert-machine">${a.machine_id} — ${a.alert_type}</div>
            <div class="alert-message">${a.message}</div>
            <div class="alert-time">${formatTime(a.timestamp)}</div>
          </div>
          <div class="alert-actions">
            <span class="risk-pill ${(a.severity||"").toUpperCase()}">${a.severity}</span>
            ${!a.acknowledged
              ? `<button class="btn-ack" onclick="ackAlert(${a.id})">Acknowledge</button>`
              : `<span style="color:var(--text-dim);font-size:12px">✓ Acked</span>`}
          </div>
        </div>`;
    }).join("");
  } catch (e) { console.error("Alerts failed", e); }
}

async function ackAlert(id) {
  await fetch(`${API}/api/alerts/${id}/acknowledge`, { method: "POST" });
  document.getElementById(`alert-${id}`)?.classList.add("acknowledged");
  loadStats();
  showToast("Alert acknowledged", "success");
}

// ══════════════════ SENSOR INPUTS ══════════════════
function buildSensorInputs() {
  const grid = document.getElementById("sensor-inputs");
  grid.innerHTML = Object.entries(featureRanges).map(([key, r]) => `
    <div class="sensor-item">
      <label>
        ${key.replace(/_/g, " ")}
        <span id="lbl-${key}">-- ${r.unit}</span>
      </label>
      <input type="number" id="inp-${key}" class="sensor-input"
        min="${r.min}" max="${r.max}" step="${key === "rotational_speed" || key === "tool_wear" ? 1 : 0.1}"
        placeholder="${r.default}"
        value=""
        onchange="updateSensorLabel('${key}')"
        oninput="updateSensorLabel('${key}')"/>
    </div>`).join("");
}

function updateSensorLabel(key) {
  const r   = featureRanges[key];
  const el  = document.getElementById(`inp-${key}`);
  const lbl = document.getElementById(`lbl-${key}`);
  const val = parseFloat(el.value);
  if (Number.isNaN(val)) {
    lbl.textContent = `-- ${r.unit}`;
    el.classList.remove("warn", "crit");
    return;
  }
  lbl.textContent = `${val} ${r.unit}`;
  el.classList.remove("warn", "crit");
  const pct = (val - r.min) / (r.max - r.min);
  if (pct > 0.9) el.classList.add("crit");
  else if (pct > 0.7) el.classList.add("warn");
}

function getSensorValues() {
  const vals = {};
  for (const key of Object.keys(featureRanges)) {
    const value = parseFloat(document.getElementById(`inp-${key}`).value);
    vals[key] = Number.isNaN(value) ? null : value;
  }
  return vals;
}


function resetSensors() {
  for (const [key, r] of Object.entries(featureRanges)) {
    const input = document.getElementById(`inp-${key}`);
    input.value = "";
    updateSensorLabel(key);
    input.classList.remove("warn", "crit");
  }
}

async function loadSelectedMachineSensors() {
  const machineId = document.getElementById("pred-machine")?.value;
  if (!machineId) {
    resetSensors();
    return;
  }

  const selectedOption = document.getElementById("pred-machine")?.selectedOptions?.[0];
  const machineName   = selectedOption?.dataset.machineName || machineId;

  try {
    // Prefer exact CSV row values from machine-samples (more accurate)
    let found = false;
    try {
      const samplesRes = await fetch(`${API}/api/machine-samples`);
      const samplesData = await samplesRes.json();
      if (samplesData.success) {
        const match = samplesData.data.find(r => r.machine_id === machineId);
        if (match) {
          const map = {
            air_temperature:     match.air_temperature,
            process_temperature: match.process_temperature,
            rotational_speed:    match.rotational_speed,
            torque:              match.torque,
            tool_wear:           match.tool_wear,
            vibration:           match.vibration,
          };
          for (const [key, val] of Object.entries(map)) {
            const el = document.getElementById(`inp-${key}`);
            if (el) { el.value = val; updateSensorLabel(key); }
          }
          showToast(`Loaded exact CSV sample for ${machineName}`, "success");
          found = true;
        }
      }
    } catch (e) {
      console.warn("machine-samples fetch failed, falling back to profile", e);
    }

    if (!found) {
      // Fallback: averaged sensor profile from dataset endpoint
      const res  = await fetch(`${API}/api/dataset/machine-sensor-profile?machine_id=${encodeURIComponent(machineId)}`);
      const data = await res.json();
      if (!data.success) return;
      const p = data.data;
      const map = {
        air_temperature:     p.air_temperature,
        process_temperature: p.process_temperature,
        rotational_speed:    p.rotational_speed,
        torque:              p.torque,
        tool_wear:           p.tool_wear,
        vibration:           p.vibration,
      };
      for (const [key, val] of Object.entries(map)) {
        const el = document.getElementById(`inp-${key}`);
        if (el) { el.value = val; updateSensorLabel(key); }
      }
      showToast(`Loaded sensor profile for ${machineName}`, "success");
    }
  } catch (e) { console.error("loadSelectedMachineSensors failed", e); }
}

function quickPredict(machineId) {
  document.querySelectorAll(".nav-btn").forEach(b => b.classList.remove("active"));
  document.querySelectorAll(".section").forEach(s => s.classList.remove("active"));
  document.querySelector('[data-section="predict"]').classList.add("active");
  document.getElementById("section-predict").classList.add("active");
}

// ══════════════════ PREDICTION ══════════════════
async function runPrediction() {
  const machineId = document.getElementById("pred-machine").value;
  if (!machineId) { showToast("Please select a machine", "warning"); return; }
  const sensor = getSensorValues();
  if (Object.values(sensor).some(v => v === null)) {
    showToast("Please load sensor values by selecting a machine first", "warning");
    return;
  }

  showLoading(true);
  try {
    const res  = await fetch(`${API}/api/predict`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ machine_id: machineId, ...sensor })
    });
    const data = await res.json();
    if (!data.success) { showToast("Prediction failed: " + data.error, "error"); return; }
    renderPredictionResult(data.prediction, data.radar);
    showToast("Prediction complete!", "success");
    loadStats();
  } catch (e) {
    showToast("Server error: " + e.message, "error");
  } finally {
    showLoading(false);
  }
}

function renderPredictionResult(pred, radar) {
  document.getElementById("result-placeholder").style.display = "none";
  document.getElementById("result-content").style.display     = "block";

  const score = pred.risk_score;
  const level = pred.risk_level;

  document.getElementById("gauge-score").textContent = score.toFixed(1) + "%";
  document.getElementById("gauge-risk").textContent  = level;
  document.getElementById("gauge-score").style.color = riskColor(level);
  document.getElementById("gauge-risk").style.color  = riskColor(level);

  document.getElementById("rf-bar").style.width = pred.rf_confidence + "%";
  document.getElementById("gb-bar").style.width = pred.gb_confidence + "%";
  document.getElementById("rf-val").textContent = pred.rf_confidence.toFixed(1) + "%";
  document.getElementById("gb-val").textContent = pred.gb_confidence.toFixed(1) + "%";

  const recBox = document.getElementById("recommendation-box");
  recBox.className = "recommendation-box " + level;
  document.getElementById("recommendation-text").textContent = pred.recommendation;

  renderGauge(score, level);
  if (radar && radar.labels) renderRadarChart(radar);
}

// ══════════════════ CSV BATCH ══════════════════
async function uploadCSV(event) {
  const file = event.target.files[0];
  if (!file) return;
  const formData = new FormData();
  formData.append("file", file);
  showLoading(true);
  try {
    const res  = await fetch(`${API}/api/predict/batch`, { method: "POST", body: formData });
    const data = await res.json();
    const box  = document.getElementById("batch-result");
    box.style.display = "block";
    if (data.success) {
      const bPct = (data.breakdown_count / data.total_records * 100).toFixed(1);
      box.innerHTML = `
        <div style="color:var(--accent-green);margin-bottom:8px">✅ Batch Complete</div>
        <div>📄 Total Records: <strong>${data.total_records}</strong></div>
        <div>⚠️ Predicted Breakdowns: <strong style="color:var(--accent-red)">${data.breakdown_count} (${bPct}%)</strong></div>`;
      showToast(`Batch: ${data.breakdown_count} breakdowns detected`, "warning");
    } else {
      box.innerHTML = `<div style="color:var(--accent-red)">❌ ${data.error}</div>`;
    }
  } catch (e) {
    showToast("Upload error: " + e.message, "error");
  } finally {
    showLoading(false);
  }
}

// ══════════════════ CHART RENDERERS ══════════════════
const chartDefaults = {
  plugins: {
    legend: { labels: { color: "#8b98b4", font: { family: "Exo 2", size: 12 } } },
    tooltip: { backgroundColor: "#141820", borderColor: "#1e2840", borderWidth: 1,
               titleColor: "#e2e8f0", bodyColor: "#8b98b4" }
  },
  scales: {
    x: { ticks: { color: "#8b98b4" }, grid: { color: "#1e2840" } },
    y: { ticks: { color: "#8b98b4" }, grid: { color: "#1e2840" } }
  }
};

function destroyChart(id) { if (charts[id]) { charts[id].destroy(); delete charts[id]; } }

function renderTimelineChart(data) {
  destroyChart("timeline");
  const ctx = document.getElementById("chart-timeline").getContext("2d");
  charts["timeline"] = new Chart(ctx, {
    type: "bar",
    data: {
      labels: data.x || [],
      datasets: [
        { type: "bar",  label: "Breakdown Events", data: data.breakdowns || [],
          backgroundColor: "rgba(239,68,68,0.6)", borderColor: "#ef4444", borderWidth: 1, yAxisID: "y1" },
        { type: "line", label: "Total Predictions", data: data.total || [],
          borderColor: "#3b82f6", backgroundColor: "rgba(59,130,246,0.1)",
          fill: true, tension: 0.4, pointRadius: 3, yAxisID: "y2" }
      ]
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: chartDefaults.plugins,
      scales: {
        x:  chartDefaults.scales.x,
        y1: { ticks: { color: "#ef4444" }, grid: { color: "#1e2840" }, position: "left" },
        y2: { ticks: { color: "#3b82f6" }, grid: { display: false }, position: "right" }
      }
    }
  });
}

function renderDistributionChart(data) {
  destroyChart("distribution");
  const ctx = document.getElementById("chart-distribution").getContext("2d");
  charts["distribution"] = new Chart(ctx, {
    type: "doughnut",
    data: {
      labels: data.labels || [],
      datasets: [{ data: data.values || [], backgroundColor: data.colors || [],
                   borderColor: "#0e1117", borderWidth: 3 }]
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: {
        legend: { position: "bottom", labels: { color: "#8b98b4", padding: 16 } },
        tooltip: chartDefaults.plugins.tooltip
      },
      cutout: "65%"
    }
  });
}

function renderTrendChart(data) {
  destroyChart("trend");
  const ctx = document.getElementById("chart-trend").getContext("2d");
  charts["trend"] = new Chart(ctx, {
    type: "line",
    data: {
      labels: data.x || [],
      datasets: [
        { label: "Avg Risk Score", data: data.y_avg || [], borderColor: "#3b82f6",
          backgroundColor: "rgba(59,130,246,0.1)", fill: true, tension: 0.4, pointRadius: 4,
          pointBackgroundColor: "#3b82f6" },
        { label: "Max Risk Score", data: data.y_max || [], borderColor: "#ef4444",
          backgroundColor: "transparent", borderDash: [4,4], tension: 0.4, pointRadius: 3 }
      ]
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: chartDefaults.plugins,
      scales: {
        x: chartDefaults.scales.x,
        y: { ...chartDefaults.scales.y, min: 0, max: 100,
             ticks: { ...chartDefaults.scales.y.ticks, callback: v => v + "%" } }
      }
    }
  });
}

function renderImportanceChart(data) {
  destroyChart("importance");
  if (!data.labels) return;
  const ctx = document.getElementById("chart-importance").getContext("2d");
  const colors = data.values.map(v =>
    v > 30 ? "#ef4444" : v > 20 ? "#f97316" : v > 12 ? "#f59e0b" : "#3b82f6"
  );
  charts["importance"] = new Chart(ctx, {
    type: "bar",
    data: {
      labels: data.labels,
      datasets: [{ label: "Importance %", data: data.values, backgroundColor: colors, borderRadius: 4 }]
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      indexAxis: "y",
      plugins: chartDefaults.plugins,
      scales: {
        x: { ...chartDefaults.scales.x, ticks: { ...chartDefaults.scales.x.ticks, callback: v => v + "%" } },
        y: chartDefaults.scales.y
      }
    }
  });
}

function renderGauge(score, level) {
  if (gaugeChart) { gaugeChart.destroy(); gaugeChart = null; }
  const ctx = document.getElementById("chart-gauge").getContext("2d");
  gaugeChart = new Chart(ctx, {
    type: "doughnut",
    data: {
      datasets: [{
        data: [score, 100 - score],
        backgroundColor: [riskColor(level), "#1e2840"],
        borderWidth: 0, circumference: 180, rotation: 270
      }]
    },
    options: {
      responsive: false, maintainAspectRatio: false,
      plugins: { legend: { display: false }, tooltip: { enabled: false } },
      cutout: "72%"
    }
  });
}

function renderRadarChart(data) {
  if (radarChart) { radarChart.destroy(); radarChart = null; }
  const ctx = document.getElementById("chart-radar").getContext("2d");
  radarChart = new Chart(ctx, {
    type: "radar",
    data: {
      labels: data.labels,
      datasets: [
        { label: "Current", data: data.current, borderColor: "#ef4444",
          backgroundColor: "rgba(239,68,68,0.2)", pointBackgroundColor: "#ef4444", pointRadius: 4 },
        { label: "Normal",  data: data.normal,  borderColor: "#22c55e",
          backgroundColor: "rgba(34,197,94,0.1)", pointBackgroundColor: "#22c55e",
          pointRadius: 3, borderDash: [4,4] }
      ]
    },
    options: {
      responsive: true, maintainAspectRatio: true,
      plugins: chartDefaults.plugins,
      scales: {
        r: {
          angleLines:  { color: "#1e2840" },
          grid:        { color: "#1e2840" },
          pointLabels: { color: "#8b98b4", font: { size: 11, family: "Exo 2" } },
          ticks:       { color: "#4a5568", backdropColor: "transparent" },
          min: 0, max: 100
        }
      }
    }
  });
}

// ══════════════════ TABLE ══════════════════
function renderPredTable() {
  const tbody = document.getElementById("pred-table-body");
  if (!predTableData.length) {
    tbody.innerHTML = `<tr><td colspan="12" class="table-empty">No predictions yet — run a prediction first</td></tr>`;
    return;
  }
  tbody.innerHTML = predTableData.map((p, i) => {
    const color  = riskColor(p.risk_level);
    const bdFlag = p.predicted_breakdown
      ? `<span style="color:var(--accent-red)">⚠ YES</span>`
      : `<span style="color:var(--accent-green)">✓ NO</span>`;
    return `<tr>
      <td>${i+1}</td>
      <td style="color:var(--accent-cyan)">${p.machine_id}</td>
      <td>${formatTime(p.timestamp)}</td>
      <td>${p.air_temperature?.toFixed(1) ?? "—"}</td>
      <td>${p.process_temperature?.toFixed(1) ?? "—"}</td>
      <td>${p.rotational_speed?.toFixed(0) ?? "—"}</td>
      <td>${p.torque?.toFixed(1) ?? "—"}</td>
      <td>${p.tool_wear?.toFixed(0) ?? "—"}</td>
      <td>${p.vibration?.toFixed(2) ?? "—"}</td>
      <td><strong style="color:${color}">${p.risk_score?.toFixed(1)}%</strong></td>
      <td><span class="risk-pill ${p.risk_level}">${p.risk_level}</span></td>
      <td>${bdFlag}</td>
    </tr>`;
  }).join("");
}

function exportCSV() {
  if (!predTableData.length) { showToast("No data to export", "warning"); return; }
  const cols = ["machine_id","timestamp","air_temperature","process_temperature",
                "rotational_speed","torque","tool_wear","vibration",
                "risk_score","risk_level","predicted_breakdown"];
  const csv = [cols.join(","),
    ...predTableData.map(p => cols.map(c => p[c] ?? "").join(","))
  ].join("\n");
  const a = document.createElement("a");
  a.href = URL.createObjectURL(new Blob([csv], { type: "text/csv" }));
  a.download = `jsw_predictions_${Date.now()}.csv`;
  a.click();
  showToast("CSV exported!", "success");
}

// ══════════════════ UTILS ══════════════════
function riskColor(level) {
  return { LOW:"#22c55e", MEDIUM:"#f59e0b", HIGH:"#f97316", CRITICAL:"#ef4444" }[level] || "#4a5568";
}

function formatTime(ts) {
  if (!ts) return "—";
  return new Date(ts).toLocaleString("en-IN", { dateStyle: "short", timeStyle: "short" });
}

function showToast(msg, type = "info") {
  const el = document.getElementById("toast");
  el.textContent = msg;
  el.className = `toast ${type} show`;
  clearTimeout(el._timer);
  el._timer = setTimeout(() => el.classList.remove("show"), 3500);
}

function showLoading(show) {
  document.getElementById("loading").style.display = show ? "flex" : "none";
}
