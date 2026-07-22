import { expect, test } from '@playwright/test';

/**
 * UXR1 V2 Phase 2A — scoped shell + Dashboard smoke.
 */
const base = process.env.BASE_URL || 'http://localhost:3000';

async function login(page: import('@playwright/test').Page) {
  await page.goto(`${base}/login`);
  await page.locator('input[type="email"], input[name="email"]').first().fill('superadmin@investhome.demo');
  await page.locator('input[type="password"], input[name="password"]').first().fill('Demo123!');
  await page.locator('button[type="submit"]').first().click();
  await page.waitForURL(/dashboard/);
}

test.describe('UXR1 V2 Phase 2A', () => {
  test('Dashboard home activates V2 shell', async ({ page }) => {
    await login(page);
    await page.goto(`${base}/dashboard`);
    await expect(page.getByTestId('os-shell-v2')).toBeVisible({ timeout: 60_000 });
    await expect(page.getByTestId('dashboard-home-v2')).toBeVisible();
    await expect(page.locator('[data-ds-version="v2"]')).toHaveCount(1);
  });

  test('Executive G8 activates V2 shell and keeps widgets', async ({ page }) => {
    await login(page);
    await page.goto(`${base}/dashboard/executive`);
    await expect(page.getByTestId('os-shell-v2')).toBeVisible({ timeout: 60_000 });
    await expect(page.getByTestId('executive-dashboard-g8')).toBeVisible({ timeout: 60_000 });
    await expect(page.getByTestId('g8-kpi-strip')).toBeVisible();
    const ds = page.locator('[data-ds-version="v2"]');
    await expect(ds).toHaveCount(1);
  });

  test('Legacy CRM route does not activate V2 shell', async ({ page }) => {
    await login(page);
    // Prefer CRM leads if present; fall back to sales
    const crmRes = await page.goto(`${base}/dashboard/leads`);
    expect(crmRes?.ok() || crmRes?.status() === 200 || (crmRes?.status() ?? 500) < 500).toBeTruthy();
    await expect(page.getByTestId('os-shell-v2')).toHaveCount(0);
    await expect(page.getByTestId('os-shell')).toBeVisible({ timeout: 45_000 });
  });

  test('tablet executive has no horizontal overflow', async ({ page }) => {
    await login(page);
    await page.setViewportSize({ width: 1024, height: 900 });
    await page.goto(`${base}/dashboard/executive`);
    await expect(page.getByTestId('executive-dashboard-g8')).toBeVisible({ timeout: 60_000 });
    const overflow = await page.evaluate(
      () => document.documentElement.scrollWidth > document.documentElement.clientWidth + 2,
    );
    expect(overflow).toBeFalsy();
  });
});
