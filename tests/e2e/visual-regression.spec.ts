import { expect, test } from '@playwright/test';

// Visual-regression baseline for critical UX journeys.
// This suite stays skipped in API-doc CI because mkdocs journey routes are not served by the API web server.
// Run manually against a docs host with: PLAYWRIGHT_BASE_URL=<docs-url> npx playwright test tests/e2e/visual-regression.spec.ts

test.describe.skip('UX Visual Regression (Docs Journeys)', () => {
  const routes = [
    '/HOSTED_SANDBOX/',
    '/DEMO_LAB/',
    '/REPLAY_LAB/',
    '/INCIDENT_RESPONSE/',
    '/TENANT_ROLLOUTS/',
  ];

  for (const route of routes) {
    test(`visual baseline ${route}`, async ({ page }) => {
      await page.goto(route, { waitUntil: 'domcontentloaded' });
      await expect(page).toHaveScreenshot(route.replaceAll('/', '_') + '.png', {
        fullPage: true,
      });
    });
  }
});
