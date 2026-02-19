import assert from "node:assert/strict";
import test from "node:test";

import { AgentGateApiError, AgentGateClient } from "../src/index.js";

function jsonResponse(payload, status = 200) {
  return new Response(JSON.stringify(payload), {
    status,
    headers: { "content-type": "application/json" },
  });
}

test("uses configured api key for admin policy-exception endpoints", async () => {
  const calls = [];
  const fetchImpl = async (url, init) => {
    calls.push({ url, init });
    if (url.endsWith("/admin/policies/exceptions") && init.method === "POST") {
      return jsonResponse({ exception_id: "pex-1", status: "active" });
    }
    if (url.includes("/admin/policies/exceptions/pex-1/revoke")) {
      return jsonResponse({ exception_id: "pex-1", status: "revoked" });
    }
    return jsonResponse({ exceptions: [] });
  };

  const client = new AgentGateClient({
    baseUrl: "http://agentgate.test",
    apiKey: "admin-key",
    fetchImpl,
  });

  const created = await client.createPolicyException({
    toolName: "db_insert",
    reason: "maintenance",
    expiresInSeconds: 120,
    sessionId: "sess-1",
  });
  assert.equal(created.status, "active");

  const revoked = await client.revokePolicyException({ exceptionId: "pex-1" });
  assert.equal(revoked.status, "revoked");

  assert.equal(calls.length, 2);
  assert.equal(calls[0].init.headers["X-API-Key"], "admin-key");
  assert.equal(calls[1].init.headers["X-API-Key"], "admin-key");
});

test("supports fromEnv bootstrap with default headers", async () => {
  const fetchImpl = async (url, init) => {
    assert.equal(url, "http://agentgate.local/health");
    assert.equal(init.headers["X-AgentGate-Requested-Version"], "v1");
    return jsonResponse({ status: "ok" });
  };

  const client = AgentGateClient.fromEnv({
    env: {
      AGENTGATE_URL: "http://agentgate.local",
      AGENTGATE_REQUESTED_API_VERSION: "v1",
      AGENTGATE_ADMIN_API_KEY: "env-admin-key",
    },
    fetchImpl,
  });

  const health = await client.health();
  assert.equal(health.status, "ok");
});

test("raises structured API error payload", async () => {
  const fetchImpl = async () =>
    jsonResponse(
      {
        error: "Unsupported API version",
        supported_versions: ["v1"],
      },
      400
    );

  const client = new AgentGateClient({
    baseUrl: "http://agentgate.local",
    requestedApiVersion: "v2",
    fetchImpl,
  });

  await assert.rejects(
    async () => {
      await client.health();
    },
    (error) => {
      assert.ok(error instanceof AgentGateApiError);
      assert.equal(error.statusCode, 400);
      assert.equal(error.payload.error, "Unsupported API version");
      return true;
    }
  );
});

test("adds tenant and includeInactive query params", async () => {
  const fetchImpl = async (url, init) => {
    const parsed = new URL(url);
    assert.equal(parsed.searchParams.get("include_inactive"), "true");
    assert.equal(init.headers["X-AgentGate-Tenant-ID"], "tenant-a");
    return jsonResponse({ exceptions: [] });
  };

  const client = new AgentGateClient({
    baseUrl: "http://agentgate.local",
    apiKey: "admin-key",
    tenantId: "tenant-a",
    fetchImpl,
  });

  const result = await client.listPolicyExceptions({ includeInactive: true });
  assert.deepEqual(result, { exceptions: [] });
});
