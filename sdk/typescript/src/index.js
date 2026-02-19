export class AgentGateApiError extends Error {
  constructor({ method, path, statusCode, payload }) {
    const detail =
      payload && typeof payload === "object"
        ? payload.detail || payload.error
        : payload;
    const suffix = detail ? `: ${detail}` : "";
    super(`${method} ${path} failed with status ${statusCode}${suffix}`);
    this.name = "AgentGateApiError";
    this.method = method;
    this.path = path;
    this.statusCode = statusCode;
    this.payload = payload;
  }
}

export class AgentGateClient {
  constructor({
    baseUrl,
    apiKey,
    tenantId,
    requestedApiVersion,
    headers,
    fetchImpl,
  }) {
    if (!baseUrl || typeof baseUrl !== "string") {
      throw new Error("baseUrl is required");
    }
    this.baseUrl = baseUrl.replace(/\/+$/, "");
    this.apiKey = apiKey ?? null;
    this.tenantId = tenantId ?? null;
    this.fetch = fetchImpl ?? globalThis.fetch;
    if (typeof this.fetch !== "function") {
      throw new Error("fetch implementation is required");
    }
    this.headers = { ...(headers ?? {}) };
    if (requestedApiVersion) {
      this.headers["X-AgentGate-Requested-Version"] = requestedApiVersion;
    }
  }

  static fromEnv({ env = process.env, fetchImpl, headers } = {}) {
    const baseUrl = env.AGENTGATE_URL || "http://localhost:8000";
    return new AgentGateClient({
      baseUrl,
      apiKey: env.AGENTGATE_ADMIN_API_KEY,
      tenantId: env.AGENTGATE_TENANT_ID,
      requestedApiVersion: env.AGENTGATE_REQUESTED_API_VERSION,
      fetchImpl,
      headers,
    });
  }

  _buildHeaders({ apiKey, tenantId, extraHeaders, requireApiKey = false } = {}) {
    const headers = { ...this.headers, ...(extraHeaders ?? {}) };
    const resolvedApiKey = apiKey ?? this.apiKey;
    if (requireApiKey && !resolvedApiKey) {
      throw new Error("apiKey required for admin endpoint");
    }
    if (resolvedApiKey) {
      headers["X-API-Key"] = resolvedApiKey;
    }
    const resolvedTenant = tenantId ?? this.tenantId;
    if (resolvedTenant) {
      headers["X-AgentGate-Tenant-ID"] = resolvedTenant;
    }
    return headers;
  }

  async _request(method, path, { body, query, apiKey, tenantId, requireApiKey = false } = {}) {
    const url = new URL(`${this.baseUrl}${path}`);
    if (query) {
      for (const [key, value] of Object.entries(query)) {
        if (value !== undefined && value !== null) {
          url.searchParams.set(key, String(value));
        }
      }
    }
    const headers = this._buildHeaders({
      apiKey,
      tenantId,
      requireApiKey,
    });
    const payload = body === undefined ? undefined : JSON.stringify(body);
    if (payload !== undefined) {
      headers["content-type"] = "application/json";
    }

    const response = await this.fetch(url.toString(), {
      method,
      headers,
      body: payload,
    });

    const responseText = await response.text();
    let parsed = null;
    if (responseText) {
      try {
        parsed = JSON.parse(responseText);
      } catch {
        parsed = responseText;
      }
    }

    if (!response.ok) {
      throw new AgentGateApiError({
        method,
        path,
        statusCode: response.status,
        payload: parsed,
      });
    }
    if (parsed && typeof parsed === "object") {
      return parsed;
    }
    return {};
  }

  async health() {
    return this._request("GET", "/health");
  }

  async listTools({ sessionId }) {
    return this._request("GET", "/tools/list", {
      query: { session_id: sessionId },
    });
  }

  async callTool({ sessionId, toolName, arguments: args, approvalToken, context }) {
    const body = {
      session_id: sessionId,
      tool_name: toolName,
      arguments: args,
    };
    if (approvalToken !== undefined) {
      body.approval_token = approvalToken;
    }
    if (context !== undefined) {
      body.context = context;
    }
    return this._request("POST", "/tools/call", { body });
  }

  async killSession({ sessionId, reason }) {
    await this._request("POST", `/sessions/${sessionId}/kill`, {
      body: { reason: reason ?? null },
    });
  }

  async exportEvidence({ sessionId }) {
    return this._request("GET", `/sessions/${sessionId}/evidence`);
  }

  async createPolicyException({
    toolName,
    reason,
    expiresInSeconds,
    sessionId,
    tenantId,
    createdBy,
    apiKey,
  }) {
    const body = {
      tool_name: toolName,
      reason,
      expires_in_seconds: expiresInSeconds,
    };
    if (sessionId !== undefined) {
      body.session_id = sessionId;
    }
    if (tenantId !== undefined) {
      body.tenant_id = tenantId;
    }
    if (createdBy !== undefined) {
      body.created_by = createdBy;
    }
    return this._request("POST", "/admin/policies/exceptions", {
      body,
      apiKey,
      requireApiKey: true,
    });
  }

  async listPolicyExceptions({ includeInactive = false, apiKey } = {}) {
    return this._request("GET", "/admin/policies/exceptions", {
      query: { include_inactive: includeInactive },
      apiKey,
      requireApiKey: true,
    });
  }

  async revokePolicyException({ exceptionId, revokedBy, apiKey }) {
    const body = {};
    if (revokedBy !== undefined) {
      body.revoked_by = revokedBy;
    }
    return this._request(
      "POST",
      `/admin/policies/exceptions/${exceptionId}/revoke`,
      {
        body,
        apiKey,
        requireApiKey: true,
      }
    );
  }

  async createReplayRun({ payload, apiKey, tenantId }) {
    return this._request("POST", "/admin/replay/runs", {
      body: payload,
      apiKey,
      tenantId,
      requireApiKey: true,
    });
  }

  async releaseIncident({ incidentId, releasedBy, apiKey, tenantId }) {
    return this._request("POST", `/admin/incidents/${incidentId}/release`, {
      body: { released_by: releasedBy },
      apiKey,
      tenantId,
      requireApiKey: true,
    });
  }

  async startRollout({ tenantId, payload, apiKey }) {
    return this._request("POST", `/admin/tenants/${tenantId}/rollouts`, {
      body: payload,
      apiKey,
      requireApiKey: true,
    });
  }

  async getRolloutObservability({ tenantId, apiKey }) {
    return this._request(
      "GET",
      `/admin/tenants/${tenantId}/rollouts/observability`,
      {
        apiKey,
        requireApiKey: true,
      }
    );
  }
}

export default AgentGateClient;
