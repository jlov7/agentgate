(function () {
  const STORAGE_KEY = "ag_ux_telemetry_v1";
  const FEEDBACK_KEY = "ag_ux_feedback_v1";
  const MAX_EVENTS = 1200;

  function loadState() {
    try {
      const raw = window.localStorage.getItem(STORAGE_KEY);
      if (!raw) {
        return { events: [], experiments: {} };
      }
      const parsed = JSON.parse(raw);
      return {
        events: Array.isArray(parsed.events) ? parsed.events : [],
        experiments: typeof parsed.experiments === "object" && parsed.experiments ? parsed.experiments : {},
      };
    } catch (_) {
      return { events: [], experiments: {} };
    }
  }

  function saveState(state) {
    try {
      window.localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
    } catch (_) {
      // Ignore storage failures.
    }
  }

  function chooseVariant(key, variants) {
    const state = loadState();
    if (state.experiments[key]) {
      return state.experiments[key];
    }
    const variant = variants[Math.floor(Math.random() * variants.length)];
    state.experiments[key] = variant;
    saveState(state);
    return variant;
  }

  function track(name, props) {
    const state = loadState();
    const event = {
      name,
      props: props || {},
      at: new Date().toISOString(),
      path: window.location.pathname,
    };
    state.events.push(event);
    if (state.events.length > MAX_EVENTS) {
      state.events = state.events.slice(state.events.length - MAX_EVENTS);
    }
    saveState(state);
    return event;
  }

  function getEvents() {
    return loadState().events;
  }

  function metricCount(name) {
    return getEvents().filter((event) => event.name === name).length;
  }

  function firstEvent(name) {
    return getEvents().find((event) => event.name === name) || null;
  }

  function renderDashboard(node) {
    const state = loadState();
    const events = state.events;

    const firstValue = firstEvent("sandbox_first_pass") || firstEvent("workflow_summary_generated");
    const onboardingStart = firstEvent("onboarding_viewed");
    let timeToValue = "n/a";
    if (onboardingStart && firstValue) {
      const delta = Math.max(0, (Date.parse(firstValue.at) - Date.parse(onboardingStart.at)) / 1000);
      timeToValue = `${Math.round(delta)}s`;
    }

    const activation = metricCount("onboarding_completed");
    const journeyCompletion = metricCount("workflow_summary_generated") + metricCount("trial_handoff_completed");
    const dropOff = Math.max(0, metricCount("onboarding_viewed") - activation);

    const frictionEvents = events.filter((event) =>
      ["workflow_back", "workflow_gate_blocked", "sandbox_flow_failed", "dead_end", "rage_click"].includes(event.name),
    );
    const retries = metricCount("sandbox_flow_retry");
    const confidenceScore = Math.max(
      0,
      100 - frictionEvents.length * 3 + metricCount("trial_handoff_completed") * 5 + metricCount("workflow_patch_applied") * 2,
    );

    const personaMap = {};
    for (const event of events) {
      const persona = event.props && typeof event.props.persona === "string" ? event.props.persona : "unknown";
      personaMap[persona] = personaMap[persona] || { events: 0, completed: 0 };
      personaMap[persona].events += 1;
      if (event.name === "workflow_summary_generated" || event.name === "trial_handoff_completed") {
        personaMap[persona].completed += 1;
      }
    }

    const personaRows = Object.entries(personaMap)
      .map(
        ([persona, stats]) =>
          `<tr><td>${persona}</td><td>${stats.events}</td><td>${stats.completed}</td></tr>`,
      )
      .join("");

    const replayFailures = events.filter((event) => event.name === "workflow_replay_failure").slice(-5);
    const replayRows = replayFailures
      .map(
        (event) =>
          `<li><code>${event.at}</code> ${event.props.reason || "unknown"} (${event.props.step || "n/a"})</li>`,
      )
      .join("");

    const weeklyHealth = Math.max(0, Math.min(100, Math.round(confidenceScore - dropOff * 2 + journeyCompletion * 2)));

    const feedback = (() => {
      try {
        const raw = window.localStorage.getItem(FEEDBACK_KEY);
        return raw ? JSON.parse(raw) : [];
      } catch (_) {
        return [];
      }
    })();

    const feedbackRows = feedback
      .slice(-5)
      .map((entry) => `<li><code>${entry.at}</code> ${entry.note}</li>`)
      .join("");

    node.innerHTML = `
      <div class="ag-lab-grid">
        <section class="ag-card">
          <h3>North-star metrics</h3>
          <ul>
            <li><strong>time_to_value</strong>: ${timeToValue}</li>
            <li><strong>activation</strong>: ${activation}</li>
            <li><strong>journey_completion</strong>: ${journeyCompletion}</li>
            <li><strong>drop_off</strong>: ${dropOff}</li>
            <li><strong>confidence_score</strong>: ${confidenceScore}</li>
          </ul>
        </section>
        <section class="ag-card">
          <h3>Friction</h3>
          <ul>
            <li>workflow_backtracks: ${metricCount("workflow_back")}</li>
            <li>workflow_gate_blocked: ${metricCount("workflow_gate_blocked")}</li>
            <li>sandbox_retries: ${retries}</li>
            <li>rage_click: ${metricCount("rage_click")}</li>
            <li>dead_end: ${metricCount("dead_end")}</li>
          </ul>
        </section>
        <section class="ag-card">
          <h3>Experiments</h3>
          <ul>
            <li>onboarding_variant: ${state.experiments.onboarding_variant || "n/a"}</li>
            <li>cta_variant: ${state.experiments.cta_variant || "n/a"}</li>
          </ul>
          <p>Weekly UX health scorecard: <strong>${weeklyHealth}/100</strong></p>
        </section>
      </div>

      <h3>Role-based journey dashboard</h3>
      <table class="ag-workflow-table">
        <thead><tr><th>Persona</th><th>Events</th><th>Completions</th></tr></thead>
        <tbody>${personaRows || "<tr><td colspan=3>no data</td></tr>"}</tbody>
      </table>

      <h3>Replay diagnostics for failed sessions</h3>
      <ul>${replayRows || "<li>No replay failure events captured.</li>"}</ul>

      <h3>Milestone feedback</h3>
      <ul>${feedbackRows || "<li>No qualitative feedback submitted yet.</li>"}</ul>
      <div class="ag-lab-actions">
        <input data-field="feedback-note" type="text" placeholder="Share feedback from this milestone" aria-label="Feedback note" />
        <button class="ag-btn ag-btn--ghost" data-action="submit-feedback">Submit feedback</button>
      </div>
    `;

    const feedbackButton = node.querySelector("[data-action='submit-feedback']");
    if (feedbackButton instanceof HTMLElement) {
      feedbackButton.addEventListener("click", () => {
        const noteInput = node.querySelector("[data-field='feedback-note']");
        if (!(noteInput instanceof HTMLInputElement) || !noteInput.value.trim()) {
          return;
        }
        let existing = [];
        try {
          const raw = window.localStorage.getItem(FEEDBACK_KEY);
          existing = raw ? JSON.parse(raw) : [];
        } catch (_) {
          existing = [];
        }
        existing.push({ at: new Date().toISOString(), note: noteInput.value.trim() });
        window.localStorage.setItem(FEEDBACK_KEY, JSON.stringify(existing));
        track("feedback_submitted", { note_length: noteInput.value.trim().length });
        renderDashboard(node);
      });
    }
  }

  function installRageClickHeuristic() {
    let lastTarget = null;
    let lastAt = 0;
    let burst = 0;

    document.addEventListener("click", (event) => {
      const target = event.target;
      if (!(target instanceof HTMLElement)) {
        return;
      }
      const now = Date.now();
      const targetKey = target.getAttribute("data-action") || target.id || target.tagName;
      if (targetKey === lastTarget && now - lastAt < 900) {
        burst += 1;
      } else {
        burst = 1;
      }
      lastTarget = targetKey;
      lastAt = now;
      if (burst >= 4) {
        track("rage_click", { target: targetKey });
      }

      if (target.matches("[disabled]")) {
        track("dead_end", { target: targetKey });
      }
    });
  }

  function init() {
    const onboardingVariant = chooseVariant("onboarding_variant", ["checklist_a", "checklist_b"]);
    const ctaVariant = chooseVariant("cta_variant", ["verb_first", "trust_first"]);

    track("analytics_booted", { onboarding_variant: onboardingVariant, cta_variant: ctaVariant });

    installRageClickHeuristic();

    window.addEventListener("ag-ux-event", (event) => {
      const detail = event instanceof CustomEvent ? event.detail : null;
      if (!detail || typeof detail.name !== "string") {
        return;
      }
      track(detail.name, detail.props || {});
    });

    const dashboard = document.getElementById("ag-ux-analytics");
    if (dashboard) {
      renderDashboard(dashboard);
    }
  }

  window.AgentGateUX = {
    track,
    events: getEvents,
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
