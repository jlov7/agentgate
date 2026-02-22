(function () {
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
      // Ignore storage failures.
    }
  }

  function emitUxEvent(name, props) {
    window.dispatchEvent(new CustomEvent("ag-ux-event", { detail: { name, props: props || {} } }));
  }

  function docsRootPath() {
    if (window.__md_scope && typeof window.__md_scope.pathname === "string") {
      return window.__md_scope.pathname.endsWith("/")
        ? window.__md_scope.pathname
        : `${window.__md_scope.pathname}/`;
    }
    return "/";
  }

  function resolveDocsHref(path) {
    const normalizedPath = String(path || "").replace(/^\/+/, "");
    return `${docsRootPath()}${normalizedPath}`;
  }

  window.AgentGateUi = {
    escapeHtml,
    loadJson,
    saveJson,
    emitUxEvent,
    docsRootPath,
    resolveDocsHref,
  };
})();
