(function () {
  const ui = window.AgentGateUi || {};
  const root = document.getElementById("ag-hosted-sandbox");
  if (!root) {
    return;
  }

  const flowsPath = root.dataset.flows || "";
  const SAFE_SAMPLE_TENANT = "tenant-safe-sample";

  const state = {
    flows: [],
    runs: [],
    mockMode: false,
    trialStartAt: Date.now(),
    timerId: null,
    milestones: {
      first_flow: null,
      first_pass: null,
      transcript_exported: null,
      handoff_completed: null,
    },
  };

  const escapeHtml =
    ui.escapeHtml ||
    function (value) {
      return String(value)
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#39;");
    };

  function formatErrorState(whatHappened, why, howToFix, docsPath) {
    return [
      '<article class="ag-empty" role="alert">',
      "<h4>Unable to load sandbox</h4>",
      `<p><strong>What happened:</strong> ${escapeHtml(whatHappened)}</p>`,
      `<p><strong>Why:</strong> ${escapeHtml(why)}</p>`,
      `<p><strong>How to fix:</strong> ${escapeHtml(howToFix)}</p>`,
      `<p><a href="${escapeHtml(docsPath)}">Open docs</a></p>`,
      "</article>",
    ].join("");
  }

  function formatJson(value) {
    try {
      return JSON.stringify(value, null, 2);
    } catch (_) {
      return String(value);
    }
  }

  function find(selector) {
    return root.querySelector(selector);
  }

  const emitUxEvent =
    ui.emitUxEvent ||
    function (name, props) {
      window.dispatchEvent(new CustomEvent("ag-ux-event", { detail: { name, props: props || {} } }));
    };

  const resolveDocsHref =
    ui.resolveDocsHref ||
    function (path) {
      return String(path || "");
    };

  function inputValue(selector) {
    const node = find(selector);
    if (!(node instanceof HTMLInputElement)) {
      return "";
    }
    return node.value.trim();
  }

  function markMilestone(key) {
    if (!state.milestones[key]) {
      state.milestones[key] = new Date().toISOString();
      renderMilestones();
    }
  }

  function setInlineFeedback(level, message) {
    const slot = find("[data-slot='inline-feedback']");
    if (!slot) {
      return;
    }
    const tone = level === "error" ? "critical" : level === "warn" ? "warn" : "info";
    slot.innerHTML = `<p class="ag-risk ag-risk--${tone}">${escapeHtml(message)}</p>`;
  }

  function clearInlineFeedback() {
    const slot = find("[data-slot='inline-feedback']");
    if (slot) {
      slot.innerHTML = "";
    }
  }

  function renderTimer() {
    const slot = find("[data-slot='ttv']");
    if (!slot) {
      return;
    }
    const elapsedSeconds = Math.max(0, Math.floor((Date.now() - state.trialStartAt) / 1000));
    const mins = Math.floor(elapsedSeconds / 60);
    const secs = elapsedSeconds % 60;
    slot.innerHTML = `<strong>Time-to-value</strong> <code>${String(mins).padStart(2, "0")}:${String(secs).padStart(2, "0")}</code>`;
  }

  function renderMilestones() {
    const slot = find("[data-slot='milestones']");
    if (!slot) {
      return;
    }

    const labels = {
      first_flow: "First flow executed",
      first_pass: "First passing flow",
      transcript_exported: "Trial report exported",
      handoff_completed: "Trial-to-production handoff completed",
    };

    const rows = Object.entries(labels)
      .map(([key, label]) => {
        const value = state.milestones[key];
        const className = value ? "ag-risk ag-risk--info" : "ag-empty";
        const status = value ? `done at ${value}` : "pending";
        return `<li class="${className}"><strong>${escapeHtml(label)}</strong><br>${escapeHtml(status)}</li>`;
      })
      .join("");

    slot.innerHTML = `<ul class="ag-workflow-timeline">${rows}</ul>`;
  }

  function buildHeaders() {
    const headers = { "Content-Type": "application/json" };
    const tenantId = inputValue("[data-field='tenant-id']");
    const adminKey = inputValue("[data-field='admin-key']");
    const requestedVersion = inputValue("[data-field='requested-version']");

    if (tenantId) {
      headers["X-Tenant-ID"] = tenantId;
    }
    if (adminKey) {
      headers["X-API-Key"] = adminKey;
    }
    if (requestedVersion) {
      headers["X-AgentGate-Requested-Version"] = requestedVersion;
    }
    return headers;
  }

  function buildUrl(baseUrl, path) {
    if (/^https?:\/\//.test(path)) {
      return path;
    }
    const normalizedBase = baseUrl.replace(/\/+$/, "");
    const normalizedPath = path.startsWith("/") ? path : `/${path}`;
    return `${normalizedBase}${normalizedPath}`;
  }

  function narrativeSummary(passCount, failCount) {
    if (failCount === 0 && passCount > 0) {
      return "Trial completed cleanly. You can proceed to production handoff.";
    }
    if (passCount === 0) {
      return "No successful flows yet. Start with health check and sample tenant mode.";
    }
    return "Mixed trial outcome. Review failed flows and remediate before handoff.";
  }

  function renderRuns() {
    const panel = find("[data-slot='runs']");
    if (!panel) {
      return;
    }

    if (state.runs.length === 0) {
      panel.innerHTML = "<p>No runs yet. Execute a flow to capture trial evidence.</p>";
      return;
    }

    const passCount = state.runs.filter((entry) => entry.matchedExpectation).length;
    const failCount = state.runs.length - passCount;
    const summary = narrativeSummary(passCount, failCount);

    const rows = state.runs
      .map((run) => {
        const stateClass = run.matchedExpectation ? "pass" : "fail";
        const badge = run.matchedExpectation ? "PASS" : "FAIL";
        return `
          <article class="ag-sandbox-run ag-sandbox-run--${stateClass}">
            <header>
              <strong>${escapeHtml(run.title)}</strong>
              <span>${escapeHtml(run.timestamp)}</span>
            </header>
            <p>
              <span class="ag-tag">${badge}</span>
              status: <code>${escapeHtml(run.status)}</code>
              expected: <code>${escapeHtml(run.expectedStatus)}</code>
            </p>
            <pre><code>${escapeHtml(formatJson(run.payload))}</code></pre>
          </article>
        `;
      })
      .join("");

    panel.innerHTML = `
      <div class="ag-lab-signature">
        <span>Run summary</span>
        <strong>${passCount} pass · ${failCount} fail</strong>
        <p>${escapeHtml(summary)}</p>
      </div>
      ${rows}
    `;
  }

  function renderFlowButtons() {
    const panel = find("[data-slot='flows']");
    if (!panel) {
      return;
    }
    panel.innerHTML = state.flows
      .map(
        (flow) => `
          <button class="ag-lab-chip" data-flow-id="${escapeHtml(flow.id)}" title="${escapeHtml(flow.description)}">
            ${escapeHtml(flow.title)}
            <code>${escapeHtml(flow.expected_status)}</code>
          </button>
        `,
      )
      .join("");
  }

  async function runFlow(flowId) {
    const flow = state.flows.find((entry) => entry.id === flowId);
    if (!flow) {
      return;
    }

    markMilestone("first_flow");
    clearInlineFeedback();
    emitUxEvent("sandbox_flow_started", { flow_id: flow.id });

    const request = flow.request || {};
    const method = String(request.method || "GET").toUpperCase();
    const timestamp = new Date().toISOString();
    let status = "error";
    let payload = {};

    if (state.mockMode) {
      await new Promise((resolve) => window.setTimeout(resolve, 120));
      status = String(flow.expected_status);
      payload = {
        mock_mode: true,
        request: { method, path: request.path || "/" },
        result: "simulated response from hosted sandbox mock mode",
      };
    } else {
      const baseUrl = inputValue("[data-field='base-url']");
      if (!baseUrl) {
        setInlineFeedback("warn", "Set Base URL before running a live flow, or enable mock mode.");
        emitUxEvent("sandbox_flow_retry", { flow_id: flow.id, reason: "missing_base_url" });
        return;
      }

      const url = buildUrl(baseUrl, String(request.path || "/"));
      const init = {
        method,
        headers: buildHeaders(),
      };
      if (request.body !== undefined) {
        init.body = JSON.stringify(request.body);
      }

      try {
        const response = await fetch(url, init);
        status = String(response.status);
        const text = await response.text();
        try {
          payload = text ? JSON.parse(text) : {};
        } catch (_) {
          payload = { raw: text };
        }
      } catch (error) {
        payload = { error: error instanceof Error ? error.message : String(error) };
        setInlineFeedback("warn", "Flow request failed. Check endpoint reachability, CORS, and credentials.");
      }
    }

    const matchedExpectation = Number(status) === Number(flow.expected_status);
    if (matchedExpectation) {
      markMilestone("first_pass");
      clearInlineFeedback();
      emitUxEvent("sandbox_first_pass", { flow_id: flow.id, mock_mode: state.mockMode });
    } else {
      setInlineFeedback(
        "warn",
        `Flow did not match expected status (${flow.expected_status}). Review response payload and headers.`,
      );
      emitUxEvent("sandbox_flow_failed", { flow_id: flow.id, status });
    }

    state.runs.unshift({
      id: flow.id,
      title: flow.title,
      timestamp,
      status,
      expectedStatus: String(flow.expected_status),
      payload,
      matchedExpectation,
      mock_mode: state.mockMode,
    });
    renderRuns();
  }

  async function runAllFlows() {
    emitUxEvent("sandbox_run_all_started", { flow_count: state.flows.length });
    for (const flow of state.flows) {
      await runFlow(flow.id);
    }
    emitUxEvent("sandbox_run_all_completed", { run_count: state.runs.length });
  }

  function buildTrialReport() {
    const passCount = state.runs.filter((entry) => entry.matchedExpectation).length;
    const failCount = state.runs.length - passCount;
    return {
      generated_at: new Date().toISOString(),
      mode: state.mockMode ? "mock" : "live",
      safe_sample_tenant: inputValue("[data-field='tenant-id']") === SAFE_SAMPLE_TENANT,
      narrative_summary: narrativeSummary(passCount, failCount),
      metrics: {
        total_runs: state.runs.length,
        pass_count: passCount,
        fail_count: failCount,
      },
      milestones: state.milestones,
      raw_transcript: state.runs,
    };
  }

  function downloadTrialReport() {
    const report = buildTrialReport();
    const blob = new Blob([JSON.stringify(report, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = `trial-report-${Date.now()}.json`;
    anchor.click();
    URL.revokeObjectURL(url);
    markMilestone("transcript_exported");
    emitUxEvent("trial_report_exported", { runs: state.runs.length, mode: state.mockMode ? "mock" : "live" });
  }

  function downloadTranscript() {
    const transcript = {
      generated_at: new Date().toISOString(),
      flow_count: state.flows.length,
      runs: state.runs,
    };
    const blob = new Blob([JSON.stringify(transcript, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = `hosted-sandbox-${Date.now()}.json`;
    anchor.click();
    URL.revokeObjectURL(url);
    emitUxEvent("sandbox_transcript_exported", { runs: state.runs.length });
  }

  function completeHandoffChecklist() {
    const checks = Array.from(root.querySelectorAll("[data-handoff-check]"));
    const allChecked = checks.every((entry) => entry instanceof HTMLInputElement && entry.checked);
    const status = find("[data-slot='handoff-status']");
    if (!status) {
      return;
    }

    if (!allChecked) {
      status.innerHTML = '<p class="ag-risk ag-risk--warn">Complete all handoff checks before promotion.</p>';
      return;
    }

    markMilestone("handoff_completed");
    emitUxEvent("trial_handoff_completed", { runs: state.runs.length });
    status.innerHTML = '<p class="ag-risk ag-risk--info">Trial-to-production handoff complete. Continue to replay and rollout gates.</p>';
  }

  function wireEvents() {
    root.addEventListener("click", (event) => {
      const target = event.target;
      if (!(target instanceof HTMLElement)) {
        return;
      }

      const flowNode = target.closest("[data-flow-id]");
      if (flowNode instanceof HTMLElement && root.contains(flowNode)) {
        void runFlow(flowNode.dataset.flowId || "");
      }

      const actionNode = target.closest("[data-action]");
      if (!(actionNode instanceof HTMLElement) || !root.contains(actionNode)) {
        return;
      }

      if (actionNode.matches("[data-action='run-all']")) {
        void runAllFlows();
      }

      if (actionNode.matches("[data-action='download']")) {
        downloadTranscript();
      }

      if (actionNode.matches("[data-action='download-trial-report']")) {
        downloadTrialReport();
      }

      if (actionNode.matches("[data-action='toggle-mock']")) {
        state.mockMode = !state.mockMode;
        actionNode.textContent = state.mockMode ? "Disable mock mode" : "Enable mock mode";
        emitUxEvent("sandbox_mock_mode_toggled", { enabled: state.mockMode });
      }

      if (actionNode.matches("[data-action='safe-sample-tenant']")) {
        const tenantField = find("[data-field='tenant-id']");
        const baseField = find("[data-field='base-url']");
        if (tenantField instanceof HTMLInputElement) {
          tenantField.value = SAFE_SAMPLE_TENANT;
        }
        if (baseField instanceof HTMLInputElement && !baseField.value.trim()) {
          baseField.value = "https://agentgate-sandbox.example.com";
        }
        emitUxEvent("sandbox_safe_sample_enabled", { tenant: SAFE_SAMPLE_TENANT });
      }

      if (actionNode.matches("[data-action='complete-handoff']")) {
        completeHandoffChecklist();
      }
    });
  }

  async function loadFlows() {
    const response = await fetch(flowsPath);
    if (!response.ok) {
      throw new Error(`failed to load flows (${response.status})`);
    }
    const payload = await response.json();
    if (!Array.isArray(payload)) {
      throw new Error("flows payload must be a list");
    }
    if (payload.length === 0) {
      throw new Error("at least one flow is required");
    }
    state.flows = payload;
  }

  async function initialize() {
    root.innerHTML = `
      <div class="ag-lab-signature" data-slot="ttv" aria-live="polite"></div>
      <div class="ag-next-steps">
        <h3>Milestone timeline</h3>
        <div data-slot="milestones" aria-live="polite">
          <div class="ag-skeleton ag-skeleton--line"></div>
          <div class="ag-skeleton ag-skeleton--line"></div>
        </div>
      </div>
      <div class="ag-sandbox-form">
        <label>Base URL <input data-field="base-url" type="url" placeholder="https://your-agentgate.example.com"></label>
        <label>Tenant ID <input data-field="tenant-id" type="text" placeholder="tenant-01"></label>
        <label>Admin API Key <input data-field="admin-key" type="password" placeholder="optional"></label>
        <label>Requested Version <input data-field="requested-version" type="text" value="2026-02-17"></label>
      </div>
      <div data-slot="inline-feedback" aria-live="polite"></div>
      <div class="ag-lab-actions">
        <button class="ag-btn ag-btn--ghost" data-action="toggle-mock">Enable mock mode</button>
        <button class="ag-btn ag-btn--ghost" data-action="safe-sample-tenant">Use safe sample tenant mode</button>
      </div>
      <div class="ag-next-steps">
        <h3>Credential Helper</h3>
        <ul>
          <li><code>Base URL</code> is required in live mode and optional in mock mode.</li>
          <li><code>X-Tenant-ID</code> is optional unless tenant isolation is enforced.</li>
          <li><code>X-API-Key</code> is required for admin-only flows.</li>
          <li><code>X-AgentGate-Requested-Version</code> validates compatibility with your deployment.</li>
        </ul>
      </div>
      <div class="ag-lab-controls">
        <div data-slot="flows" class="ag-lab-chip-row"></div>
        <div class="ag-lab-actions">
          <button class="ag-btn" data-action="run-all">Run all flows</button>
          <button class="ag-btn ag-btn--ghost" data-action="download">Download transcript</button>
          <button class="ag-btn ag-btn--ghost" data-action="download-trial-report">Download trial report</button>
        </div>
      </div>
      <div data-slot="runs" class="ag-sandbox-runs" aria-live="polite">
        <div class="ag-skeleton ag-skeleton--card"></div>
      </div>
      <div class="ag-next-steps">
        <h3>Trial-to-production handoff</h3>
        <label class="ag-check"><input type="checkbox" data-handoff-check> Replace sample tenant with production tenant</label>
        <label class="ag-check"><input type="checkbox" data-handoff-check> Replace trial key with scoped production credential</label>
        <label class="ag-check"><input type="checkbox" data-handoff-check> Confirm replay and rollout gates pass</label>
        <button class="ag-btn" data-action="complete-handoff">Complete handoff</button>
        <div data-slot="handoff-status" aria-live="polite"></div>
      </div>
    `;

    try {
      await loadFlows();
      renderFlowButtons();
      renderRuns();
      renderTimer();
      renderMilestones();
      wireEvents();
      emitUxEvent("sandbox_loaded", { flow_count: state.flows.length });
      state.timerId = window.setInterval(renderTimer, 1000);
    } catch (error) {
      const details = error instanceof Error ? error.message : String(error);
      root.innerHTML = formatErrorState(
        details,
        "The hosted flow fixtures or endpoint configuration did not initialize.",
        "Check the flows asset path and retry in mock mode for deterministic validation.",
        resolveDocsHref("HOSTED_SANDBOX/"),
      );
    }
  }

  void initialize();
})();
