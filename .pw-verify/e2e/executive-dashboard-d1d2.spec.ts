import { test, expect, type Page } from '@playwright/test';

const DEMO_PASSWORD = 'Demo123!';
const DEMO_USERS = {
  superadmin: 'superadmin@investhome.demo',
  sales: 'sales@investhome.demo',
} as const;

async function loginAs(page: Page, email: string, password = DEMO_PASSWORD) {
  await page.goto('/login');
  await page.fill('input[type="email"]', email);
  await page.fill('input[type="password"]', password);
  await page.click('button[type="submit"]');
  await expect(page.locator('.dashboard-shell')).toBeVisible({ timeout: 45_000 });
}

test.describe('D1D.2 executive dashboard recovery', () => {
  test('prototype returns 200 for admin', async ({ page }) => {
    await loginAs(page, DEMO_USERS.superadmin);
    const response = await page.goto('/dashboard/admin/design-system/executive-dashboard');
    expect(response?.status()).toBe(200);
    await expect(page.getByTestId('executive-dashboard-prototype')).toBeVisible();
    await expect(page.getByTestId('exec-proto-marketing-widget')).toBeVisible();
    await expect(page.getByTestId('exec-proto-tasks-widget')).toBeVisible();
    await expect(page.getByTestId('exec-proto-calendar-widget')).toBeVisible();
    await expect(page.getByTestId('exec-proto-ai-widget')).toBeVisible();
    await expect(page.getByTestId('exec-proto-comms-widget')).toBeVisible();
  });

  test('prototype redirects non-admin away', async ({ page }) => {
    await loginAs(page, DEMO_USERS.sales);
    await page.goto('/dashboard/admin/design-system/executive-dashboard');
    await expect(page).toHaveURL(/\/forbidden|\/dashboard(?!\/admin\/design-system)/, {
      timeout: 30_000,
    });
    await expect(page.getByTestId('executive-dashboard-prototype')).toHaveCount(0);
  });

  test('production defaults to new D1D dashboard', async ({ page }) => {
    await loginAs(page, DEMO_USERS.superadmin);
    const response = await page.goto('/dashboard/executive');
    expect(response?.status()).toBe(200);
    await expect(page.getByTestId('executive-dashboard-production')).toBeVisible();
    await expect(page.getByTestId('executive-dashboard-legacy')).toHaveCount(0);
    await expect(page.getByTestId('exec-prod-kpi-strip')).toBeVisible();
    await expect(page.getByTestId('exec-prod-marketing-widget')).toBeVisible();
    await expect(page.getByTestId('exec-prod-tasks-widget')).toBeVisible();
    await expect(page.getByTestId('exec-prod-calendar-widget')).toBeVisible();
    await expect(page.getByTestId('exec-prod-ai-widget')).toBeVisible();
    await expect(page.getByTestId('exec-prod-comms-widget')).toBeVisible();
  });

  test('legacy query shows old dashboard only', async ({ page }) => {
    await loginAs(page, DEMO_USERS.superadmin);
    const response = await page.goto('/dashboard/executive?view=legacy');
    expect(response?.status()).toBe(200);
    await expect(page.getByTestId('executive-dashboard-legacy')).toBeVisible();
    await expect(page.getByTestId('executive-dashboard-production')).toHaveCount(0);
  });

  test('unknown view falls back to new dashboard', async ({ page }) => {
    await loginAs(page, DEMO_USERS.superadmin);
    await page.goto('/dashboard/executive?view=not-a-real-view');
    await expect(page.getByTestId('executive-dashboard-production')).toBeVisible();
    await expect(page.getByTestId('executive-dashboard-legacy')).toHaveCount(0);
  });

  test('mobile has no horizontal overflow on production', async ({ page }) => {
    await loginAs(page, DEMO_USERS.superadmin);
    await page.setViewportSize({ width: 390, height: 844 });
    await page.goto('/dashboard/executive');
    await expect(page.getByTestId('executive-dashboard-production')).toBeVisible();
    const overflow = await page.evaluate(
      () => document.documentElement.scrollWidth > document.documentElement.clientWidth + 2,
    );
    expect(overflow).toBe(false);
  });
});
