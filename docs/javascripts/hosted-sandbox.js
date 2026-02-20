(function () {
  const root = document.getElementById("ag-hosted-sandbox");
  if (!root) {
    return;
  }

  const flowsPath = root.dataset.flows || "";
  const state = {
    flows: [],
    runs: [],
  };

  function escapeHtml(value) {
    return String(value)
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#39;");
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

  function inputValue(selector) {
    const node = find(selector);
    if (!(node instanceof HTMLInputElement)) {
      return "";
    }
    return node.value.trim();
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

    const rows = state.runs
      .map((run) => {
        const stateClass = run.matchedExpectation ? "pass" : "fail";
        return `
          <article class="ag-sandbox-run ag-sandbox-run--${stateClass}">
            <header>
              <strong>${escapeHtml(run.title)}</strong>
              <span>${escapeHtml(run.timestamp)}</span>
            </header>
            <p>
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

    const baseUrl = inputValue("[data-field='base-url']");
    if (!baseUrl) {
      window.alert("Set Base URL before running a flow.");
      return;
    }

    const request = flow.request || {};
    const method = String(request.method || "GET").toUpperCase();
    const url = buildUrl(baseUrl, String(request.path || "/"));
    const init = {
      method,
      headers: buildHeaders(),
    };
    if (request.body !== undefined) {
      init.body = JSON.stringify(request.body);
    }

    const timestamp = new Date().toISOString();
    let status = "error";
    let payload = {};

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
    }

    const matchedExpectation = Number(status) === Number(flow.expected_status);
    state.runs.unshift({
      id: flow.id,
      title: flow.title,
      timestamp,
      status,
      expectedStatus: String(flow.expected_status),
      payload,
      matchedExpectation,
    });
    renderRuns();
  }

  async function runAllFlows() {
    for (const flow of state.flows) {
      // Keep order deterministic for transcript readability.
      await runFlow(flow.id);
    }
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
  }

  function wireEvents() {
    root.addEventListener("click", (event) => {
      const target = event.target;
      if (!(target instanceof HTMLElement)) {
        return;
      }

      if (target.matches("[data-flow-id]")) {
        void runFlow(target.dataset.flowId || "");
      }

      if (target.matches("[data-action='run-all']")) {
        void runAllFlows();
      }

      if (target.matches("[data-action='download']")) {
        downloadTranscript();
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
    state.flows = payload;
  }

  async function initialize() {
    root.innerHTML = `
      <div class="ag-sandbox-form">
        <label>Base URL <input data-field="base-url" type="url" placeholder="https://your-agentgate.example.com"></label>
        <label>Tenant ID <input data-field="tenant-id" type="text" placeholder="tenant-01"></label>
        <label>Admin API Key <input data-field="admin-key" type="password" placeholder="optional"></label>
        <label>Requested Version <input data-field="requested-version" type="text" value="2026-02-17"></label>
      </div>
      <div class="ag-next-steps">
        <h3>Credential Helper</h3>
        <ul>
          <li><code>Base URL</code> is required.</li>
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
        </div>
      </div>
      <div data-slot="runs" class="ag-sandbox-runs"></div>
    `;

    try {
      await loadFlows();
      renderFlowButtons();
      renderRuns();
      wireEvents();
    } catch (error) {
      root.innerHTML = `<p>Sandbox failed to load. ${escapeHtml(error instanceof Error ? error.message : String(error))}</p>`;
    }
  }

  void initialize();
})();
