(() => {
  "use strict";

  const state = {
    telemetry: null,
    decision: null,
    control: null,
    alert: null,
    event: null,
    operator_summary: null,
    websocket: null,
    reconnectTimer: null,
    reconnectAttempts: 0,
    maxSamples: 60,
    powerHistory: [],
    socHistory: []
  };

  const $ = (id) => document.getElementById(id);

  const fmt = (value, digits = 2) => {
    const number = Number(value);
    return Number.isFinite(number) ? number.toFixed(digits) : "—";
  };

  const shortTime = (value) => {
    if (!value) return "—";
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return String(value);
    return date.toLocaleTimeString([], {
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit"
    });
  };

  function showToast(message) {
    const toast = $("toast");
    toast.textContent = message;
    toast.classList.add("show");
    clearTimeout(showToast.timer);
    showToast.timer = setTimeout(() => {
      toast.classList.remove("show");
    }, 2600);
  }

  function setConnection(online, text) {
    const pill = $("connectionPill");
    pill.classList.toggle("status-online", online);
    pill.classList.toggle("status-offline", !online);
    $("connectionText").textContent = text;
  }

  function severityClass(severity) {
    const value = String(severity || "NONE").toLowerCase();
    if (["low", "medium", "high", "critical"].includes(value)) {
      return `severity-${value}`;
    }
    return "severity-none";
  }

  function setSeverityBadge(element, severity, label = null) {
    element.className = `severity-badge ${severityClass(severity)}`;
    element.textContent = label || severity || "NONE";
  }

  async function fetchJSON(path) {
    const response = await fetch(path, {
      headers: { Accept: "application/json" },
      cache: "no-store"
    });

    if (!response.ok) {
      throw new Error(`${response.status} ${response.statusText}`);
    }

    return response.json();
  }

  async function loadSnapshot() {
    try {
      const result = await fetchJSON("/api/v1/live");
      const snapshot = result?.data?.data || {};
      mergeSnapshot(snapshot);
      renderAll();
      showToast("Live snapshot refreshed");
    } catch (error) {
      showToast(`Snapshot unavailable: ${error.message}`);
    }
  }

  async function loadHealth() {
    try {
      const health = await fetchJSON("/api/v1/health");
      $("footerApiStatus").textContent = "API: online";
      $("footerMqttStatus").textContent =
        `MQTT: ${health.mqtt_connected ? "connected" : "disconnected"}`;
      $("footerMessageCount").textContent =
        `Messages: ${health.live_message_count ?? 0}`;
    } catch {
      $("footerApiStatus").textContent = "API: unavailable";
    }
  }

  async function loadAlerts() {
    try {
      const result = await fetchJSON("/api/v1/alerts?limit=20");
      renderAlerts(result.data || []);
    } catch (error) {
      $("alertsList").innerHTML =
        `<div class="empty-state">Alert history unavailable: ${escapeHTML(error.message)}</div>`;
    }
  }

  function mergeSnapshot(snapshot) {
    for (const key of [
      "telemetry",
      "decision",
      "control",
      "alert",
      "event",
      "operator_summary"
    ]) {
      if (snapshot[key] !== undefined && snapshot[key] !== null) {
        state[key] = snapshot[key];
      }
    }
  }

  function connectWebSocket() {
    if (state.websocket && state.websocket.readyState <= 1) {
      return;
    }

    const protocol = location.protocol === "https:" ? "wss" : "ws";
    const url = `${protocol}://${location.host}/ws/live`;

    setConnection(false, "Connecting");

    const websocket = new WebSocket(url);
    state.websocket = websocket;

    websocket.onopen = () => {
      state.reconnectAttempts = 0;
      setConnection(true, "Live");
    };

    websocket.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data);

        if (message.type === "snapshot") {
          mergeSnapshot(message.payload?.data || {});
          renderAll();
          return;
        }

        if (Object.prototype.hasOwnProperty.call(state, message.type)) {
          state[message.type] = message.payload;
          renderAll();

          if (message.type === "telemetry") {
            captureHistory();
          }

          if (message.type === "alert") {
            loadAlerts();
          }
        }
      } catch (error) {
        console.error("WebSocket message error", error);
      }
    };

    websocket.onerror = () => {
      setConnection(false, "Connection issue");
    };

    websocket.onclose = () => {
      setConnection(false, "Reconnecting");
      scheduleReconnect();
    };
  }

  function scheduleReconnect() {
    clearTimeout(state.reconnectTimer);
    state.reconnectAttempts += 1;

    const delay = Math.min(
      1000 * Math.pow(1.7, state.reconnectAttempts),
      15000
    );

    state.reconnectTimer = setTimeout(
      connectWebSocket,
      delay
    );
  }

  function decisionBundle() {
    return state.decision || {};
  }

  function getDecision() {
    return decisionBundle().decision || {};
  }

  function getOptimization() {
    return decisionBundle().optimization || {};
  }

  function getForecast() {
    return decisionBundle().forecast || {};
  }

  function getAnomaly() {
    return decisionBundle().anomaly || {};
  }

  function getOperatorSummary() {
    return (
      state.operator_summary ||
      decisionBundle().operator_summary ||
      {}
    );
  }

  function renderAll() {
    renderMetrics();
    renderDecision();
    renderForecast();
    renderOptimization();
    renderAnomaly();
    renderOperatorSummary();
    renderAgents();
    renderEnergyFlow();
    drawCharts();
  }

  function renderMetrics() {
    const t = state.telemetry || {};
    const o = getOptimization();
    const f = getForecast();

    $("demandValue").textContent = fmt(t.demand_kw);
    $("solarValue").textContent = fmt(t.solar_generation_kw);
    $("batteryValue").textContent = fmt(t.battery_soc_percent);
    $("gridValue").textContent = fmt(
      o.recommended_grid_import_kw ?? t.net_grid_demand_kw
    );
    $("priceValue").textContent = fmt(t.grid_price_inr_per_kwh);
    $("carbonValue").textContent = fmt(
      t.grid_carbon_intensity_g_per_kwh,
      1
    );

    $("readingId").textContent = t.reading_id ?? "—";
    $("lastUpdated").textContent = shortTime(t.timestamp);

    const demand = Number(t.demand_kw);
    const solar = Number(t.solar_generation_kw);
    const coverage =
      Number.isFinite(demand) && demand > 0 && Number.isFinite(solar)
        ? (solar / demand) * 100
        : NaN;

    $("solarCoverage").textContent =
      `Coverage ${Number.isFinite(coverage) ? coverage.toFixed(1) + "%" : "—"}`;

    $("batteryDispatch").textContent =
      `Dispatch ${fmt(o.recommended_battery_power_kw)} kW`;

    $("gridReduction").textContent =
      `Reduction ${fmt(o.estimated_grid_reduction_kw)} kW`;

    $("costRate").textContent =
      `₹${fmt(o.estimated_cost_inr_per_hour)} / hour`;

    $("carbonRate").textContent =
      `${fmt(o.estimated_carbon_kg_per_hour)} kg CO₂ / hour`;

    $("demandTrend").textContent =
      `Forecast trend ${f.trend || "—"}`;
  }

  function renderDecision() {
    const decision = getDecision();
    const optimization = getOptimization();
    const anomaly = getAnomaly();

    $("heroDecision").textContent =
      humanize(decision.action || "WAITING_FOR_DATA");
    $("heroPriority").textContent =
      `Priority ${decision.priority || "—"}`;
    $("heroReason").textContent =
      decision.reason ||
      "Waiting for the first live decision from the agentic controller.";
    $("controlMode").textContent =
      humanize(optimization.control_mode || "—");
    $("anomalySignals").textContent =
      anomaly.combined_alert_count ?? 0;

    setSeverityBadge(
      $("systemSeverityBadge"),
      anomaly.highest_severity || "NONE",
      anomaly.overall_status || "NORMAL"
    );
  }

  function renderForecast() {
    const f = getForecast();

    $("forecastHorizon").textContent =
      f.forecast_horizon_minutes ?? 15;
    $("forecastValue").textContent =
      fmt(f.predicted_demand_kw);
    $("forecastCurrent").textContent =
      fmt(f.current_demand_kw);
    $("forecastChange").textContent =
      signed(f.demand_change_kw);
    $("forecastTrendBadge").textContent =
      humanize(f.trend || "—");
    $("forecastMae").textContent =
      `${fmt(f.model_mae_kw, 3)} kW`;
    $("forecastRmse").textContent =
      `${fmt(f.model_rmse_kw, 3)} kW`;
    $("forecastR2").textContent =
      fmt(f.model_r2, 4);
  }

  function renderOptimization() {
    const o = getOptimization();

    $("optBattery").textContent =
      fmt(o.recommended_battery_power_kw);
    $("optGrid").textContent =
      fmt(o.recommended_grid_import_kw);
    $("optLoadReduction").textContent =
      fmt(o.recommended_load_reduction_kw);
    $("optSoc").textContent =
      fmt(o.projected_soc_percent);
    $("optCost").textContent =
      fmt(o.estimated_cost_inr_per_hour);
    $("optCarbon").textContent =
      fmt(o.estimated_carbon_kg_per_hour);
    $("optimizationExplanation").textContent =
      o.explanation || "Waiting for optimizer output.";

    const constrained = Boolean(o.battery_constraint_active);
    $("constraintBadge").textContent =
      constrained ? "battery constrained" : "within limits";
  }

  function renderAnomaly() {
    const a = getAnomaly();

    $("anomalyStatus").textContent =
      a.overall_status || "NORMAL";
    $("anomalySummary").textContent =
      a.summary || "Waiting for anomaly analysis.";
    $("ruleAnomalyCount").textContent =
      a.rule_anomaly_count ?? 0;
    $("mlAnomalyStatus").textContent =
      a.ml_status || "—";
    $("mlAnomalySeverity").textContent =
      a.ml_severity || "—";
    $("mlDecisionScore").textContent =
      fmt(a.ml_decision_score, 4);

    setSeverityBadge(
      $("anomalySeverityBadge"),
      a.highest_severity || "NONE"
    );

    const events = Array.isArray(a.rule_events)
      ? a.rule_events
      : [];

    if (!events.length) {
      $("ruleEventList").innerHTML =
        `<div class="empty-state">No active rule-based anomalies.</div>`;
      return;
    }

    $("ruleEventList").innerHTML = events
      .map((event) => `
        <div class="rule-event">
          <strong>${escapeHTML(humanize(event.anomaly_type || "Anomaly"))}</strong>
          <p>${escapeHTML(event.message || "")}</p>
        </div>
      `)
      .join("");
  }

  function renderOperatorSummary() {
    const o = getOperatorSummary();

    $("operatorHeadline").textContent =
      o.headline || "Operator intelligence will appear here.";
    $("operatorSituation").textContent =
      o.situation ||
      "The local LLM summarizes deterministic controller outputs without changing actuator commands.";
    $("operatorWhy").textContent =
      o.why || "—";
    $("operatorSource").textContent =
      humanize(o.source || "awaiting");
    $("operatorModel").textContent =
      `Model ${o.model || "—"}`;
    $("operatorTrigger").textContent =
      `Trigger ${humanize(o.trigger || "—")}`;
    $("operatorLatency").textContent =
      `Latency ${fmt(o.latency_ms, 0)} ms`;

    renderList(
      $("operatorActions"),
      o.operator_actions,
      "No operator action suggested."
    );

    renderList(
      $("operatorRisks"),
      o.risks,
      "No active risk identified."
    );
  }

  function renderList(element, items, emptyText) {
    if (!Array.isArray(items) || !items.length) {
      element.innerHTML = `<li>${escapeHTML(emptyText)}</li>`;
      return;
    }

    element.innerHTML = items
      .slice(0, 3)
      .map((item) => `<li>${escapeHTML(item)}</li>`)
      .join("");
  }

  function renderAgents() {
    const bundle = decisionBundle();
    const agents = bundle.agents || {};
    const forecast = getForecast();

    const data = [
      ["Load Agent", pickStatus(agents.load)],
      ["Battery Agent", pickStatus(agents.battery)],
      ["Pricing Agent", pickStatus(agents.pricing)],
      ["Solar Agent", pickStatus(agents.solar)],
      ["Grid Agent", pickStatus(agents.grid)],
      ["Forecast Agent", forecast.trend || "—"]
    ];

    $("agentsGrid").innerHTML = data
      .map(([name, value]) => `
        <div class="agent-tile">
          <span>${escapeHTML(name)}</span>
          <strong>${escapeHTML(humanize(value))}</strong>
        </div>
      `)
      .join("");
  }

  function pickStatus(agent) {
    if (!agent || typeof agent !== "object") return "—";
    return (
      agent.status ||
      agent.level ||
      agent.dependency ||
      agent.carbon_level ||
      agent.recommendation ||
      "active"
    );
  }

  function renderEnergyFlow() {
    const t = state.telemetry || {};
    const o = getOptimization();

    $("flowSolar").textContent = fmt(t.solar_generation_kw);
    $("flowDemand").textContent = fmt(t.demand_kw);
    $("flowGrid").textContent = fmt(
      o.recommended_grid_import_kw ?? t.net_grid_demand_kw
    );
    $("flowBatteryPower").textContent =
      fmt(o.recommended_battery_power_kw);
    $("flowTimestamp").textContent =
      shortTime(t.timestamp);

    const soc = Math.max(
      0,
      Math.min(100, Number(t.battery_soc_percent) || 0)
    );

    $("socTrackLabel").textContent = `${fmt(soc)}%`;
    $("socTrackFill").style.width = `${soc}%`;
  }

  function captureHistory() {
    const t = state.telemetry || {};
    const o = getOptimization();

    const sample = {
      timestamp: t.timestamp || new Date().toISOString(),
      demand: Number(t.demand_kw),
      solar: Number(t.solar_generation_kw),
      grid: Number(
        o.recommended_grid_import_kw ?? t.net_grid_demand_kw
      ),
      soc: Number(t.battery_soc_percent)
    };

    if (!Number.isFinite(sample.demand)) {
      return;
    }

    state.powerHistory.push(sample);
    state.socHistory.push(sample);

    if (state.powerHistory.length > state.maxSamples) {
      state.powerHistory.shift();
    }

    if (state.socHistory.length > state.maxSamples) {
      state.socHistory.shift();
    }

    drawCharts();
  }

  function drawCharts() {
    drawLineChart(
      $("powerChart"),
      state.powerHistory,
      [
        { key: "demand", cssVar: "--accent" },
        { key: "solar", cssVar: "--accent-2" },
        { key: "grid", cssVar: "--info" }
      ],
      false
    );

    drawLineChart(
      $("socChart"),
      state.socHistory,
      [
        { key: "soc", fixedColor: "#d399ff" }
      ],
      true
    );
  }

  function drawLineChart(canvas, samples, series, socChart) {
    if (!canvas) return;

    const rect = canvas.getBoundingClientRect();
    const dpr = Math.max(1, window.devicePixelRatio || 1);

    canvas.width = Math.floor(rect.width * dpr);
    canvas.height = Math.floor(rect.height * dpr);

    const ctx = canvas.getContext("2d");
    ctx.scale(dpr, dpr);

    const width = rect.width;
    const height = rect.height;

    ctx.clearRect(0, 0, width, height);

    const pad = {
      left: 42,
      right: 12,
      top: 14,
      bottom: 26
    };

    const innerWidth = width - pad.left - pad.right;
    const innerHeight = height - pad.top - pad.bottom;

    ctx.font = "10px system-ui";
    ctx.lineWidth = 1;
    ctx.strokeStyle = "rgba(255,255,255,.07)";
    ctx.fillStyle = "rgba(147,170,168,.82)";

    const allValues = samples.flatMap((sample) =>
      series
        .map((item) => Number(sample[item.key]))
        .filter(Number.isFinite)
    );

    let minValue = socChart ? 0 : 0;
    let maxValue = socChart ? 100 : Math.max(10, ...allValues, 10);

    if (!socChart) {
      maxValue *= 1.12;
    }

    for (let i = 0; i <= 4; i += 1) {
      const y = pad.top + (innerHeight * i) / 4;
      ctx.beginPath();
      ctx.moveTo(pad.left, y);
      ctx.lineTo(width - pad.right, y);
      ctx.stroke();

      const label =
        maxValue - ((maxValue - minValue) * i) / 4;

      ctx.fillText(
        label.toFixed(0),
        6,
        y + 3
      );
    }

    if (!samples.length) {
      ctx.fillStyle = "rgba(147,170,168,.75)";
      ctx.font = "12px system-ui";
      ctx.fillText(
        "Waiting for live samples…",
        pad.left + 8,
        pad.top + innerHeight / 2
      );
      return;
    }

    series.forEach((item) => {
      const cssColor = item.fixedColor ||
        getComputedStyle(document.documentElement)
          .getPropertyValue(item.cssVar)
          .trim();

      ctx.strokeStyle = cssColor;
      ctx.lineWidth = 2;
      ctx.beginPath();

      samples.forEach((sample, index) => {
        const value = Number(sample[item.key]);
        if (!Number.isFinite(value)) return;

        const x =
          pad.left +
          (samples.length === 1
            ? innerWidth / 2
            : (index / (samples.length - 1)) * innerWidth);

        const y =
          pad.top +
          innerHeight -
          ((value - minValue) / (maxValue - minValue || 1)) *
            innerHeight;

        if (index === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
      });

      ctx.stroke();
    });

    const first = samples[0];
    const last = samples[samples.length - 1];

    ctx.fillStyle = "rgba(147,170,168,.82)";
    ctx.font = "9px system-ui";
    ctx.fillText(
      shortTime(first.timestamp),
      pad.left,
      height - 7
    );

    const rightLabel = shortTime(last.timestamp);
    const widthLabel = ctx.measureText(rightLabel).width;
    ctx.fillText(
      rightLabel,
      width - pad.right - widthLabel,
      height - 7
    );
  }

  function renderAlerts(alerts) {
    if (!Array.isArray(alerts) || !alerts.length) {
      $("alertsList").innerHTML =
        `<div class="empty-state">No persisted alerts yet.</div>`;
      return;
    }

    $("alertsList").innerHTML = alerts
      .map((alert) => {
        const severity = String(alert.severity || "NONE");
        const markerColor =
          severity === "CRITICAL" || severity === "HIGH"
            ? "var(--danger)"
            : severity === "MEDIUM"
            ? "var(--warning)"
            : "var(--accent)";

        return `
          <div class="history-item">
            <span
              class="history-marker"
              style="background:${markerColor}; box-shadow:0 0 12px ${markerColor};"
            ></span>
            <div class="history-copy">
              <strong>
                ${escapeHTML(alert.lifecycle || "ALERT")}
                • ${escapeHTML(severity)}
              </strong>
              <p>${escapeHTML(alert.summary || "")}</p>
            </div>
            <span class="history-time">${escapeHTML(shortTime(alert.timestamp))}</span>
          </div>
        `;
      })
      .join("");
  }

  function humanize(value) {
    if (value === null || value === undefined) return "—";
    return String(value)
      .replaceAll("_", " ")
      .replace(/\b\w/g, (char) => char.toUpperCase());
  }

  function signed(value) {
    const number = Number(value);
    if (!Number.isFinite(number)) return "—";
    return `${number >= 0 ? "+" : ""}${number.toFixed(2)}`;
  }

  function escapeHTML(value) {
    return String(value ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#039;");
  }

  function init() {
    $("refreshButton").addEventListener(
      "click",
      async () => {
        await loadSnapshot();
        await loadHealth();
      }
    );

    $("loadAlertsButton").addEventListener(
      "click",
      loadAlerts
    );

    window.addEventListener(
      "resize",
      drawCharts
    );

    loadSnapshot();
    loadHealth();
    loadAlerts();
    connectWebSocket();

    setInterval(loadHealth, 15000);
  }

  document.addEventListener(
    "DOMContentLoaded",
    init
  );
})();
