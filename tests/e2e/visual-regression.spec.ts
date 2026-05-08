import { expect, test } from '@playwright/test';

const routes = ['/', '/GET_STARTED/', '/HOSTED_SANDBOX/', '/DEMO_LAB/', '/REPLAY_LAB/', '/INCIDENT_RESPONSE/', '/TENANT_ROLLOUTS/'];

test.describe('UX Visual Regression (Docs Journeys)', () => {
  for (const route of routes) {
    test(`visual baseline ${route}`, async ({ page }) => {
      await page.goto(route, { waitUntil: 'networkidle' });
      await page.addStyleTag({
        content:
          '*,:before,:after{animation:none !important;transition:none !important;scroll-behavior:auto !important;}',
      });
      await page.waitForTimeout(120);
      await expect(page).toHaveScreenshot(route.replaceAll('/', '_') + '.png', {
        fullPage: true,
      });
    });
  }
});
