/** AXON Phase 1 live telemetry dashboard (vanilla JS). */

const SIGNALS = [
  { key: "emg", label: "EMG" },
  { key: "ecg_like", label: "ECG-like" },
  { key: "imu", label: "IMU" },
  { key: "spo2_proxy", label: "SpO2-proxy" },
  { key: "robot_state", label: "Robot State" },
];

const config = window.AXON_CONFIG || { apiBase: "http://localhost:8000", wsBase: "ws://localhost:8000" };

const state = {
  events: [],
  counters: Object.fromEntries(SIGNALS.map((s) => [s.key, 0])),
  sparkHistory: Object.fromEntries(SIGNALS.map((s) => [s.key, []])),
  scenario: "—",
  mode: "awaiting",
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

function pushEvent(event) {
  state.events.unshift(event);
  if (state.events.length > 20) state.events.pop();
  document.getElementById("event-counter").textContent = String(
    Number(document.getElementById("event-counter").textContent) + 1
  );
  updateCard(event);
  renderTable();
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

function connectWs(path, statusId, filterFn) {
  const ws = new WebSocket(`${config.wsBase}${path}`);
  ws.onopen = () => setDot(statusId, true);
  ws.onclose = () => {
    setDot(statusId, false);
    setTimeout(() => connectWs(path, statusId, filterFn), 2000);
  };
  ws.onerror = () => setDot(statusId, false);
  ws.onmessage = (ev) => {
    try {
      const msg = JSON.parse(ev.data);
      if (filterFn && !filterFn(msg)) return;
      handleWsMessage(msg);
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
checkApiHealth();
setInterval(checkApiHealth, 10000);

connectWs("/ws/v1/sensors", "ws-sensors-status", (msg) => {
  if (msg.type === "event") return msg.event?.signal_type !== "robot_state";
  return true;
});

connectWs("/ws/v1/robot-state", "ws-robot-status", (msg) => {
  if (msg.type === "event") return msg.event?.signal_type === "robot_state";
  return true;
});
