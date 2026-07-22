import { test, expect } from '@playwright/test';

test.describe('Marketing G6 workspace', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/login');
    await page.locator('input[type="email"], input[name="email"]').first().fill('superadmin@investhome.demo');
    await page.locator('input[type="password"], input[name="password"]').first().fill('Demo123!');
    await page.locator('button[type="submit"]').first().click();
    await page.waitForURL(/dashboard/);
  });

  test('opens overview and campaigns drawer', async ({ page }) => {
    await page.goto('/dashboard/marketing');
    await expect(page.getByTestId('mkt-g6-workspace')).toBeVisible();
    await expect(page.getByTestId('mkt-g6-overview')).toBeVisible({ timeout: 45_000 });

    await page.goto('/dashboard/marketing?view=campaigns');
    await expect(page.getByTestId('mkt-g6-campaigns')).toBeVisible({ timeout: 45_000 });
    const row = page.locator('[data-testid^="mkt-g6-campaign-row-"], [data-testid^="mkt-g6-campaign-card-"]').first();
    await row.click();
    await expect(page.getByTestId('mkt-g6-drawer')).toBeVisible();
  });

  test('provider disclosure on seo and paid ads', async ({ page }) => {
    await page.goto('/dashboard/marketing?view=seo');
    await expect(page.getByTestId('mkt-g6-seo')).toBeVisible({ timeout: 45_000 });
    await expect(page.locator('.mkt-g6__data-tag--blocked').first()).toBeVisible();

    await page.goto('/dashboard/marketing?view=paid_ads');
    await expect(page.getByTestId('mkt-g6-paid-ads')).toBeVisible({ timeout: 45_000 });
  });
});
