import { test, expect, loginAs, DEMO_USERS } from './fixtures';

test.describe('UXR1 V2 Phase 2A', () => {
  test('Dashboard home activates V2 shell', async ({ page }) => {
    await loginAs(page, DEMO_USERS.superadmin);
    const response = await page.goto('/dashboard');
    expect(response?.status()).toBe(200);
    await expect(page.getByTestId('os-shell-v2')).toBeVisible({ timeout: 60_000 });
    await expect(page.getByTestId('dashboard-home-v2')).toBeVisible();
    await expect(page.locator('[data-ds-version="v2"]')).toHaveCount(1);
  });

  test('Executive G8 activates V2 shell and widgets', async ({ page }) => {
    await loginAs(page, DEMO_USERS.superadmin);
    const response = await page.goto('/dashboard/executive');
    expect(response?.status()).toBe(200);
    await expect(page.getByTestId('os-shell-v2')).toBeVisible({ timeout: 60_000 });
    await expect(page.getByTestId('executive-dashboard-g8')).toBeVisible({ timeout: 60_000 });
    await expect(page.getByTestId('g8-kpi-strip')).toBeVisible();
  });

  test('Legacy leads route does not activate V2 shell', async ({ page }) => {
    await loginAs(page, DEMO_USERS.superadmin);
    const response = await page.goto('/dashboard/leads');
    expect(response?.ok()).toBeTruthy();
    await expect(page.getByTestId('os-shell-v2')).toHaveCount(0);
    await expect(page.getByTestId('os-shell')).toBeVisible({ timeout: 45_000 });
  });

  test('tablet executive has no horizontal overflow', async ({ page }) => {
    await loginAs(page, DEMO_USERS.superadmin);
    await page.setViewportSize({ width: 1024, height: 900 });
    await page.goto('/dashboard/executive');
    await expect(page.getByTestId('executive-dashboard-g8')).toBeVisible({ timeout: 60_000 });
    const overflow = await page.evaluate(
      () => document.documentElement.scrollWidth > document.documentElement.clientWidth + 2,
    );
    expect(overflow).toBe(false);
  });
});
