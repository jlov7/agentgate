// spec: specs/e2e-plan.md
// seed: seed.spec.ts

import { test, expect } from '@playwright/test';
import { waitForHealthy } from './_helpers';

test.describe('Documentation & Health', () => {
  test('Load Swagger UI', async ({ page, request }) => {
    // 1. Open `/docs`
    await waitForHealthy(request);
    await page.goto('/docs', { waitUntil: 'domcontentloaded' });

    // 2. Wait for the Swagger UI container to render
    await expect(page.locator('#swagger-ui')).toBeVisible();

    // 3. Confirm the API title includes "AgentGate"
    await expect(page.getByText('AgentGate', { exact: false }).first()).toBeVisible();
  });

  test('Load ReDoc', async ({ page, request }) => {
    // 1. Open `/redoc`
    await waitForHealthy(request);
    await page.goto('/redoc', { waitUntil: 'domcontentloaded' });

    // 2. Wait for ReDoc content to render
    await expect(page.getByRole('heading', { name: /AgentGate/i }).first()).toBeVisible();
  });
});
