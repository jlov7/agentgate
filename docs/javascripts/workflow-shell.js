(function () {
  const ui = window.AgentGateUi || {};
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
      "<h4>Workflow unavailable</h4>",
      `<p><strong>What happened:</strong> ${escapeHtml(whatHappened)}</p>`,
      `<p><strong>Why:</strong> ${escapeHtml(why)}</p>`,
      `<p><strong>How to fix:</strong> ${escapeHtml(howToFix)}</p>`,
      `<p><a href="${escapeHtml(docsPath)}">Open docs</a></p>`,
      "</article>",
    ].join("");
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

  async function loadJson(path) {
    if (!path) {
      return [];
    }
    const response = await fetch(path);
    if (!response.ok) {
      throw new Error(`Failed to load fixture: ${path}`);
    }
    const payload = await response.json();
    return Array.isArray(payload) ? payload : [];
  }

  function getRiskClass(severity) {
    const normalized = String(severity || "info").toLowerCase();
    if (normalized === "critical") return "ag-risk--critical";
    if (normalized === "high") return "ag-risk--high";
    if (normalized === "warn" || normalized === "warning") return "ag-risk--warn";
    if (normalized === "medium") return "ag-risk--warn";
    return "ag-risk--info";
  }

  function renderStepper(node, steps, index) {
    const slot = node.querySelector("[data-slot='stepper']");
    if (!slot) {
      return;
    }
    const markup = steps
      .map((label, stepIndex) => {
        const state = stepIndex < index ? "done" : stepIndex === index ? "active" : "todo";
        const current = stepIndex === index ? ' aria-current="step"' : "";
        return [
          `<button type=\"button\" class=\"ag-workflow-step ag-workflow-step--${state}\" data-action=\"goto-step\" data-step-index=\"${stepIndex}\"${current}>`,
          `<span class=\"ag-workflow-step__index\">${stepIndex + 1}</span>`,
          `<span class=\"ag-workflow-step__label\">${escapeHtml(label)}</span>`,
          "</button>",
        ].join("");
      })
      .join("");
    slot.innerHTML = `<div class=\"ag-workflow-stepper\">${markup}</div>`;
  }

  function showPanel(node, index) {
    const panels = Array.from(node.querySelectorAll("[data-step-panel]"));
    for (const panel of panels) {
      const panelIndex = Number(panel.getAttribute("data-step-panel"));
      panel.hidden = panelIndex !== index;
    }
  }

  function completionTarget(kind) {
    if (kind === "replay") {
      return { href: resolveDocsHref("TENANT_ROLLOUTS/"), label: "Continue to tenant rollouts" };
    }
    if (kind === "incident") {
      return { href: resolveDocsHref("TENANT_ROLLOUTS/"), label: "Continue to tenant rollouts" };
    }
    if (kind === "rollout") {
      return { href: resolveDocsHref("OBSERVABILITY_PACK/"), label: "Review observability pack" };
    }
    return { href: resolveDocsHref("JOURNEYS/"), label: "Return to journey map" };
  }

  function renderControls(node, index, total, kind, completed) {
    const slot = node.querySelector("[data-slot='controls']");
    if (!slot) {
      return;
    }
    if (completed) {
      const target = completionTarget(kind);
      slot.innerHTML = [
        '<div class="ag-workflow-controls">',
        '<button type="button" class="ag-btn ag-btn--ghost" data-action="restart">Run workflow again</button>',
        `<a class="ag-btn" href="${escapeHtml(target.href)}">${escapeHtml(target.label)}</a>`,
        "</div>",
        '<p class="ag-workflow-note">Workflow completion recorded. Continue to the next operational gate.</p>',
      ].join("");
      return;
    }
    const isFirst = index === 0;
    const isLast = index >= total - 1;
    slot.innerHTML = [
      '<div class="ag-workflow-controls">',
      `<button type=\"button\" class=\"ag-btn ag-btn--ghost\" data-action=\"prev\" ${isFirst ? "disabled" : ""}>Back</button>`,
      `<button type=\"button\" class=\"ag-btn\" data-action=\"next\">${isLast ? "Finish" : "Continue"}</button>`,
      "</div>",
      '<p class="ag-workflow-note">Use the stepper to review each decision point before promotion.</p>',
    ].join("");
  }

  function renderReplayDeltas(node, deltas) {
    const container = node.querySelector("[data-slot='delta-groups']");
    if (!container) {
      return;
    }

    if (!deltas.length) {
      container.innerHTML = '<div class="ag-empty"><h4>No deltas found</h4><p>Run replay to compare decisions.</p></div>';
      return;
    }

    const groups = {};
    for (const delta of deltas) {
      const key = String(delta.severity || "info").toLowerCase();
      groups[key] = groups[key] || [];
      groups[key].push(delta);
    }

    const order = ["critical", "high", "medium", "low"];
    container.innerHTML = order
      .filter((key) => groups[key])
      .map((key) => {
        const list = groups[key]
          .map(
            (delta) => `
            <article class="ag-risk ${getRiskClass(delta.severity)}">
              <header>
                <strong>${escapeHtml(delta.change)}</strong>
                <code>${escapeHtml(delta.tenant_id)} · ${escapeHtml(delta.session_id)}</code>
              </header>
              <p>${escapeHtml(delta.impact)}</p>
              <p><strong>Tool:</strong> <code>${escapeHtml(delta.tool || "n/a")}</code></p>
            </article>
          `,
          )
          .join("");
        return `<section><h4>${escapeHtml(key.toUpperCase())}</h4>${list}</section>`;
      })
      .join("");
  }

  function renderIncidentTimeline(node, timeline) {
    const slot = node.querySelector("[data-slot='incident-timeline']");
    if (!slot) {
      return;
    }
    slot.innerHTML = timeline
      .map(
        (event) => `
        <li class="ag-workflow-timeline-item">
          <span class="ag-workflow-timeline-time">${escapeHtml(event.time)}</span>
          <strong>${escapeHtml(event.action)}</strong>
          <p>${escapeHtml(event.rationale)}</p>
          <p><em>Rollback preview:</em> ${escapeHtml(event.rollback_preview)}</p>
        </li>
      `,
      )
      .join("");
  }

  function renderRolloutStages(node, stages) {
    const tableSlot = node.querySelector("[data-slot='rollout-stage-table']");
    if (!tableSlot) {
      return;
    }

    const rows = stages
      .map(
        (stage, index) => `
        <tr>
          <td>${index + 1}</td>
          <td>${escapeHtml(stage.stage)}</td>
          <td>${escapeHtml(stage.baseline)}</td>
          <td>${escapeHtml(stage.candidate)}</td>
          <td><span class="ag-risk ${getRiskClass(stage.gate_status)}">${escapeHtml(stage.gate_status)}</span></td>
        </tr>
      `,
      )
      .join("");

    tableSlot.innerHTML = `
      <table class="ag-workflow-table">
        <thead>
          <tr><th>#</th><th>Stage</th><th>Baseline</th><th>Candidate</th><th>Gate</th></tr>
        </thead>
        <tbody>${rows}</tbody>
      </table>
    `;

    const compare = node.querySelector("[data-slot='rollout-change-diff']");
    if (compare && stages.length) {
      const first = stages[0];
      compare.innerHTML = `<p><strong>${escapeHtml(first.stage)}</strong>: ${escapeHtml(first.change_summary)}</p><p><code>${escapeHtml(first.gate_details)}</code></p>`;
    }
  }

  function validateStepGate(node, index) {
    const panel = node.querySelector(`[data-step-panel='${index}']`);
    if (!panel) {
      return true;
    }

    const checks = Array.from(panel.querySelectorAll("[data-gate-required]"));
    if (checks.length === 0) {
      return true;
    }

    const allChecked = checks.every((entry) => entry instanceof HTMLInputElement && entry.checked);
    const gate = panel.querySelector("[data-slot='gate-warning']");
    if (gate) {
      gate.textContent = allChecked ? "" : "Complete all gate checks before continuing.";
    }
    return allChecked;
  }

  function focusActivePanelHeading(node, index) {
    const activePanel = node.querySelector(`[data-step-panel='${index}']`);
    if (!activePanel) {
      return;
    }
    const activeHeading = activePanel.querySelector("h2, h3, h4, h5, h6");
    if (activeHeading instanceof HTMLElement) {
      activeHeading.setAttribute("tabindex", "-1");
      activeHeading.focus();
    }
  }

  function mountWorkflow(node) {
    const steps = String(node.dataset.steps || "")
      .split(";;")
      .map((value) => value.trim())
      .filter(Boolean);

    if (!steps.length) {
      return;
    }

    const kind = String(node.dataset.workflowKind || "generic");
    const state = {
      index: 0,
      replayDeltas: [],
      incidentTimeline: [],
      rolloutStages: [],
      selectedQuarantine: "",
      completed: false,
    };

    const deltaSlot = node.querySelector("[data-slot='delta-groups']");
    if (deltaSlot) {
      deltaSlot.innerHTML = '<div class="ag-skeleton ag-skeleton--card"></div>';
    }
    const incidentSlot = node.querySelector("[data-slot='incident-timeline']");
    if (incidentSlot) {
      incidentSlot.innerHTML =
        '<li class="ag-skeleton ag-skeleton--line"></li><li class="ag-skeleton ag-skeleton--line"></li>';
    }
    const rolloutSlot = node.querySelector("[data-slot='rollout-stage-table']");
    if (rolloutSlot) {
      rolloutSlot.innerHTML =
        '<div class="ag-skeleton ag-skeleton--line"></div><div class="ag-skeleton ag-skeleton--line"></div>';
    }

    function render(options) {
      const shouldFocus = Boolean(options && options.focusHeading);
      renderStepper(node, steps, state.index);
      showPanel(node, state.index);
      renderControls(node, state.index, steps.length, kind, state.completed);
      if (shouldFocus) {
        focusActivePanelHeading(node, state.index);
      }

      const status = node.querySelector("[data-slot='status']");
      if (status) {
        status.setAttribute("aria-live", "polite");
        status.textContent = state.completed
          ? `Workflow completion recorded for ${steps[state.index]}.`
          : `Step ${state.index + 1} of ${steps.length}: ${steps[state.index]}`;
      }
      emitUxEvent("workflow_step_viewed", { workflow: kind, step: state.index + 1, label: steps[state.index] });
    }

    function markCompleted() {
      if (state.completed) {
        return;
      }
      state.completed = true;
      emitUxEvent("workflow_completed", { workflow: kind, step: state.index + 1, total_steps: steps.length });
    }

    node.addEventListener("click", (event) => {
      const target = event.target;
      if (!(target instanceof HTMLElement)) {
        return;
      }
      const actionNode = target.closest("[data-action]");
      if (!(actionNode instanceof HTMLElement) || !node.contains(actionNode)) {
        return;
      }

      if (actionNode.matches("[data-action='goto-step']")) {
        state.completed = false;
        state.index = Number(actionNode.dataset.stepIndex || 0);
        emitUxEvent("workflow_step_jump", { workflow: kind, step: state.index + 1 });
        render({ focusHeading: true });
      }

      if (actionNode.matches("[data-action='prev']")) {
        state.completed = false;
        state.index = Math.max(0, state.index - 1);
        emitUxEvent("workflow_back", { workflow: kind, step: state.index + 1 });
        render({ focusHeading: true });
      }

      if (actionNode.matches("[data-action='next']")) {
        if (!validateStepGate(node, state.index)) {
          emitUxEvent("workflow_gate_blocked", { workflow: kind, step: state.index + 1 });
          return;
        }

        if (state.index < steps.length - 1) {
          state.completed = false;
          state.index += 1;
        } else {
          markCompleted();
        }
        render({ focusHeading: true });
      }

      if (actionNode.matches("[data-action='restart']")) {
        state.completed = false;
        state.index = 0;
        emitUxEvent("workflow_restarted", { workflow: kind });
        render({ focusHeading: true });
      }

      if (actionNode.matches("[data-action='generate-replay-test']")) {
        const slot = node.querySelector("[data-slot='generated-test']");
        if (!slot) {
          return;
        }
        const delta = state.replayDeltas.find((entry) => String(entry.severity).toLowerCase() === "critical") || state.replayDeltas[0];
        if (!delta) {
          slot.innerHTML = "<p>No replay delta available.</p>";
          emitUxEvent("workflow_replay_failure", { workflow: kind, reason: "missing_delta", step: state.index + 1 });
          return;
        }
        slot.innerHTML = `<pre><code>${escapeHtml(delta.suggested_patch)}\n\n${escapeHtml(delta.regression_test)}</code></pre>`;
        emitUxEvent("workflow_replay_test_generated", { workflow: kind, severity: delta.severity || "unknown" });
      }

      if (actionNode.matches("[data-action='apply-patch']")) {
        const slot = node.querySelector("[data-slot='patch-status']");
        if (slot) {
          slot.innerHTML = '<p class="ag-risk ag-risk--info">Patch applied to candidate policy workspace. Re-run replay before promotion.</p>';
        }
        emitUxEvent("workflow_patch_applied", { workflow: kind });
      }

      if (actionNode.matches("[data-action='quarantine-choice']")) {
        const choice = String(actionNode.getAttribute("data-choice") || "");
        state.selectedQuarantine = choice;
        const slot = node.querySelector("[data-slot='quarantine-rationale']");
        if (slot) {
          slot.innerHTML = `<p class="ag-risk ag-risk--high">Decision: <strong>${escapeHtml(choice)}</strong>. Capture rationale and rollback preview before execution.</p>`;
        }
        emitUxEvent("workflow_quarantine_choice", { workflow: kind, choice });
      }

      if (actionNode.matches("[data-action='rollout-compare']")) {
        const select = node.querySelector("[data-field='stage-select']");
        if (!(select instanceof HTMLSelectElement)) {
          return;
        }
        const stage = state.rolloutStages.find((entry) => entry.stage === select.value) || state.rolloutStages[0];
        const slot = node.querySelector("[data-slot='rollout-change-diff']");
        if (slot && stage) {
          slot.innerHTML = `<p><strong>${escapeHtml(stage.stage)}</strong>: ${escapeHtml(stage.change_summary)}</p><p><code>${escapeHtml(stage.gate_details)}</code></p>`;
          emitUxEvent("workflow_rollout_compare", { workflow: kind, stage: stage.stage, gate: stage.gate_status });
        }
      }

      if (actionNode.matches("[data-action='generate-summary']")) {
        const slot = node.querySelector("[data-slot='workflow-summary']");
        if (!slot) {
          return;
        }

        if (kind === "incident") {
          if (!state.selectedQuarantine) {
            slot.innerHTML =
              '<p class="ag-risk ag-risk--warn">Select a quarantine scope in Step 2 before generating workflow completion summary.</p>';
            emitUxEvent("workflow_summary_blocked", { workflow: kind, reason: "missing_quarantine_choice" });
            return;
          }
          const finalEvent = state.incidentTimeline[state.incidentTimeline.length - 1];
          slot.innerHTML = `<pre><code>Incident Summary\n- decision: ${escapeHtml(state.selectedQuarantine || "quarantine-confirmed")}\n- timeline_events: ${state.incidentTimeline.length}\n- final_state: ${escapeHtml(finalEvent ? finalEvent.state : "unknown")}\n- next_action: monitor for recurrence</code></pre>`;
        } else if (kind === "rollout") {
          const completed = state.rolloutStages.filter((entry) => String(entry.gate_status).toLowerCase() === "pass").length;
          slot.innerHTML = `<pre><code>Rollout Summary\n- stages_total: ${state.rolloutStages.length}\n- stages_passed: ${completed}\n- candidate_version: ${escapeHtml(state.rolloutStages[0]?.candidate || "n/a")}\n- recommendation: ${completed === state.rolloutStages.length ? "promote" : "hold"}</code></pre>`;
        }
        emitUxEvent("workflow_summary_generated", { workflow: kind, step: state.index + 1 });
      }
    });

    Promise.all([
      loadJson(node.dataset.replayDeltas || ""),
      loadJson(node.dataset.incidentTimeline || ""),
      loadJson(node.dataset.rolloutStages || ""),
    ])
      .then(([replayDeltas, incidentTimeline, rolloutStages]) => {
        state.replayDeltas = replayDeltas;
        state.incidentTimeline = incidentTimeline;
        state.rolloutStages = rolloutStages;

        renderReplayDeltas(node, replayDeltas);
        renderIncidentTimeline(node, incidentTimeline);
        renderRolloutStages(node, rolloutStages);
        emitUxEvent("workflow_loaded", {
          workflow: kind,
          replay_count: replayDeltas.length,
          incident_count: incidentTimeline.length,
          rollout_count: rolloutStages.length,
        });

        const select = node.querySelector("[data-field='stage-select']");
        if (select instanceof HTMLSelectElement && rolloutStages.length) {
          select.innerHTML = rolloutStages
            .map((stage) => `<option value=\"${escapeHtml(stage.stage)}\">${escapeHtml(stage.stage)}</option>`)
            .join("");
        }

        render();
      })
      .catch((error) => {
        const details = error instanceof Error ? error.message : String(error);
        const status = node.querySelector("[data-slot='status']");
        if (status) {
          status.textContent = "Workflow shell failed to load.";
        }
        const currentPanel = node.querySelector("[data-step-panel='0']");
        if (currentPanel) {
          currentPanel.innerHTML = formatErrorState(
            details,
            "Fixture assets were unavailable or malformed.",
            "Validate the fixture path and JSON schema, then reload the page.",
            resolveDocsHref("JOURNEYS/"),
          );
        }
        emitUxEvent("workflow_replay_failure", { workflow: kind, reason: details, step: state.index + 1 });
      });
  }

  function init() {
    const workflows = Array.from(document.querySelectorAll("[data-ag-workflow]"));
    for (const workflow of workflows) {
      mountWorkflow(workflow);
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
