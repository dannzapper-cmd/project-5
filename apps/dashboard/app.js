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
};

const SENSOR_STATUS_CLASS = {
  active: "status-active",
  stale: "status-stale",
  dropout: "status-dropout",
  degraded: "status-degraded",
  corrupt: "status-corrupt",
};

function setDot(id, online, waiting = false) {
  const el = document.getElementById(id);
  el.className = "dot " + (online ? "online" : waiting ? "waiting" : "offline");
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
  updateCard(event);
  renderTable();
}

function pushModelScore(event) {
  state.modelScores.unshift(event);
  if (state.modelScores.length > 20) state.modelScores.pop();
  document.getElementById("model-score-counter").textContent = String(
    Number(document.getElementById("model-score-counter").textContent) + 1
  );
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
  renderTracesTable();
}

function pushDecision(event) {
  state.decisions.unshift(event);
  if (state.decisions.length > 30) state.decisions.pop();
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
}

function updateSafetyPanel(s) {
  state.safety = s;
  document.getElementById("safety-mode").textContent = s.safety_mode || "deterministic";
  document.getElementById("safety-stale").textContent = String(s.stale_telemetry ?? "—");
  document.getElementById("safety-missing").textContent =
    (s.missing_signals || []).join(", ") || "none";
  document.getElementById("safety-low-conf").textContent = String(s.low_confidence ?? "—");
  document.getElementById("safety-high-risk").textContent = String(s.high_risk ?? "—");
  document.getElementById("safety-llm").textContent = s.llm_authority || "advisory only";
  document.getElementById("active-injections").textContent =
    (s.active_injections || []).join(", ") || "none";
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

async function refreshCurrentDecision() {
  try {
    const res = await fetch(`${config.apiBase}/api/v1/decisions/current`);
    const data = await res.json();
    const id = data.decision_id;
    state.currentDecisionId = id || null;
    document.getElementById("hitl-decision-id").textContent = id || "none";
    const pending = data.status === "pending_human_confirmation";
    document.getElementById("hitl-confirm").disabled = !pending;
    document.getElementById("hitl-reject").disabled = !pending;
    if (data.decision_id) updateDecisionPanel(data);
  } catch (_) {
    document.getElementById("hitl-confirm").disabled = true;
    document.getElementById("hitl-reject").disabled = true;
  }
}

async function hitlAction(action) {
  if (!state.currentDecisionId) return;
  const note = document.getElementById("hitl-note").value || "";
  const url = `${config.apiBase}/api/v1/decisions/${state.currentDecisionId}/${action}`;
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
      document.getElementById("hitl-confirm").disabled = true;
      document.getElementById("hitl-reject").disabled = true;
    }
  } catch (_) {
    /* ignore */
  }
}

async function triggerInjection(scenario) {
  try {
    await fetch(`${config.apiBase}/api/v1/failure-injection/${scenario}`, { method: "POST" });
    const res = await fetch(`${config.apiBase}/api/v1/safety/status`);
    if (res.ok) updateSafetyPanel(await res.json());
  } catch (_) {
    /* ignore */
  }
}

async function resetInjection() {
  try {
    await fetch(`${config.apiBase}/api/v1/failure-injection/reset`, { method: "POST" });
    document.getElementById("active-injections").textContent = "none";
  } catch (_) {
    /* ignore */
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
  try {
    const res = await fetch(`${config.apiBase}/api/v1/mlops/promote-candidate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ signal_type: "emg", dry_run: true, operator_note: "dashboard-simulated-review" }),
    });
    const data = await res.json();
    document.getElementById("mlops-review-id").textContent =
      data.review_record_id ? `Review record: ${data.review_record_id}` : "";
  } catch (_) {
    document.getElementById("mlops-review-id").textContent = "Promotion dry-run failed (API unavailable)";
  }
});

pollMlopsStatus();
setInterval(pollMlopsStatus, 10000);

function updateTwinPanel(twin) {
  if (!twin) return;
  state.twin = twin;
  const mode = twin.robot_state?.mode || "idle";
  const svg = document.getElementById("twin-svg");
  svg.className = "twin-svg mode-" + mode;

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
    el.className = "twin-sensor " + (SENSOR_STATUS_CLASS[status] || "status-dropout");
    el.setAttribute("title", `${key}: ${twin.sensor_nodes[key].latest_value_summary}`);
  }

  const robotG = document.getElementById("twin-robot");
  if (robotG && twin.robot_state?.pose) {
    const ox = (twin.robot_state.pose.orientation_deg || 0) * 0.3;
    robotG.setAttribute("transform", `translate(${210 + ox}, 160)`);
  }
}

async function sendTwinCommand(command, extra = {}) {
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
    document.getElementById("twin-cmd-result").textContent =
      `${data.status}: ${data.reason || data.command} (trace ${(data.trace_id || "").slice(0, 12)}…)`;
    return data;
  } catch (e) {
    document.getElementById("twin-cmd-result").textContent = "Command failed";
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
