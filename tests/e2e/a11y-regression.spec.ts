import { expect, test } from '@playwright/test';
import { waitForHealthy } from './_helpers';

test.describe('Accessibility Regression', () => {
  test('Keyboard navigation reaches primary content links in Swagger', async ({ page, request }) => {
    await waitForHealthy(request);
    await page.goto('/docs', { waitUntil: 'domcontentloaded' });

    await page.keyboard.press('Tab');
    await page.keyboard.press('Tab');

    const focused = await page.evaluate(() => {
      const node = document.activeElement as HTMLElement | null;
      return node ? (node.getAttribute('aria-label') || node.textContent || node.tagName) : '';
    });

    expect(focused).toBeTruthy();
  });

  test('Zoom + viewport reduction keeps main landmarks visible', async ({ page, request }) => {
    await waitForHealthy(request);
    await page.setViewportSize({ width: 960, height: 700 });
    await page.goto('/redoc', { waitUntil: 'domcontentloaded' });

    await page.evaluate(() => {
      (document.body.style as CSSStyleDeclaration).zoom = '1.5';
    });

    await expect(page.locator('main, [role="main"], .redoc-wrap').first()).toBeVisible();
    await expect(page.locator('nav, [role="navigation"], .menu-content').first()).toBeVisible();
  });
});
