(function () {
  const CONTEXT_KEY = "ag_context_v1";
  const CHECKLIST_KEY = "ag_onboarding_checklist_v1";
  const TOUR_KEY = "ag_start_tour_completed_v1";
  const TIP_KEY_PREFIX = "ag_tip_seen_";
  const RETURNING_KEY = "ag_returning_user_v1";

  const quickLinks = [
    { label: "Start Here", href: "../GET_STARTED/" },
    { label: "Try in 5 Minutes", href: "../TRY_NOW/" },
    { label: "Hosted Sandbox", href: "../HOSTED_SANDBOX/" },
    { label: "Demo Lab", href: "../DEMO_LAB/" },
    { label: "Replay Lab", href: "../REPLAY_LAB/" },
    { label: "Incident Response", href: "../INCIDENT_RESPONSE/" },
    { label: "Tenant Rollouts", href: "../TENANT_ROLLOUTS/" },
    { label: "Operational Trust", href: "../OPERATIONAL_TRUST_LAYER/" },
  ];

  function escapeHtml(value) {
    return String(value)
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#39;");
  }

  function loadJson(key, fallback) {
    try {
      const raw = window.localStorage.getItem(key);
      if (!raw) {
        return fallback;
      }
      return JSON.parse(raw);
    } catch (_) {
      return fallback;
    }
  }

  function saveJson(key, value) {
    try {
      window.localStorage.setItem(key, JSON.stringify(value));
    } catch (_) {
      // Ignore storage failures in private mode.
    }
  }

  function emitUxEvent(name, props) {
    window.dispatchEvent(new CustomEvent("ag-ux-event", { detail: { name, props: props || {} } }));
  }

  function defaultContext() {
    return {
      environment: "staging",
      tenantId: "tenant-a",
      policyVersion: "v2.2",
    };
  }

  function contextState() {
    return {
      ...defaultContext(),
      ...loadJson(CONTEXT_KEY, {}),
    };
  }

  function renderContextChips(context) {
    return [
      `<span class="ag-shell-chip"><strong>Env</strong>${escapeHtml(context.environment)}</span>`,
      `<span class="ag-shell-chip"><strong>Tenant</strong>${escapeHtml(context.tenantId)}</span>`,
      `<span class="ag-shell-chip"><strong>Policy</strong>${escapeHtml(context.policyVersion)}</span>`,
    ].join("");
  }

  function mountContextBar() {
    const nodes = Array.from(document.querySelectorAll("[data-ag-context]"));
    if (nodes.length === 0) {
      return;
    }

    const context = contextState();
    for (const node of nodes) {
      node.innerHTML = [
        '<div class="ag-shell-bar">',
        '<div class="ag-shell-title">Workspace Context</div>',
        `<div class="ag-shell-chip-row">${renderContextChips(context)}</div>`,
        '<button class="ag-btn ag-btn--ghost ag-shell-edit" type="button" data-action="edit-context">Edit</button>',
        "</div>",
      ].join("");

      node.addEventListener("click", (event) => {
        const target = event.target;
        if (!(target instanceof HTMLElement) || target.dataset.action !== "edit-context") {
          return;
        }

        const current = contextState();
        const environment = window.prompt("Environment", current.environment) || current.environment;
        const tenantId = window.prompt("Tenant ID", current.tenantId) || current.tenantId;
        const policyVersion = window.prompt("Policy version", current.policyVersion) || current.policyVersion;

        const next = { environment, tenantId, policyVersion };
        saveJson(CONTEXT_KEY, next);
        emitUxEvent("context_updated", next);
        mountContextBar();
      });
    }
  }

  function mountBreadcrumbs() {
    if (document.querySelector(".ag-breadcrumb")) {
      return;
    }

    const container = document.querySelector(".md-content__inner");
    if (!(container instanceof HTMLElement)) {
      return;
    }

    const path = window.location.pathname.replace(/\/+$/, "");
    const segments = path.split("/").filter(Boolean);

    const crumbs = ['<a href="../">Home</a>'];
    let current = "";
    for (const segment of segments.slice(1)) {
      current += `/${segment}`;
      const label = segment.replace(/[-_]/g, " ").replace(/\b\w/g, (s) => s.toUpperCase());
      crumbs.push(`<a href="${escapeHtml(current)}/">${escapeHtml(label)}</a>`);
    }

    const nav = document.createElement("nav");
    nav.className = "ag-breadcrumb";
    nav.setAttribute("aria-label", "Breadcrumb");
    nav.innerHTML = crumbs.join('<span class="ag-breadcrumb-sep">/</span>');
    container.prepend(nav);
  }

  function mountCommandPalette() {
    if (document.getElementById("ag-command-launch")) {
      return;
    }

    const launch = document.createElement("button");
    launch.id = "ag-command-launch";
    launch.className = "ag-command-launch";
    launch.type = "button";
    launch.textContent = "Quick Actions";
    launch.setAttribute("aria-haspopup", "dialog");
    launch.setAttribute("aria-controls", "ag-command-modal");

    const modal = document.createElement("div");
    modal.id = "ag-command-modal";
    modal.className = "ag-command-modal";
    modal.setAttribute("aria-hidden", "true");
    modal.innerHTML = [
      '<div class="ag-command-overlay" data-action="close"></div>',
      '<div class="ag-command-panel" role="dialog" aria-modal="true" aria-label="Quick actions">',
      '<div class="ag-command-head"><h2>Quick Actions</h2><button type="button" class="ag-btn ag-btn--ghost" data-action="close">Close</button></div>',
      '<p class="ag-command-copy">Jump directly to the next task in your current journey.</p>',
      '<div class="ag-command-links">',
      quickLinks
        .map(
          (entry) =>
            `<a class="ag-command-link" href="${escapeHtml(entry.href)}"><span>${escapeHtml(entry.label)}</span><code>Go</code></a>`,
        )
        .join(""),
      "</div>",
      "</div>",
    ].join("");

    let lastFocused = null;

    function focusableNodes() {
      return Array.from(
        modal.querySelectorAll(
          'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])',
        ),
      ).filter((node) => node instanceof HTMLElement && !node.hasAttribute("disabled"));
    }

    function open() {
      lastFocused = document.activeElement;
      modal.classList.add("ag-command-modal--open");
      modal.setAttribute("aria-hidden", "false");
      const first = focusableNodes()[0];
      if (first instanceof HTMLElement) {
        first.focus();
      }
      emitUxEvent("quick_actions_opened");
    }

    function close() {
      modal.classList.remove("ag-command-modal--open");
      modal.setAttribute("aria-hidden", "true");
      if (lastFocused instanceof HTMLElement) {
        lastFocused.focus();
      }
    }

    launch.addEventListener("click", open);
    modal.addEventListener("click", (event) => {
      const target = event.target;
      if (!(target instanceof HTMLElement)) {
        return;
      }
      if (target.dataset.action === "close") {
        close();
      } else if (target.matches(".ag-command-link")) {
        emitUxEvent("quick_action_navigate", { label: target.textContent ? target.textContent.trim() : "" });
      }
    });

    document.addEventListener("keydown", (event) => {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        open();
      }
      if (modal.classList.contains("ag-command-modal--open") && event.key === "Tab") {
        const nodes = focusableNodes();
        if (nodes.length === 0) {
          return;
        }
        const first = nodes[0];
        const last = nodes[nodes.length - 1];
        const active = document.activeElement;
        if (!event.shiftKey && active === last) {
          event.preventDefault();
          first.focus();
        } else if (event.shiftKey && active === first) {
          event.preventDefault();
          last.focus();
        }
      }
      if (event.key === "Escape") {
        close();
      }
    });

    document.body.appendChild(launch);
    document.body.appendChild(modal);
  }

  function mountOnboardingChecklist() {
    const root = document.getElementById("ag-onboarding-checklist");
    const resume = document.getElementById("ag-onboarding-resume");
    if (!root) {
      return;
    }

    const tasks = (root.dataset.tasks || "")
      .split(";;")
      .map((value) => value.trim())
      .filter(Boolean);

    const links = (root.dataset.links || "")
      .split(";;")
      .map((value) => value.trim())
      .filter(Boolean);

    const progress = loadJson(CHECKLIST_KEY, {});

    function render() {
      const items = tasks
        .map((task, index) => {
          const checked = Boolean(progress[index]);
          const attr = checked ? "checked" : "";
          return [
            '<label class="ag-check">',
            `<input type="checkbox" data-check-index="${index}" ${attr}>`,
            `<span>${escapeHtml(task)}</span>`,
            "</label>",
          ].join("");
        })
        .join("");

      root.innerHTML = `<div class="ag-checklist">${items}</div>`;

      const nextIndex = tasks.findIndex((_, index) => !progress[index]);
      if (resume) {
        if (nextIndex === -1) {
          resume.innerHTML = '<p class="ag-next-state">Onboarding complete. You can move to advanced workflows.</p>';
        } else {
          const href = links[nextIndex] || "../JOURNEYS/";
          resume.innerHTML = `<p class="ag-next-state">Next recommended step: <a href="${escapeHtml(href)}">${escapeHtml(tasks[nextIndex])}</a></p>`;
        }
      }
    }

    root.addEventListener("change", (event) => {
      const target = event.target;
      if (!(target instanceof HTMLInputElement)) {
        return;
      }
      const index = Number(target.dataset.checkIndex);
      if (Number.isNaN(index)) {
        return;
      }
      progress[index] = target.checked;
      saveJson(CHECKLIST_KEY, progress);
      emitUxEvent("onboarding_step_toggled", { step_index: index, checked: target.checked });
      const allDone = tasks.every((_, taskIndex) => Boolean(progress[taskIndex]));
      if (allDone) {
        emitUxEvent("onboarding_completed");
      }
      render();
    });

    render();
    emitUxEvent("onboarding_viewed");
    saveJson(RETURNING_KEY, { seen: true, updated_at: new Date().toISOString() });
  }

  function mountContextTips() {
    const tips = Array.from(document.querySelectorAll("[data-ag-tip]"));
    for (const node of tips) {
      const key = `${TIP_KEY_PREFIX}${node.getAttribute("data-ag-tip")}`;
      const seen = loadJson(key, { seen: false });
      if (seen.seen) {
        node.remove();
        continue;
      }

      node.classList.add("ag-next-steps");
      node.innerHTML = [
        "<h3>Quick Orientation</h3>",
        "<p>Use Quick Actions (or Cmd/Ctrl+K) to jump between setup, sandbox, and operational workflows.</p>",
        '<button type="button" class="ag-btn ag-btn--ghost" data-action="dismiss-tip">Dismiss</button>',
      ].join("");

      node.addEventListener("click", (event) => {
        const target = event.target;
        if (!(target instanceof HTMLElement) || target.dataset.action !== "dismiss-tip") {
          return;
        }
        saveJson(key, { seen: true, updated_at: new Date().toISOString() });
        emitUxEvent("orientation_tip_dismissed", { tip: node.getAttribute("data-ag-tip") || "" });
        node.remove();
      });
    }
  }

  function mountStartTour() {
    const root = document.getElementById("ag-tour");
    if (!root) {
      return;
    }

    const done = loadJson(TOUR_KEY, { done: false }).done;
    if (done) {
      root.innerHTML = "<h3>2-Minute Tour</h3><p>Tour completed. Re-open via Quick Actions if needed.</p>";
      return;
    }

    const steps = [
      { title: "Step 1", text: "Set workspace context and run hosted sandbox health check." },
      { title: "Step 2", text: "Run allow/deny flows and verify expected outcomes." },
      { title: "Step 3", text: "Open Demo Lab and compare scenario blast radius." },
      { title: "Step 4", text: "Continue to Replay, Incident, and Rollout journeys." },
    ];

    root.innerHTML = [
      "<h3>2-Minute Tour</h3>",
      "<p>Use this short guided sequence to reduce setup friction.</p>",
      '<ol class="ag-tour-list">',
      steps.map((step) => `<li><strong>${escapeHtml(step.title)}:</strong> ${escapeHtml(step.text)}</li>`).join(""),
      "</ol>",
      '<button type="button" class="ag-btn ag-btn--ghost" data-action="complete-tour">Mark Tour Complete</button>',
    ].join("");

    root.addEventListener("click", (event) => {
      const target = event.target;
      if (!(target instanceof HTMLElement) || target.dataset.action !== "complete-tour") {
        return;
      }
      saveJson(TOUR_KEY, { done: true, updated_at: new Date().toISOString() });
      emitUxEvent("tour_completed");
      mountStartTour();
    });
  }

  function init() {
    mountBreadcrumbs();
    mountContextBar();
    mountCommandPalette();
    mountOnboardingChecklist();
    mountContextTips();
    mountStartTour();
    emitUxEvent("page_view", { path: window.location.pathname });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
