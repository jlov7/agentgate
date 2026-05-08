import { expect, test } from '@playwright/test';

const TOUCH_TARGET_SELECTOR = '.ag-btn, .ag-lab-chip, .ag-command-link, .ag-workflow-step';

test.describe('Docs Frontend Mobile Geometry', () => {
  test('mobile journeys avoid horizontal overflow and preserve touch target size', async ({ page }) => {
    await page.goto('/GET_STARTED/', { waitUntil: 'networkidle' });

    const noOverflow = await page.evaluate(() => {
      const doc = document.documentElement;
      return doc.scrollWidth <= window.innerWidth + 1;
    });
    expect(noOverflow).toBeTruthy();

    const smallTargets = await page.evaluate((selector) => {
      const nodes = Array.from(document.querySelectorAll<HTMLElement>(selector));
      return nodes
        .map((node) => {
          const rect = node.getBoundingClientRect();
          return {
            text: (node.textContent || '').trim().slice(0, 48),
            width: rect.width,
            height: rect.height,
          };
        })
        .filter((entry) => entry.width > 0 && entry.height > 0)
        .filter((entry) => entry.width < 44 || entry.height < 44);
    }, TOUCH_TARGET_SELECTOR);

    expect(smallTargets, JSON.stringify(smallTargets, null, 2)).toEqual([]);
  });

  test('floating quick actions button remains visible in safe area', async ({ page }) => {
    await page.goto('/HOSTED_SANDBOX/', { waitUntil: 'networkidle' });
    const launch = page.locator('#ag-command-launch');
    await expect(launch).toBeVisible();

    const box = await launch.boundingBox();
    const viewport = page.viewportSize();
    expect(box).not.toBeNull();
    expect(viewport).not.toBeNull();

    if (box && viewport) {
      expect(box.y + box.height).toBeLessThanOrEqual(viewport.height);
      expect(box.x + box.width).toBeLessThanOrEqual(viewport.width);
    }
  });
});
