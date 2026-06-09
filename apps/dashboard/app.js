/** AXON Phase 5 live telemetry, model scores, and digital twin dashboard. */

const SIGNALS = [
  { key: "emg", label: "EMG" },
  { key: "ecg_like", label: "ECG-like" },
  { key: "imu", label: "IMU" },
  { key: "spo2_proxy", label: "SpO2-proxy" },
  { key: "robot_state", label: "Robot State" },
];

const MODELS = [
  { key: "emg_anomaly", label: "EMG Anomaly-like" },
  { key: "imu_movement", label: "IMU Movement-risk-like" },
];

const config = window.AXON_CONFIG || { apiBase: "http://localhost:8000", wsBase: "ws://localhost:8000" };

const state = {
  events: [],
  modelScores: [],
  traces: [],
  decisions: [],
  currentDecisionId: null,
  safety: {},
  counters: Object.fromEntries(SIGNALS.map((s) => [s.key, 0])),
  sparkHistory: Object.fromEntries(SIGNALS.map((s) => [s.key, []])),
  latestScores: {},
  latencyHistory: [],
  scenario: "—",
  mode: "awaiting",
  twin: null,
  wsStatus: {},
  proof: {
    sensors: 0,
    scores: 0,
    agents: 0,
    decisions: 0,
    safety: 0,
    twin: 0,
    lastTelemetryAt: null,
    lastScoreAt: null,
    lastMissionAt: null,
    traceId: null,
    commandId: null,
    decisionId: null,
  },
  actionLog: [],
};

const WS_STATUS_IDS = [
  "ws-sensors-status",
  "ws-robot-status",
  "ws-model-scores-status",
  "ws-agents-status",
  "ws-decisions-status",
  "ws-safety-status",
  "ws-twin-status",
  "ws-nav-slam-status",
];

const SENSOR_STATUS_CLASS = {
  active: "status-active",
  stale: "status-stale",
  dropout: "status-dropout",
  degraded: "status-degraded",
  corrupt: "status-corrupt",
};

function setDot(id, online, waiting = false) {
  const el = document.getElementById(id);
  state.wsStatus[id] = !!online;
  if (el) {
    el.className = "dot " + (online ? "online" : waiting ? "waiting" : "offline");
  }
  updateWsConnectedCount();
}

function updateWsConnectedCount() {
  const online = WS_STATUS_IDS.filter((id) => state.wsStatus[id]).length;
  const el = document.getElementById("proof-ws-connected");
  if (el) el.textContent = `${online} / ${WS_STATUS_IDS.length}`;
}

function initCards() {
  const container = document.getElementById("signal-cards");
  container.innerHTML = SIGNALS.map(
    (s) => `
    <div class="card" id="card-${s.key}">
      <h3>${s.label}</h3>
      <div class="metric" id="value-${s.key}">—</div>
      <canvas class="sparkline" id="spark-${s.key}" width="180" height="48"></canvas>
      <div class="sub">Quality: <span id="quality-${s.key}">—</span></div>
      <div class="sub">Updated: <span id="time-${s.key}">—</span></div>
    </div>`
  ).join("");
}

function initModelScoreCards() {
  const container = document.getElementById("model-score-cards");
  container.innerHTML = MODELS.map(
    (m) => `
    <div class="card model-card" id="model-card-${m.key}">
      <h3>${m.label}</h3>
      <div class="metric" id="score-${m.key}">—</div>
      <div class="sub">Label: <span id="label-${m.key}">—</span></div>
      <div class="sub">Confidence: <span id="confidence-${m.key}">—</span></div>
      <div class="sub">Latency: <span id="model-latency-${m.key}">—</span> ms</div>
      <div class="sub">Version: <span id="version-${m.key}">—</span></div>
      <div class="sub">Input: <span id="input-signal-${m.key}">—</span></div>
      <div class="sub">Updated: <span id="model-time-${m.key}">—</span></div>
    </div>`
  ).join("");
}

function drawSparkline(key) {
  const canvas = document.getElementById(`spark-${key}`);
  if (!canvas) return;
  const ctx = canvas.getContext("2d");
  const data = state.sparkHistory[key];
  const w = canvas.width;
  const h = canvas.height;
  ctx.clearRect(0, 0, w, h);
  if (data.length < 2) return;
  const min = Math.min(...data);
  const max = Math.max(...data);
  const range = max - min || 1;
  ctx.strokeStyle = "#3dd6c6";
  ctx.lineWidth = 1.5;
  ctx.beginPath();
  data.forEach((v, i) => {
    const x = (i / (data.length - 1)) * (w - 4) + 2;
    const y = h - 2 - ((v - min) / range) * (h - 4);
    if (i === 0) ctx.moveTo(x, y);
    else ctx.lineTo(x, y);
  });
  ctx.stroke();
}

function updateCard(event) {
  const key = event.signal_type;
  if (!state.counters[key]) state.counters[key] = 0;
  state.counters[key] += 1;

  const latest = event.values[event.values.length - 1];
  state.sparkHistory[key].push(latest);
  if (state.sparkHistory[key].length > 30) state.sparkHistory[key].shift();

  document.getElementById(`value-${key}`).textContent = latest.toFixed
    ? latest.toFixed(3)
    : latest;
  document.getElementById(`quality-${key}`).textContent = event.quality.toFixed(3);
  document.getElementById(`time-${key}`).textContent = new Date(event.timestamp).toLocaleTimeString();
  drawSparkline(key);

  if (event.metadata?.scenario) {
    state.scenario = event.metadata.scenario;
    document.getElementById("scenario-label").textContent = `Scenario: ${state.scenario}`;
  }
  if (event.metadata?.mode) {
    state.mode = event.metadata.mode;
    document.getElementById("mode-label").textContent = `Mode: ${state.mode}`;
  }
}

function percentile(arr, p) {
  if (!arr.length) return 0;
  const sorted = [...arr].sort((a, b) => a - b);
  const idx = Math.ceil((p / 100) * sorted.length) - 1;
  return sorted[Math.max(0, idx)];
}

function updateModelScoreCard(event) {
  const key = event.model_name;
  state.latestScores[key] = event;
  state.latencyHistory.push(event.latency_ms);
  if (state.latencyHistory.length > 100) state.latencyHistory.shift();

  const scoreEl = document.getElementById(`score-${key}`);
  if (!scoreEl) return;

  document.getElementById(`score-${key}`).textContent = event.score.toFixed(3);
  document.getElementById(`label-${key}`).textContent = event.output_label;
  document.getElementById(`confidence-${key}`).textContent = event.confidence.toFixed(3);
  document.getElementById(`model-latency-${key}`).textContent = event.latency_ms.toFixed(2);
  document.getElementById(`version-${key}`).textContent = event.model_version;
  document.getElementById(`input-signal-${key}`).textContent =
    event.metadata?.input_signal || event.metadata?.signal_type || "—";
  document.getElementById(`model-time-${key}`).textContent = new Date(event.timestamp).toLocaleTimeString();

  document.getElementById("last-model-name").textContent = event.model_name;
  document.getElementById("last-latency").textContent = event.latency_ms.toFixed(2) + " ms";
  document.getElementById("latency-p50").textContent = percentile(state.latencyHistory, 50).toFixed(2) + " ms";
  document.getElementById("latency-p95").textContent = percentile(state.latencyHistory, 95).toFixed(2) + " ms";
}

function pushEvent(event) {
  state.events.unshift(event);
  if (state.events.length > 20) state.events.pop();
  document.getElementById("event-counter").textContent = String(
    Number(document.getElementById("event-counter").textContent) + 1
  );
  state.proof.sensors += 1;
  state.proof.lastTelemetryAt = event.timestamp;
  if (event.trace_id) state.proof.traceId = event.trace_id;
  updateCard(event);
  renderTable();
}

function pushModelScore(event) {
  state.modelScores.unshift(event);
  if (state.modelScores.length > 20) state.modelScores.pop();
  document.getElementById("model-score-counter").textContent = String(
    Number(document.getElementById("model-score-counter").textContent) + 1
  );
  state.proof.scores += 1;
  state.proof.lastScoreAt = event.timestamp;
  updateModelScoreCard(event);
  renderModelScoresTable();
}

function renderTable() {
  const tbody = document.getElementById("events-table");
  tbody.innerHTML = state.events
    .map((e) => {
      const latest = e.values[e.values.length - 1];
      return `<tr>
        <td>${new Date(e.timestamp).toLocaleTimeString()}</td>
        <td>${e.signal_type}</td>
        <td>${typeof latest === "number" ? latest.toFixed(3) : latest}</td>
        <td>${e.quality.toFixed(3)}</td>
        <td>${e.metadata?.mode || "—"}</td>
        <td>${e.trace_id.slice(0, 12)}…</td>
      </tr>`;
    })
    .join("");
}

function renderModelScoresTable() {
  const tbody = document.getElementById("model-scores-table");
  tbody.innerHTML = state.modelScores
    .map((e) => `<tr>
      <td>${new Date(e.timestamp).toLocaleTimeString()}</td>
      <td>${e.model_name}</td>
      <td>${e.model_version}</td>
      <td>${e.metadata?.input_signal || e.metadata?.signal_type || "—"}</td>
      <td>${e.score.toFixed(3)}</td>
      <td>${e.confidence.toFixed(3)}</td>
      <td>${e.output_label}</td>
      <td>${e.latency_ms.toFixed(2)}</td>
    </tr>`)
    .join("");
}

function handleWsMessage(msg) {
  if (msg.type === "event" && msg.event) {
    pushEvent(msg.event);
    return;
  }
  if (msg.type === "status" && msg.status === "awaiting_data") {
    setDot("ws-sensors-status", false, true);
    setDot("ws-robot-status", false, true);
    document.getElementById("mode-label").textContent = "Mode: awaiting data";
  }
}

function handleModelScoreMessage(msg) {
  if (msg.type === "model_score" && msg.event) {
    pushModelScore(msg.event);
    return;
  }
  if (msg.type === "waiting") {
    setDot("ws-model-scores-status", false, true);
  }
}

function pushTrace(event) {
  state.traces.unshift(event);
  if (state.traces.length > 30) state.traces.pop();
  state.proof.agents += 1;
  if (event.trace_id) state.proof.traceId = event.trace_id;
  renderTracesTable();
}

function pushDecision(event) {
  state.decisions.unshift(event);
  if (state.decisions.length > 30) state.decisions.pop();
  state.proof.decisions += 1;
  if (event.decision_id) state.proof.decisionId = event.decision_id;
  updateDecisionPanel(event);
  renderDecisionsTable();
  refreshCurrentDecision();
}

function updateDecisionPanel(d) {
  document.getElementById("decision-risk").textContent = d.risk_level || "—";
  document.getElementById("decision-action").textContent = d.recommended_action || "—";
  document.getElementById("decision-confidence").textContent =
    d.confidence != null ? d.confidence.toFixed(2) : "—";
  document.getElementById("decision-status").textContent = d.status || "—";
  document.getElementById("decision-hitl").textContent =
    d.requires_human_confirmation ? "requires operator confirmation" : "not required";
  document.getElementById("decision-rationale").textContent = d.rationale || "—";
  document.getElementById("decision-evidence").textContent =
    (d.evidence_refs || []).join(", ") || "—";
  document.getElementById("decision-signals").textContent =
    (d.contributing_signals || []).join(", ") || "all present";
  const copilotEl = document.getElementById("decision-copilot");
  if (copilotEl) {
    const rationale = d.rationale || "";
    const marker = rationale.indexOf("Copilot:");
    copilotEl.textContent =
      marker >= 0 ? rationale.slice(marker + "Copilot:".length).trim() : "advisory only";
  }
}

function updateSafetyPanel(s) {
  const prevInjections = (state.safety.active_injections || []).join(",");
  state.safety = s;
  state.proof.safety += 1;
  document.getElementById("safety-mode").textContent = s.safety_mode || "deterministic";
  document.getElementById("safety-stale").textContent = String(s.stale_telemetry ?? "—");
  document.getElementById("safety-missing").textContent =
    (s.missing_signals || []).join(", ") || "none";
  document.getElementById("safety-low-conf").textContent = String(s.low_confidence ?? "—");
  document.getElementById("safety-high-risk").textContent = String(s.high_risk ?? "—");
  document.getElementById("safety-llm").textContent = s.llm_authority || "advisory only";
  const injections = s.active_injections || [];
  document.getElementById("active-injections").textContent =
    injections.join(", ") || "none";

  const failureBadge = document.getElementById("safety-active-failure");
  if (failureBadge) {
    const active = injections.length > 0;
    failureBadge.textContent = active ? injections.join(", ") : "none";
    failureBadge.className = "failure-mode-badge " + (active ? "active" : "none");
  }

  const nowInjections = injections.join(",");
  if (typeof logAction === "function" && nowInjections !== prevInjections && nowInjections) {
    pulse("safety-panel");
  }
}

function renderTracesTable() {
  const tbody = document.getElementById("traces-table");
  tbody.innerHTML = state.traces
    .map((t) => `<tr>
      <td>${new Date(t.timestamp).toLocaleTimeString()}</td>
      <td>${t.agent_name}</td>
      <td>${t.stage}</td>
      <td>${t.confidence != null ? t.confidence.toFixed(2) : "—"}</td>
      <td>${t.risk_level || "—"}</td>
      <td>${t.duration_ms != null ? t.duration_ms.toFixed(1) : "—"}</td>
      <td>${t.llm_used ? "yes" : "no"}</td>
      <td>${(t.tool_calls || []).join(", ") || "—"}</td>
    </tr>`)
    .join("");
}

function renderDecisionsTable() {
  const tbody = document.getElementById("decisions-table");
  tbody.innerHTML = state.decisions
    .map((d) => `<tr>
      <td>${new Date(d.timestamp).toLocaleTimeString()}</td>
      <td>${(d.decision_id || "").slice(0, 8)}…</td>
      <td>${d.risk_level}</td>
      <td>${d.recommended_action}</td>
      <td>${d.status}</td>
      <td>${d.requires_human_confirmation ? "yes" : "no"}</td>
    </tr>`)
    .join("");
}

function setHitlState(pending, data) {
  const confirmBtn = document.getElementById("hitl-confirm");
  const rejectBtn = document.getElementById("hitl-reject");
  if (confirmBtn) confirmBtn.disabled = !pending;
  if (rejectBtn) rejectBtn.disabled = !pending;
  const stateText = document.getElementById("hitl-state-text");
  const reasonEl = document.getElementById("hitl-reason");
  const riskEl = document.getElementById("hitl-risk-conf");
  if (pending && data) {
    if (stateText) {
      stateText.innerHTML =
        'HITL gate <strong class="hitl-pending">PENDING</strong> — review the decision below and confirm or reject.';
    }
    if (reasonEl) {
      reasonEl.textContent =
        data.rationale || (data.requires_human_confirmation ? "requires operator confirmation" : "—");
    }
    if (riskEl) {
      const conf = data.confidence != null ? Number(data.confidence).toFixed(2) : "—";
      riskEl.textContent = `${data.risk_level || "—"} / ${conf}`;
    }
  } else {
    if (stateText) {
      stateText.innerHTML =
        'No pending HITL gate. Trigger one with the <em>Low Confidence</em> failure injection below, then confirm or reject here.';
    }
    if (reasonEl) reasonEl.textContent = "—";
    if (riskEl) riskEl.textContent = "—";
  }
}

async function refreshCurrentDecision() {
  try {
    const res = await fetch(`${config.apiBase}/api/v1/decisions/current`);
    const data = await res.json();
    const id = data.decision_id;
    state.currentDecisionId = id || null;
    document.getElementById("hitl-decision-id").textContent = id || "none";
    if (id) state.proof.decisionId = id;
    const pending = data.status === "pending_human_confirmation";
    setHitlState(pending, data);
    if (data.decision_id) updateDecisionPanel(data);
  } catch (_) {
    setHitlState(false, null);
  }
}

async function hitlAction(action) {
  const id = state.currentDecisionId;
  if (!id) return;
  const note = document.getElementById("hitl-note").value || "";
  const url = `${config.apiBase}/api/v1/decisions/${id}/${action}`;
  const label = action === "confirm" ? "Confirm decision" : "Reject decision";
  logAction(label, "HITL / Safety", "sent", `decision ${id.slice(0, 8)}…`, "hitl-panel");
  try {
    const res = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ operator_id: "dashboard-operator", note }),
    });
    if (res.ok) {
      const data = await res.json();
      pushDecision(data);
      state.currentDecisionId = null;
      document.getElementById("hitl-decision-id").textContent = "none";
      setHitlState(false, null);
      const receipt = `${data.status} (decision ${id.slice(0, 8)}…)`;
      const receiptEl = document.getElementById("hitl-receipt");
      if (receiptEl) receiptEl.textContent = receipt;
      logAction(label, "HITL / Safety", "backend", receipt, "hitl-panel");
      showToast(`Decision ${data.status}`, action === "confirm" ? "ok" : "warn");
      pulse("hitl-panel");
    } else {
      logAction(label, "HITL / Safety", "rejected", `HTTP ${res.status}`, "hitl-panel");
      showToast(`HITL ${action} failed (HTTP ${res.status})`, "danger");
    }
  } catch (_) {
    logAction(label, "HITL / Safety", "error", "API unreachable", "hitl-panel");
    showToast("HITL action failed — API unreachable", "danger");
  }
}

async function triggerInjection(scenario) {
  logAction("Failure injection", "Failure Injection", "sent", scenario, "failure-injection-panel");
  try {
    const res0 = await fetch(`${config.apiBase}/api/v1/failure-injection/${scenario}`, {
      method: "POST",
    });
    if (!res0.ok) {
      logAction("Failure injection", "Failure Injection", "rejected", `HTTP ${res0.status}`, "failure-injection-panel");
      showToast(`Injection rejected (HTTP ${res0.status})`, "danger");
      return;
    }
    const res = await fetch(`${config.apiBase}/api/v1/safety/status`);
    if (res.ok) updateSafetyPanel(await res.json());
    logAction("Failure injection applied", "Failure Injection", "backend", scenario, "safety-panel");
    showToast(`Failure injected: ${scenario}`, "warn");
    pulse("failure-injection-panel");
    pulse("safety-panel");
    if (scenario === "model_low_confidence") {
      showToast("Low confidence may open a HITL gate shortly", "warn");
      setTimeout(refreshCurrentDecision, 1500);
      setTimeout(refreshCurrentDecision, 6000);
    }
  } catch (_) {
    logAction("Failure injection", "Failure Injection", "error", "API unreachable", "failure-injection-panel");
    showToast("Injection failed — API unreachable", "danger");
  }
}

async function resetInjection() {
  logAction("Reset failure injection", "Failure Injection", "sent", "reset", "failure-injection-panel");
  try {
    const res = await fetch(`${config.apiBase}/api/v1/failure-injection/reset`, { method: "POST" });
    document.getElementById("active-injections").textContent = "none";
    const failureBadge = document.getElementById("safety-active-failure");
    if (failureBadge) {
      failureBadge.textContent = "none";
      failureBadge.className = "failure-mode-badge none";
    }
    logAction("Reset failure injection", "Failure Injection", res.ok ? "backend" : "rejected", "cleared", "safety-panel");
    showToast("Failure injection cleared", "ok");
    pulse("failure-injection-panel");
    pulse("safety-panel");
  } catch (_) {
    logAction("Reset failure injection", "Failure Injection", "error", "API unreachable", "failure-injection-panel");
    showToast("Reset failed — API unreachable", "danger");
  }
}

function connectWs(path, statusId, filterFn, handler) {
  const ws = new WebSocket(`${config.wsBase}${path}`);
  ws.onopen = () => setDot(statusId, true);
  ws.onclose = () => {
    setDot(statusId, false);
    setTimeout(() => connectWs(path, statusId, filterFn, handler), 2000);
  };
  ws.onerror = () => setDot(statusId, false);
  ws.onmessage = (ev) => {
    try {
      const msg = JSON.parse(ev.data);
      if (filterFn && !filterFn(msg)) return;
      handler(msg);
    } catch (_) {
      /* ignore malformed */
    }
  };
  return ws;
}

async function checkApiHealth() {
  try {
    const res = await fetch(`${config.apiBase}/health`);
    if (res.ok) {
      setDot("api-status", true);
      const data = await res.json();
      if (data.mqtt_connected === false) setDot("api-status", false, true);
    } else {
      setDot("api-status", false);
    }
  } catch {
    setDot("api-status", false);
  }
}

initCards();
initModelScoreCards();
checkApiHealth();
setInterval(checkApiHealth, 10000);

connectWs("/ws/v1/sensors", "ws-sensors-status", (msg) => {
  if (msg.type === "event") return msg.event?.signal_type !== "robot_state";
  return true;
}, handleWsMessage);

connectWs("/ws/v1/robot-state", "ws-robot-status", (msg) => {
  if (msg.type === "event") return msg.event?.signal_type === "robot_state";
  return true;
}, handleWsMessage);

connectWs("/ws/v1/model-scores", "ws-model-scores-status", null, handleModelScoreMessage);

connectWs("/ws/v1/agents", "ws-agents-status", null, (msg) => {
  if (msg.type === "agent_trace" && msg.event) pushTrace(msg.event);
});

connectWs("/ws/v1/decisions", "ws-decisions-status", null, (msg) => {
  if (msg.type === "decision" && msg.event) {
    pushDecision(msg.event);
    refreshCurrentDecision();
  }
});

connectWs("/ws/v1/safety", "ws-safety-status", null, (msg) => {
  if (msg.type === "safety_status" && msg.status) updateSafetyPanel(msg.status);
});

document.getElementById("hitl-confirm").addEventListener("click", () => hitlAction("confirm"));
document.getElementById("hitl-reject").addEventListener("click", () => hitlAction("reject"));
document.querySelectorAll("[data-scenario]").forEach((btn) => {
  btn.addEventListener("click", () => triggerInjection(btn.dataset.scenario));
});
document.getElementById("injection-reset").addEventListener("click", resetInjection);

refreshCurrentDecision();
fetch(`${config.apiBase}/api/v1/safety/status`)
  .then((r) => r.json())
  .then(updateSafetyPanel)
  .catch(() => {});

function setDriftBadge(status) {
  const el = document.getElementById("mlops-drift-badge");
  el.textContent = status || "—";
  el.className = "drift-badge " + (
    status === "nominal" ? "green" : status === "drift_detected" ? "amber" : "gray"
  );
}

async function pollMlopsStatus() {
  try {
    const res = await fetch(`${config.apiBase}/api/v1/mlops/status`);
    if (!res.ok) return;
    const data = await res.json();
    document.getElementById("mlops-active-emg").textContent =
      data.active_model_version?.emg || "—";
    document.getElementById("mlops-candidate-emg").textContent =
      data.candidate_model_version?.emg || "—";
    document.getElementById("mlops-promotion-emg").textContent =
      data.candidate_promotion_status?.emg || "—";
    setDriftBadge(data.drift?.status);
    document.getElementById("mlops-last-eval").textContent =
      data.last_eval_at || "No evaluation run yet";
    document.getElementById("mlops-empty").style.display =
      data.has_eval_run ? "none" : "block";
    if (data.latest_eval) {
      const ev = data.latest_eval;
      document.getElementById("mlops-v1-acc").textContent =
        ev.v1?.accuracy != null ? ev.v1.accuracy.toFixed(4) : "—";
      document.getElementById("mlops-v2-acc").textContent =
        ev.v2_candidate?.accuracy != null ? ev.v2_candidate.accuracy.toFixed(4) : "—";
      document.getElementById("mlops-rec").textContent =
        ev.improvement?.recommendation || "—";
    }
    document.getElementById("mlops-artifacts").textContent =
      "Artifacts: " + (data.artifact_paths?.artifacts_root || "—");
    if (data.safety_notice) {
      document.getElementById("mlops-safety-notice").textContent = data.safety_notice;
    }
  } catch (_) {
    /* graceful empty state */
  }
}

document.getElementById("mlops-promote-btn").addEventListener("click", async () => {
  logAction("MLOps dry-run review", "MLOps Evidence", "sent", "promote-candidate (dry_run)", "mlops-panel");
  try {
    const res = await fetch(`${config.apiBase}/api/v1/mlops/promote-candidate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ signal_type: "emg", dry_run: true, operator_note: "dashboard-simulated-review" }),
    });
    const data = await res.json();
    document.getElementById("mlops-review-id").textContent =
      data.review_record_id ? `Review record: ${data.review_record_id}` : "";
    logAction("MLOps dry-run review", "MLOps Evidence", "backend",
      data.review_record_id ? `review ${data.review_record_id}` : "dry-run complete", "mlops-panel");
    showToast("MLOps dry-run review recorded (no promotion)", "ok");
    pulse("mlops-panel");
  } catch (_) {
    document.getElementById("mlops-review-id").textContent = "Promotion dry-run failed (API unavailable)";
    logAction("MLOps dry-run review", "MLOps Evidence", "error", "API unavailable", "mlops-panel");
    showToast("MLOps dry-run failed — API unavailable", "danger");
  }
});

pollMlopsStatus();
setInterval(pollMlopsStatus, 10000);

function updateTwinPanel(twin) {
  if (!twin) return;
  const prevMode = state.twin?.robot_state?.mode;
  state.twin = twin;
  state.proof.twin += 1;
  if (twin.agents?.trace_id) state.proof.traceId = twin.agents.trace_id;
  const mode = twin.robot_state?.mode || "idle";
  if (typeof state.twinAwaitingBroadcast !== "undefined" && state.twinAwaitingBroadcast && prevMode !== mode) {
    state.twinAwaitingBroadcast = false;
    const resultEl = document.getElementById("twin-cmd-result");
    if (resultEl) resultEl.textContent = `Twin broadcast received — mode now ${mode}.`;
    pulse("digital-twin-panel");
    if (typeof logAction === "function") {
      logAction("Twin state changed", "Digital Twin", "backend", `mode → ${mode}`, "digital-twin-panel");
    }
  }
  const svg = document.getElementById("twin-svg");
  svg.setAttribute("class", "twin-svg mode-" + mode);

  document.getElementById("twin-mode").textContent = mode;
  document.getElementById("twin-confidence").textContent =
    twin.fusion?.global_confidence != null ? twin.fusion.global_confidence.toFixed(2) : "—";
  document.getElementById("twin-risk-level").textContent = twin.fusion?.risk_level || "—";
  document.getElementById("twin-agent").textContent = twin.agents?.active_agent || "—";
  document.getElementById("twin-action").textContent = twin.agents?.last_action || "—";
  document.getElementById("twin-trace").textContent =
    (twin.agents?.trace_id || "").slice(0, 16) + (twin.agents?.trace_id ? "…" : "");
  document.getElementById("twin-hitl").textContent =
    twin.agents?.hitl_pending ? "PENDING" : "clear";
  document.getElementById("twin-safety").textContent =
    twin.safety?.blocked_reason || twin.safety?.envelope_status || "—";
  document.getElementById("twin-ros2").textContent = twin.ros2_bridge?.status || "offline";
  document.getElementById("twin-robot-mode").textContent = mode;
  document.getElementById("twin-risk-text").textContent =
    `${twin.fusion?.risk_level || "—"} / ${twin.fusion?.global_confidence?.toFixed(2) ?? "—"}`;

  const joint = twin.robot_state?.joint_angle_deg ?? 30;
  const armRight = document.getElementById("twin-arm-right");
  if (armRight) {
    armRight.setAttribute("transform", `rotate(${joint - 30}, 46, -22)`);
  }

  const sensorMap = { emg: "twin-sensor-emg", ecg: "twin-sensor-ecg", imu: "twin-sensor-imu", spo2: "twin-sensor-spo2" };
  for (const [key, elId] of Object.entries(sensorMap)) {
    const el = document.getElementById(elId);
    if (!el || !twin.sensor_nodes?.[key]) continue;
    const status = twin.sensor_nodes[key].status || "dropout";
    el.setAttribute("class", "twin-sensor " + (SENSOR_STATUS_CLASS[status] || "status-dropout"));
    el.setAttribute("title", `${key}: ${twin.sensor_nodes[key].latest_value_summary}`);
  }

  const robotG = document.getElementById("twin-robot");
  if (robotG && twin.robot_state?.pose) {
    const ox = (twin.robot_state.pose.orientation_deg || 0) * 0.3;
    robotG.setAttribute("transform", `translate(${210 + ox}, 160)`);
  }
}

async function sendTwinCommand(command, extra = {}) {
  logAction("Twin command", "Digital Twin", "sent", command, "digital-twin-panel");
  try {
    const res = await fetch(`${config.apiBase}/api/v1/twin/command`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        schema_version: "v1",
        command,
        requested_by: "dashboard-operator",
        ...extra,
      }),
    });
    const data = await res.json();
    const trace = (data.trace_id || "").slice(0, 12);
    if (data.trace_id) state.proof.commandId = data.trace_id;
    document.getElementById("twin-cmd-result").textContent =
      `${data.status}: ${data.reason || data.command} (trace ${trace}…). Backend accepted — waiting for next twin broadcast.`;
    state.twinAwaitingBroadcast = data.status === "accepted" || data.status === "ok";
    logAction("Twin command", "Digital Twin", "backend", `${data.status}: ${data.command}`, "digital-twin-panel");
    showToast(`Twin: ${command} → ${data.status}`, data.status === "rejected" ? "danger" : "ok");
    pulse("digital-twin-panel");
    return data;
  } catch (e) {
    document.getElementById("twin-cmd-result").textContent = "Command failed (API unreachable)";
    logAction("Twin command", "Digital Twin", "error", "API unreachable", "digital-twin-panel");
    showToast("Twin command failed — API unreachable", "danger");
    return null;
  }
}

connectWs("/ws/v1/twin", "ws-twin-status", null, (msg) => {
  if (msg.type === "twin_state" && msg.state) updateTwinPanel(msg.state);
});

document.getElementById("twin-cmd-pause").addEventListener("click", () => sendTwinCommand("pause"));
document.getElementById("twin-cmd-resume").addEventListener("click", () => sendTwinCommand("resume"));
document.getElementById("twin-cmd-safety-stop").addEventListener("click", () =>
  sendTwinCommand("request_safety_stop")
);
document.getElementById("twin-cmd-assist").addEventListener("click", () => {
  const mode = document.getElementById("twin-assist-mode").value;
  sendTwinCommand("set_assist_mode", { assist_mode: mode });
});

/* ---------------- Phase 5.5 Nav2 + SLAM MiniLab panel ---------------- */
// Static lab geometry (mirrors services/.../config/world.yaml). Scene only;
// robot pose / goal / path / status come from live backend data.
const NAV_SLAM_WORLD = { width: 6.0, height: 4.0 };
const NAV_SLAM_OBSTACLES = [
  { name: "treadmill", x: 1.0, y: 0.4, w: 0.8, h: 1.0 },
  { name: "parallel_bars", x: 3.8, y: 0.5, w: 0.8, h: 1.7 },
  { name: "mat_stack", x: 0.5, y: 2.8, w: 1.1, h: 0.6 },
  { name: "pillar", x: 2.8, y: 2.9, w: 0.4, h: 0.4 },
  { name: "storage_cart", x: 4.9, y: 2.9, w: 0.6, h: 0.6 },
];
const NAV_SLAM_SCALE_X = 600 / NAV_SLAM_WORLD.width;
const NAV_SLAM_SCALE_Y = 400 / NAV_SLAM_WORLD.height;

function navSlamSx(x) {
  return x * NAV_SLAM_SCALE_X;
}
function navSlamSy(y) {
  // Flip Y: world origin bottom-left, SVG origin top-left.
  return 400 - y * NAV_SLAM_SCALE_Y;
}

function initNavSlamScene() {
  const walls = document.getElementById("nav-slam-walls");
  if (walls) {
    walls.innerHTML = `<rect x="2" y="2" width="596" height="396" rx="6"
      class="nav-slam-wall" fill="none"/>`;
  }
  const obs = document.getElementById("nav-slam-obstacles");
  if (obs) {
    obs.innerHTML = NAV_SLAM_OBSTACLES.map((o) => {
      const x = navSlamSx(o.x);
      const y = navSlamSy(o.y + o.h);
      const w = o.w * NAV_SLAM_SCALE_X;
      const h = o.h * NAV_SLAM_SCALE_Y;
      return `<rect x="${x}" y="${y}" width="${w}" height="${h}" rx="3"
        class="nav-slam-obstacle"><title>${o.name}</title></rect>`;
    }).join("");
  }
}

function setNavSlamOffline() {
  const svg = document.getElementById("nav-slam-svg");
  if (svg) svg.classList.add("offline");
  const robot = document.getElementById("nav-slam-robot");
  const goal = document.getElementById("nav-slam-goal");
  if (robot) robot.setAttribute("transform", "translate(-100,-100)");
  if (goal) {
    goal.setAttribute("cx", "-100");
    goal.setAttribute("cy", "-100");
  }
  const path = document.getElementById("nav-slam-path");
  if (path) path.setAttribute("d", "");
  document.getElementById("nav-slam-overlay").textContent = "MiniLab — offline";
  const bridge = document.getElementById("nav-slam-bridge");
  bridge.textContent = "offline";
  bridge.className = "badge offline-badge";
  setNavSlamLiveControls(false);
}

const NAV_SLAM_LIVE_BTN_IDS = [
  "nav-slam-cmd-mapping",
  "nav-slam-cmd-goal",
  "nav-slam-cmd-blocked",
  "nav-slam-cmd-reset",
];

function setNavSlamLiveControls(online) {
  NAV_SLAM_LIVE_BTN_IDS.forEach((id) => {
    const btn = document.getElementById(id);
    if (!btn) return;
    btn.disabled = !online;
    btn.title = online
      ? "Live MiniLab command (bridge online)"
      : "Disabled — requires the ros2-nav-slam profile (see activation command)";
  });
  const cta = document.getElementById("nav-slam-offline-cta");
  if (cta) cta.style.display = online ? "none" : "block";
}

function updateNavSlamPanel(s) {
  if (!s) return;
  const bridgeStatus = s.bridge_status || "offline";
  const bridgeEl = document.getElementById("nav-slam-bridge");
  bridgeEl.textContent = bridgeStatus;
  bridgeEl.className =
    "badge " +
    (bridgeStatus === "online"
      ? "online-badge"
      : bridgeStatus === "degraded"
      ? "degraded-badge"
      : "offline-badge");

  const svg = document.getElementById("nav-slam-svg");
  if (bridgeStatus === "offline") {
    setNavSlamOffline();
    document.getElementById("nav-slam-nav-status").textContent =
      s.nav_status || "—";
    return;
  }
  if (svg) svg.classList.remove("offline");
  setNavSlamLiveControls(true);

  document.getElementById("nav-slam-nav-status").textContent = s.nav_status || "—";
  document.getElementById("nav-slam-reason").textContent = s.nav_status_reason || "—";
  document.getElementById("nav-slam-demo").textContent = s.active_demo || "—";
  const slam = s.slam || {};
  document.getElementById("nav-slam-slam-status").textContent = slam.status || "—";
  document.getElementById("nav-slam-coverage").textContent =
    slam.coverage_pct != null ? slam.coverage_pct.toFixed(1) + "%" : "—";
  document.getElementById("nav-slam-map-updates").textContent =
    slam.map_updates != null ? slam.map_updates : "—";

  const pose = s.robot_pose || [0, 0, 0];
  document.getElementById("nav-slam-pose").textContent =
    `(${pose[0].toFixed(2)}, ${pose[1].toFixed(2)}) θ${(pose[2] || 0).toFixed(2)}`;
  document.getElementById("nav-slam-updated").textContent = s.timestamp
    ? new Date(s.timestamp).toLocaleTimeString()
    : "—";

  // Robot marker.
  const robot = document.getElementById("nav-slam-robot");
  if (robot) {
    const deg = ((pose[2] || 0) * 180) / Math.PI;
    robot.setAttribute(
      "transform",
      `translate(${navSlamSx(pose[0])},${navSlamSy(pose[1])}) rotate(${-deg})`
    );
  }

  // Goal marker.
  const goalEl = document.getElementById("nav-slam-goal");
  if (s.goal) {
    goalEl.setAttribute("cx", navSlamSx(s.goal.x));
    goalEl.setAttribute("cy", navSlamSy(s.goal.y));
    document.getElementById("nav-slam-goal-text").textContent =
      `(${s.goal.x.toFixed(2)}, ${s.goal.y.toFixed(2)})`;
  } else {
    goalEl.setAttribute("cx", "-100");
    goalEl.setAttribute("cy", "-100");
    document.getElementById("nav-slam-goal-text").textContent = "—";
  }

  // Path.
  const path = document.getElementById("nav-slam-path");
  const wps = (s.path && s.path.waypoints) || [];
  if (path && wps.length > 1) {
    path.setAttribute(
      "d",
      wps
        .map((w, i) => `${i === 0 ? "M" : "L"} ${navSlamSx(w[0])} ${navSlamSy(w[1])}`)
        .join(" ")
    );
  } else if (path) {
    path.setAttribute("d", "");
  }
  document.getElementById("nav-slam-path-text").textContent =
    s.path && s.path.waypoint_count
      ? `${s.path.waypoint_count} wp / ${(s.path.length_m || 0).toFixed(2)} m`
      : "—";

  document.getElementById("nav-slam-overlay").textContent =
    `SLAM ${slam.status || "—"} · Nav ${s.nav_status || "—"}`;
}

async function sendNavSlamCommand(command, extra = {}) {
  logAction("MiniLab command", "Robotics Lab", "sent", command, "nav-slam-panel");
  try {
    const res = await fetch(`${config.apiBase}/api/v1/nav-slam/command`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        schema_version: "v1",
        command,
        requested_by: "dashboard-operator",
        ...extra,
      }),
    });
    const data = await res.json();
    if (data.trace_id) state.proof.commandId = data.trace_id;
    document.getElementById("nav-slam-cmd-result").textContent =
      `${data.status}: ${data.reason || data.command} (trace ${(data.trace_id || "").slice(0, 12)}…)`;
    logAction("MiniLab command", "Robotics Lab", "backend", `${data.status}: ${command}`, "nav-slam-panel");
    showToast(`MiniLab: ${command} → ${data.status}`, "ok");
  } catch (_) {
    document.getElementById("nav-slam-cmd-result").textContent =
      "Command failed (MiniLab/API offline)";
    logAction("MiniLab command", "Robotics Lab", "error", "MiniLab/API offline", "nav-slam-panel");
    showToast("MiniLab command failed — bridge offline", "danger");
  }
}

async function pollNavSlamStatus() {
  try {
    const res = await fetch(`${config.apiBase}/api/v1/nav-slam/status`);
    if (!res.ok) {
      setNavSlamOffline();
      return;
    }
    updateNavSlamPanel(await res.json());
  } catch (_) {
    setNavSlamOffline();
  }
}

initNavSlamScene();
setNavSlamOffline();
connectWs("/ws/v1/nav-slam", "ws-nav-slam-status", null, (msg) => {
  if (msg.type === "nav_slam_state" && msg.state) updateNavSlamPanel(msg.state);
});
pollNavSlamStatus();
setInterval(pollNavSlamStatus, 5000);

document
  .getElementById("nav-slam-cmd-mapping")
  .addEventListener("click", () => sendNavSlamCommand("start_mapping"));
document
  .getElementById("nav-slam-cmd-goal")
  .addEventListener("click", () =>
    sendNavSlamCommand("send_goal", {
      goal: { schema_version: "v1", x: 5.0, y: 1.0, theta_deg: 0.0 },
      demo: "nav_goal_demo",
    })
  );
document
  .getElementById("nav-slam-cmd-blocked")
  .addEventListener("click", () =>
    sendNavSlamCommand("send_goal", {
      goal: { schema_version: "v1", x: 4.2, y: 1.3, theta_deg: 0.0 },
      demo: "blocked_goal_demo",
    })
  );
document
  .getElementById("nav-slam-cmd-reset")
  .addEventListener("click", () => sendNavSlamCommand("reset"));

// --- Phase 6A Federated Learning panel ---
function fmtNum(v, digits = 4) {
  return v == null ? "—" : Number(v).toFixed(digits);
}

function updateFederatedPanel(data) {
  if (!data) return;
  document.getElementById("fl-status").textContent = data.status || "idle";
  document.getElementById("fl-clients").textContent =
    data.num_clients ? String(data.num_clients) : "—";
  document.getElementById("fl-rounds").textContent =
    data.completed_rounds != null ? String(data.completed_rounds) : "—";
  document.getElementById("fl-accuracy").textContent = fmtNum(data.latest_global_accuracy);
  document.getElementById("fl-loss").textContent = fmtNum(data.latest_global_loss);

  const summary = data.summary || {};
  document.getElementById("fl-model").textContent = summary.model_type
    ? `${summary.model_type} (${summary.model_param_count ?? "?"} params)`
    : "—";
  document.getElementById("fl-framework").textContent =
    summary.framework ? `${summary.framework} · ${summary.strategy || "FedAvg"}` : "—";
  document.getElementById("fl-mlflow").textContent = data.mlflow_run_id || "—";
  document.getElementById("fl-report-path").textContent =
    "Report: " + (data.report_path || data.artifact_dir || "—");
  document.getElementById("fl-empty").style.display = data.has_run ? "none" : "block";

  const clientsBody = document.getElementById("fl-clients-table");
  clientsBody.innerHTML = (data.client_summaries || [])
    .map(
      (c) =>
        `<tr><td>${c.client_id}</td><td>${c.signal_type}</td><td>${c.data_size}</td>` +
        `<td>${fmtNum(c.anomaly_ratio, 2)}</td><td>${fmtNum(c.final_local_loss)}</td></tr>`
    )
    .join("");

  const convBody = document.getElementById("fl-convergence-table");
  convBody.innerHTML = (data.convergence || [])
    .map(
      (r) =>
        `<tr><td>${r.round}</td><td>${fmtNum(r.global_loss)}</td>` +
        `<td>${fmtNum(r.global_accuracy)}</td></tr>`
    )
    .join("");

  if (data.disclaimer) {
    document.getElementById("fl-disclaimer").textContent = data.disclaimer;
  }
}

async function pollFederatedStatus() {
  try {
    const res = await fetch(`${config.apiBase}/api/learning/federated/status`);
    if (!res.ok) return;
    updateFederatedPanel(await res.json());
  } catch (_) {
    /* graceful empty state — panel keeps its disclaimer + idle defaults */
  }
}

pollFederatedStatus();
setInterval(pollFederatedStatus, 10000);

// --- Phase 6B RL Micro-module panel ---
function updateRLPanel(data) {
  if (!data) return;
  const summary = data.summary || {};
  const policy = data.policy_summary || {};
  document.getElementById("rl-status").textContent = data.status || "idle";
  document.getElementById("rl-env").textContent = data.env_name || "—";
  document.getElementById("rl-algo").textContent = data.algorithm || "—";
  document.getElementById("rl-mean-reward").textContent = fmtNum(data.mean_reward, 3);
  document.getElementById("rl-baseline").textContent = fmtNum(data.baseline_reward, 3);
  document.getElementById("rl-trained").textContent = fmtNum(data.trained_policy_reward, 3);
  document.getElementById("rl-improvement").textContent = fmtNum(data.policy_improvement_ratio, 3);
  document.getElementById("rl-unsafe").textContent = fmtNum(data.unsafe_action_rate, 3);
  document.getElementById("rl-hitl").textContent = fmtNum(data.hitl_suggestion_rate, 3);
  document.getElementById("rl-mlflow").textContent = data.mlflow_run_id || "—";
  document.getElementById("rl-report-path").textContent =
    "Report: " + (data.report_path || data.artifact_dir || "—");
  document.getElementById("rl-empty").style.display = data.has_run ? "none" : "block";

  if (data.disclaimer) {
    document.getElementById("rl-disclaimer").textContent = data.disclaimer;
  }
}

async function updateRLRewardCurve() {
  try {
    const res = await fetch(`${config.apiBase}/api/learning/rl/latest`);
    if (!res.ok) return;
    const data = await res.json();
    const body = document.getElementById("rl-reward-curve-table");
    body.innerHTML = (data.reward_curve || [])
      .map((p) => `<tr><td>${p.timesteps}</td><td>${fmtNum(p.mean_episode_reward, 3)}</td></tr>`)
      .join("");
  } catch (_) {
    /* graceful empty state */
  }
}

async function pollRLStatus() {
  try {
    const res = await fetch(`${config.apiBase}/api/learning/rl/status`);
    if (!res.ok) return;
    updateRLPanel(await res.json());
    updateRLRewardCurve();
  } catch (_) {
    /* graceful empty state — panel keeps its disclaimer + idle defaults */
  }
}

pollRLStatus();
setInterval(pollRLStatus, 10000);

// --- Phase 7 Operational / Reliability panel ---
const CORE_COMPONENTS = new Set([
  "api",
  "redis",
  "mqtt",
  "telemetry_pipeline",
  "edge_inference",
  "digital_twin",
  "agents_hitl",
  "dashboard",
]);
const OPS_STATUS_CLASS = {
  ok: "ok",
  degraded: "degraded",
  unavailable: "unavailable",
  inactive: "inactive",
  error: "error",
};

function setOpsStatus(elId, status) {
  const el = document.getElementById(elId);
  if (!el) return;
  const normalized = OPS_STATUS_CLASS[status] ? status : "unavailable";
  el.textContent = normalized;
  el.className = "ops-status " + normalized;
}

function renderOpsRow(name, comp) {
  const status = comp.status || "unavailable";
  const req = comp.required ? "yes" : "no (optional)";
  return `<tr><td>${name}</td><td class="ops-status ${status}">${status}</td><td>${req}</td><td>${comp.message || "—"}</td></tr>`;
}

async function pollOperationalStatus() {
  const unreachable = document.getElementById("ops-api-unreachable");
  const content = document.getElementById("ops-content");
  try {
    const [liveRes, readyRes, servicesRes] = await Promise.all([
      fetch(`${config.apiBase}/health/live`),
      fetch(`${config.apiBase}/health/ready`),
      fetch(`${config.apiBase}/status/services`),
    ]);
    if (!liveRes.ok || !servicesRes.ok) {
      throw new Error("API unreachable");
    }
    if (unreachable) unreachable.style.display = "none";
    if (content) content.style.display = "block";

    const live = await liveRes.json();
    const ready = readyRes.ok ? await readyRes.json() : { status: "unavailable" };
    const services = await servicesRes.json();

    setOpsStatus("ops-liveness", live.status || "ok");
    setOpsStatus("ops-readiness", ready.status || "unavailable");
    setOpsStatus("ops-overall", services.status || "unavailable");
    document.getElementById("ops-last-check").textContent =
      services.timestamp || new Date().toISOString();

    const components = services.components || {};
    const coreBody = document.getElementById("ops-components-core");
    const optBody = document.getElementById("ops-components-optional");
    if (!Object.keys(components).length) {
      const ev = document.getElementById("ops-evidence-summary");
      if (ev) ev.textContent = "No components reported.";
    } else {
      if (coreBody) {
        coreBody.innerHTML = Object.entries(components)
          .filter(([name]) => CORE_COMPONENTS.has(name))
          .map(([name, comp]) => renderOpsRow(name, comp))
          .join("");
      }
      if (optBody) {
        optBody.innerHTML = Object.entries(components)
          .filter(([name]) => !CORE_COMPONENTS.has(name))
          .map(([name, comp]) => renderOpsRow(name, comp))
          .join("");
      }
      const fl = components.fl_module?.status;
      const rl = components.rl_module?.status;
      document.getElementById("ops-evidence-summary").textContent =
        `Evidence: FL=${fl || "—"}, RL=${rl || "—"}, MLOps=${components.mlops_evidence?.status || "—"}`;
    }
    document.getElementById("ops-reliability-report").textContent =
      "Reliability report: artifacts/reliability/phase7a_reliability_report.json (run scripts/reliability/check_phase7_reliability.py)";
    document.getElementById("ops-observability-report").textContent =
      "Observability report: artifacts/observability/phase7b_observability_report.json (run scripts/observability/check_phase7_observability.py)";
  } catch (_) {
    if (unreachable) unreachable.style.display = "block";
    if (content) content.style.display = "none";
    setOpsStatus("ops-overall", "unavailable");
    setOpsStatus("ops-readiness", "unavailable");
    setOpsStatus("ops-liveness", "unavailable");
  }
}

pollOperationalStatus();
setInterval(pollOperationalStatus, 15000);

// --- Phase 8 Mission Control panel ---
const MISSION_STATUS_CLASS = {
  ok: "ok",
  offline: "offline",
  unknown: "unknown",
  artifact_only: "artifact_only",
  simulated: "simulated",
  degraded: "degraded",
  inactive: "inactive",
  error: "error",
  loading: "loading",
};

const MISSION_COMPONENT_LABELS = {
  synthetic_telemetry: "Telemetry",
  edge_inference: "Edge inference",
  anomaly_safety: "Anomaly / safety",
  agent_decision: "Agent decision",
  hitl_safety_gate: "HITL / safety gate",
  digital_twin: "Digital twin",
  ros2: "ROS2",
  nav_slam: "Nav2 / SLAM",
  fl_evidence: "FL evidence",
  rl_evidence: "RL evidence",
  observability: "Observability",
  reliability: "Reliability",
  evidence_center: "Evidence Center",
};

function setMissionStatus(elId, status) {
  const el = document.getElementById(elId);
  if (!el) return;
  const normalized = MISSION_STATUS_CLASS[status] ? status : "unknown";
  el.textContent = normalized;
  el.className = "mission-status " + normalized;
}

function renderMissionComponentCards(components) {
  const container = document.getElementById("mission-component-cards");
  if (!container) return;
  const entries = Object.entries(components || {});
  if (!entries.length) {
    container.innerHTML = '<p class="muted">No component status reported.</p>';
    return;
  }
  container.innerHTML = entries
    .filter(([key]) => MISSION_COMPONENT_LABELS[key])
    .map(([key, comp]) => {
      const label = MISSION_COMPONENT_LABELS[key] || key;
      const status = comp.status || "unknown";
      return `<div class="card mission-card"><h3>${label}</h3><div class="metric mission-status ${status}">${status}</div><div class="sub">${comp.message || "—"}</div></div>`;
    })
    .join("");
}

function renderMissionTimeline(events) {
  const body = document.getElementById("mission-timeline-body");
  if (!body) return;
  if (!events || !events.length) {
    body.innerHTML = '<tr><td colspan="4">No timeline events — run a scenario for artifact-backed timeline.</td></tr>';
    return;
  }
  body.innerHTML = events
    .slice(0, 20)
    .map(
      (ev) =>
        `<tr><td>${ev.stage}</td><td class="mission-status ${ev.status}">${ev.status}</td><td>${ev.source_component}</td><td>${ev.summary || "—"}</td></tr>`
    )
    .join("");
}

function renderMissionEvidence(items, summary) {
  const body = document.getElementById("mission-evidence-body");
  const summaryEl = document.getElementById("mission-evidence-summary");
  if (summaryEl && summary) {
    summaryEl.textContent = `Evidence: ${summary.available || 0} available / ${summary.total || 0} indexed (${summary.missing || 0} missing)`;
  }
  if (!body) return;
  const preview = (items || []).slice(0, 12);
  if (!preview.length) {
    body.innerHTML = '<tr><td colspan="4">No evidence items indexed.</td></tr>';
    return;
  }
  body.innerHTML = preview
    .map(
      (item) =>
        `<tr><td>${item.category}</td><td>${item.title}</td><td class="mission-status ${item.status}">${item.status}</td><td><code>${item.path}</code></td></tr>`
    )
    .join("");
}

function showMissionFallback(message) {
  const unreachable = document.getElementById("mission-api-unreachable");
  const content = document.getElementById("mission-content");
  if (unreachable) {
    unreachable.style.display = "block";
    if (message) unreachable.textContent = message;
  }
  if (content) content.style.opacity = "0.65";
  setMissionStatus("mission-mode", "offline");
  setMissionStatus("mission-degraded", "unknown");
}

async function pollMissionControl() {
  const unreachable = document.getElementById("mission-api-unreachable");
  const content = document.getElementById("mission-content");
  try {
    const [statusRes, timelineRes, evidenceRes] = await Promise.all([
      fetch(`${config.apiBase}/mission/status`),
      fetch(`${config.apiBase}/mission/timeline`),
      fetch(`${config.apiBase}/mission/evidence`),
    ]);
    if (!statusRes.ok) throw new Error("Mission API unreachable");
    if (unreachable) unreachable.style.display = "none";
    if (content) content.style.opacity = "1";

    const status = await statusRes.json();
    const timeline = timelineRes.ok ? await timelineRes.json() : { events: [] };
    const evidence = evidenceRes.ok ? await evidenceRes.json() : { items: [], summary: {} };

    state.proof.lastMissionAt = status.timestamp || state.proof.lastMissionAt;
    document.getElementById("mission-mode").textContent = status.system_mode || "unknown";
    document.getElementById("mission-run-id").textContent = status.run_id || status.mission_id || "—";
    setMissionStatus("mission-degraded", status.degraded ? "degraded" : "ok");
    document.getElementById("mission-last-update").textContent =
      status.timestamp || new Date().toISOString();

    renderMissionComponentCards(status.components);
    renderMissionTimeline(timeline.events);
    renderMissionEvidence(evidence.items, evidence.summary);
  } catch (_) {
    showMissionFallback(
      "Mission API unavailable — showing fallback state. Start the API or run a Phase 8 scenario script for artifacts."
    );
    renderMissionTimeline([]);
    renderMissionEvidence([], null);
    const cards = document.getElementById("mission-component-cards");
    if (cards) cards.innerHTML = '<p class="muted">Component cards unavailable until Mission API responds.</p>';
  }
}

async function runMissionScenario(scenario) {
  const resultEl = document.getElementById("mission-scenario-result");
  if (resultEl) resultEl.textContent = `Running scenario ${scenario}…`;
  logAction("Run mission scenario", "Mission Control", "sent", scenario, "mission-control-panel");
  try {
    const res = await fetch(`${config.apiBase}/mission/scenarios/run`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ scenario }),
    });
    const data = await res.json();
    if (!res.ok) {
      if (resultEl) resultEl.textContent = `Scenario failed: ${data.detail || res.status}`;
      logAction("Run mission scenario", "Mission Control", "rejected", `HTTP ${res.status}`, "mission-control-panel");
      showToast(`Scenario failed (HTTP ${res.status})`, "danger");
      return;
    }
    if (resultEl) {
      resultEl.textContent = `Latest scenario: ${data.scenario} (${data.run_id}) — ${data.status}`;
    }
    if (data.run_id) state.proof.commandId = data.run_id;
    logAction("Run mission scenario", "Mission Control", "backend", `${data.scenario} → ${data.status}`, "mission-control-panel");
    showToast(`Scenario ${data.scenario}: ${data.status}`, "ok");
    pulse("mission-control-panel");
    pollMissionControl();
  } catch (_) {
    if (resultEl) {
      resultEl.textContent =
        "Scenario POST failed — run offline: python scripts/run_phase8_mission_scenario.py --scenario " +
        scenario;
    }
    logAction("Run mission scenario", "Mission Control", "error", "API unreachable", "mission-control-panel");
    showToast("Scenario failed — API unreachable", "danger");
  }
}

document.querySelectorAll(".mission-scenario-btn").forEach((btn) => {
  btn.addEventListener("click", () => runMissionScenario(btn.dataset.scenario));
});

pollMissionControl();
setInterval(pollMissionControl, 10000);

/* =========================================================================
 * Phase 10C-2A — Interactive demo cockpit: action log, toasts, pulses,
 * backend proof, capabilities, copilot, guided demo, robotics-lab preview.
 * ========================================================================= */

const RESULT_CLASS = {
  sent: "log-sent",
  backend: "log-backend",
  rejected: "log-rejected",
  unavailable: "log-unavailable",
  error: "log-error",
};

function nowTime() {
  return new Date().toLocaleTimeString();
}

function logAction(action, module, result, detail, targetId) {
  const entry = { time: nowTime(), action, module, result, detail: detail || "", targetId: targetId || "" };
  state.actionLog.unshift(entry);
  if (state.actionLog.length > 60) state.actionLog.pop();
  renderActionLog();
}

function renderActionLog() {
  const body = document.getElementById("action-log-body");
  const count = document.getElementById("action-log-count");
  if (count) count.textContent = `${state.actionLog.length} events`;
  if (!body) return;
  if (!state.actionLog.length) {
    body.innerHTML = '<tr><td colspan="6" class="muted">No actions yet — click any button to see it logged here.</td></tr>';
    return;
  }
  body.innerHTML = state.actionLog
    .map((e) => {
      const cls = RESULT_CLASS[e.result] || "log-sent";
      const jump = e.targetId
        ? `<button type="button" class="jump-btn" data-jump="${e.targetId}">Jump →</button>`
        : "";
      return `<tr>
        <td>${e.time}</td>
        <td>${e.action}</td>
        <td>${e.module}</td>
        <td><span class="log-result ${cls}">${e.result}</span></td>
        <td>${e.detail}</td>
        <td>${jump}</td>
      </tr>`;
    })
    .join("");
}

function showToast(message, kind = "ok") {
  const container = document.getElementById("toast-container");
  if (!container) return;
  const toast = document.createElement("div");
  toast.className = `toast toast-${kind}`;
  toast.textContent = message;
  container.appendChild(toast);
  requestAnimationFrame(() => toast.classList.add("show"));
  setTimeout(() => {
    toast.classList.remove("show");
    setTimeout(() => toast.remove(), 300);
  }, 3800);
}

function pulse(elId) {
  const el = document.getElementById(elId);
  if (!el) return;
  el.classList.remove("pulse-highlight");
  void el.offsetWidth;
  el.classList.add("pulse-highlight");
  setTimeout(() => el.classList.remove("pulse-highlight"), 1600);
}

function scrollToPanel(id) {
  const el = document.getElementById(id);
  if (!el) return;
  el.scrollIntoView({ behavior: "smooth", block: "start" });
  pulse(id);
}

document.getElementById("action-log-body")?.addEventListener("click", (ev) => {
  const btn = ev.target.closest("[data-jump]");
  if (btn) scrollToPanel(btn.dataset.jump);
});

document.getElementById("action-log-clear")?.addEventListener("click", () => {
  state.actionLog = [];
  renderActionLog();
});

renderActionLog();

/* ---- Recommended demo flow jump buttons ---- */
document.querySelectorAll(".flow-step").forEach((btn) => {
  btn.addEventListener("click", () => {
    scrollToPanel(btn.dataset.target);
    logAction("Jump to section", "Demo Cockpit", "sent", btn.textContent.trim(), btn.dataset.target);
  });
});

/* ---- Copy buttons (literal text or element textContent) ---- */
async function copyText(text) {
  try {
    if (navigator.clipboard && navigator.clipboard.writeText) {
      await navigator.clipboard.writeText(text);
      return true;
    }
  } catch (_) {
    /* fall through */
  }
  try {
    const ta = document.createElement("textarea");
    ta.value = text;
    ta.style.position = "fixed";
    ta.style.opacity = "0";
    document.body.appendChild(ta);
    ta.select();
    const ok = document.execCommand("copy");
    ta.remove();
    return ok;
  } catch (_) {
    return false;
  }
}

document.addEventListener("click", async (ev) => {
  const btn = ev.target.closest(".copy-btn");
  if (!btn) return;
  let text = btn.dataset.copyText || "";
  if (!text && btn.dataset.copyTarget) {
    const el = document.getElementById(btn.dataset.copyTarget);
    text = el ? (el.textContent || "").replace(/^[^:]*:\s*/, "").trim() : "";
  }
  if (!text) return;
  const ok = await copyText(text);
  showToast(ok ? "Copied to clipboard" : "Copy failed — select manually", ok ? "ok" : "warn");
  logAction("Copy", "Demo Cockpit", ok ? "backend" : "error", text.slice(0, 60), null);
});

/* ---- Backend proof panel ---- */
const ENDPOINTS = [
  "/health",
  "/health/live",
  "/health/ready",
  "/telemetry/status",
  "/model-scores/status",
  "/mission/status",
  "/status/services",
  "/api/v1/system/info",
  "/openapi.json",
];

function initEndpointLinks() {
  const container = document.getElementById("endpoint-links");
  if (!container) return;
  container.innerHTML = ENDPOINTS.map(
    (ep) =>
      `<span class="endpoint-row"><a class="endpoint-link" href="${config.apiBase}${ep}" target="_blank" rel="noopener">${ep}</a>` +
      `<button type="button" class="copy-btn" data-copy-text="${config.apiBase}${ep}">Copy</button></span>`
  ).join("");
}

function fmtTs(ts) {
  if (!ts) return "—";
  try {
    return new Date(ts).toLocaleTimeString();
  } catch (_) {
    return String(ts);
  }
}

function shortId(id) {
  if (!id) return "—";
  return id.length > 18 ? id.slice(0, 18) + "…" : id;
}

function renderProofCounters() {
  const set = (id, v) => {
    const el = document.getElementById(id);
    if (el) el.textContent = String(v);
  };
  set("proof-cnt-sensors", state.proof.sensors);
  set("proof-cnt-scores", state.proof.scores);
  set("proof-cnt-agents", state.proof.agents);
  set("proof-cnt-decisions", state.proof.decisions);
  set("proof-cnt-safety", state.proof.safety);
  set("proof-cnt-twin", state.proof.twin);
  document.getElementById("proof-last-telemetry").textContent = fmtTs(state.proof.lastTelemetryAt);
  document.getElementById("proof-last-score").textContent = fmtTs(state.proof.lastScoreAt);
  document.getElementById("proof-last-mission").textContent = fmtTs(state.proof.lastMissionAt);
  document.getElementById("proof-trace-id").textContent = shortId(state.proof.traceId);
  document.getElementById("proof-command-id").textContent = shortId(state.proof.commandId);
  document.getElementById("proof-decision-id").textContent = shortId(state.proof.decisionId);
  document.getElementById("proof-scenario").textContent = state.scenario || "—";
  document.getElementById("proof-mode").textContent = state.mode || "—";
}

function setHeaderLive(online) {
  const badge = document.getElementById("header-live-badge");
  if (!badge) return;
  badge.textContent = online ? "Backend: live" : "Backend: offline";
  badge.className = "badge " + (online ? "live-badge-on" : "live-badge-off");
}

async function pollBackendProof() {
  try {
    const [healthRes, liveRes, readyRes, infoRes] = await Promise.all([
      fetch(`${config.apiBase}/health`),
      fetch(`${config.apiBase}/health/live`),
      fetch(`${config.apiBase}/health/ready`),
      fetch(`${config.apiBase}/api/v1/system/info`),
    ]);
    const online = healthRes.ok;
    setHeaderLive(online);
    setOpsStatus("proof-api-health", online ? "ok" : "error");
    if (liveRes.ok) {
      const live = await liveRes.json();
      setOpsStatus("proof-liveness", live.status || "ok");
    }
    if (readyRes) {
      const ready = await readyRes.json().catch(() => ({}));
      setOpsStatus("proof-readiness", ready.status || (readyRes.ok ? "ok" : "error"));
    }
    if (infoRes.ok) {
      const info = await infoRes.json();
      document.getElementById("proof-service").textContent = info.service || "—";
      document.getElementById("proof-version").textContent = info.version || "—";
      if (info.trace_id) state.proof.traceId = state.proof.traceId || info.trace_id;
      updateCopilotInfo(info);
    }
  } catch (_) {
    setHeaderLive(false);
    setOpsStatus("proof-api-health", "error");
    setOpsStatus("proof-liveness", "unavailable");
    setOpsStatus("proof-readiness", "unavailable");
  }
  renderProofCounters();
  renderCapabilities();
}

initEndpointLinks();
pollBackendProof();
setInterval(pollBackendProof, 5000);
setInterval(renderProofCounters, 2000);

/* ---- Operator copilot (LLM) panel ---- */
function updateCopilotInfo(info) {
  const llm = (info && info.llm) || {};
  const set = (id, v) => {
    const el = document.getElementById(id);
    if (el) el.textContent = v == null ? "—" : String(v);
  };
  set("copilot-mode", llm.mode);
  set("copilot-provider", llm.provider);
  set("copilot-model", llm.model);
  set("copilot-authority", llm.authority || "advisory_only");
  set("copilot-real", llm.real_llm_configured ? "yes" : "no (optional)");
  const act = document.getElementById("copilot-activation");
  if (act && llm.activation) act.textContent = llm.activation;
  state.copilotLlm = llm;
}

document.getElementById("copilot-generate")?.addEventListener("click", async () => {
  const out = document.getElementById("copilot-output");
  const traceEl = document.getElementById("copilot-trace");
  const note = document.getElementById("hitl-note")?.value || "";
  if (out) out.textContent = "Generating…";
  logAction("Generate copilot explanation", "Operator Copilot", "sent", "mock advisory", "copilot-panel");
  try {
    const res = await fetch(`${config.apiBase}/api/v1/system/copilot/explain`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ operator_note: note }),
    });
    const data = await res.json();
    if (out) out.textContent = data.explanation || "—";
    if (traceEl) traceEl.textContent = data.trace_id || "—";
    if (data.trace_id) state.proof.traceId = data.trace_id;
    logAction("Generate copilot explanation", "Operator Copilot", "backend", `${data.mode} · advisory_only`, "copilot-panel");
    showToast("Copilot explanation generated (advisory only)", "ok");
    pulse("copilot-panel");
  } catch (_) {
    if (out) out.textContent = "Copilot unavailable — API not reachable.";
    logAction("Generate copilot explanation", "Operator Copilot", "error", "API unreachable", "copilot-panel");
    showToast("Copilot failed — API unreachable", "danger");
  }
});

/* ---- Capabilities & profiles matrix ---- */
function statusFromDot(id) {
  return state.wsStatus[id] ? "active" : "offline";
}

function renderCapabilities() {
  const body = document.getElementById("capabilities-body");
  if (!body) return;
  const apiOnline = document.getElementById("header-live-badge")?.textContent === "Backend: live";
  const navOnline = (document.getElementById("nav-slam-bridge")?.textContent || "offline") === "online";
  const flStatus = document.getElementById("fl-status")?.textContent || "idle";
  const rlStatus = document.getElementById("rl-status")?.textContent || "idle";
  const llm = state.copilotLlm || {};
  const flLive = flStatus && flStatus !== "idle" && flStatus !== "—";
  const rlLive = rlStatus && rlStatus !== "idle" && rlStatus !== "—";

  const rows = [
    ["Core telemetry", apiOnline ? "active" : "offline", "Yes", "Runs in <code>core</code> profile (default)."],
    ["Edge inference", state.proof.scores > 0 ? "active" : (apiOnline ? "active" : "offline"), "Yes", "Runs in <code>core</code> profile."],
    ["Agents / HITL", state.wsStatus["ws-agents-status"] ? "active" : "offline", "Yes", "Runs in <code>core</code> profile."],
    ["Digital twin", state.wsStatus["ws-twin-status"] ? "active" : "offline", "Yes", "Runs in <code>core</code> profile."],
    ["Operator copilot (LLM)", llm.real_llm_configured ? "real LLM" : "mock (advisory)", "Yes (mock)",
      "Optional real LLM: set <code>AXON_LLM_MODE=real</code> + provider key."],
    ["Federated learning", flLive ? "active" : "artifact-only", "No",
      "Run <code>make learning-fl-run</code> or <code>--profile learning</code>."],
    ["RL micro-module", rlLive ? "active" : "artifact-only", "No",
      "Run <code>make learning-rl-run</code> or <code>--profile learning</code>."],
    ["MLOps evidence", "artifact-only", "No", "Run <code>make mlops-pipeline</code>."],
    ["ROS2 bridge", "optional profile", "No", "<code>docker compose --profile ros2 up -d --build</code>"],
    ["ROS2 Nav2 / SLAM", navOnline ? "active" : "offline in core", "No",
      "<code>docker compose --profile ros2-nav-slam up -d --build</code>"],
    ["Observability profile", "optional profile", "No", "<code>docker compose --profile obs up -d</code>"],
  ];

  const statusClass = (s) => {
    if (["active", "real LLM"].includes(s)) return "cap-active";
    if (["artifact-only", "mock (advisory)"].includes(s)) return "cap-artifact";
    if (s.includes("optional") || s.includes("offline")) return "cap-optional";
    return "cap-optional";
  };

  body.innerHTML = rows
    .map(
      ([cap, status, core, how]) =>
        `<tr><td>${cap}</td><td><span class="cap-status ${statusClass(status)}">${status}</span></td><td>${core}</td><td>${how}</td></tr>`
    )
    .join("");
}

/* ---- Robotics Lab local preview (UI-only, not live ROS2) ---- */
const NAV_PREVIEW_PATHS = {
  goal: [[0.5, 0.5], [1.5, 1.2], [2.6, 1.6], [3.6, 1.2], [5.0, 1.0]],
  blocked: [[0.5, 0.5], [1.4, 1.0], [2.6, 1.4], [3.6, 1.5]],
};

let navPreviewTimer = null;

function clearNavPreview() {
  if (navPreviewTimer) {
    clearInterval(navPreviewTimer);
    navPreviewTimer = null;
  }
}

function navPreviewBanner(text) {
  document.getElementById("nav-slam-overlay").textContent = text;
  document.getElementById("nav-slam-cmd-result").textContent =
    "Local preview only; live Nav2 requires the ros2-nav-slam profile.";
}

function runNavPreviewPath(kind) {
  clearNavPreview();
  const svg = document.getElementById("nav-slam-svg");
  if (svg) svg.classList.remove("offline");
  svg?.classList.add("preview");
  const wps = NAV_PREVIEW_PATHS[kind];
  const path = document.getElementById("nav-slam-path");
  if (path) {
    path.setAttribute(
      "d",
      wps.map((w, i) => `${i === 0 ? "M" : "L"} ${navSlamSx(w[0])} ${navSlamSy(w[1])}`).join(" ")
    );
  }
  const goalEl = document.getElementById("nav-slam-goal");
  const last = wps[wps.length - 1];
  if (goalEl) {
    goalEl.setAttribute("cx", navSlamSx(last[0]));
    goalEl.setAttribute("cy", navSlamSy(last[1]));
  }
  const robot = document.getElementById("nav-slam-robot");
  let i = 0;
  navPreviewTimer = setInterval(() => {
    if (i >= wps.length) {
      clearNavPreview();
      if (kind === "blocked") {
        navPreviewBanner("Preview — goal blocked by obstacle (local)");
      } else {
        navPreviewBanner("Preview — goal reached (local)");
      }
      return;
    }
    const w = wps[i];
    if (robot) robot.setAttribute("transform", `translate(${navSlamSx(w[0])},${navSlamSy(w[1])})`);
    document.getElementById("nav-slam-pose").textContent = `(${w[0].toFixed(2)}, ${w[1].toFixed(2)}) θ0.00`;
    i += 1;
  }, 350);
}

function runNavPreviewMapping() {
  clearNavPreview();
  const svg = document.getElementById("nav-slam-svg");
  svg?.classList.remove("offline");
  svg?.classList.add("preview");
  let coverage = 0;
  navPreviewBanner("Preview — SLAM mapping (local)");
  navPreviewTimer = setInterval(() => {
    coverage += 8;
    document.getElementById("nav-slam-coverage").textContent = `${Math.min(coverage, 96)}%`;
    document.getElementById("nav-slam-slam-status").textContent = "mapping (preview)";
    if (coverage >= 96) clearNavPreview();
  }, 300);
}

function previewAction(kind, label) {
  logAction(label, "Robotics Lab", "unavailable", "local preview (not live ROS2)", "nav-slam-panel");
  showToast(`${label} — local UI preview only`, "warn");
  if (kind === "mapping") runNavPreviewMapping();
  else runNavPreviewPath(kind);
  pulse("nav-slam-panel");
}

document.getElementById("nav-slam-preview-mapping")?.addEventListener("click", () =>
  previewAction("mapping", "Preview Mapping Flow")
);
document.getElementById("nav-slam-preview-goal")?.addEventListener("click", () =>
  previewAction("goal", "Preview Nav Goal")
);
document.getElementById("nav-slam-preview-blocked")?.addEventListener("click", () =>
  previewAction("blocked", "Preview Blocked Goal")
);
document.getElementById("nav-slam-preview-reset")?.addEventListener("click", () => {
  clearNavPreview();
  document.getElementById("nav-slam-svg")?.classList.remove("preview");
  setNavSlamOffline();
  navPreviewBanner("MiniLab — offline");
  logAction("Reset Preview", "Robotics Lab", "sent", "preview cleared", "nav-slam-panel");
});

/* ---- Guided demo mode ---- */
const GUIDED_STEPS = [
  { target: "backend-proof-panel", title: "1 · Backend Proof",
    text: "Watch the WebSocket counters and timestamps increase. Open any endpoint link to verify the same data — this is a live backend, not static HTML." },
  { target: "mission-control-panel", title: "2 · Mission Control",
    text: "The operational loop status across telemetry, inference, safety, twin, and evidence. Run a scenario to see the timeline update." },
  { target: "failure-injection-panel", title: "3 · Failure Injection",
    text: "Click 'Low Confidence' to inject a controlled fault. Watch the Safety Panel and System Event Timeline react immediately." },
  { target: "hitl-panel", title: "4 · HITL / Safety",
    text: "When a gate is pending, Confirm/Reject become enabled. Each action returns a backend receipt and is logged." },
  { target: "digital-twin-panel", title: "5 · Digital Twin",
    text: "Pause, resume, safety-stop, or set assist mode. Commands return a receipt and the twin updates on the next broadcast." },
  { target: "learning-evidence-panel", title: "6 · Learning Evidence",
    text: "FL / RL / MLOps run on demand. Copy the exact run command or report path — artifact-backed, not always-on." },
  { target: "nav-slam-panel", title: "7 · Robotics Lab",
    text: "Nav2 + SLAM is offline in the core demo by design. Use the local preview buttons, or copy the activation command for the ros2-nav-slam profile." },
  { target: "evidence-center-panel", title: "8 · Evidence Center",
    text: "Reproducibility artifacts and the evidence index. Everything here is backed by committed files or honest not-generated states." },
];

let guidedIndex = 0;

function renderGuidedStep() {
  const step = GUIDED_STEPS[guidedIndex];
  document.getElementById("guided-demo-title").textContent = step.title;
  document.getElementById("guided-demo-text").textContent = step.text;
  document.getElementById("guided-demo-progress").textContent =
    `Step ${guidedIndex + 1} of ${GUIDED_STEPS.length}`;
  document.getElementById("guided-demo-prev").disabled = guidedIndex === 0;
  const nextBtn = document.getElementById("guided-demo-next");
  nextBtn.textContent = guidedIndex === GUIDED_STEPS.length - 1 ? "Finish" : "Next";
  document.querySelectorAll(".flow-step").forEach((b) => {
    b.classList.toggle("flow-step-current", b.dataset.target === step.target);
  });
  scrollToPanel(step.target);
}

function startGuidedDemo() {
  guidedIndex = 0;
  document.getElementById("guided-demo-overlay").hidden = false;
  renderGuidedStep();
  logAction("Start guided demo", "Demo Cockpit", "sent", "step 1", "backend-proof-panel");
}

function endGuidedDemo() {
  document.getElementById("guided-demo-overlay").hidden = true;
  document.querySelectorAll(".flow-step").forEach((b) => b.classList.remove("flow-step-current"));
  logAction("End guided demo", "Demo Cockpit", "sent", "", null);
}

document.getElementById("guided-demo-start")?.addEventListener("click", startGuidedDemo);
document.getElementById("guided-demo-end")?.addEventListener("click", endGuidedDemo);
document.getElementById("guided-demo-prev")?.addEventListener("click", () => {
  if (guidedIndex > 0) {
    guidedIndex -= 1;
    renderGuidedStep();
  }
});
document.getElementById("guided-demo-next")?.addEventListener("click", () => {
  if (guidedIndex < GUIDED_STEPS.length - 1) {
    guidedIndex += 1;
    renderGuidedStep();
  } else {
    endGuidedDemo();
  }
});
document.addEventListener("keydown", (ev) => {
  if (document.getElementById("guided-demo-overlay").hidden) return;
  if (ev.key === "Escape") endGuidedDemo();
  if (ev.key === "ArrowRight") document.getElementById("guided-demo-next").click();
  if (ev.key === "ArrowLeft") document.getElementById("guided-demo-prev").click();
});
