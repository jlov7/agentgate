// spec: specs/e2e-plan.md
// seed: seed.spec.ts

import { test, expect } from '@playwright/test';
import { waitForHealthy } from './_helpers';

test.describe('Core Tool Flows', () => {
  test('Health check returns ok', async ({ request }) => {
    // 1. Send `GET /health`
    await waitForHealthy(request);
    const response = await request.get('/health');

    // 2. Confirm status is `200`
    expect(response.status()).toBe(200);

    // 3. Verify `status` is `ok`, `opa` is `true`, `redis` is `true`
    const body = await response.json();
    expect(body).toMatchObject({ status: 'ok', opa: true, redis: true });
  });

  test('List allowed tools', async ({ request }) => {
    // 1. Send `GET /tools/list?session_id=e2e-happy-tools`
    await waitForHealthy(request);
    const response = await request.get('/tools/list?session_id=e2e-happy-tools');

    // 2. Confirm status is `200`
    expect(response.status()).toBe(200);

    // 3. Verify `db_query` appears in the tool list
    const body = await response.json();
    expect(body.tools).toContain('db_query');
  });

  test('Allowed read-only tool call', async ({ request }) => {
    // 1. Send `POST /tools/call` for `db_query`
    await waitForHealthy(request);
    const response = await request.post('/tools/call', {
      data: {
        session_id: 'e2e-read-only',
        tool_name: 'db_query',
        arguments: { query: 'SELECT * FROM widgets LIMIT 1' },
      },
    });

    // 2. Provide a `session_id` and query arguments
    expect(response.status()).toBe(200);

    // 3. Confirm the response indicates `success: true`
    const body = await response.json();
    expect(body.success).toBe(true);
    expect(body.result?.rows?.length).toBeGreaterThan(0);
  });

  test('Approved write tool call', async ({ request }) => {
    // 1. Send `POST /tools/call` for `db_update` with `approval_token=approved`
    await waitForHealthy(request);
    const response = await request.post('/tools/call', {
      data: {
        session_id: 'e2e-approved-write',
        tool_name: 'db_update',
        approval_token: 'approved',
        arguments: { table: 'widgets' },
      },
    });

    // 2. Provide a `session_id`
    expect(response.status()).toBe(200);

    // 3. Confirm the response indicates `success: true`
    const body = await response.json();
    expect(body.success).toBe(true);
    expect(body.result?.updated).toBe(1);
  });

  test('Session appears after tool call', async ({ request }) => {
    // 1. Send `POST /tools/call` for `db_query` with a new `session_id`
    await waitForHealthy(request);
    const sessionId = 'e2e-session-trace';
    await request.post('/tools/call', {
      data: {
        session_id: sessionId,
        tool_name: 'db_query',
        arguments: { query: 'SELECT * FROM widgets LIMIT 1' },
      },
    });

    // 2. Send `GET /sessions`
    const response = await request.get('/sessions');

    // 3. Verify the session id appears in the list
    const body = await response.json();
    expect(body.sessions).toContain(sessionId);
  });

  test('Export evidence pack (JSON)', async ({ request }) => {
    // 1. Send `POST /tools/call` for `db_query` with a new `session_id`
    await waitForHealthy(request);
    const sessionId = 'e2e-evidence-json';
    await request.post('/tools/call', {
      data: {
        session_id: sessionId,
        tool_name: 'db_query',
        arguments: { query: 'SELECT * FROM widgets LIMIT 1' },
      },
    });

    // 2. Send `GET /sessions/{session_id}/evidence`
    const response = await request.get(`/sessions/${sessionId}/evidence`);

    // 3. Verify `metadata.session_id` matches the session
    const body = await response.json();
    expect(body.metadata?.session_id).toBe(sessionId);
  });
});
