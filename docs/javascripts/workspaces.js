(function () {
  const ui = window.AgentGateUi || {};
  const root = document.getElementById("ag-workspaces");
  if (!root) {
    return;
  }

  const catalogPath = root.dataset.personas || "";
  const LAYOUT_KEY = "ag_workspace_layout_v1";
  const VIEWS_KEY = "ag_workspace_saved_views_v1";
  const MODE_KEY = "ag_workspace_terminology_mode_v1";
  const DEFAULT_WORKSPACE_PATH = "JOURNEYS/";
  const actionDestinations = {
    "Review trust posture": "OPERATIONAL_TRUST_LAYER/",
    "Validate launch gate": "JOURNEYS/",
    "Share executive proof bundle": "DEMO_DAY/",
    "Run replay delta analysis": "REPLAY_LAB/",
    "Execute quarantine decision": "INCIDENT_RESPONSE/",
    "Publish incident summary": "INCIDENT_RESPONSE/",
    "Run hosted sandbox": "HOSTED_SANDBOX/",
    "Compare rollout stages": "TENANT_ROLLOUTS/",
    "Inspect observability pack": "OBSERVABILITY_PACK/",
    "Open evidence center": "OPERATIONAL_TRUST_LAYER/",
    "Validate signature lineage": "THREAT_MODEL/",
    "Package support bundle": "SUPPORT_TIERS/",
    "Triage live alerts": "OBSERVABILITY_PACK/",
    "Open rollback runbook": "INCIDENT_RESPONSE/",
    "Confirm on-call handoff": "SUPPORT_TIERS/",
  };

  const state = {
    catalog: [],
    persona: "executive",
    tenant: "tenant-a",
    terminologyMode: "technical",
    layout: ["kpis", "actions", "notes"],
    adminPolicyLocked: false,
  };

  const emitUxEvent =
    ui.emitUxEvent ||
    function (name, props) {
      window.dispatchEvent(new CustomEvent("ag-ux-event", { detail: { name, props: props || {} } }));
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

  const loadJson =
    ui.loadJson ||
    function (key, fallback) {
      try {
        const raw = window.localStorage.getItem(key);
        return raw ? JSON.parse(raw) : fallback;
      } catch (_) {
        return fallback;
      }
    };

  const saveJson =
    ui.saveJson ||
    function (key, value) {
      try {
        window.localStorage.setItem(key, JSON.stringify(value));
      } catch (_) {
        // Ignore local storage failures.
      }
    };

  const resolveDocsHref =
    ui.resolveDocsHref ||
    function (path) {
      return String(path || "");
    };

  function currentPersona() {
    return state.catalog.find((entry) => entry.persona === state.persona) || state.catalog[0];
  }

  function workspaceCopyLabel(label) {
    if (state.terminologyMode === "non_technical") {
      return label
        .replace("Policy drift events", "Policy changes")
        .replace("Canary gate", "Staged launch check")
        .replace("Control mapping", "Compliance mapping")
        .replace("Rollback readiness", "Recovery readiness");
    }
    return label;
  }

  function actionPath(label) {
    return actionDestinations[label] || DEFAULT_WORKSPACE_PATH;
  }

  function adaptiveDefaultPersona() {
    // adaptive default: infer from recent event usage if no explicit choice was saved.
    const events = window.AgentGateUX && typeof window.AgentGateUX.events === "function" ? window.AgentGateUX.events() : [];
    const counts = { executive: 0, security: 0, engineering: 0, compliance: 0, ops: 0 };
    for (const event of events.slice(-80)) {
      if (event.path && String(event.path).includes("REPLAY")) counts.security += 1;
      if (event.path && String(event.path).includes("ROLLOUT")) counts.engineering += 1;
      if (event.path && String(event.path).includes("TRUST")) counts.compliance += 1;
      if (event.path && String(event.path).includes("INCIDENT")) counts.ops += 1;
      if (event.path && String(event.path).includes("EXEC")) counts.executive += 1;
    }
    const best = Object.entries(counts).sort((a, b) => b[1] - a[1])[0];
    return best && best[1] > 0 ? best[0] : "executive";
  }

  function renderLayoutControls() {
    const slot = root.querySelector("[data-slot='layout-controls']");
    if (!slot) {
      return;
    }

    const blocks = state.layout
      .map(
        (item, index) => `
        <li class="ag-card">
          <strong>${escapeHtml(item)}</strong>
          <div class="ag-lab-actions">
            <button class="ag-btn ag-btn--ghost" data-action="move-up" data-index="${index}">Move up</button>
            <button class="ag-btn ag-btn--ghost" data-action="move-down" data-index="${index}">Move down</button>
          </div>
        </li>
      `,
      )
      .join("");

    slot.innerHTML = `<ul class="ag-card-grid">${blocks}</ul>`;
  }

  function renderWorkspace() {
    const persona = currentPersona();
    if (!persona) {
      return;
    }

    const actions = persona.actions
      .map((action) => {
        const path = actionPath(action);
        return `<li><a href="${escapeHtml(resolveDocsHref(path))}" data-action="workspace-action" data-action-label="${escapeHtml(action)}" data-action-path="${escapeHtml(path)}">${escapeHtml(action)}</a></li>`;
      })
      .join("");

    const kpiRows = persona.kpis
      .map(
        (kpi) => `
        <article class="ag-kpi">
          <span class="ag-kpi__label">${escapeHtml(workspaceCopyLabel(kpi.label))}</span>
          <strong>${escapeHtml(kpi.value)}</strong>
        </article>
      `,
      )
      .join("");

    const label = state.terminologyMode === "technical" ? "Technical terminology" : "Non-technical terminology";
    const adminPolicyLine = state.adminPolicyLocked
      ? '<p class="ag-risk ag-risk--warn"><strong>Admin policy</strong>: regulated tenant defaults are enforced and layout changes are locked.</p>'
      : '<p class="ag-risk ag-risk--info"><strong>Admin policy</strong>: default workspace can be customized for this tenant.</p>';

    root.querySelector("[data-slot='workspace']").innerHTML = `
      <div class="ag-next-steps">
        <h3>${escapeHtml(persona.headline)}</h3>
        <p>Mode: <strong>${escapeHtml(label)}</strong></p>
        ${adminPolicyLine}
      </div>
      <div class="ag-kpis">${kpiRows}</div>
      <div class="ag-next-steps">
        <h3>Next actions</h3>
        <ul>${actions}</ul>
      </div>
    `;

    renderLayoutControls();
  }

  function renderPersonaTabs() {
    const slot = root.querySelector("[data-slot='persona-tabs']");
    if (!slot) {
      return;
    }

    slot.innerHTML = state.catalog
      .map((entry) => {
        const active = entry.persona === state.persona ? "ag-lab-chip ag-lab-chip--active" : "ag-lab-chip";
        return `<button type="button" class="${active}" data-action="select-persona" data-persona="${escapeHtml(entry.persona)}">${escapeHtml(entry.persona)}</button>`;
      })
      .join("");
  }

  function saveView() {
    const saved = loadJson(VIEWS_KEY, []);
    const view = {
      at: new Date().toISOString(),
      tenant: state.tenant,
      persona: state.persona,
      terminology: state.terminologyMode,
      layout: state.layout.slice(),
    };
    saved.unshift(view);
    saveJson(VIEWS_KEY, saved.slice(0, 20));
    emitUxEvent("workspace_saved_view", { persona: state.persona, tenant: state.tenant });
  }

  function renderSavedViews() {
    const slot = root.querySelector("[data-slot='saved-views']");
    if (!slot) {
      return;
    }
    const saved = loadJson(VIEWS_KEY, []);
    if (!saved.length) {
      slot.innerHTML = [
        '<article class="ag-empty">',
        "<h4>No saved views yet</h4>",
        "<p>Save your current view to reopen this workspace with the same persona and layout.</p>",
        '<button class="ag-btn ag-btn--ghost" type="button" data-action="save-view">Save your current view</button>',
        "</article>",
      ].join("");
      return;
    }
    slot.innerHTML = saved
      .slice(0, 6)
      .map(
        (view, index) => `
        <button class="ag-card" data-action="load-view" data-view-index="${index}">
          <strong>${escapeHtml(view.persona)} @ ${escapeHtml(view.tenant)}</strong>
          <span>${escapeHtml(view.at)}</span>
        </button>
      `,
      )
      .join("");
  }

  function persistLayout() {
    saveJson(LAYOUT_KEY, { persona: state.persona, layout: state.layout });
  }

  function wireEvents() {
    root.addEventListener("click", (event) => {
      const target = event.target;
      if (!(target instanceof HTMLElement)) {
        return;
      }
      const actionNode = target.closest("[data-action]");
      if (!(actionNode instanceof HTMLElement) || !root.contains(actionNode)) {
        return;
      }

      if (actionNode.matches("[data-action='select-persona']")) {
        state.persona = String(actionNode.getAttribute("data-persona") || "executive");
        const persona = currentPersona();
        state.layout = Array.isArray(persona.default_layout) ? persona.default_layout.slice() : state.layout;
        persistLayout();
        renderPersonaTabs();
        renderWorkspace();
        emitUxEvent("workspace_persona_selected", { persona: state.persona, tenant: state.tenant });
      }

      if (actionNode.matches("[data-action='toggle-terminology']")) {
        state.terminologyMode = state.terminologyMode === "technical" ? "non_technical" : "technical";
        saveJson(MODE_KEY, { terminology: state.terminologyMode });
        renderWorkspace();
        emitUxEvent("workspace_terminology_changed", { mode: state.terminologyMode, persona: state.persona });
      }

      if (actionNode.matches("[data-action='save-view']")) {
        saveView();
        renderSavedViews();
      }

      if (actionNode.matches("[data-action='load-view']")) {
        const saved = loadJson(VIEWS_KEY, []);
        const index = Number(actionNode.getAttribute("data-view-index") || 0);
        const view = saved[index];
        if (!view) {
          return;
        }
        state.tenant = view.tenant;
        state.persona = view.persona;
        state.terminologyMode = view.terminology;
        state.layout = Array.isArray(view.layout) ? view.layout.slice() : state.layout;
        renderPersonaTabs();
        renderWorkspace();
        emitUxEvent("workspace_saved_view_loaded", { persona: state.persona, tenant: state.tenant });
      }

      if (actionNode.matches("[data-action='move-up']") || actionNode.matches("[data-action='move-down']")) {
        if (state.adminPolicyLocked) {
          emitUxEvent("workspace_layout_change_blocked", { reason: "admin_policy_locked" });
          return;
        }
        const index = Number(actionNode.getAttribute("data-index") || 0);
        const nextIndex = actionNode.matches("[data-action='move-up']") ? index - 1 : index + 1;
        if (nextIndex < 0 || nextIndex >= state.layout.length) {
          return;
        }
        const clone = state.layout.slice();
        const temp = clone[index];
        clone[index] = clone[nextIndex];
        clone[nextIndex] = temp;
        state.layout = clone;
        persistLayout();
        renderLayoutControls();
        emitUxEvent("workspace_layout_changed", { layout: state.layout, persona: state.persona });
      }

      if (actionNode.matches("[data-action='toggle-admin-policy']")) {
        state.adminPolicyLocked = !state.adminPolicyLocked;
        renderWorkspace();
        emitUxEvent("workspace_admin_policy_toggled", { locked: state.adminPolicyLocked });
      }

      if (actionNode.matches("[data-action='workspace-action']")) {
        emitUxEvent("workspace_action_clicked", {
          persona: state.persona,
          action: actionNode.getAttribute("data-action-label") || "",
          destination: actionNode.getAttribute("data-action-path") || "",
        });
      }
    });
  }

  async function loadCatalog() {
    const response = await fetch(catalogPath);
    if (!response.ok) {
      throw new Error(`failed to load workspace catalog (${response.status})`);
    }
    const payload = await response.json();
    if (!Array.isArray(payload)) {
      throw new Error("workspace catalog must be an array");
    }
    if (payload.length === 0) {
      throw new Error("workspace catalog is empty");
    }
    state.catalog = payload;
  }

  function hydrateDefaults() {
    const layoutState = loadJson(LAYOUT_KEY, {});
    const terminologyState = loadJson(MODE_KEY, {});

    state.terminologyMode = terminologyState.terminology || state.terminologyMode;

    if (layoutState.persona && Array.isArray(layoutState.layout) && layoutState.layout.length) {
      state.persona = layoutState.persona;
      state.layout = layoutState.layout;
    } else {
      state.persona = adaptiveDefaultPersona();
      const persona = currentPersona();
      if (persona && Array.isArray(persona.default_layout)) {
        state.layout = persona.default_layout.slice();
      }
      emitUxEvent("workspace_adaptive_default_applied", { adaptive_default: state.persona });
    }
  }

  async function initialize() {
    root.innerHTML = `
      <div class="ag-next-steps">
        <h3>Workspace controls</h3>
        <div class="ag-lab-actions">
          <button class="ag-btn ag-btn--ghost" data-action="toggle-terminology">Toggle terminology</button>
          <button class="ag-btn ag-btn--ghost" data-action="save-view">Save view</button>
          <button class="ag-btn ag-btn--ghost" data-action="toggle-admin-policy">Toggle admin policy lock</button>
        </div>
      </div>
      <div data-slot="persona-tabs" class="ag-lab-chip-row" aria-live="polite"></div>
      <div data-slot="workspace" class="ag-lab" aria-live="polite"></div>
      <div class="ag-next-steps">
        <h3>My workspace layout</h3>
        <div data-slot="layout-controls"></div>
      </div>
      <div class="ag-next-steps">
        <h3>Saved views</h3>
        <div data-slot="saved-views" class="ag-card-grid"></div>
      </div>
    `;

    try {
      await loadCatalog();
      hydrateDefaults();
      renderPersonaTabs();
      renderWorkspace();
      renderSavedViews();
      wireEvents();
      emitUxEvent("workspace_loaded", { persona: state.persona, terminology: state.terminologyMode });
    } catch (error) {
      root.innerHTML = `<article class="ag-empty"><h4>Workspace unavailable</h4><p>${escapeHtml(
        error instanceof Error ? error.message : String(error),
      )}</p></article>`;
    }
  }

  void initialize();
})();
