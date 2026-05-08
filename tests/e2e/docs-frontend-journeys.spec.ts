import { expect, test } from '@playwright/test';

async function openQuickActions(page: import('@playwright/test').Page): Promise<void> {
  await page.goto('/GET_STARTED/', { waitUntil: 'networkidle' });
  await page.locator('#ag-command-launch').click();
  await expect(page.locator('#ag-command-modal')).toHaveClass(/ag-command-modal--open/);
}

test.describe('Docs Frontend Journeys', () => {
  test('quick actions modal supports focus trap and escape/backdrop close', async ({ page }) => {
    await openQuickActions(page);

    await expect(page.locator('#ag-command-modal')).toBeVisible();
    await expect(page.locator('#ag-command-modal [role="dialog"]')).toBeVisible();
    await expect(page.locator('#ag-command-launch')).toHaveAttribute('aria-expanded', 'true');

    await page.keyboard.press('Tab');
    await page.keyboard.press('Tab');
    await page.keyboard.press('Escape');

    await expect(page.locator('#ag-command-modal')).toBeHidden();
    await expect(page.locator('#ag-command-launch')).toBeFocused();
    await expect(page.locator('#ag-command-launch')).toHaveAttribute('aria-expanded', 'false');

    await openQuickActions(page);
    await page.locator('#ag-command-modal .ag-command-overlay').click({ position: { x: 8, y: 8 } });
    await expect(page.locator('#ag-command-modal')).toBeHidden();
  });

  test('workspace persona tabs are keyboard navigable', async ({ page }) => {
    await page.goto('/WORKSPACES/', { waitUntil: 'networkidle' });

    const tablist = page.locator('[role="tablist"]').first();
    await expect(tablist).toBeVisible();

    const first = tablist.locator('[role="tab"]').first();
    const second = tablist.locator('[role="tab"]').nth(1);
    await first.focus();
    await page.keyboard.press('ArrowRight');

    await expect(second).toBeFocused();
    await expect(second).toHaveAttribute('aria-selected', 'true');
  });

  test('core empty/loading/error copy is actionable', async ({ page }) => {
    await page.goto('/HOSTED_SANDBOX/', { waitUntil: 'networkidle' });
    await expect(page.getByText('No runs yet. Execute a flow to capture trial evidence.')).toBeVisible();

    await page.goto('/REPLAY_LAB/', { waitUntil: 'networkidle' });
    await expect(page.getByText('Use the stepper to review each decision point before promotion.')).toBeVisible();

    await page.goto('/404.html', { waitUntil: 'networkidle' });
    await expect(page.getByRole('heading', { name: /Page not found/i })).toBeVisible();
    await expect(page.getByRole('link', { name: /Go to Home/i })).toBeVisible();
  });
});
