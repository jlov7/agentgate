// spec: specs/e2e-plan.md
// seed: seed.spec.ts

import { test, expect } from '@playwright/test';
import { waitForHealthy } from './_helpers';

test.describe('Negative & Edge Scenarios', () => {
  test('Missing required fields (422)', async ({ request }) => {
    // 1. Send `POST /tools/call` with an empty JSON body
    await waitForHealthy(request);
    const response = await request.post('/tools/call', { data: {} });

    // Expected: Request fails with HTTP 422 validation error.
    expect(response.status()).toBe(422);
  });

  test('Invalid tool name characters', async ({ request }) => {
    // 1. Send `POST /tools/call` with `tool_name` containing `/` or spaces
    await waitForHealthy(request);
    const response = await request.post('/tools/call', {
      data: {
        session_id: 'e2e-invalid-tool-name',
        tool_name: 'bad/name',
        arguments: { query: 'SELECT 1' },
      },
    });

    // Expected: Response indicates denial due to invalid tool name.
    expect(response.status()).toBe(200);
    const body = await response.json();
    expect(body.success).toBe(false);
    expect(body.error).toContain('Invalid tool name');
  });

  test('Unknown tool denied', async ({ request }) => {
    // 1. Send `POST /tools/call` with `tool_name=unknown_tool`
    await waitForHealthy(request);
    const response = await request.post('/tools/call', {
      data: {
        session_id: 'e2e-unknown-tool',
        tool_name: 'unknown_tool',
        arguments: {},
      },
    });

    // Expected: Response indicates the tool is not in the allowlist.
    const body = await response.json();
    expect(body.success).toBe(false);
    expect(body.error).toContain('allowlist');
  });

  test('Write tool without approval', async ({ request }) => {
    // 1. Send `POST /tools/call` for `db_update` without `approval_token`
    await waitForHealthy(request);
    const response = await request.post('/tools/call', {
      data: {
        session_id: 'e2e-write-no-approval',
        tool_name: 'db_update',
        arguments: { table: 'widgets' },
      },
    });

    // Expected: Response indicates approval is required.
    const body = await response.json();
    expect(body.success).toBe(false);
    expect(body.error).toContain('Approval required');
  });

  test('Rate limit exceeded', async ({ request }) => {
    // 1. Send 11 calls to `rate_limited_tool` in the same session
    await waitForHealthy(request);
    const sessionId = 'e2e-rate-limit';
    const responses = [];

    for (let i = 0; i < 11; i += 1) {
      const response = await request.post('/tools/call', {
        data: {
          session_id: sessionId,
          tool_name: 'rate_limited_tool',
          arguments: { seq: i },
        },
      });
      responses.push(await response.json());
    }

    // Expected: At least one response indicates rate limit exceeded.
    const denied = responses.some(
      (body) => body.success === false && String(body.error).includes('Rate limit'),
    );
    expect(denied).toBe(true);
  });

  test('Request body too large (413)', async ({ request }) => {
    // 1. Send `POST /tools/call` with a payload larger than 1MB
    await waitForHealthy(request);
    const oversized = 'a'.repeat(1024 * 1024 + 200);
    const response = await request.post('/tools/call', {
      data: {
        session_id: 'e2e-too-large',
        tool_name: 'db_query',
        arguments: { query: oversized },
      },
    });

    // Expected: Request rejected with HTTP 413.
    expect(response.status()).toBe(413);
  });

  test('Killed session blocks tool calls (expired session)', async ({ request }) => {
    // 1. Send `POST /sessions/{id}/kill`
    await waitForHealthy(request);
    const sessionId = 'e2e-killed-session';
    const killResponse = await request.post(`/sessions/${sessionId}/kill`, {
      data: { reason: 'expired' },
    });
    expect(killResponse.status()).toBe(200);

    // 2. Send `POST /tools/call` using the killed `session_id`
    const response = await request.post('/tools/call', {
      data: {
        session_id: sessionId,
        tool_name: 'db_query',
        arguments: { query: 'SELECT 1' },
      },
    });

    // Expected: Tool call is denied due to kill switch.
    const body = await response.json();
    expect(body.success).toBe(false);
    expect(body.error).toContain('Kill switch');
  });

  test('Global pause blocks tool calls', async ({ request }) => {
    // 1. Send `POST /system/pause`
    await waitForHealthy(request);
    const pauseResponse = await request.post('/system/pause', {
      data: { reason: 'maintenance' },
    });
    expect(pauseResponse.status()).toBe(200);

    try {
      // 2. Send `POST /tools/call` with any tool
      const response = await request.post('/tools/call', {
        data: {
          session_id: 'e2e-global-pause',
          tool_name: 'db_query',
          arguments: { query: 'SELECT 1' },
        },
      });

      // Expected: Tool call is denied while paused.
      const body = await response.json();
      expect(body.success).toBe(false);
      expect(body.error).toContain('Kill switch');
    } finally {
      // 3. Send `POST /system/resume`
      const resumeResponse = await request.post('/system/resume');
      expect(resumeResponse.status()).toBe(200);
    }
  });

  test('Invalid admin API key', async ({ request }) => {
    // 1. Send `POST /admin/policies/reload` with wrong `X-API-Key`
    await waitForHealthy(request);
    const response = await request.post('/admin/policies/reload', {
      headers: {
        'X-API-Key': 'wrong-key',
      },
    });

    // Expected: Request rejected with HTTP 403.
    expect(response.status()).toBe(403);
  });

  test('Network failure to API host', async ({ playwright }) => {
    // 1. Send `GET /health` using an invalid base URL
    const badContext = await playwright.request.newContext({
      baseURL: 'http://127.0.0.1:9',
    });

    await expect(badContext.get('/health')).rejects.toThrow();
    await badContext.dispose();
  });

  test('Invalid evidence format returns 400', async ({ request }) => {
    await waitForHealthy(request);
    const response = await request.get('/sessions/e2e-invalid-format/evidence?format=htm');

    expect(response.status()).toBe(400);
    const body = await response.json();
    expect(body.error).toContain('Invalid format');
  });
});
