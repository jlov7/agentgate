import { expect, test, type Page } from '@playwright/test';

const routes = ['/', '/console', '/sessions/sess-containment-8241', '/policies', '/operations'];

function collectConsoleErrors(page: Page) {
  const errors: string[] = [];
  page.on('console', (message) => {
    if (message.type() === 'error') {
      errors.push(message.text());
    }
  });
  page.on('pageerror', (error) => errors.push(error.message));
  return errors;
}

async function gotoClean(page: Page, errors: string[], route: string) {
  errors.length = 0;
  await page.goto(route, { waitUntil: 'networkidle' });
  expect(errors).toEqual([]);
}

test.describe('AgentGate console frontend', () => {
  test('public front door exposes product-first CTAs', async ({ page }) => {
    const errors = collectConsoleErrors(page);
    await gotoClean(page, errors, '/');
    await expect(page.getByRole('heading', { name: /Stop unsafe tool calls/i })).toBeVisible();
    await expect(page.getByRole('link', { name: /Open console demo/i })).toBeVisible();
    await expect(page.getByRole('link', { name: /Read reference/i })).toBeVisible();
  });

  test('command center exposes sessions and command palette', async ({ page }) => {
    const errors = collectConsoleErrors(page);
    await gotoClean(page, errors, '/console');
    await expect(page.getByRole('heading', { name: /Containment cockpit/i })).toBeVisible();
    await expect(page.getByText('sess-containment-8241')).toBeVisible();

    await page.getByRole('button', { name: /Command K/i }).click();
    await expect(page.getByRole('dialog')).toBeVisible();
    await expect(page.getByPlaceholder(/Search sessions/i)).toBeVisible();
    await page.keyboard.press('Escape');
  });

  test('primary routes have no horizontal overflow', async ({ page }) => {
    const errors = collectConsoleErrors(page);
    for (const route of routes) {
      await gotoClean(page, errors, route);
      const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
      expect(overflow).toBeLessThanOrEqual(1);
    }
  });
});

test.describe('AgentGate console visual baselines', () => {
  for (const route of routes) {
    test(`visual baseline ${route}`, async ({ page }, testInfo) => {
      test.skip(testInfo.project.name !== 'console-chromium', 'visual snapshots are isolated to Chromium');
      await page.goto(route, { waitUntil: 'networkidle' });
      await page.addStyleTag({
        content: '*,:before,:after{animation:none !important;transition:none !important;scroll-behavior:auto !important;}',
      });
      await expect(page).toHaveScreenshot(`console${route.replaceAll('/', '_')}.png`, {
        fullPage: true,
      });
    });
  }
});
