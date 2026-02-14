import { expect, test } from '@playwright/test';
import { waitForHealthy } from './_helpers';

test.describe('Accessibility Smoke', () => {
  test('Swagger UI exposes basic title and landmarks', async ({ page, request }) => {
    await waitForHealthy(request);
    await page.goto('/docs', { waitUntil: 'domcontentloaded' });

    await expect(page).toHaveTitle(/AgentGate/i);
    await expect(page.locator('main, [role="main"], #swagger-ui').first()).toBeVisible();
    await expect(page.locator('nav, [role="navigation"], .ag-docs-nav').first()).toBeVisible();
  });

  test('ReDoc exposes basic title and landmarks', async ({ page, request }) => {
    await waitForHealthy(request);
    await page.goto('/redoc', { waitUntil: 'domcontentloaded' });

    await expect(page).toHaveTitle(/AgentGate/i);
    await expect(page.locator('main, [role="main"], .redoc-wrap').first()).toBeVisible();
    await expect(page.locator('nav, [role="navigation"], .menu-content').first()).toBeVisible();
  });
});
