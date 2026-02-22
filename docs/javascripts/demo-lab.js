(function () {
  const ui = window.AgentGateUi || {};
  const root = document.getElementById("ag-demo-lab");
  if (!root) {
    return;
  }

  const scenarioPaths = (root.dataset.scenarios || "")
    .split(",")
    .map((value) => value.trim())
    .filter(Boolean);

  const state = {
    scenarios: [],
    activeId: "",
    replayTimer: null,
    personaMode: "executive",
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

  function formatErrorState(whatHappened, why, howToFix, docsPath) {
    return [
      '<article class="ag-empty" role="alert">',
      "<h4>Unable to load demo lab</h4>",
      `<p><strong>What happened:</strong> ${escapeHtml(whatHappened)}</p>`,
      `<p><strong>Why:</strong> ${escapeHtml(why)}</p>`,
      `<p><strong>How to fix:</strong> ${escapeHtml(howToFix)}</p>`,
      `<p><a href="${escapeHtml(docsPath)}">Open docs</a></p>`,
      "</article>",
    ].join("");
  }

  function activeScenario() {
    return state.scenarios.find((entry) => entry.id === state.activeId);
  }

  function stopReplay() {
    if (state.replayTimer) {
      window.clearInterval(state.replayTimer);
      state.replayTimer = null;
    }
  }

  function renderScenarioList() {
    const scenarioButtons = state.scenarios
      .map((scenario) => {
        const selected = scenario.id === state.activeId ? "ag-lab-chip--active" : "";
        return `<button class="ag-lab-chip ${selected}" data-scenario-id="${escapeHtml(scenario.id)}">${escapeHtml(scenario.title)}</button>`;
      })
      .join("");

    root.querySelector("[data-slot='scenario-list']").innerHTML = scenarioButtons;
  }

  function metricRows(metrics) {
    return Object.entries(metrics)
      .map(([key, value]) => {
        const label = key.replaceAll("_", " ");
        return `<div class="ag-lab-metric"><span>${escapeHtml(label)}</span><strong>${escapeHtml(value)}</strong></div>`;
      })
      .join("");
  }

  function listRows(items) {
    return items.map((item) => `<li>${escapeHtml(item)}</li>`).join("");
  }

  function timelineRows(timeline, revealCount) {
    return timeline
      .map((step, index) => {
        const revealed = index < revealCount ? "ag-lab-timeline__item--revealed" : "";
        return [
          `<li class="ag-lab-timeline__item ${revealed}">`,
          `<span class="ag-lab-timeline__time">${escapeHtml(step.time)}</span>`,
          `<span class="ag-lab-timeline__event">${escapeHtml(step.event)}</span>`,
          `<span class="ag-lab-timeline__decision">${escapeHtml(step.decision)}</span>`,
          `<span class="ag-lab-timeline__impact">${escapeHtml(step.impact)}</span>`,
          "</li>",
        ].join("");
      })
      .join("");
  }

  function scriptRows(scenario) {
    const executiveScript = scenario.non_technical_script || [];
    const technicalScript = scenario.technical_script || [];
    if (state.personaMode === "engineering") {
      return {
        title: "Technical talk track",
        rows: technicalScript,
      };
    }
    if (state.personaMode === "security") {
      return {
        title: "Security talk track",
        rows: technicalScript,
      };
    }
    return {
      title: "Executive talk track",
      rows: executiveScript,
    };
  }

  function renderDetails(revealCount) {
    const scenario = activeScenario();
    if (!scenario) {
      return;
    }

    const artifacts = (scenario.artifacts || [])
      .map(
        (item) =>
          `<li><a href="${escapeHtml(item.path)}">${escapeHtml(item.label)}</a> <code>${escapeHtml(item.type)}</code></li>`,
      )
      .join("");

    const patchBlock = scenario.patch_suggestion
      ? `<pre><code>${escapeHtml(scenario.patch_suggestion.rego)}\n${escapeHtml(scenario.patch_suggestion.regression_test)}</code></pre>`
      : "";

    const rollbackBlock = Array.isArray(scenario.rollback_steps)
      ? `<h4>Rollback steps</h4><ul>${listRows(scenario.rollback_steps)}</ul>`
      : "";

    const lineageBlock = scenario.lineage
      ? `<h4>Rollout lineage</h4><pre><code>${escapeHtml(JSON.stringify(scenario.lineage, null, 2))}</code></pre>`
      : "";

    const script = scriptRows(scenario);

    root.querySelector("[data-slot='scenario-detail']").innerHTML = `
      <div class="ag-lab-headline">
        <p class="ag-eyebrow">${escapeHtml(scenario.tagline)}</p>
        <h2>${escapeHtml(scenario.title)}</h2>
        <p>${escapeHtml(scenario.why_it_matters)}</p>
      </div>
      <div class="ag-lab-signature">
        <span>Scenario progress</span>
        <strong>${Math.min(revealCount, (scenario.timeline || []).length)} / ${(scenario.timeline || []).length} timeline events revealed</strong>
      </div>
      <div class="ag-lab-signature">
        <span>Signed evidence</span>
        <strong>${escapeHtml(scenario.signature.algorithm)} · ${escapeHtml(scenario.signature.digest)}</strong>
      </div>
      <div class="ag-lab-grid">
        <section>
          <h3>Blast radius</h3>
          <div class="ag-lab-metrics">${metricRows(scenario.blast_radius || {})}</div>
        </section>
        <section>
          <h3>What to watch</h3>
          <ul>${listRows((scenario.timeline || []).slice(0, 2).map((entry) => entry.event))}</ul>
          <h3>${escapeHtml(script.title)}</h3>
          <ul>${listRows(script.rows)}</ul>
        </section>
      </div>
      <section>
        <h3>Decision timeline</h3>
        <ol class="ag-lab-timeline">${timelineRows(scenario.timeline || [], revealCount)}</ol>
      </section>
      <section>
        <h3>Artifacts</h3>
        <ul>${artifacts}</ul>
        ${patchBlock}
        ${rollbackBlock}
        ${lineageBlock}
      </section>
    `;
  }

  function replayScenario() {
    stopReplay();
    const scenario = activeScenario();
    if (!scenario) {
      return;
    }

    let revealCount = 0;
    renderDetails(revealCount);
    const totalSteps = (scenario.timeline || []).length;
    emitUxEvent("demo_replay_started", { scenario_id: scenario.id, persona: state.personaMode });

    state.replayTimer = window.setInterval(() => {
      revealCount += 1;
      renderDetails(revealCount);
      emitUxEvent("demo_replay_progress", { scenario_id: scenario.id, reveal_count: revealCount });
      if (revealCount >= totalSteps) {
        stopReplay();
        emitUxEvent("demo_replay_completed", { scenario_id: scenario.id, persona: state.personaMode });
      }
    }, 700);
  }

  function downloadProofBundle() {
    const scenario = activeScenario();
    if (!scenario) {
      return;
    }

    const bundle = {
      generated_at: new Date().toISOString(),
      persona_mode: state.personaMode,
      scenario,
      call_to_action: {
        try_now: "Run `make try` locally.",
        docs: "Use TRY_NOW.md and DEMO_DAY.md for guided demos.",
      },
    };

    const blob = new Blob([JSON.stringify(bundle, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = `${scenario.id}-proof-bundle.json`;
    anchor.click();
    URL.revokeObjectURL(url);
    emitUxEvent("demo_proof_bundle_exported", { scenario_id: scenario.id, persona: state.personaMode });
  }

  function wireEvents() {
    root.addEventListener("click", (event) => {
      const target = event.target;
      if (!(target instanceof HTMLElement)) {
        return;
      }

      const scenarioNode = target.closest("[data-scenario-id]");
      if (scenarioNode instanceof HTMLElement && root.contains(scenarioNode)) {
        state.activeId = scenarioNode.dataset.scenarioId || "";
        stopReplay();
        renderScenarioList();
        renderDetails((activeScenario()?.timeline || []).length);
        emitUxEvent("demo_scenario_selected", { scenario_id: state.activeId, persona: state.personaMode });
      }

      const actionNode = target.closest("[data-action]");
      if (!(actionNode instanceof HTMLElement) || !root.contains(actionNode)) {
        return;
      }

      if (actionNode.matches("[data-action='replay']")) {
        replayScenario();
      }

      if (actionNode.matches("[data-action='download']")) {
        downloadProofBundle();
      }
    });

    root.addEventListener("change", (event) => {
      const target = event.target;
      if (!(target instanceof HTMLSelectElement)) {
        return;
      }
      if (target.matches("[data-field='persona-mode']")) {
        state.personaMode = target.value;
        renderDetails((activeScenario()?.timeline || []).length);
        emitUxEvent("demo_persona_changed", { persona: state.personaMode });
      }
    });
  }

  async function loadScenarios() {
    const loaded = await Promise.all(
      scenarioPaths.map(async (path) => {
        const response = await fetch(path);
        if (!response.ok) {
          throw new Error(`Failed to load scenario: ${path}`);
        }
        return response.json();
      }),
    );
    if (!loaded.length) {
      throw new Error("No scenarios configured.");
    }
    state.scenarios = loaded;
    state.activeId = loaded[0]?.id || "";
  }

  async function initialize() {
    root.innerHTML = `
      <div class="ag-lab-controls">
        <div data-slot="scenario-list" class="ag-lab-chip-row"></div>
        <div class="ag-lab-actions">
          <label>Persona scripts
            <select data-field="persona-mode">
              <option value="executive">Executive</option>
              <option value="security">Security</option>
              <option value="engineering">Engineering</option>
            </select>
          </label>
          <button class="ag-btn" data-action="replay">Replay scenario</button>
          <button class="ag-btn ag-btn--ghost" data-action="download">Download proof bundle</button>
        </div>
      </div>
      <div data-slot="scenario-detail" class="ag-lab-detail" aria-live="polite">
        <div class="ag-skeleton ag-skeleton--line"></div>
        <div class="ag-skeleton ag-skeleton--card"></div>
      </div>
    `;

    try {
      await loadScenarios();
      renderScenarioList();
      renderDetails((activeScenario()?.timeline || []).length);
      wireEvents();
      emitUxEvent("demo_loaded", { scenario_count: state.scenarios.length, persona: state.personaMode });
    } catch (error) {
      const details = error instanceof Error ? error.message : String(error);
      root.innerHTML = formatErrorState(
        details,
        "Scenario fixtures could not be loaded from the configured paths.",
        "Verify scenario JSON paths and refresh the page.",
        resolveDocsHref("DEMO_LAB/"),
      );
    }
  }

  void initialize();
})();
