import { expect, test } from '@playwright/test';

const routes = ['/GET_STARTED/', '/HOSTED_SANDBOX/', '/REPLAY_LAB/', '/WORKSPACES/'];

test.describe('Docs Frontend Accessibility Journeys', () => {
  for (const route of routes) {
    test(`landmarks and headings are present: ${route}`, async ({ page }) => {
      await page.goto(route, { waitUntil: 'networkidle' });
      await expect(page.locator('main, [role="main"]').first()).toBeVisible();
      await expect(page.locator('h1').first()).toBeVisible();
      await expect(page.locator('#ag-command-launch')).toHaveAttribute('aria-label', /Quick actions/i);
    });
  }

  test('command palette announces dialog semantics', async ({ page }) => {
    await page.goto('/GET_STARTED/', { waitUntil: 'networkidle' });
    await page.locator('#ag-command-launch').click();
    await expect(page.locator('#ag-command-modal [role="dialog"]')).toHaveAttribute('aria-modal', 'true');
    await expect(page.locator('#ag-command-modal [role="dialog"]')).toHaveAttribute(
      'aria-labelledby',
      'ag-command-title',
    );
  });
});
